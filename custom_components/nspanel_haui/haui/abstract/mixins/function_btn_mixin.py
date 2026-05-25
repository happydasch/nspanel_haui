"""Function button system mixin for HAUIPage.

Manages the four header function buttons (left-primary, left-secondary,
right-primary, right-secondary) including auto-assignment of navigation
functions, icon/color updates, and touch event dispatch.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from ..component import Component

if TYPE_CHECKING:
    from ....nspanel_haui import NSPanelHAUI
    from ..haui_base import HAUIBase
    from ..haui_event import HAUIEvent
    from ..haui_panel import HAUIPanel

    _FunctionButtonMixinBase = HAUIBase
else:
    _FunctionButtonMixinBase = object

from ...mapping.const import SysPanelKey
from ...mapping.icons import (
    ICO_ABOUT,
    ICO_LOCKED,
    ICO_NAV_CLOSE,
    ICO_NAV_HOME,
    ICO_NAV_MESSAGE,
    ICO_NAV_NEXT,
    ICO_NAV_PREV,
    ICO_NAV_UP,
    ICO_SLEEP,
    ICO_UNLOCKED,
)


class FncButton(StrEnum):
    """Internal function button identifiers."""

    LEFT_PRI = "fnc_btn_left_pri"
    LEFT_SEC = "fnc_btn_left_sec"
    RIGHT_PRI = "fnc_btn_right_pri"
    RIGHT_SEC = "fnc_btn_right_sec"


class FncType(StrEnum):
    """Internal function component types."""

    NAV_NEXT = "nav_next"
    NAV_PREV = "nav_prev"
    NAV_UP = "nav_up"
    NAV_CLOSE = "nav_close"
    NAV_HOME = "nav_home"
    NAV_SLEEP = "nav_sleep"
    NAV_NOTIF = "nav_notif"
    NAV_ABOUT = "nav_about"
    UNLOCK = "unlock"


class FunctionButtonMixin(_FunctionButtonMixinBase):
    """Mixin that manages function button registration, rendering, and dispatch.

    Depends on the host class providing:
    * ``self._fnc_items`` (set in :class:`~haui.page.HAUIPage.__init__`)
    * ``self.FNC_BTN_L_PRI`` / ``L_SEC`` / ``R_PRI`` / ``R_SEC`` (ClassVar)
    * ``self.FNC_TYPE_NAV_*`` and ``self.FNC_TYPE_UNLOCK`` (ClassVar)
    * ``ICO_*`` icon constants (ClassVar)
    * :class:`~haui.page.component_mixin.ComponentMixin` methods
    """

    # internal function button ids
    def get_color(self, key: str) -> int:
        """Provided by ``HAUIBase`` at runtime via MRO (mixin + base class).

        This method delegates to ``super()`` for mypy satisfaction and runtime
        forwarding — the downstream ``HAUIBase`` (or a subclass further right
        in the MRO) provides the actual implementation.
        """
        return super().get_color(key)

    # internal function button ids
    FNC_BTN_L_PRI = FncButton.LEFT_PRI
    FNC_BTN_L_SEC = FncButton.LEFT_SEC
    FNC_BTN_R_PRI = FncButton.RIGHT_PRI
    FNC_BTN_R_SEC = FncButton.RIGHT_SEC

    # functions for function components
    FNC_TYPE_NAV_NEXT = FncType.NAV_NEXT
    FNC_TYPE_NAV_PREV = FncType.NAV_PREV
    FNC_TYPE_NAV_UP = FncType.NAV_UP
    FNC_TYPE_NAV_CLOSE = FncType.NAV_CLOSE
    FNC_TYPE_NAV_HOME = FncType.NAV_HOME
    FNC_TYPE_NAV_SLEEP = FncType.NAV_SLEEP
    FNC_TYPE_NAV_NOTIF = FncType.NAV_NOTIF
    FNC_TYPE_NAV_ABOUT = FncType.NAV_ABOUT
    FNC_TYPE_UNLOCK = FncType.UNLOCK

    if TYPE_CHECKING:
        # Provided by HAUIPage / HAUIBase / ComponentMixin at runtime via MRO.
        app: NSPanelHAUI
        _fnc_items: dict
        panel: HAUIPanel | None

        # Methods from HAUIBase / ComponentMixin
        def log(self, msg: str, **kwargs: Any) -> None: ...
        def set_component_value(self, component: Component, value: int) -> None: ...
        def set_component_text(self, component: Component, text: str) -> None: ...
        def set_component_touch(self, component: Component, state: bool) -> None: ...
        def set_component_text_color(
            self, component: Component, color: int | str | list | tuple
        ) -> None: ...
        def set_component_text_color_pressed(
            self, component: Component, color: int | str | list | tuple
        ) -> None: ...
        def set_component_back_color(
            self, component: Component, color: int | str | list | tuple
        ) -> None: ...
        def set_component_back_color_pressed(
            self, component: Component, color: int | str | list | tuple
        ) -> None: ...
        def show_component(self, component: Component) -> None: ...
        def hide_component(self, component: Component) -> None: ...

    # ------------------------------------------------------------------
    # Button configuration
    # ------------------------------------------------------------------

    def set_function_buttons(
        self,
        btn_l_pri: tuple | list | dict | None,
        btn_l_sec: tuple | list | dict | None,
        btn_r_pri: tuple | list | dict | None,
        btn_r_sec: tuple | list | dict | None,
    ) -> None:
        """Sets all function buttons at once.

        can be a dict:
        item = {'fnc_component': (..., ...), 'fnc_name': 'name', fnc_args={}}

        can be list|tuple (component):
        item = (..., ...)

        Args:
            btn_l_pri (tuple|list|dict): Primary left function button
            btn_l_sec (tuple|list|dict): Secondary left function button
            btn_r_pri (tuple|list|dict): Primary right function button
            btn_r_sec (tuple|list|dict): Secondary right function button
        """
        for fnc_id, item in [
            (self.FNC_BTN_L_PRI, btn_l_pri),
            (self.FNC_BTN_L_SEC, btn_l_sec),
            (self.FNC_BTN_R_PRI, btn_r_pri),
            (self.FNC_BTN_R_SEC, btn_r_sec),
        ]:
            if isinstance(item, (list, tuple)):
                self.set_function_component(item, fnc_id)
            elif isinstance(item, dict):
                btn = item.get("fnc_component", None)
                fnc_name = item.get("fnc_name", None)
                fnc_args = item.get("fnc_args", {})
                self.set_function_component(btn, fnc_id, fnc_name, **fnc_args)
            else:
                self.set_function_component(None, fnc_id)

    def get_button_colors(self, active: bool) -> tuple:
        """Returns default colors for buttons.

        Args:
            active (bool): is the button active

        Returns:
            tuple: (color, color_pressed, back_color, back_color_pressed)
        """
        if active:
            color = self.get_color("component_active")
            color_pressed = self.get_color("component_text")
            back_color_pressed = self.get_color("component_pressed")
        else:
            color = self.get_color("text_disabled")
            color_pressed = self.get_color("text_disabled")
            back_color_pressed = self.get_color("background")
        back_color = self.get_color("background")
        return color, color_pressed, back_color, back_color_pressed

    # ------------------------------------------------------------------
    # Function component registration
    # ------------------------------------------------------------------

    def get_function_components(self, return_copy: bool = True) -> dict:
        """Returns the function buttons.

        Args:
            return_copy (bool): should a copy of the buttons be returned

        Returns:
            dict: Function buttons
        """
        if return_copy:
            return self._fnc_items.copy()
        return self._fnc_items

    def set_function_component(
        self,
        component: tuple | list | None,
        fnc_id: str,
        fnc_name: str | None = None,
        **fnc_args: Any,
    ) -> None:
        """Sets the function component.

        To remove a function component:

        self.set_function_component(None, fnc_id)

        To add a function component, do the following:

        - set button as a function component
          self.set_function_component(btn, fnc_id)
          This will use a default function and a default icon

        or

        - set button as a function component
          self.set_function_component(btn, fnc_id, fnc_name='functionname',
                                    icon='icon', color=0)
          This will use a custom function and a custom icon

        To add a custom function component, do the following:

        - set component as a function component
          self.set_function_component(component, fnc_id,
                                    fnc_name='functionname',
                                    fnc_args={'icon': icon, 'color': 0})
        - overwrite callback_function_component(fnc_id, fnc_name)
          and check for fnc_id
        - do action if fnc_id matches

        Args:
            component (tuple): Component
            fnc_id (str): Function Component ID
            fnc_name (str, optional): Function name, if not defined, default
                                      function will be used
            fnc_args (dict): Function arguments
        """
        if component is not None:
            item = self._fnc_items.get(fnc_id, {})
            item = {
                **item,
                "fnc_component": component,
                "fnc_name": fnc_name,
                "fnc_args": fnc_args,
            }
            self._fnc_items[fnc_id] = item
        elif fnc_id in self._fnc_items:
            self.log(f"Removing function component {fnc_id}")
            del self._fnc_items[fnc_id]

    def update_function_component(
        self, fnc_id: str, update_fnc_name: str | None = None, **kwargs: Any
    ) -> None:
        """Updates the function component.

        Args:
            fnc_id (str): Function Component ID
            update_fnc_name (str): Optional, new function name
            kwargs (dict): Arguments
        """

        if fnc_id not in self._fnc_items:
            self.log(f"function component {fnc_id} not found")
            return
        fnc_item = self._fnc_items[fnc_id]
        fnc_component = fnc_item["fnc_component"]
        fnc_args = fnc_item["fnc_args"]
        fnc_args = fnc_item["fnc_args"] = {**fnc_args, **kwargs}
        if update_fnc_name is not None:
            fnc_item["fnc_name"] = update_fnc_name
        fnc_name = fnc_item["fnc_name"]

        # get infos for component
        value = fnc_args.get("value", None)
        text = fnc_args.get("text", None)
        icon = fnc_args.get("icon", None)
        touch = fnc_args.get("touch_events", None)
        color = fnc_args.get("color", None)
        visible = fnc_args.get("visible", True)

        # set value
        if value is not None and fnc_item.get("current_value") != value:
            self.set_component_value(fnc_component, value)
            fnc_item["current_value"] = value

        # set text (can also contain icons)
        elif text is not None and fnc_item.get("current_text") != text:
            self.set_component_text(fnc_component, text)
            fnc_item["current_text"] = text

        # set icon
        else:
            if icon is None:
                if fnc_name == self.FNC_TYPE_NAV_PREV:
                    icon = ICO_NAV_PREV
                elif fnc_name == self.FNC_TYPE_NAV_NEXT:
                    icon = ICO_NAV_NEXT
                elif fnc_name == self.FNC_TYPE_NAV_HOME:
                    icon = ICO_NAV_HOME
                elif fnc_name == self.FNC_TYPE_NAV_SLEEP:
                    icon = ICO_SLEEP
                elif fnc_name == self.FNC_TYPE_NAV_NOTIF:
                    icon = ICO_NAV_MESSAGE
                elif fnc_name == self.FNC_TYPE_NAV_ABOUT:
                    icon = ICO_ABOUT
                elif fnc_name == self.FNC_TYPE_NAV_UP:
                    icon = ICO_NAV_UP
                elif fnc_name == self.FNC_TYPE_NAV_CLOSE:
                    icon = ICO_NAV_CLOSE
                elif fnc_name == self.FNC_TYPE_UNLOCK:
                    if fnc_args.get("locked", False):
                        icon = ICO_LOCKED
                    else:
                        icon = ICO_UNLOCKED
            if icon is not None and fnc_item.get("current_icon") != icon:
                self.set_component_text(fnc_component, icon)
                fnc_item["current_icon"] = icon

        # set touch events
        if touch is not None and fnc_item.get("current_touch_events") != touch:
            self.set_component_touch(fnc_component, touch)
            fnc_item["current_touch_events"] = touch

        # set colors
        if (
            color is None
            and fnc_args.get("locked", None) is not None
            and fnc_name == self.FNC_TYPE_UNLOCK
            and not fnc_args.get("locked", False)
        ):
            color = self.get_color("component_accent")
        if color is None:
            color = self.get_color("header_text")
        color_pressed = fnc_args.get("color_pressed")
        back_color = fnc_args.get("back_color")
        if back_color is None:
            back_color = self.get_color("header_background")
        back_color_pressed = fnc_args.get("back_color_pressed")
        if color is not None and fnc_item.get("current_color") != color:
            self.set_component_text_color(fnc_component, color)
            fnc_item["current_color"] = color
        if color_pressed is not None and fnc_item.get("current_color_pressed") != color_pressed:
            self.set_component_text_color_pressed(fnc_component, color_pressed)
            fnc_item["current_color_pressed"] = color_pressed
        if back_color is not None and fnc_item.get("current_back_color") != back_color:
            self.set_component_back_color(fnc_component, back_color)
            fnc_item["current_back_color"] = back_color
        if (
            back_color_pressed is not None
            and fnc_item.get("current_back_color_pressed") != back_color_pressed
        ):
            self.set_component_back_color_pressed(fnc_component, back_color_pressed)
            fnc_item["current_back_color_pressed"] = back_color_pressed

        # set visibility
        if visible is not None and fnc_item.get("current_visible", None) is not visible:
            if visible:
                self.show_component(fnc_component)
            else:
                self.hide_component(fnc_component)
            fnc_item["current_visible"] = visible

    # ------------------------------------------------------------------
    # Auto-assignment
    # ------------------------------------------------------------------

    def _auto_assign_fncs(self, panel: HAUIPanel) -> None:
        """Auto-assign default function types to header buttons that have no explicit assignment.

        This is called once per ``config_panel()`` cycle.  Only buttons whose
        ``fnc_name`` is still ``None`` are assigned.  Each slot is handled by
        an independent ``if/elif`` branch (all four slots are mutually
        exclusive IDs).

        Args:
            panel (HAUIPanel): Current panel
        """
        home_key = self.app.device.get("home_panel")
        for fnc_id, fnc_item in self._fnc_items.items():
            show_in_nav = panel.show_in_navigation()
            is_popup = panel.can_show_popup()
            if fnc_item["fnc_name"] is None:
                # left primary: popup with home button => HOME, navigation => PREV, otherwise => UP
                if fnc_id == self.FNC_BTN_L_PRI:
                    if (
                        is_popup
                        and not (home_key and panel.get("key") == home_key)
                        and panel.show_home_button()
                    ):
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_HOME
                    elif show_in_nav:
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_PREV
                    else:
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_UP
                # left secondary: on home panel => NOTIF (fallback SLEEP),
                # otherwise on non-popup panels => HOME
                elif fnc_id == self.FNC_BTN_L_SEC:
                    if not is_popup:
                        is_home = home_key and panel.get("key") == home_key
                        if not is_home and panel.show_home_button():
                            fnc_item["fnc_name"] = self.FNC_TYPE_NAV_HOME
                        elif is_home:
                            if panel.show_notifications_button():
                                notification = self.app.controller["notification"]
                                fnc_item["fnc_name"] = self.FNC_TYPE_NAV_NOTIF
                                fnc_item["fnc_args"]["visible"] = notification.has_notifications()
                            if (
                                fnc_item["fnc_args"].get("visible") is False
                                and panel.show_sleep_button()
                            ):
                                fnc_item["fnc_name"] = self.FNC_TYPE_NAV_SLEEP
                                fnc_item["fnc_args"]["visible"] = True
                # right primary: navigation => NEXT, otherwise => CLOSE
                elif fnc_id == self.FNC_BTN_R_PRI:
                    if show_in_nav:
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_NEXT
                    else:
                        fnc_item["fnc_name"] = self.FNC_TYPE_NAV_CLOSE
                # right secondary: locked panel => UNLOCK indicator
                elif fnc_id == self.FNC_BTN_R_SEC:
                    locked = panel.get_state("locked")
                    if locked is not None:
                        fnc_item["fnc_name"] = self.FNC_TYPE_UNLOCK
                        fnc_item["fnc_args"]["locked"] = locked
            # visibility: hide buttons with no assigned function, show ones that do
            if fnc_item["fnc_args"].get("visible", None) is None:
                if fnc_item["fnc_name"] is None:
                    fnc_item["fnc_args"]["visible"] = False
                else:
                    fnc_item["fnc_args"]["visible"] = True

    def _swap_slots_if_single_nav(self, pri_key: str, sec_key: str) -> None:
        """Swap secondary button slot with primary when both exist and primary is nav-unused.

        When there is only a single navigation panel, the primary prev/next
        buttons are not needed.  This method hides the primary button and
        swaps its component slot with the secondary so the secondary's icon
        appears in the primary position.

        Args:
            pri_key (str): Primary function button key (e.g. FNC_BTN_L_PRI)
            sec_key (str): Secondary function button key (e.g. FNC_BTN_L_SEC)
        """
        if pri_key not in self._fnc_items:
            return
        pri = self._fnc_items[pri_key]
        is_unused_nav = pri["fnc_name"] is None or pri["fnc_name"] in (
            self.FNC_TYPE_NAV_PREV,
            self.FNC_TYPE_NAV_NEXT,
        )
        if not is_unused_nav:
            return
        pri["fnc_args"]["visible"] = False
        if sec_key not in self._fnc_items:
            return
        sec = self._fnc_items[sec_key]
        pri_comp = pri["fnc_component"]
        sec_comp = sec["fnc_component"]
        pri["fnc_component"] = sec_comp
        sec["fnc_component"] = pri_comp
        self._fnc_items[pri_key] = sec
        self._fnc_items[sec_key] = pri

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        """Gets called when a function component was pressed.

        This method is intended to be overwritten if a custom function
        component is used.

        Args:
            fnc_id (str): Function Component ID
            fnc_name (str): Function Name
        """

    def callback_function_components(
        self, event: HAUIEvent, component: Component, button_state: int
    ) -> None:
        """Callback method for function component events.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (int): Value of the component event
        """
        # process function button press callback
        if button_state != 0:
            return

        # check what button was pressed
        fnc_id = None
        fnc_item = None
        for _fnc_id, _fnc_cnt in self._fnc_items.items():
            if _fnc_cnt["fnc_component"] == component:
                fnc_id = _fnc_id
                fnc_item = _fnc_cnt
                break

        # if unknown function do nothing
        if fnc_id is None or fnc_item is None:
            self.log(f"Unknown function component {component}")
            return
        navigation = self.app.controller["navigation"]
        fnc_name = fnc_item["fnc_name"]
        fnc_args = fnc_item["fnc_args"]

        # check the function that is defined for the button
        if fnc_name == self.FNC_TYPE_NAV_PREV:
            navigation.open_prev_panel()
        elif fnc_name == self.FNC_TYPE_NAV_NEXT:
            navigation.open_next_panel()
        elif fnc_name == self.FNC_TYPE_NAV_HOME:
            navigation.open_home_panel()
        elif fnc_name == self.FNC_TYPE_NAV_SLEEP:
            navigation.open_sleep_panel()
        elif fnc_name == self.FNC_TYPE_NAV_NOTIF:
            navigation.open_panel(SysPanelKey.POPUP_NOTIFS)
        elif fnc_name == self.FNC_TYPE_NAV_ABOUT:
            navigation.open_panel(SysPanelKey.SYS_ABOUT)
        elif fnc_name == self.FNC_TYPE_NAV_UP or fnc_name == self.FNC_TYPE_NAV_CLOSE:
            navigation.close_panel()
        elif fnc_name == self.FNC_TYPE_UNLOCK:
            locked = fnc_args.get("locked", False)
            # lock panel if not locked
            if not locked and self.panel is not None:
                self.panel.set_state("locked", True)
                navigation.reload_panel()

        # notify about function button press
        self.callback_function_component(fnc_id, fnc_name)
