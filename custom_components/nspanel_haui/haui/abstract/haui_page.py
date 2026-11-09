"""Represents a page on the Nextion display."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeGuard

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import NotifEvent, PopupPanelKey
from ..utils.text import TextBox, fit_line, text_width
from .mixins.component_mixin import ComponentMixin
from .mixins.function_btn_mixin import FunctionButtonMixin
from .mixins.touch_input_mixin import TouchInputMixin

# entity_map() key of the panel's main entity; Nextion widget names cannot hold "#".
PAGE_ENTITY_KEY = "#page"


class HAUIPage(TouchInputMixin, FunctionButtonMixin, ComponentMixin, HAUIBase):
    """Represents a page on the nextion display.

    Every page on the display needs a page defined here to
    be able to interact with the components.

    - Process events on page
    - Render panel on page
    - Main logic for panels
    """

    COMPONENTS: ClassVar[ComponentRegistry] = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
    )

    # Pages with non-standard color palettes (about, clock, clocktwo, weather)
    # should set this to ``False`` so user-defined color overrides are bypassed
    # and the page's built-in palette is used instead.
    USE_SYSTEM_COLORS: ClassVar[bool] = True

    # The header title widget (``tTitle``) as the HMIs define it, per
    # orientation.  A page whose title widget differs overrides these.
    TITLE_BOX: ClassVar[dict[str, TextBox]] = {
        "landscape": TextBox(250, 50, 2, 40),
        "portrait": TextBox(320, 50, 2, 40),
    }
    TITLE_FONT: ClassVar[int] = 1

    # Popup opened by execute_item() for an entity domain when the item has no
    # ``popup_key``.  popup_timer has no domain (the timer is display-local);
    # items reach it through ``popup_key``.  mapping/panel.py derives the popup
    # aliases of the domain pages from it.
    DEFAULT_POPUPS: ClassVar[dict[str, str]] = {
        "light": PopupPanelKey.POPUP_LIGHT,
        "media_player": PopupPanelKey.POPUP_MEDIA_PLAYER,
        "vacuum": PopupPanelKey.POPUP_VACUUM,
        "cover": PopupPanelKey.POPUP_COVER,
        "climate": PopupPanelKey.POPUP_CLIMATE,
        "alarm_control_panel": PopupPanelKey.POPUP_ALARM,
    }

    # item options a popup keeps from the item that opened it
    _POPUP_ITEM_OVERRIDES = ("name", "icon", "color", "value", "state")

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        super().__init__(app, config)
        self.page_id = int(self.get("page_id"))
        # current panel
        self.panel: HAUIPanel | None = None
        # what prepare_page_load() sent ahead of the page switch
        self._load_commands: list[str] | None = None
        # function items, components
        self._fnc_items: dict = {}
        # function button inverse lookup: comp_id -> fnc_id
        self._fnc_id_by_component: dict[int, str] = {}
        # item state listener handles, with their metadata for debugging
        self._handles: list[str] = []
        self._listener_meta: dict[str, dict] = {}
        self._init_touch_input()
        # subclass init hook
        self.prepare()

    def prepare(self) -> None:
        """Initialize page instance attributes.

        Override this instead of ``__init__`` to set default attribute
        values.  Called automatically after the base class constructor
        runs.  No need to call ``super().prepare()`` — the base
        implementation is a no-op.
        """

    # part

    def stop_part(self) -> None:
        """Stops of part.

        This is called when the part is stopped.
        """
        self._reset_touch_input()
        self.set_panel(None)

    # panel lifecycle

    def set_panel(self, panel: HAUIPanel | None) -> None:
        """Sets a panel for the page.

        This is used to set a panel for current page.
        The panel is set to the page and the panel is then being rendered.

        Args:
            panel (HAUIPanel): The panel to set.
        """
        from ..mapping.panel import PAGE_MAPPING

        # prepare panel
        if self.panel is not None:
            self.stop_panel(self.panel)
        self.panel = panel
        if panel is None:
            self.log(f"Page {PAGE_MAPPING.get(self.page_id)} | closed")
            return
        panel_key = panel.get("key", "")
        panel_type = panel.get_type()
        self.log(f"Page {PAGE_MAPPING.get(self.page_id)} | Panel: {panel_key} ({panel_type})")

        # Batch ALL commands from start_panel, config_panel, and render_panel
        # into a single send_commands call so the ESP32 receives them as one
        # ESPHome service call.  Multiple rapid-fire service calls can overflow
        # the Nextion's serial buffer before the display finishes processing.
        # rec_cmd is re-entrant, so inner rec_cmd blocks in config_panel and
        # render_panel are absorbed into this outer batch.
        rendered = False
        self._fnc_items = {}
        with self.rec_cmd:
            self.start_panel(panel)

            # call config for panel
            self.config_panel(panel)
            # call before render for panel
            if self.before_render_panel(panel):
                self.log(
                    f"Rendering panel {panel.id}",
                    level="DEBUG",
                )
                # Render function components (init vis/color/text) and the
                # panel's display content in one batch so the dedup logic
                # collapses redundant writes — e.g. ``vis x,0`` from an
                # ``update_function_component`` followed by ``vis x,1``
                # from ``render_panel`` becomes a single ``vis x,1``.
                self._render_function_components()
                self.render_panel(panel)
                rendered = True

        # call after render for panel
        self.after_render_panel(panel, rendered)

    def refresh_panel(self) -> None:
        """Refreshes the current panel.

        This gives the possibility to update the panel.
        """
        if self.panel is None:
            return
        self.log(
            f"Refreshing panel {self.panel.id}",
            level="DEBUG",
        )
        with self.rec_cmd:
            self.render_panel(self.panel)

    def _render_function_components(self) -> None:
        """Send the current state of all registered function components.

        All components are rendered (including hidden ones) so that same-page
        panel transitions correctly hide components that were visible in the
        previous panel. Batch dedup collapses hide-then-show sequences to show.
        """
        for fnc_id in self._fnc_items:
            self.update_function_component(fnc_id)

    def page_load_commands(self, panel: HAUIPanel) -> list[str]:
        """The commands the display reads while it loads this page for ``panel``.

        The display runs a page's Preinitialize code before it draws the page:
        the solid-colour pages paint themselves from the theme globals there.
        A page whose load code reads more (a picture background) extends this.

        Args:
            panel (HAUIPanel): Panel the page is loaded for
        """
        # The device's theme, not get_color(): own-palette pages read none of
        # it, and the globals outlive this page on the display.
        return self.app.color_theme.display_commands()

    def prepare_page_load(self, panel: HAUIPanel) -> None:
        """Send ``page_load_commands()``; call right before goto_page.

        They must reach the display ahead of the page command, or the page
        shows its compiled look first and changes when the hub repaints it.

        Args:
            panel (HAUIPanel): Panel the page is loaded for
        """
        self._load_commands = self.page_load_commands(panel)
        with self.rec_cmd:
            for cmd in self._load_commands:
                self.send_cmd(cmd)

    @property
    def load_commands(self) -> list[str]:
        """The commands ``prepare_page_load`` sent ahead of loading this page.

        Raises:
            RuntimeError: If the page was never prepared for loading.
        """
        if self._load_commands is None:
            raise RuntimeError("The page was not prepared for loading")
        return list(self._load_commands)

    def is_loaded_for(self, panel: HAUIPanel) -> bool:
        """Whether the display loaded this page with what ``panel`` reads while loading.

        Only then can the page show ``panel`` without loading again: the load
        code painted the theme and background ``panel`` needs.

        Args:
            panel (HAUIPanel): Panel to show on the loaded page
        """
        return self._load_commands == self.page_load_commands(panel)

    def start_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is started.

        This method should be overwritten in the page. No need to call super.

        Args:
            panel (HAUIPanel): Current panel
        """

    def config_panel(self, panel: HAUIPanel) -> None:
        """Sets up the header buttons and registers the function components.

        Header slots ``start_panel`` registered without a function get the
        default one for ``header_panel(panel)`` (``_auto_assign_fncs``).

        Args:
            panel (HAUIPanel): Current panel
        """
        header = (self.FNC_BTN_L_PRI, self.FNC_BTN_L_SEC, self.FNC_BTN_R_PRI, self.FNC_BTN_R_SEC)
        if any(fnc_id in self._fnc_items for fnc_id in header):
            self._auto_assign_fncs(self.header_panel(panel))

        # special case, single nav panel
        # swap secondary buttons with primary buttons, since nav is not used
        nav_panels = self.app.device_config.get_panels(True)
        if len(nav_panels) <= 1:
            self._swap_slots_if_single_nav(self.FNC_BTN_L_PRI, self.FNC_BTN_L_SEC)
            self._swap_slots_if_single_nav(self.FNC_BTN_R_PRI, self.FNC_BTN_R_SEC)

        # register function items (rendering deferred to render batch)
        self._fnc_id_by_component.clear()
        for fnc_id, fnc_item in self._fnc_items.items():
            comp = fnc_item["fnc_component"]
            # Function buttons act on release (callback_function_components
            # ignores presses).  Register only when the page did not bind
            # the component itself: ``start_panel`` may already hold the
            # slot (e.g. the media page's volume slider is both a drag
            # control and a ``set_volume`` fnc item), and then the page's
            # callback owns the release.
            if comp.id not in self._callback_map:
                self.on_release(
                    comp,
                    lambda event, component: self.callback_function_components(event, component, 0),
                )
            self._fnc_id_by_component[comp.id] = fnc_id

    def header_panel(self, panel: HAUIPanel) -> HAUIPanel:
        """The panel whose navigation state picks the default header buttons.

        Args:
            panel (HAUIPanel): Current panel
        """
        return panel

    def before_render_panel(self, panel: HAUIPanel) -> bool:
        """Called before the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel

        Returns:
            bool, if False then panel will not be rendered
        """
        return True

    def render_panel(self, panel: HAUIPanel) -> None:
        """Called when the panel is rendered.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """

    def after_render_panel(self, panel: HAUIPanel, rendered: bool) -> None:
        """Called after the panel is rendered.

        This gives the possibility to execute some checks after showing panel.

        Args:
            panel (HAUIPanel): Current panel
            rendered (bool): Was the panel rendered
        """

    def stop_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is stopped.

        Clears all item state listeners, then calls ``_stop_panel()``
        so subclasses can do their own cleanup without calling super.

        Args:
            panel (HAUIPanel): Current panel
        """
        for handle in list(self._handles):
            self.app.cancel_listen_state(handle)
        self._handles.clear()
        self._listener_meta.clear()
        self._clear_component_callbacks()
        self._stop_panel(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        """Subclass hook for panel cleanup.

        Override this instead of ``stop_panel``.  No need to call super.
        """

    # display

    def get_color(self, key: str) -> int:
        """Return the selected theme or the contrast palette paired with the page background."""
        if not self.USE_SYSTEM_COLORS:
            if getattr(self, "_use_color_scheme", False):
                return self.app.color_theme.get(key)
            variant = getattr(self, "_background_variant", "dark")
            return self.app.color_theme.get_background_color(key, variant)
        return super().get_color(key)

    def set_title(
        self, title: str, component: Component | None = None, *, reserve: str = ""
    ) -> None:
        """Set a header title, checked against the title widget.

        Every title shown on the display goes through this method, so a title
        that is wider than the widget (or longer than its text storage) is cut
        to fit and ends in ".." instead of being clipped by the Nextion.

        Args:
            title: Title text, already translated.
            component: Title widget; defaults to this page's ``title``.
            reserve: Text that must stay visible after the title, such as a
                notification's page counter.  It is never cut; the title is
                shortened to leave room for it.
        """
        component = component or self.COMPONENTS.title
        fitted = self._fit_title(title, reserve)
        if fitted != f"{title} {reserve}".strip():
            self.log(
                f"Title {title!r} is longer than the title widget; showing {fitted!r}",
                level="DEBUG",
            )
        self.set_component_text(component, fitted)

    def _fit_title(self, title: str, reserve: str = "") -> str:
        """Fit *title* into the title widget, leaving *reserve* visible."""
        box = self._title_box()
        if not reserve:
            return fit_line([title], self.TITLE_FONT, box)
        gap = f" {reserve}"
        room = TextBox(
            box.width - text_width(gap, self.TITLE_FONT),
            box.height,
            box.border,
            box.max_len - len(gap.encode()),
        )
        base = fit_line([title], self.TITLE_FONT, room)
        return f"{base}{gap}" if base else reserve

    def _title_box(self) -> TextBox:
        """The title widget geometry for this device's orientation."""
        return self.TITLE_BOX["portrait" if self.app.device.is_portrait else "landscape"]

    def set_slider_color(self, slider: Component, show_toggle: bool = True) -> None:
        """Set the slider's handle color.

        Sliders on NSPanel displays use ``.bco`` for the unfilled track, which
        the page's theme code paints in ``component_background`` while it
        loads, and ``.pco`` for the handle/foreground color. Sliders compiled
        without a cursor (light, cover, row) show no handle at all.

        Args:
            slider: The slider ``Component`` to colour.
            show_toggle: True for a primary control (dark-accent handle), False
                for a secondary one (``component_pressed`` handle).
        """
        if show_toggle:
            self.set_component_text_color(slider, self.get_color("component_active_dark"))
        else:
            self.set_component_text_color(slider, self.get_color("component_pressed"))

    # device entities

    def get_inside_temp_entity_id(self, panel: HAUIPanel | None = None) -> str | None:
        """Resolve the entity id for the inside-temperature display value.

        A panel-level ``inside_temp_item`` override (clock/weather panel
        config) replaces the device's own temperature sensor. Without an
        override, resolve the firmware sensor by its ESPHome-authored name on
        this device rather than guessing an HA entity ID from the hub slug.

        Args:
            panel: The panel whose ``inside_temp_item`` override to honour.

        Returns:
            The selected entity id, or None when no sensor resolves.
        """
        if panel is not None:
            override = panel.get("inside_temp_item", None)
            if isinstance(override, list):
                override = override[0] if override else None
            override_id = self._extract_entity_id(override)
            if override_id:
                return override_id
        return self.find_esphome_entity_id("sensor", "Temperature")

    def suspends_auto_page(self) -> bool:
        """Whether this page prevents automatic navigation to the idle page."""
        return False

    # items

    def _build_items_from_panel(self, panel: HAUIPanel, *keys: str) -> list[HAUIItem]:
        """Build HAUIItem list from a panel's item config keys.

        Reads each config key in order.  For each key, if the value is a
        list every entry is added as a separate item; if it's a single
        value (dict or string) it is wrapped as a single item.

        Args:
            panel: The panel whose item config to read.
            *keys: Config key(s) to read item entries from.

        Returns:
            List of HAUIItem objects.
        """
        items: list[HAUIItem] = []
        for key in keys:
            val = panel.get(key, None)
            if isinstance(val, list):
                for entry in val:
                    items.append(HAUIItem(self.app, entry))
            elif val is not None:
                items.append(HAUIItem(self.app, val))
        return items

    @staticmethod
    def _extract_entity_id(value: Any) -> str | None:
        """Extract an entity ID from a config value that is a plain string or ``{item: ...}``.

        The frontend serializes ``kind="item"`` fields through ``serializeItem()``,
        which stores them as ``{item: "entity_id"}`` dicts.
        """
        if isinstance(value, dict):
            return value.get("item")
        return value

    def entity_map_components(self) -> list[tuple[Component, HAUIItem]]:
        """Return page-specific widget/entity links outside the panel's main item."""
        return []

    def entity_map(self) -> dict[str, str]:
        """Widget name -> entity id of the entities this page shows.

        Used by the editor's live preview to name the entity under the mouse.
        Covers the panel's main entity (keyed ``PAGE_ENTITY_KEY``: it applies
        anywhere on the page), page-specific widget/entity links, function
        components with an item (header buttons, clock entity buttons) and the
        grid/row tiles (keyed by each tile's overlay).
        """
        result: dict[str, str] = {}

        def add(component: Any, item: HAUIItem | None) -> None:
            entity_id = item.get_item_id() if item is not None else ""
            if not entity_id or not self.app.item_exists(entity_id):
                return
            name = getattr(component, "name", None)
            if name is None and isinstance(component, tuple | list):
                name = component[1]
            if name:
                result[name] = entity_id

        if self.panel is not None:
            main = self._extract_entity_id(
                self.panel.get("item_id", None) or self.panel.get("item", None)
            )
            if main and self.app.item_exists(main):
                result[PAGE_ENTITY_KEY] = main
        for component, item in self.entity_map_components():
            add(component, item)
        for fnc in self._fnc_items.values():
            add(fnc.get("fnc_component"), fnc.get("fnc_args", {}).get("item"))
        for component, item in getattr(self, "_active_items", {}).items():
            add(component, item)
        return result

    def _entity_ids(self, values: list) -> list[str]:
        """Entity IDs of the string-or-dict config values that have one."""
        ids = (self._extract_entity_id(value) for value in values)
        return [entity_id for entity_id in ids if entity_id]

    def _item_from_ref(self, value: Any) -> HAUIItem | None:
        """Build an item for a string-or-dict entity reference, or None if it has no ID."""
        entity_id = self._extract_entity_id(value)
        return HAUIItem(self.app, {"item": entity_id}) if entity_id else None

    def _panel_title(self, panel: HAUIPanel, item: HAUIItem | None, default: str) -> str:
        """Returns the panel title, falling back to the item's friendly name.

        An explicit panel title is overridden by the item's friendly name, so
        panels controlling one entity are titled after it.

        Args:
            panel: The panel to title.
            item: The item the panel controls, if any.
            default: Translated default title; callers pass a literal translate() call
                so translation extraction finds the string.

        Returns:
            str: Title
        """
        title = panel.get_title(default)
        if item is not None:
            title = item.get_item_attr("friendly_name", title)
        return title

    def _resolve_panel_item(self, panel: HAUIPanel) -> HAUIItem | None:
        """Resolve the single entity item a panel controls.

        Popups get the entity id from the opening item (``item_id``); panels
        built in the editor store an item config under the ``item`` option.

        Args:
            panel: The panel to resolve the item for.

        Returns:
            The item, or None if the panel configures none.
        """
        entity_id = panel.get("item_id", None)
        if entity_id:
            # execute_item passes the opening item's config; keep its overrides
            config = {
                key: panel.get(key)
                for key in self._POPUP_ITEM_OVERRIDES
                if panel.get(key, None) is not None
            }
            return HAUIItem(self.app, {**config, "item": entity_id})
        items = self._build_items_from_panel(panel, "item")
        return items[0] if items else None

    @staticmethod
    def item_is_available(item: HAUIItem | None) -> TypeGuard[HAUIItem]:
        """Whether an entity-backed item refers to an entity with a usable state.

        Internal items (navigate/action/text) have no entity and are always
        executable; ``get_item_state()`` returns None for them, so they must
        not be gated by the entity state here.
        """
        if item is None:
            return False
        if item.is_internal():
            return True
        return item.get_item_state() not in (None, "unknown", "unavailable")

    def execute_item(self, item: HAUIItem) -> None:
        """Executes the given item.

        Args:
            item (HAUIItem): item
        """
        item_type = item.get_item_type()
        navigation = self.app.controller["navigation"]
        available = self.item_is_available(item)

        # item is not available
        if not available:
            msg = self.translate("The item {} is currently unavailable.")
            msg = msg.format(item.get_name())
            msg += "\r\n\r\n"
            msg += self.translate("Entity:")
            msg += "\r\n"
            msg += item.get_item_id()
            # open notification
            navigation.open_panel(
                PopupPanelKey.POPUP_NOTIFY,
                title=self.translate("Unavailable"),
                btn_right=self.translate("Close"),
                icon=item.get_icon(),
                notification=msg,
            )

        # execute popup ("" is what the editor stores after the field is cleared)
        elif popup_name := item.get("popup_key", None) or self.DEFAULT_POPUPS.get(item_type):
            kwargs = item.get_config()
            kwargs["item_id"] = item.get_item_id()
            # open popup
            navigation.open_panel(popup_name, **kwargs)
        # execute default
        else:
            self.log(f"Executing item {item.get_name()} - {item_type}")
            item.execute()

    def turn_on_item(self, item: HAUIItem) -> None:
        """Turns on the given item.

        Args:
            item (HAUIItem): item
        """
        self.log(f"Switching item on: {item.get_name()} ({item.get_item_id()})")
        item_type = item.get_item_type()
        if item_type == "media_player":
            item.call_item_service("media_play")
        else:
            item.call_item_service("turn_on")

    def turn_off_item(self, item: HAUIItem) -> None:
        """Turns off the given item.

        Args:
            item (HAUIItem): item
        """
        self.log(f"Switching item off: {item.get_name()} ({item.get_item_id()})")
        item_type = item.get_item_type()
        if item_type == "media_player":
            item.call_item_service("media_stop")
        else:
            item.call_item_service("turn_off")

    # item state listeners

    def listen_items(self, items: list[HAUIItem], render: Callable[[], None]) -> None:
        """Re-render with ``render`` whenever one of ``items`` changes state.

        Internal items have no entity and are skipped. The listeners end with
        the panel (``stop_panel`` clears them).

        Args:
            items: Items shown on the page.
            render: Redraws the slots that show these items.
        """

        def _on_change(*_args: Any) -> None:
            with self.rec_cmd:
                render()

        item_ids = {item.get_item_id() for item in items if not item.is_internal()}
        for item_id in sorted(i for i in item_ids if i):
            self.add_item_listener(item_id, _on_change, attribute="all")

    def add_item_listener(
        self, item_id: str, callback: Callable, attribute: str | None = None
    ) -> str:
        """Adds a item state listener.

        The registered callback logs every entity/attribute change at DEBUG
        (``entity attribute: old -> new``) before forwarding the unchanged
        ``(entity_id, attribute, old, new, kwargs)`` arguments to ``callback``.

        Args:
            item_id (str): Item ID
            callback (function): Callback
            attribute (str): Attribute

        Returns:
            handle (str): Handle
        """

        def _log_change(event_item: str, event_attr: str, old: Any, new: Any, kwargs: Any) -> None:
            self.log(
                f"Item change: {event_item} {event_attr}: {old!r} -> {new!r}",
                level="DEBUG",
            )
            callback(event_item, event_attr, old, new, kwargs)

        handle = self.app.listen_state(_log_change, item_id, attribute=attribute)
        self.log(
            f"Adding listener for {item_id},"
            f" attribute={attribute},"
            f" callback={getattr(callback, '__name__', str(callback))},"
            f" handle={handle}",
            level="DEBUG",
        )
        self._handles.append(handle)
        self._listener_meta[handle] = {
            "item_id": item_id,
            "attribute": attribute,
            "callback_name": getattr(callback, "__name__", str(callback)),
        }
        return handle

    def remove_item_listener(self, handle: str) -> None:
        """Removes a item state listener.

        Args:
            handle (str): Handle
        """
        if handle not in self._handles:
            return
        self.app.cancel_listen_state(handle)
        self.log(
            f"Removing listener,"
            f" handle={handle},"
            f" item={self._listener_meta.get(handle, {}).get('item_id', '?')}",
            level="DEBUG",
        )
        self._handles.remove(handle)
        self._listener_meta.pop(handle, None)

    # events

    def process_event(self, event: HAUIEvent) -> None:
        """Processes app events.

        Args:
            event (HAUIEvent): Event
        """
        self.log(
            f"Page process_event: {event.name} value={str(event.value)[:100]}",
            level="DEBUG",
        )
        self._process_touch_event(event)
        if event.name in (NotifEvent.NOTIF_ADD, NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR):
            self._update_notif_badge()

    def _update_notif_badge(self) -> None:
        """Shows the notification badge on the header slot that holds it.

        The badge can live on any header slot whose fnc_name is NAV_NOTIF (set
        by _auto_assign_fncs; normally a right slot, or the idle button's
        left-secondary slot as a fallback when pagination claims both right
        slots).
        """
        for slot in (
            self.FNC_BTN_R_SEC,
            self.FNC_BTN_R_PRI,
            self.FNC_BTN_L_SEC,
            self.FNC_BTN_L_PRI,
        ):
            item = self._fnc_items.get(slot)
            if item is not None and item["fnc_name"] == self.FNC_TYPE_NAV_NOTIF:
                notification = self.app.controller["notification"]
                self.update_function_component(
                    slot,
                    color=self.get_color("header_accent"),
                    visible=notification.has_notifications(),
                )
                return
