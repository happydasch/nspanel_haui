from ..mapping.color import COLORS
from ..config import HAUIConfigPanel

from .alarm import AlarmPage


class UnlockPage(AlarmPage):
    _input = ""
    _title = ""
    _unlock_panel: HAUIConfigPanel = None

    # panel

    def start_panel(self, panel: HAUIConfigPanel):
        # store panel infos
        self._unlock_panel = unlock_panel = panel.get("unlock_panel")
        self._title = panel.get("title", self.translate("Unlock Panel"))
        # lock right secondary function button
        lock_btn = {
            "fnc_component": AlarmPage.BTN_FNC_RIGHT_SEC,
            "fnc_name": "unlock_indicator",
            "fnc_args": {
                "locked": True,
                "icon": self.ICO_LOCKED,
                "color": COLORS["component"],
                "back_color_pressed": COLORS["background"],
            },
        }

        self.start_rec_cmd()

        # set function buttons
        self.set_function_buttons(
            AlarmPage.BTN_FNC_LEFT_PRI,
            AlarmPage.BTN_FNC_LEFT_SEC,
            AlarmPage.BTN_FNC_RIGHT_PRI,
            lock_btn,
        )

        # set components
        for c in [
            AlarmPage.BTN_KEY_0,
            AlarmPage.BTN_KEY_1,
            AlarmPage.BTN_KEY_2,
            AlarmPage.BTN_KEY_3,
            AlarmPage.BTN_KEY_4,
            AlarmPage.BTN_KEY_5,
            AlarmPage.BTN_KEY_6,
            AlarmPage.BTN_KEY_7,
            AlarmPage.BTN_KEY_8,
            AlarmPage.BTN_KEY_9,
            AlarmPage.BTN_KEY_CLR,
            AlarmPage.BTN_KEY_DEL,
        ]:
            self.add_component_callback(c, self.callback_keypad)
        self.add_component_callback(AlarmPage.B1_FNC, self.callback_unlock)
        self.set_function_component(
            component=AlarmPage.B1_FNC,
            fnc_id=AlarmPage.B1_FNC[1],
            fnc_name=AlarmPage.B1_FNC[1],
            color=COLORS["text_disabled"],
            text=self.translate("Unlock"),
            locked=getattr(panel, "locked", False),
        )

        # prepare unlock panel using config from locked panel
        if unlock_panel:
            config = panel.get_config(return_copy=False)
            config["mode"] = unlock_panel.get_mode()
            self._title = unlock_panel.get_title(self._title)
            self._unlock_code = unlock_panel.get("unlock_code")

        self.stop_rec_cmd(send_commands=True)

    def before_render_panel(self, panel: HAUIConfigPanel):
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

    def render_panel(self, panel: HAUIConfigPanel):
        self.update_components()

    # misc

    def update_components(self):
        # show either password stars or title
        if len(self._input):
            passwd = f"{AlarmPage.ICO_PASSWORD}" * len(self._input)
            self.set_component_text(AlarmPage.TXT_TITLE, passwd)
        else:
            self.set_component_text(AlarmPage.TXT_TITLE, self._title)

        # update unlock indicator in header
        color = COLORS["component"]
        if len(self._input) > 0:
            color = COLORS["component_accent"]
        self.update_function_component(AlarmPage.FNC_BTN_R_SEC, color=color)

        # update unlock button
        unlock_btn_enabled = False
        if str(self._input) == str(self._unlock_code):
            unlock_btn_enabled = True
        if unlock_btn_enabled:
            self.update_function_component(
                fnc_id=AlarmPage.B1_FNC[1],
                touch_events=True,
                color=COLORS["component_active"],
                color_pressed=COLORS["component"],
                back_color=COLORS["background"],
                back_color_pressed=COLORS["component_pressed"],
            )
        else:
            self.update_function_component(
                fnc_id=AlarmPage.B1_FNC[1],
                touch_events=False,
                color=COLORS["text_disabled"],
                color_pressed=COLORS["text_disabled"],
                back_color=COLORS["background"],
                back_color_pressed=COLORS["background"],
            )

    # callback

    def callback_keypad(self, event, component, button_state):
        if button_state:
            return
        self.log(f"Got keypad press: {component}-{button_state}")
        self.start_rec_cmd()

        # process keypad value
        if component[1].startswith("bKey"):
            bKeyVal = component[1][4:]
            if bKeyVal not in ["Del", "Clr"]:
                self._input += str(bKeyVal)
            elif bKeyVal == "Clr":
                self._input = ""
            elif bKeyVal == "Del":
                self._input = self._input[:-1]

        self.update_components()

        self.stop_rec_cmd(send_commands=True)

    def callback_unlock(self, event, component, button_state):
        if button_state:
            return
        if str(self._input) != str(self._unlock_code):
            self.start_rec_cmd()
            self._input = ""
            self.update_components()
            self.stop_rec_cmd(send_commands=True)
            return
        # unlock panel and close this unlock popup
        self.log(f"Panel {self._unlock_panel.id} unlocked, closing unlock popup.")
        config = self._unlock_panel.get_persistent_config(return_copy=False)
        config["locked"] = False
        navigation = self.app.controller["navigation"]
        navigation.close_panel()
