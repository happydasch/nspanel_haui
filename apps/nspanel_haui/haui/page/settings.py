from ..mapping.const import ESP_REQUEST, ESP_RESPONSE
from ..abstract.panel import HAUIPanel
from ..abstract.event import HAUIEvent

from . import HAUIPage


class SettingsPage(HAUIPage):
    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # subtitle brightness
    TXT_BRGHT_TITLE = (7, "tBrghtTitle")
    # brightness components
    TXT_BRGHT_ICO, SLD_BRGHT, TXT_BRGHT_PCT = (
        (8, "tBrghtIco"),
        (9, "hBrght"),
        (10, "tBrghtPct"),
    )
    TXT_BRGHT_DIM_ICO, SLD_BRGHT_DIM, TXT_BRGHT_DIM_PCT = (
        (11, "tBrghtDimIco"),
        (12, "hBrghtDim"),
        (13, "tBrghtDimPct"),
    )

    # panel

    def start_panel(self, panel: HAUIPanel):
        name = self.app.device.get_name()

        # auto dimming component
        self.auto_dimming = self.app.get_entity(
            f"switch.{name}_use_auto_dimming"
        )
        self._use_auto_dimming = self.auto_dimming.get_state()
        self.auto_dimming.turn_off()

        # brightness components
        self.brightness_full_entity = self.app.get_entity(
            f"number.{name}_brightness_full"
        )
        self.brightness_dimmed_entity = self.app.get_entity(
            f"number.{name}_brightness_dimmed"
        )
        self._handle_brightness_full = self.brightness_full_entity.listen_state(
            self.callback_brightness
        )
        self._handle_brightness_dimmed = self.brightness_dimmed_entity.listen_state(
            self.callback_brightness
        )
        self._full_brightness = self.brightness_full_entity.get_state()
        self._dimmed_brightness = self.brightness_dimmed_entity.get_state()

        # display components
        self.add_component_callback(self.SLD_BRGHT, self.callback_slider_brightness)
        self.add_component_callback(self.SLD_BRGHT_DIM, self.callback_slider_brightness)

        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )

    def stop_panel(self, panel: HAUIPanel):
        # remove exisiting handles
        if self._handle_brightness_full:
            self.app.cancel_listen_state(self._handle_brightness_full)
        if self._handle_brightness_dimmed:
            self.app.cancel_listen_state(self._handle_brightness_dimmed)
        if self._use_auto_dimming:
            self.auto_dimming.turn_on()

    def render_panel(self, panel: HAUIPanel):
        title = panel.get_title(self.translate("Settings"))
        self.set_component_text(self.TXT_TITLE, title)
        self.set_component_text(
            self.TXT_BRGHT_TITLE, self.translate("Full and Dimmed Brightness:")
        )
        # update settings
        brightness_full_state = self.brightness_full_entity.get_state()
        if brightness_full_state != "unavailable":
            brightness_full = int(float(brightness_full_state))
            self.set_brightness_full_slider(brightness_full)
        brightness_dimmed_state = self.brightness_dimmed_entity.get_state()
        if brightness_dimmed_state != "unavailable":
            brightness_dimmed = int(float(brightness_dimmed_state))
            self.set_brightness_dim_slider(brightness_dimmed)

    # misc

    def set_brightness_full_slider(self, value):
        self.set_component_value(self.SLD_BRGHT, value)
        self.send_cmd(f"click {self.TXT_BRGHT_PCT[1]},0")

    def set_brightness_dim_slider(self, value):
        self.set_component_value(self.SLD_BRGHT_DIM, value)
        self.send_cmd(f"click {self.TXT_BRGHT_DIM_PCT[1]},0")

    # callback

    def callback_slider_brightness(self, event, component, button_state):
        self.log(f"Got slider brightness press: {component}-{button_state}")
        if button_state:
            return
        self.send_mqtt(ESP_REQUEST["req_val"], component[1], force=True)

    def callback_brightness(self, entity, attribute, old, new, cb_args):
        self.log(f"Got brightness callback: {entity}.{attribute}:{new}")
        # callback from ha
        if (
            self.brightness_full_entity
            and entity == self.brightness_full_entity.entity_id
        ):
            if new.isnumeric():
                if self._full_brightness != new:
                    self._full_brightness = new
                self.set_brightness_full_slider(new)
        elif (
            self.brightness_dimmed_entity
            and entity == self.brightness_dimmed_entity.entity_id
        ):
            if new.isnumeric():
                if self._dimmed_brightness != new:
                    self._dimmed_brightness = new
                self.set_brightness_dim_slider(new)

    # event

    def process_event(self, event: HAUIEvent):
        super().process_event(event)
        # check for values for full and dimmed brightness
        if event.name == ESP_RESPONSE["res_val"]:
            # parse json response, set brightness
            data = event.as_json()
            if data.get("name", "") == self.SLD_BRGHT[1]:
                if self._full_brightness != data["value"]:
                    self._full_brightness = data["value"]
                    self.brightness_full_entity.set_state(state=data["value"])
            elif data.get("name", "") == self.SLD_BRGHT_DIM[1]:
                if self._dimmed_brightness != data["value"]:
                    self._dimmed_brightness = data["value"]
                    self.brightness_dimmed_entity.set_state(state=data["value"])
