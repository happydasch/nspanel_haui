from __future__ import annotations

from ..abstract.component import Component
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import PopupPanelKey
from ..mapping.descriptor import PageDescriptor, _
from ..mapping.icons import ICO_LOCKED, ICO_PASSWORD
from .alarm import AlarmPage


class UnlockPage(AlarmPage):
    DESCRIPTOR = PageDescriptor(
        type_key="popup_unlock",
        page_name="unlock",
        page_id=17,
        label=_("Unlock"),
        description=_("PIN unlock overlay for locked panels."),
        is_system=True,
        sys_panel_default={
            "key": PopupPanelKey.POPUP_UNLOCK,
            "show_in_navigation": False,
        },
        popup_alias_for="alarm",
        can_show_popup=True,
        icon="mdi:lock-outline",
        # The panel to unlock; a card render turns the config into a panel.
        preview_kwargs={"unlock_panel": {"unlock_code": "1234"}},
    )

    _title = ""
    _unlock_panel: HAUIPanel | None = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # store panel infos
        self._unlock_panel = unlock_panel = panel.get("unlock_panel", None)
        # The system panel's default title is "", not missing.
        self._title = panel.get("title") or self.translate("Unlock Panel")
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
            # the alarm page's load event hides the keypad
            for c in self._keypad_buttons:
                self.on_release(c, self.callback_keypad)
                self.show_component(c)
            # match the alarm keypad's button styling
            self._style_keypad(panel)
            self.on_release(AlarmPage.COMPONENTS.b1_fnc, self.callback_unlock)
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
                self._title = unlock_panel.get_title(self._title)
                self._unlock_code = unlock_panel.get("unlock_code")

        # The header follows the panel it guards (prev/next in navigation). Not
        # as the popup's own state: navigation reads that on the next opening
        # and would make the popup the current navigation panel.
        self._auto_assign_fncs(
            panel, show_in_nav=unlock_panel.show_in_navigation() if unlock_panel else None
        )

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
        unlock_btn_enabled = str(self._input) == str(self._unlock_code)
        self.update_function_component(
            fnc_id=AlarmPage.COMPONENTS.b1_fnc.name,
            touch=unlock_btn_enabled,
            **self.button_color_args(unlock_btn_enabled, back_color=True),
        )

    # callback

    def callback_unlock(self, event: HAUIEvent, component: Component) -> None:
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
