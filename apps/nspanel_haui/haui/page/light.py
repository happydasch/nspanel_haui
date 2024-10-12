import threading
from typing import List, Optional

from ..mapping.const import ESP_REQUEST, ESP_RESPONSE, ESP_EVENT
from ..mapping.color import COLORS
from ..helper.color import pos_to_color, color_to_pos
from ..helper.icon import get_icon
from ..helper.value import scale
from ..abstract.panel import HAUIPanel
from ..abstract.entity import HAUIEntity
from ..abstract.event import HAUIEvent

from . import HAUIPage


class LightPage(HAUIPage):
    # https://developers.home-assistant.io/docs/core/entity/light

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # function buttons
    BTN_LIGHT_FNC_1, BTN_LIGHT_FNC_2 = (7, "btLightFnc1"), (8, "btLightFnc2")
    BTN_LIGHT_FNC_3, BTN_LIGHT_FNC_4 = (9, "btLightFnc3"), (10, "btLightFnc4")
    # selectors
    PIC_COLOR_WHEEL, H_BRIGHTNESS = (11, "pColorWheel"), (12, "hBrightness")
    H_COLOR_TEMP, BTN_POWER = (13, "hColorTemp"), (14, "bPower")
    # info
    TXT_INFO = (15, "tInfo")

    # hardcoded to not request too often, needed for color to pos
    PIC_COLOR_WHEEL_WH = 200
    PIC_COLOR_WHEEL_X = 125
    PIC_COLOR_WHEEL_Y = 75

    # icons for light functions
    ICO_BRIGHTNESS = get_icon("mdi:brightness-6")
    ICO_COLOR = get_icon("mdi:palette")
    ICO_COLOR_TEMP = get_icon("mdi:thermometer")
    ICO_EFFECT = get_icon("mdi:fire")
    ICO_POWER = get_icon("mdi:power")

    DEFAULT_FUNCTION = "brightness"

    _title = ""
    _light_entity = None
    _show_kelvin = True
    _color_temp_min = 0
    _color_temp_max = 0
    _light_functions = {}
    _current_light_function = None
    _touch_track = False
    _touch_timer = None
    _touch_color = None

    # panel

    def start_panel(self, panel: HAUIPanel) -> None:
        # set component callbacks
        self.add_component_callback(self.PIC_COLOR_WHEEL, self.callback_color_wheel)
        self.add_component_callback(self.H_BRIGHTNESS, self.callback_brightness)
        self.add_component_callback(self.H_COLOR_TEMP, self.callback_color_temp)
        self.add_component_callback(self.BTN_POWER, self.callback_power)
        # set function buttons
        power_off_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "power_off",
            "fnc_args": {
                "icon": self.ICO_POWER,
                "color": COLORS["component_accent"],
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            power_off_btn,
        )
        # set light function button callbacks
        for btn in [
            self.BTN_LIGHT_FNC_1,
            self.BTN_LIGHT_FNC_2,
            self.BTN_LIGHT_FNC_3,
            self.BTN_LIGHT_FNC_4,
        ]:
            self.add_component_callback(btn, self.callback_light_function_button)
        # if kelvin should be used instead of mired
        self._show_kelvin = panel.get("show_kelvin", self._show_kelvin)
        # set entity
        entity = None
        entity_id = panel.get("entity_id")
        if entity_id:
            entity = HAUIEntity(self.app, {"entity": entity_id})
        if entity is None:
            entities = panel.get_entities()
            if len(entities) > 0:
                entity = entities[0]
        self.set_light_entity(entity)
        # set title
        title = panel.get_title(self.translate("Light"))
        if entity is not None:
            title = entity.get_name()
        self._title = title

    def render_panel(self, panel: HAUIPanel) -> None:
        # set basic panel info
        self.set_component_text(self.TXT_TITLE, self._title)
        if not self.update_functions(self.DEFAULT_FUNCTION) and self.panel.get_mode() == "popup":
            self.stop_rec_cmd(send_commands=False)
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    # misc

    def set_light_entity(self, entity: HAUIEntity) -> None:
        self._light_entity = entity
        if not entity or not entity.has_entity_id():
            return
        attr_names = ["state", "effect", "brightness", "rgb_color"]
        if self._show_kelvin:
            attr_names.append("color_temp_kelvin")
            self._color_temp_min = entity.get_entity_attr("min_color_temp_kelvin", 0)
            self._color_temp_max = entity.get_entity_attr("max_color_temp_kelvin", 0)
        else:
            attr_names.append("color_temp")
            self._color_temp_min = entity.get_entity_attr("min_mireds", 0)
            self._color_temp_max = entity.get_entity_attr("max_mireds", 0)
        for attr_name in attr_names:
            self.add_entity_listener(
                entity.get_entity_id(), self.callback_light_entity, attribute=attr_name
            )

    def get_light_function(self, fnc_name: str) -> dict:
        for fnc in self._light_functions:
            if fnc["name"] == fnc_name:
                return fnc
        return None

    def get_entity_power(self) -> Optional[bool]:
        state = self._light_entity.get_entity_state()
        if state == "on":
            return True
        elif state == "off":
            return False
        return None

    def get_available_light_functions(self) -> List[dict]:
        if self._light_entity is None or not self._light_entity.has_entity():
            return []
        entity = self._light_entity.get_entity()

        # check what is supported
        power = self.get_entity_power()
        attr = entity.attributes
        color_modes = attr.get("supported_color_modes", [])

        # get currently available functions
        functions = []

        # brightness
        brightness = None
        if "brightness" in attr:
            brightness = bool(power)
        brightness_val = self._light_entity.get_entity_attr("brightness", 0)

        # color
        color = None
        color_val = 0
        list_color_modes = ["hs", "rgb", "rgbw", "rgbww", "xy"]
        if any(item in list_color_modes for item in color_modes):
            color = bool(power)

        # color temp
        color_temp = None
        if self._show_kelvin:
            color_temp_val = self._light_entity.get_entity_attr("color_temp_kelvin")
        else:
            color_temp_val = self._light_entity.get_entity_attr("color_temp")
        if "color_temp" in color_modes:
            color_temp = bool(power)

        # effects
        effect = None
        if "effect_list" in attr:
            effect = bool(power)
        effect_val = self._light_entity.get_entity_attr("effect", None)

        # update light functions
        idx = 1
        for ico, name, val, status, show_info in [
            (self.ICO_BRIGHTNESS, "brightness", brightness_val, brightness, True),
            (self.ICO_COLOR, "color", color_val, color, False),
            (self.ICO_COLOR_TEMP, "color_temp", color_temp_val, color_temp, True),
            (self.ICO_EFFECT, "effect", effect_val, effect, False),
        ]:
            if status:
                function = {
                    "idx": idx,
                    "ico": ico,
                    "name": name,
                    "val": val,
                    "status": status,
                    "show_info": show_info,
                }
                functions.append(function)
                idx += 1
        return functions

    def set_light_function_details(
        self, idx: int, ico: str, name: str, val: str,
        status: bool, show_info: bool, **kwargs
    ) -> None:
        btn = getattr(self, f"BTN_LIGHT_FNC_{idx}")
        self.set_component_text(btn, ico)
        if status is True:
            if self._current_light_function is not None:
                color = COLORS["component"]
            else:
                color = COLORS["component_active"]
            self.send_cmd(f"tsw {btn[1]},1")
            self.set_component_text_color(btn, color)
        else:
            self.send_cmd(f"tsw {btn[1]},0")
            self.set_component_text_color(btn, COLORS["text_inactive"])
        self.show_component(btn)
        return btn

    def set_brightness_info(self, value: int) -> None:
        fnc = self.get_light_function("brightness")
        if fnc is None:
            return
        # expected value: 0-255 -> 0-100
        if value is not None:
            conv_value = round(scale(value, (0, 255), (0, 100)))
        else:
            conv_value = 0
        if value is not None:
            txt_value = f"{conv_value}%"
        else:
            txt_value = self.translate("Off")
        self.set_component_value(self.H_BRIGHTNESS, conv_value)
        if self._current_light_function == "brightness":
            self.set_component_text(self.TXT_INFO, txt_value)

    def set_color_info(self, value: int) -> None:
        fnc = self.get_light_function("color")
        if fnc is None:
            return
        self.set_component_text_color(self.BTN_POWER, value)
        self.update_color_wheel()

    def set_color_temp_info(self, value: int) -> None:
        fnc = self.get_light_function("color_temp")
        if fnc is None:
            return
        # expected value: light_temp_min-light_temp_max -> 0-100
        if value is not None:
            conv_value = round(
                scale(value, (self._color_temp_max, self._color_temp_min), (0, 100))
            )
        else:
            value = 0
            conv_value = 0
        # show only info text if value is valid
        if value > 0:
            if self._show_kelvin:
                unit = "K"
            else:
                unit = "Mired"
            txt_value = f"{value}{unit}"
        else:
            txt_value = ""
        self.set_component_value(self.H_COLOR_TEMP, conv_value)
        if self._current_light_function == "color_temp":
            self.set_component_text(self.TXT_INFO, txt_value)

    def set_effect_info(self, value: str) -> None:
        fnc = self.get_light_function("effect")
        if fnc is None:
            return
        btn = fnc["btn"]
        if value is not None and value != "None":
            self.set_component_text_color(btn, COLORS["component_accent"])
        else:
            self.set_component_text_color(btn, COLORS["component"])

    def set_current_light_function(self, fnc: dict) -> None:
        functions = self.get_available_light_functions()
        for f in functions:
            if fnc is None:
                break
            if f["name"] == fnc["name"]:
                self._current_light_function = fnc["name"]
                return
        self._current_light_function = None

        if fnc is None:
            self.log(
                f"Unsetting function {fnc}, current: {self._current_light_function}"
            )
            self._current_light_function = fnc = None
        else:
            self._current_light_function = fnc["name"]
            # check for light function
            if fnc["name"] == "effect":
                navigation = self.app.controller["navigation"]
                selection = self._light_entity.get_entity_attr("effect_list", [])
                no_effect = self.translate("No effect")
                effects = []
                for name in selection:
                    value = name
                    if name == "None":
                        name = no_effect
                    effects.append({"value": value, "name": name})
                if len(effects) > 0:
                    navigation.open_popup(
                        "popup_select",
                        title=self.translate("Select effect"),
                        items=effects,
                        selection_callback_fnc=self.callback_effect,
                        close_on_select=True,
                    )

    def update_functions(self, default_function: Optional[str] = None) -> bool:
        functions = self.get_available_light_functions()
        if self._current_light_function is None and default_function is not None:
            self._current_light_function = default_function
        # check current function if it is still available
        names = [fnc["name"] for fnc in functions]
        if (
            self._current_light_function is not None
            and self._current_light_function not in names
        ):
            self._current_light_function = None

        for fnc in functions:
            if fnc["status"] is False or fnc["val"] is None:
                continue
            if fnc["name"] == "brightness":
                self.set_component_value(self.H_BRIGHTNESS, fnc["val"])
            elif fnc["name"] == "color_temp":
                self.set_component_value(self.H_COLOR_TEMP, fnc["val"])
            elif fnc["name"] == "color":
                self.update_color_wheel()

        # set light functions
        self._light_functions = functions
        light_function = None
        for fnc in self._light_functions:
            if fnc["name"] == self._current_light_function:
                light_function = fnc
                break
        if self.get_entity_power() is not None:
            self.update_power_button()
            self.update_light_functions(light_function)
            return True
        else:
            self.update_not_available()
        return False

    def update_light_functions(self, fnc: dict) -> None:
        # show function components
        to_show = None
        if fnc is not None:
            if fnc["name"] == "brightness":
                to_show = self.H_BRIGHTNESS
            elif fnc["name"] == "color":
                to_show = self.PIC_COLOR_WHEEL
            elif fnc["name"] == "color_temp":
                to_show = self.H_COLOR_TEMP
            # function info
            if not fnc["show_info"]:
                self.hide_component(self.TXT_INFO)
        else:
            self.hide_component(self.TXT_INFO)
        # function buttons
        for i in range(4):
            if i < len(self._light_functions):
                function = self._light_functions[i]
                btn = self.set_light_function_details(**function)
                function["btn"] = btn
                if function["name"] == self._current_light_function:
                    self.set_component_value(btn, 1)
                else:
                    self.set_component_value(btn, 0)
            else:
                idx = i + 1
                btn = getattr(self, f"BTN_LIGHT_FNC_{idx}")
                self.hide_component(btn)
        # function components
        for x in [self.H_BRIGHTNESS, self.PIC_COLOR_WHEEL, self.H_COLOR_TEMP]:
            if x == to_show:
                self.show_component(x)
            else:
                self.hide_component(x)
        if fnc is not None:
            if fnc["show_info"]:
                self.show_component(self.TXT_INFO)
            self.update_light_function_info(fnc)

    def update_light_function_info(self, fnc: dict) -> None:
        name = fnc["name"]
        val = fnc["val"]
        # set value
        if name == "brightness":
            self.set_brightness_info(val)
        elif name == "color":
            self.set_color_info(val)
        elif name == "color_temp":
            self.set_color_temp_info(val)
        elif name == "effect":
            self.set_effect_info(val)

    def update_color_wheel(self) -> None:
        if self._current_light_function != "color":
            return
        rgb_color = self._light_entity.get_entity_attr("rgb_color")
        if rgb_color is None:
            return
        # reduce wh to match max circle pos at border
        radius = 6
        wh = self.PIC_COLOR_WHEEL_WH - (2 * radius)
        # get pos xy based on smaller circle
        pos_x, pos_y = color_to_pos(rgb_color, wh)
        # refresh color wheel to remove circle
        self.send_cmd(f"ref {self.PIC_COLOR_WHEEL[0]}")
        if pos_x is not None and pos_y is not None and pos_x > 0 and pos_y > 0:
            self.log(f"Set color wheel: {pos_x},{pos_y}")
            # adjust pos based on radius of circle
            pos_x += self.PIC_COLOR_WHEEL_X + radius
            pos_y += self.PIC_COLOR_WHEEL_Y + radius
            self.send_cmd("doevents")
            # draw circle
            color = COLORS["component_pressed"]
            self.send_cmd(f"cirs {pos_x},{pos_y},{radius},{color}")

    def update_power_button(self) -> None:
        # update function button
        if (
            self._light_entity.get_entity_state() == "on"
            and self._current_light_function is not None
        ):
            color = COLORS["component_accent"]
            self.update_function_component(
                self.FNC_BTN_R_SEC, visible=True, color=color
            )
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

        # show on / off button only if there is nothing active
        if self._light_entity.get_entity_state() == "on":
            rgb_color = self._light_entity.get_entity_attr("rgb_color")
            color = self.parse_color(rgb_color)
        else:
            color = COLORS["entity_unavailable"]
        if self._current_light_function is None:
            self.set_component_text_color(self.BTN_POWER, color)
            self.show_component(self.BTN_POWER)
        else:
            self.hide_component(self.BTN_POWER)

    def update_not_available(self) -> None:
        self.log("update_not_available")
        color = COLORS["entity_unavailable"]
        self.set_component_text_color(self.BTN_POWER, color)
        self.show_component(self.BTN_POWER)

    # callback

    def callback_light_entity(self, entity, attribute, old, new, kwargs):
        self.log(f"Got light entity callback: {entity}.{attribute}:{new}")
        self.start_rec_cmd()
        if attribute == "state":
            if (
                not self.update_functions(self.DEFAULT_FUNCTION)
                and self.panel.get_mode() == "popup"
            ):
                self.stop_rec_cmd(send_commands=False)
                navigation = self.app.controller["navigation"]
                navigation.close_panel()
        elif attribute == "effect":
            fnc = self.get_light_function("effect")
            if fnc is None or fnc["val"] == new:
                return
            fnc["val"] = new
            if self._current_light_function == "effect":
                self.set_effect_info(new)
        elif attribute == "rgb_color":
            fnc = self.get_light_function("color")
            if fnc is None or fnc["val"] == new:
                return
            fnc["val"] = new
            self.set_color_info(new)
        elif attribute == "brightness":
            fnc = self.get_light_function("brightness")
            if fnc is None or fnc["val"] == new:
                return
            fnc["val"] = new
            self.set_brightness_info(new)
        elif ((attribute == "color_temp_kelvin" and self._show_kelvin)
                or (attribute == "color_temp" and not self._show_kelvin)):
            fnc = self.get_light_function("color_temp")
            if fnc is None or fnc["val"] == new:
                return
            fnc["val"] = new
            self.set_color_temp_info(new)
        self.stop_rec_cmd(send_commands=True)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id != self.FNC_BTN_R_SEC:
            return
        # turn of power on right secondary function button
        self.process_power(False)

    def callback_light_function_button(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            # wait for release
            return
        self.log(f"Got light function press: {component}-{button_state}")
        # check for current function
        fnc = [f for f in self._light_functions if f["btn"] == component]
        fnc = fnc[0] if len(fnc) else None
        # toggle current function
        if fnc["name"] == self._current_light_function:
            fnc = None
        self.set_current_light_function(fnc)
        # update components
        self.start_rec_cmd()
        for btn in [
            self.BTN_LIGHT_FNC_1,
            self.BTN_LIGHT_FNC_2,
            self.BTN_LIGHT_FNC_3,
            self.BTN_LIGHT_FNC_4,
        ]:
            if btn != component or (fnc and fnc["name"] == "effect"):
                self.set_component_value(btn, 0)
        # make sure power button is visible if needed
        self.update_power_button()
        self.update_light_functions(fnc)
        # make sure color is selected on color wheel
        if fnc and fnc["name"] == "color":
            self.update_color_wheel()
        self.stop_rec_cmd(send_commands=True)

    def callback_color_wheel(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log(f"Got color wheel press: {component}-{button_state}")
        if button_state:
            self._touch_track = True
            # will get set to false by touch end

    def callback_brightness(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got brightness press: {component}-{button_state}")
        self.send_mqtt(ESP_REQUEST["req_val"], self.H_BRIGHTNESS[1], force=True)

    def callback_color_temp(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got color temp press: {component}-{button_state}")
        self.send_mqtt(ESP_REQUEST["req_val"], self.H_COLOR_TEMP[1], force=True)

    def callback_power(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        if button_state:
            return
        self.log(f"Got power press: {component}-{button_state}")
        self.send_mqtt(ESP_REQUEST["req_val"], self.BTN_POWER[1], force=True)

    def callback_effect(self, selection: list) -> None:
        self.log(f"Got effect selection: {selection}")
        self._light_entity.call_entity_service("turn_on", effect=selection)

    # event

    def process_event(self, event: HAUIEvent):
        super().process_event(event)
        # touch on color wheel
        if event.name == ESP_EVENT["touch"]:
            values = event.as_str().split(",")
            if self._touch_track:
                pos_x, pos_y = [int(val) if val.isdigit() else 0 for val in values]
                if pos_x > 0 and pos_y > 0:
                    pos_x -= self.PIC_COLOR_WHEEL_X
                    pos_y -= self.PIC_COLOR_WHEEL_Y
                    color = pos_to_color(pos_x, pos_y, self.PIC_COLOR_WHEEL_WH)
                    self.process_color(color)
        elif event.name == ESP_EVENT["touch_end"]:
            values = event.as_str().split(",")
            if self._touch_track:
                self._touch_track = False
                _, _, pos_x, pos_y = [
                    int(val) if val.isdigit() else 0 for val in values
                ]
                if pos_x > 0 and pos_y > 0:
                    pos_x -= self.PIC_COLOR_WHEEL_X
                    pos_y -= self.PIC_COLOR_WHEEL_Y
                    color = pos_to_color(pos_x, pos_y, self.PIC_COLOR_WHEEL_WH)
                    self.process_color(color)
        # requested values
        if event.name == ESP_RESPONSE["res_val"]:
            data = event.as_json()
            name = data.get("name", "")
            value = int(data.get("value", 0))
            if name == self.BTN_POWER[1]:
                self.process_power(value)
            elif name == self.H_BRIGHTNESS[1]:
                self.process_brightness(value)
            elif name == self.H_COLOR_TEMP[1]:
                self.process_color_temp(value)

    def process_color(self, color):
        current_color = self._light_entity.get_entity_attr("rgb_color", None)
        if color is not None and self._touch_color != color and current_color != color:
            self.log(f"Processing color value {color}")
            if self._touch_timer is not None:
                self._touch_timer.cancel()
            self._touch_timer = threading.Timer(
                0.05,
                self._light_entity.call_entity_service,
                args=["turn_on"],
                kwargs={"rgb_color": color},
            )
            self._touch_timer.start()
            self._touch_color = color

    def process_brightness(self, brightness):
        self.log(f"Processing brightness value {brightness}")
        # scale 0-100 to ha brightness range
        brightness_ha = round(scale(brightness, (0, 100), (0, 255)))
        current_brightness = self._light_entity.get_entity_attr("brightness")
        if current_brightness != brightness_ha:
            self._light_entity.call_entity_service("turn_on", brightness=brightness_ha)

    def process_color_temp(self, color_temp):
        self.log(f"Processing color temp {color_temp}")
        # scale 0-100 from slider to color range of lamp
        color_temp = scale(
            color_temp,
            (0, 100),
            (self._color_temp_max, self._color_temp_min),
        )
        args = {}
        if self._show_kelvin:
            current_color_temp = self._light_entity.get_entity_attr("color_temp_kelvin")
            args["color_temp_kelvin"] = color_temp
        else:
            current_color_temp = self._light_entity.get_entity_attr("color_temp")
            args["color_temp"] = color_temp
        if current_color_temp != color_temp:
            self._light_entity.call_entity_service("turn_on", **args)

    def process_power(self, power):
        self.log(f"Processing power value {power}")
        if self._light_entity.get_entity_state() == "on":
            self._light_entity.call_entity_service("turn_off")
        else:
            self._light_entity.call_entity_service("turn_on")
