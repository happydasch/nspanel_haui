"""Represents a page on the Nextion display."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPEvent, NotifEvent, SysPanelKey
from ..mapping.page import PAGE_MAPPING
from .mixins.button_state_mixin import ButtonStateMixin
from .mixins.component_mixin import ComponentMixin
from .mixins.function_btn_mixin import FunctionButtonMixin


class HAUIPage(FunctionButtonMixin, ButtonStateMixin, ComponentMixin, HAUIBase):
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

    # Pages that use pre-rendered picture backgrounds (clock, clocktwo, weather)
    # should set this to ``True`` so the base class skips the ``fill`` background
    # command (picture-background pages handle their own background).
    PICTURE_BACKGROUND: ClassVar[bool] = False

    # Pages with non-standard color palettes (about, clock, clocktwo, weather)
    # should set this to ``False`` so user-defined color overrides are bypassed
    # and the page's built-in palette is used instead.
    USE_SYSTEM_COLORS: ClassVar[bool] = True

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any] | None = None) -> None:
        super().__init__(app, config)
        self.page_id = int(self.get("page_id"))
        self.page_id_recv: int | None = None  # set when a page event is received
        # current panel
        self.panel: HAUIPanel | None = None
        # function items, components
        self._fnc_items: dict = {}
        # physical buttons, components
        self._btn_state_left: Component | None = None
        self._btn_state_right: Component | None = None
        # component callbacks
        self._callbacks: list[tuple[Component, Callable]] = []
        # item handles
        self._handles: list[str] = []
        # listener metadata for debugging
        self._listener_meta: dict[str, dict] = {}
        # buffered release callback for swipe-disambiguation
        self._queued_callback: tuple[int, int, HAUIEvent] | None = None
        self._buffer_timer: str | None = None
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

    def start_part(self) -> None:
        """Starts the part.

        This is called when the part is started.
        """
        # notify about page start
        self.start_page()

    def stop_part(self) -> None:
        """Stops of part.

        This is called when the part is stopped.
        """
        self._cancel_buffer_timer()
        self._queued_callback = None
        self.set_panel(None)
        # notify about page stop
        self.stop_page()
        # clean up item handles
        for handle in self._handles.copy():
            self.remove_item_listener(handle)

    # page

    def start_page(self) -> None:
        """Starts the page.

        Put callback registration in here and code that should be run
        only once on start.

        When changing components, prefer using start_panel.
        """

    def stop_page(self) -> None:
        """Stops the page.

        Put callback deregistration in here and other code that should
        be run when stopping a part.
        """

    # panel functionality

    def refresh_panel(self) -> None:
        """Refreshes the current panel.

        This gives the possibility to update the panel.
        """
        if self.panel is None:
            return
        self.debug_log(
            f"Refreshing panel {self.panel.id}",
            min_level=2,
        )
        with self.rec_cmd:
            self.render_panel(self.panel)

    def set_panel(self, panel: HAUIPanel | None) -> None:
        """Sets a panel for the page.

        This is used to set a panel for current page.
        The panel is set to the page and the panel is then being rendered.

        Args:
            panel (HAUIPanel): The panel to set.
        """
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
        self.start_panel(panel)

        # 1. call config for panel
        self.config_panel(panel)
        # 2. call before render for panel
        rendered = False
        if self.before_render_panel(panel):
            self.debug_log(
                f"Rendering panel {panel.id}",
                min_level=2,
            )
            with self.rec_cmd:
                self.render_panel(panel)
            rendered = True
        # 4. call after render for panel
        self.after_render_panel(panel, rendered)

    def config_panel(self, panel: HAUIPanel) -> None:
        """Configures the currently set panel.

        Args:
            panel (HAUIPanel): Current panel
        """
        # Apply background color for solid-color pages.
        # Picture-background pages (clock, weather, clocktwo) handle their
        # own background via pre-compiled picture assets in the TFT.
        if not self.PICTURE_BACKGROUND:
            with self.rec_cmd:
                self.send_cmd(f"cls {self.get_color('background')}")

        if not self.PICTURE_BACKGROUND:
            with self.rec_cmd:
                # apply header colors to the header background (if the page has one)
                try:
                    header_comp = self.COMPONENTS.header
                except AttributeError:
                    pass
                else:
                    self.set_component_back_color(header_comp, self.get_color("header_background"))

                # apply header colors to the title component (if the page has one)
                try:
                    title_comp = self.COMPONENTS.title
                except AttributeError:
                    pass
                else:
                    self.set_component_text_color(title_comp, self.get_color("header_text"))
                    self.set_component_back_color(title_comp, self.get_color("header_background"))

        with self.rec_cmd:
            # physical button state
            if self._btn_state_left is not None:
                self.add_component_callback(
                    self._btn_state_left, self.callback_button_state_buttons
                )
                self.set_component_value(
                    self._btn_state_left, self.app.device.get_left_button_state()
                )
            if self._btn_state_right is not None:
                self.add_component_callback(
                    self._btn_state_right, self.callback_button_state_buttons
                )
                self.set_component_value(
                    self._btn_state_right, self.app.device.get_right_button_state()
                )

            # special case, single nav panel
            # swap secondary buttons with primary buttons, since nav is not used
            nav_panels = self.app.device_config.get_panels(True)
            if len(nav_panels) <= 1:
                self._swap_slots_if_single_nav(self.FNC_BTN_L_PRI, self.FNC_BTN_L_SEC)
                self._swap_slots_if_single_nav(self.FNC_BTN_R_PRI, self.FNC_BTN_R_SEC)

            # register function items
            for fnc_id, fnc_item in self._fnc_items.items():
                self.add_component_callback(
                    fnc_item["fnc_component"], self.callback_function_components
                )
                self.update_function_component(fnc_id)

    def create_panel(self, panel: HAUIPanel) -> None:
        """Called when a new panel is created.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """

    def start_panel(self, panel: HAUIPanel) -> None:
        """Called when a panel is started.

        Sets ``_use_system_colors`` from the page's ``USE_SYSTEM_COLORS``
        ClassVar so ``get_color()`` knows whether to respect user overrides.

        This method should be overwritten in the page.

        Args:
            panel (HAUIPanel): Current panel
        """
        self._use_system_colors = type(self).USE_SYSTEM_COLORS

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
        self._stop_panel(panel)

    def _stop_panel(self, panel: HAUIPanel) -> None:
        """Subclass hook for panel cleanup.

        Override this instead of ``stop_panel``.  No need to call super.
        """

    def _save_auto_state(self) -> dict:
        """Save and disable auto-dimming/page/sleep for popup overlays.

        Returns the saved states dict, which must be passed to the passed to
        ``_restore_auto_state()`` on cleanup.
        """
        name = self.app.device.get_name()
        states: dict = {}
        for key, suffix in (
            ("auto_dimming", "use_auto_dimming"),
            ("auto_page", "use_auto_page"),
            ("auto_sleeping", "use_auto_sleeping"),
        ):
            item = self.app.get_item(f"switch.{name}_{suffix}")
            states[key] = item.get_state()
            item.turn_off()
        return states

    def _restore_auto_state(self, states: dict) -> None:
        """Restore previously saved auto-dimming/page/sleep states.

        Args:
            states: The dict returned by ``_save_auto_state()``.
        """
        name = self.app.device.get_name()
        for key, suffix in (
            ("auto_dimming", "use_auto_dimming"),
            ("auto_page", "use_auto_page"),
            ("auto_sleeping", "use_auto_sleeping"),
        ):
            if states.get(key):
                item = self.app.get_item(f"switch.{name}_{suffix}")
                item.turn_on()

    # gesture-buffer helpers

    def _cancel_buffer_timer(self) -> None:
        """Cancels the gesture-disambiguation buffer timer, if active."""
        if self._buffer_timer is not None:
            self.app.cancel_timer(self._buffer_timer)
            self._buffer_timer = None

    def _flush_buffer_callback(self, _cb_args: dict | None = None) -> None:
        """Flushes the buffered release callback once the buffer window expires.

        Called by ``run_in`` timer callback when no GESTURE arrived before
        the 100 ms disambiguation window.  Dispatches the callback to
        the registered component handler.
        """
        if self._queued_callback is None:
            return
        comp_id, button_state, event = self._queued_callback
        self._queued_callback = None
        self._buffer_timer = None
        for component, callback in self._callbacks:
            if comp_id == component.id:
                callback(event, component, button_state)
                break

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

    # item

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

    def execute_item(self, item: HAUIItem) -> None:
        """Executes the given item.

        Args:
            item (HAUIItem): item
        """
        item_type = item.get_item_type()
        item_state = item.get_item_state()
        navigation = self.app.controller["navigation"]
        available = item_state != "unavailable"

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
                SysPanelKey.POPUP_NOTIFY,
                title=self.translate("Entity unavailable"),
                btn_right=self.translate("Close"),
                icon=item.get_icon(),
                notification=msg,
            )

        # execute popup
        elif item_type in ["light", "media_player", "vacuum", "cover", "climate"]:
            popup_name = item.get("popup_key", None)
            if popup_name is None:
                popup_name = f"popup_{item_type}"
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

    def add_item_listener(
        self, item_id: str, callback: Callable, attribute: str | None = None
    ) -> str:
        """Adds a item state listener.

        Args:
            item_id (str): Item ID
            callback (function): Callback
            attribute (str): Attribute

        Returns:
            handle (str): Handle
        """
        handle = self.app.listen_state(callback, item_id, attribute=attribute)
        self.debug_log(
            f"Adding listener for {item_id},"
            f" attribute={attribute},"
            f" callback={callback.__name__},"
            f" handle={handle}",
            min_level=2,
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
        if handle in self._handles:
            self.app.cancel_listen_state(handle)
            self.debug_log(
                f"Removing listener,"
                f" handle={handle},"
                f" item={self._listener_meta.get(handle, {}).get('item_id', '?')}",
                min_level=2,
            )
            if handle in self._handles:
                self._handles.remove(handle)
            self._listener_meta.pop(handle, None)

    # processing

    def process_event(self, event: HAUIEvent) -> None:
        """Processes app events.

        Args:
            event (HAUIEvent): Event
        """
        # component event
        if event.name == ESPEvent.COMPONENT:
            self.process_component_event(event)
        # gesture — cancel any buffered component callback (it was a swipe)
        elif event.name == ESPEvent.GESTURE:
            self._cancel_buffer_timer()
            self._queued_callback = None
        # notification indicator — the badge lives on the left-secondary button
        # when its fnc_name is NAV_NOTIF (set by _auto_assign_fncs).
        if self.FNC_BTN_L_SEC in self._fnc_items:
            left_sec = self._fnc_items[self.FNC_BTN_L_SEC]
            if left_sec["fnc_name"] == self.FNC_TYPE_NAV_NOTIF and event.name in [
                NotifEvent.NOTIF_ADD,
                NotifEvent.NOTIF_REMOVE,
                NotifEvent.NOTIF_CLEAR,
            ]:
                if event.name == NotifEvent.NOTIF_ADD:
                    color = self.get_color("header_accent")
                else:
                    color = self.get_color("component_text")
                notification = self.app.controller["notification"]
                visible = False
                if notification.has_notifications():
                    visible = True
                self.update_function_component(self.FNC_BTN_L_SEC, color=color, visible=visible)

    def process_component_event(self, event: HAUIEvent) -> None:
        """Processes component events from component callback.

        Args:
            event (str): Event
        """
        component_info = [int(x) for x in event.as_str().split(",")]
        if len(component_info) != 3:
            return
        if component_info[0] != self.page_id:
            return

        comp_id = component_info[1]
        button_state = component_info[2]

        # Press events (touch_event != 0): dispatch immediately.
        # Most callbacks are no-ops on press anyway.
        if button_state != 0:
            for component, callback in self._callbacks:
                if comp_id == component.id:
                    callback(event, component, button_state)
                    return

        # Release events (touch_event == 0): buffer briefly to allow
        # gesture detection to cancel them if the touch was a swipe.
        self._cancel_buffer_timer()
        self._queued_callback = (comp_id, button_state, event)
        self._buffer_timer = self.app.run_in(self._flush_buffer_callback, 0.1)
