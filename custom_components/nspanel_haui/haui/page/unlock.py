from __future__ import annotations

from ..abstract.component import Component
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_panel import HAUIPanel
from ..mapping.descriptor import PageDescriptor
from ..mapping.icons import ICO_LOCKED, ICO_PASSWORD
from .alarm import AlarmPage


class UnlockPage(AlarmPage):
    DESCRIPTOR = PageDescriptor(
        type_key="popup_unlock",
        page_name="unlock",
        label="Unlock",
        description="PIN unlock overlay for locked panels.",
        is_system=True,
        sys_panel_default={
            "key": "popup_unlock",
            "show_in_navigation": False,
        },
        popup_alias_for="alarm",
        can_show_popup=True,
        icon="mdi:lock-outline",
    )

    _input = ""
    _title = ""
    _unlock_panel: HAUIPanel | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # store panel infos
        self._unlock_panel = unlock_panel = panel.get("unlock_panel", None)
        self._title = panel.get("title", self.translate("Unlock Panel"))
        # lock right secondary function button
        lock_btn = {
            "fnc_component": AlarmPage.COMPONENTS.fnc_right_sec,
            "fnc_name": "unlock_indicator",
            "fnc_args": {
                "locked": True,
                "icon": ICO_LOCKED,
                "color": self.get_color("component_text"),
                "back_color_pressed": self.get_color("background"),
            },
        }

        with self.rec_cmd:
            # set function buttons
            self.set_function_buttons(
                AlarmPage.COMPONENTS.fnc_left_pri,
                AlarmPage.COMPONENTS.fnc_left_sec,
                AlarmPage.COMPONENTS.fnc_right_pri,
                lock_btn,
            )

            # set components
            for c in [
                AlarmPage.COMPONENTS.btn_key_0,
                AlarmPage.COMPONENTS.btn_key_1,
                AlarmPage.COMPONENTS.btn_key_2,
                AlarmPage.COMPONENTS.btn_key_3,
                AlarmPage.COMPONENTS.btn_key_4,
                AlarmPage.COMPONENTS.btn_key_5,
                AlarmPage.COMPONENTS.btn_key_6,
                AlarmPage.COMPONENTS.btn_key_7,
                AlarmPage.COMPONENTS.btn_key_8,
                AlarmPage.COMPONENTS.btn_key_9,
                AlarmPage.COMPONENTS.btn_key_clr,
                AlarmPage.COMPONENTS.btn_key_del,
            ]:
                self.add_component_callback(c, self.callback_keypad)
            self.add_component_callback(AlarmPage.COMPONENTS.b1_fnc, self.callback_unlock)
            self.set_function_component(
                component=AlarmPage.COMPONENTS.b1_fnc,
                fnc_id=AlarmPage.COMPONENTS.b1_fnc.name,
                fnc_name=AlarmPage.COMPONENTS.b1_fnc.name,
                color=self.get_color("text_disabled"),
                text=self.translate("Unlock"),
                locked=getattr(panel, "locked", False),
            )

            # prepare unlock panel using config from locked panel
            if unlock_panel:
                # override the unlock popup's navigation state to match the panel it is protecting
                panel.set_state("show_in_navigation", unlock_panel.show_in_navigation())
                self._title = unlock_panel.get_title(self._title)
                self._unlock_code = unlock_panel.get("unlock_code")

    def before_render_panel(self, panel: HAUIPanel) -> bool:
        # check if unlock panel is available
        navigation = self.app.controller["navigation"]
        if not self._unlock_panel:
            self.log("No unlock_panel provided")
            navigation.close_panel()
            return False
        if not self._unlock_code:
            self.log("No unlock_code provided")
            navigation.close_panel()
            return False
        return True

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_components()

    # misc

    def update_components(self) -> None:
        # show either password stars or title
        if len(self._input):
            passwd = f"{ICO_PASSWORD}" * len(self._input)
            self.set_component_text(AlarmPage.COMPONENTS.title, passwd)
        else:
            self.set_component_text(AlarmPage.COMPONENTS.title, self._title)

        # update unlock indicator in header
        color = self.get_color("component_text")
        if len(self._input) > 0:
            color = self.get_color("component_accent")
        self.update_function_component(AlarmPage.FNC_BTN_R_SEC, color=color)

        # update unlock button
        unlock_btn_enabled = False
        if str(self._input) == str(self._unlock_code):
            unlock_btn_enabled = True
        if unlock_btn_enabled:
            self.update_function_component(
                fnc_id=AlarmPage.COMPONENTS.b1_fnc.name,
                touch_events=True,
                color=self.get_color("component_active"),
                color_pressed=self.get_color("component_text"),
                back_color=self.get_color("background"),
                back_color_pressed=self.get_color("component_pressed"),
            )
        else:
            self.update_function_component(
                fnc_id=AlarmPage.COMPONENTS.b1_fnc.name,
                touch_events=False,
                color=self.get_color("text_disabled"),
                color_pressed=self.get_color("text_disabled"),
                back_color=self.get_color("background"),
                back_color_pressed=self.get_color("background"),
            )

    # callback

    def callback_keypad(self, event: HAUIEvent, component: Component, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got keypad press: {component}-{button_state}")
        with self.rec_cmd:
            # process keypad value
            if component.name.startswith("bKey"):
                bKeyVal = component.name[4:]
                if bKeyVal not in ["Del", "Clr"]:
                    self._input += str(bKeyVal)
                elif bKeyVal == "Clr":
                    self._input = ""
                elif bKeyVal == "Del":
                    self._input = self._input[:-1]

            self.update_components()

    def callback_unlock(self, event: HAUIEvent, component: Component, button_state: int) -> None:
        if button_state:
            return
        if self._unlock_panel is None:
            return
        if str(self._input) != str(self._unlock_code):
            with self.rec_cmd:
                self._input = ""
                self.update_components()
            return
        # unlock panel and close this unlock popup
        self.log(f"Panel {self._unlock_panel.id} unlocked, closing unlock popup.")
        self._unlock_panel.set_state("locked", False)
        navigation = self.app.controller["navigation"]
        navigation.close_panel()
