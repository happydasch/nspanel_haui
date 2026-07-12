from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.color import ALARM_COLORS
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import ICO_PASSWORD
from ..utils.icon import get_icon


class AlarmPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="alarm",
        page_name="alarm",
        label=_("Alarm"),
        description=_("Alarm control panel with numeric keypad."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="alarm_control_panel",
                description=_("Alarm control panel item for arming/disarming the security system."),
                section=_("Alarm"),
            ),
        ],
        icon="mdi:shield-lock-outline",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_key_1=Component(8, "bKey1"),
        btn_key_2=Component(9, "bKey2"),
        btn_key_3=Component(10, "bKey3"),
        btn_key_4=Component(11, "bKey4"),
        btn_key_5=Component(12, "bKey5"),
        btn_key_6=Component(13, "bKey6"),
        btn_key_7=Component(14, "bKey7"),
        btn_key_8=Component(15, "bKey8"),
        btn_key_9=Component(16, "bKey9"),
        btn_key_clr=Component(17, "bKeyClr"),
        btn_key_0=Component(18, "bKey0"),
        btn_key_del=Component(19, "bKeyDel"),
        b1_fnc=Component(20, "b1Fnc"),
        b2_fnc=Component(21, "b2Fnc"),
        b3_fnc=Component(22, "b3Fnc"),
        b4_fnc=Component(23, "b4Fnc"),
    )

    # alarm state icons (pre-converted to display glyphs — the display's
    # set_component_text writes raw text, so "mdi:..." names must be resolved
    # to their icon-font characters here rather than passed through verbatim).
    _ALARM_ICONS = {
        "disarmed": get_icon("mdi:shield-off-outline"),
        "armed_home": get_icon("mdi:shield-home-outline"),
        "armed_away": get_icon("mdi:shield-lock-outline"),
        "armed_night": get_icon("mdi:weather-night"),
        "armed_vacation": get_icon("mdi:shield-airplane-outline"),
        "armed_custom_bypass": get_icon("mdi:shield-check-outline"),
        "pending": get_icon("mdi:shield-outline"),
        "triggered": get_icon("mdi:alert-circle-outline"),
        "arming": get_icon("mdi:shield-sync-outline"),
        "disarming": get_icon("mdi:shield-sync-outline"),
    }

    # alarm state -> ALARM_COLORS palette key
    _ALARM_COLOR_KEYS = {
        "disarmed": "disarmed",
        "armed_home": "armed",
        "armed_away": "armed",
        "armed_night": "armed",
        "armed_vacation": "armed",
        "armed_custom_bypass": "armed",
        "pending": "arming",
        "triggered": "armed",
        "arming": "arming",
        "disarming": "arming",
    }

    # AlarmControlPanelEntityFeature bit -> (arm service, button label).
    # Ordered by display priority; only the first four supported modes fit
    # the four action-button slots.
    _ARM_MODES: list[tuple[int, str, str]] = [
        (1, "alarm_arm_home", _("Home")),
        (2, "alarm_arm_away", _("Away")),
        (4, "alarm_arm_night", _("Night")),
        (32, "alarm_arm_vacation", _("Vacation")),
        (16, "alarm_arm_custom_bypass", _("Bypass")),
    ]

    # States that are not "disarmed": while in any of them the panel offers a
    # single disarm action instead of the arm-mode buttons.
    _DISARMED_STATES = ("", "disarmed", "unknown", "unavailable")

    def prepare(self) -> None:
        # currently configured alarm item (None if unconfigured/unavailable)
        self._item: HAUIItem | None = None
        # code digits entered on the keypad
        self._input: str = ""
        # component name -> alarm service for the four action buttons
        self._btn_actions: dict[str, str] = {}

    def _alarm_color(self, state: str) -> int:
        """Resolve the icon color for an alarm *state* from ALARM_COLORS.

        Falls back to the global ``text`` color for unmapped states.
        """
        key = self._ALARM_COLOR_KEYS.get(state)
        return ALARM_COLORS[key] if key is not None else self.get_color("text")

    @property
    def _action_buttons(self) -> tuple[Component, ...]:
        """The four bottom action-button components, in slot order."""
        return (
            self.COMPONENTS.b1_fnc,
            self.COMPONENTS.b2_fnc,
            self.COMPONENTS.b3_fnc,
            self.COMPONENTS.b4_fnc,
        )

    @property
    def _keypad_buttons(self) -> tuple[Component, ...]:
        """The twelve keypad components (digits, clear, delete)."""
        return (
            self.COMPONENTS.btn_key_0,
            self.COMPONENTS.btn_key_1,
            self.COMPONENTS.btn_key_2,
            self.COMPONENTS.btn_key_3,
            self.COMPONENTS.btn_key_4,
            self.COMPONENTS.btn_key_5,
            self.COMPONENTS.btn_key_6,
            self.COMPONENTS.btn_key_7,
            self.COMPONENTS.btn_key_8,
            self.COMPONENTS.btn_key_9,
            self.COMPONENTS.btn_key_clr,
            self.COMPONENTS.btn_key_del,
        )

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set function buttons
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            self.COMPONENTS.fnc_right_sec,
        )
        self.set_function_component(
            self.COMPONENTS.fnc_right_sec, self.FNC_BTN_R_SEC, "armed_indicator"
        )
        # resolve the configured alarm item and listen for state changes
        items = self._build_items_from_panel(panel, "item", "items")
        self._item = items[0] if items else None
        if self._item is not None:
            self.add_item_listener(
                self._item.get_item_id(), self.callback_alarm_state, "state"
            )
        # wire the numeric keypad
        for comp in self._keypad_buttons:
            self.on_release(comp, self.callback_keypad)
        # register the four action buttons (rendered/labelled in update_components)
        self._btn_actions = {}
        for comp in self._action_buttons:
            self.on_release(comp, self.callback_action)
            self.set_function_component(comp, comp.name, comp.name, visible=False)
        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_components()

    # rendering

    def update_components(self) -> None:
        """Render the title, armed indicator and action buttons for the state."""
        state = self._item.get_item_state() if self._item is not None else None
        state = state or ""

        # title: show entered code as password dots, otherwise the state label
        if self._input:
            title = ICO_PASSWORD * len(self._input)
        elif state:
            title = self.translate_state("alarm_control_panel", state)
        else:
            title = self.translate("Alarm")
        self.set_component_text(self.COMPONENTS.title, title)

        # armed indicator in the header
        self.update_function_component(
            self.FNC_BTN_R_SEC,
            icon=self._ALARM_ICONS.get(state, ""),
            color=self._alarm_color(state),
            visible=True,
        )

        # action buttons: disarm while armed, otherwise the supported arm modes
        self._btn_actions = {}
        actions = self._resolve_actions(state)
        for comp, action in zip(self._action_buttons, actions, strict=False):
            service, label = action
            self._btn_actions[comp.name] = service
            self._show_action_button(comp, label)
        for comp in self._action_buttons[len(actions):]:
            self.update_function_component(fnc_id=comp.name, visible=False)

    def _resolve_actions(self, state: str) -> list[tuple[str, str]]:
        """Return (service, label) pairs for the action buttons in this state."""
        if self._item is None:
            return []
        # armed / arming / pending / triggered -> a single disarm action
        if state not in self._DISARMED_STATES:
            return [("alarm_disarm", self.translate("Disarm"))]
        # disarmed -> arm modes from supported_features
        features = int(self._item.get_item_attr("supported_features", 0) or 0)
        # some integrations don't advertise features; fall back to the common set
        if not features:
            features = 1 | 2 | 4
        actions: list[tuple[str, str]] = []
        for bit, service, label in self._ARM_MODES:
            if features & bit:
                actions.append((service, self.translate(label)))
            if len(actions) >= len(self._action_buttons):
                break
        return actions

    def _show_action_button(self, component: Component, label: str) -> None:
        """Render a single action button as an enabled, labelled control."""
        color, color_pressed, back_color, back_color_pressed = self.get_button_colors(True)
        self.update_function_component(
            fnc_id=component.name,
            text=label,
            color=color,
            color_pressed=color_pressed,
            back_color=back_color,
            back_color_pressed=back_color_pressed,
            touch_events=True,
            visible=True,
        )

    def _action_needs_code(self, service: str) -> bool:
        """Whether *service* requires a code for the configured alarm entity."""
        if self._item is None:
            return False
        if not self._item.get_item_attr("code_format"):
            return False
        if service == "alarm_disarm":
            return True
        return bool(self._item.get_item_attr("code_arm_required", True))

    # callback

    def callback_alarm_state(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        with self.rec_cmd:
            # a state transition means any in-progress code entry is done
            if old != new:
                self._input = ""
            self.update_components()

    def callback_keypad(self, event: HAUIEvent, component: Component) -> None:
        with self.rec_cmd:
            name = component.name
            if name.startswith("bKey"):
                key = name[4:]
                if key == "Clr":
                    self._input = ""
                elif key == "Del":
                    self._input = self._input[:-1]
                else:
                    self._input += str(key)
            self.update_components()

    def callback_action(self, event: HAUIEvent, component: Component) -> None:
        if self._item is None:
            return
        service = self._btn_actions.get(component.name)
        if service is None:
            return
        code = self._input
        # code required but none entered -> keep the entry, do nothing
        if self._action_needs_code(service) and not code:
            self.log(f"Alarm action {service} requires a code")
            return
        kwargs: dict[str, Any] = {}
        if code:
            kwargs["code"] = code
        self.log(f"Alarm action {service} for {self._item.get_item_id()}")
        self._item.call_item_service(service, **kwargs)
        with self.rec_cmd:
            self._input = ""
            self.update_components()
