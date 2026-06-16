from __future__ import annotations

from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import ESPEvent, SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icons import ICO_BRIGHTNESS, ICO_COLOR, ICO_COLOR_TEMP, ICO_EFFECT, ICO_POWER
from ..utils.color import color_to_rect_pos, rect_pos_to_color
from ..utils.value import scale


class LightPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="light",
        page_name="light",
        label="Light",
        description="Single light with brightness, color temperature and effects.",
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="light",
                description="Light entity to control brightness, color and temperature.",
                section="Light",
            ),
            PageOption(
                key="show_kelvin",
                kind="bool",
                default=False,
                label="Show color temperature in Kelvin",
                description="Show Kelvin instead of Mireds (Mired is default).",
                section="Light",
            ),
        ],
        can_show_popup=True,
        icon="mdi:lightbulb-outline",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_light_fnc_1=Component(8, "btLightFnc1"),
        btn_light_fnc_2=Component(9, "btLightFnc2"),
        btn_light_fnc_3=Component(10, "btLightFnc3"),
        btn_light_fnc_4=Component(11, "btLightFnc4"),
        pic_color_rect=Component(12, "pColorWheel"),
        h_brightness=Component(13, "hBrightness"),
        h_color_temp=Component(14, "hColorTemp"),
        btn_power=Component(15, "bPower"),
        t_info=Component(16, "tInfo"),
    )

    # hardcoded to not request too often, needed for color to rect pos
    PIC_COLOR_RECT_W = 200
    PIC_COLOR_RECT_H = 200
    PIC_COLOR_RECT_X = 125
    PIC_COLOR_RECT_Y = 75

    DEFAULT_FUNCTION = "brightness"

    # panel

    def prepare(self) -> None:

        self._title = ""
        self._light_item: HAUIItem | None = None
        self._show_kelvin = True
        self._color_temp_min = 0
        self._color_temp_max = 0
        self._light_functions: list[dict[str, Any]] = []
        self._current_light_function: str | None = None
        self._touch_track = False
        self._touch_color: tuple[int, int, int] | None = None

    def start_panel(self, panel: HAUIPanel) -> None:
        # set component callbacks
        self.add_component_callback(self.COMPONENTS.pic_color_rect, self.callback_color_rect)
        self.bind_slider(self.COMPONENTS.h_brightness, self.process_brightness)
        self.bind_slider(self.COMPONENTS.h_color_temp, self.process_color_temp)
        self.on_release(self.COMPONENTS.btn_power, self.callback_power)
        # set function buttons
        power_off_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "power_off",
            "fnc_args": {
                "icon": ICO_POWER,
                "color": self.get_color("header_accent"),
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            power_off_btn,
        )
        # set light function button callbacks
        self.on_release({
            self.COMPONENTS.btn_light_fnc_1: self.callback_light_function_button,
            self.COMPONENTS.btn_light_fnc_2: self.callback_light_function_button,
            self.COMPONENTS.btn_light_fnc_3: self.callback_light_function_button,
            self.COMPONENTS.btn_light_fnc_4: self.callback_light_function_button,
        })
        # if kelvin should be used instead of mired
        self._show_kelvin = panel.get("show_kelvin", self._show_kelvin)
        # set item
        item = None
        entity_id = panel.get("item_id")
        if entity_id:
            item = HAUIItem(self.app, {"item": entity_id})
        if item is None:
            items = self._build_items_from_panel(panel, "items")
            if len(items) > 0:
                item = items[0]
        self.set_light_item(item)
        # set title
        title = panel.get_title(self.translate("Light"))
        if item is not None:
            title = item.get_name()
        self._title = title

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        # set basic panel info
        self.set_component_text(self.COMPONENTS.title, self._title)
        if not self.update_functions(self.DEFAULT_FUNCTION) and panel.can_show_popup():
            self.stop_rec_cmd(send_commands=False)
            navigation = self.app.controller["navigation"]
            navigation.close_panel()

    # misc

    def set_light_item(self, item: HAUIItem | None) -> None:
        self._light_item = item
        if not item or not item.has_item_id():
            return
        attr_names = ["state", "effect", "brightness", "rgb_color"]
        if self._show_kelvin:
            attr_names.append("color_temp_kelvin")
            self._color_temp_min = item.get_item_attr("min_color_temp_kelvin", 0)
            self._color_temp_max = item.get_item_attr("max_color_temp_kelvin", 0)
        else:
            attr_names.append("color_temp")
            self._color_temp_min = item.get_item_attr("min_mireds", 0)
            self._color_temp_max = item.get_item_attr("max_mireds", 0)
        for attr_name in attr_names:
            self.add_item_listener(
                item.get_item_id(), self.callback_light_item, attribute=attr_name
            )

    def get_light_function(self, fnc_name: str) -> dict | None:
        for fnc in self._light_functions:
            if fnc["name"] == fnc_name:
                return fnc
        return None

    def get_item_power(self) -> bool | None:
        if self._light_item is None:
            return None
        state = self._light_item.get_item_state()
        if state == "on":
            return True
        elif state == "off":
            return False
        return None

    def get_available_light_functions(self) -> list[dict]:
        if self._light_item is None or not self._light_item.has_item():
            return []
        entity = self._light_item.get_item()

        # check what is supported
        power = self.get_item_power()
        attr = entity.attributes
        color_modes = attr.get("supported_color_modes", [])

        # get currently available functions
        functions = []

        # brightness
        brightness = None
        if "brightness" in attr:
            brightness = bool(power)
        brightness_val = self._light_item.get_item_attr("brightness", 0)

        # color
        color = None
        color_val = 0
        list_color_modes = ["hs", "rgb", "rgbw", "rgbww", "xy"]
        if any(item in list_color_modes for item in color_modes):
            color = bool(power)

        # color temp
        color_temp = None
        if self._show_kelvin:
            color_temp_val = self._light_item.get_item_attr("color_temp_kelvin")
        else:
            color_temp_val = self._light_item.get_item_attr("color_temp")
        if "color_temp" in color_modes:
            color_temp = bool(power)

        # effects
        effect = None
        if "effect_list" in attr:
            effect = bool(power)
        effect_val = self._light_item.get_item_attr("effect", None)

        # update light functions
        idx = 1
        for ico, name, val, status, show_info in [
            (ICO_BRIGHTNESS, "brightness", brightness_val, brightness, True),
            (ICO_COLOR, "color", color_val, color, False),
            (ICO_COLOR_TEMP, "color_temp", color_temp_val, color_temp, True),
            (ICO_EFFECT, "effect", effect_val, effect, False),
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
        self,
        idx: int,
        ico: str,
        name: str,
        val: str,
        status: bool,
        show_info: bool,
        **kwargs: Any,
    ) -> Component:
        btn = getattr(self.COMPONENTS, f"btn_light_fnc_{idx}")
        self.set_component_text(btn, ico)
        if status is True:
            if self._current_light_function is not None:
                color = self.get_color("component_text")
            else:
                color = self.get_color("component_active")
            self.send_cmd(f"tsw {btn[1]},1")
            self.set_component_text_color(btn, color)
        else:
            self.send_cmd(f"tsw {btn[1]},0")
            self.set_component_text_color(btn, self.get_color("text_inactive"))
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
        self.set_component_value(self.COMPONENTS.h_brightness, conv_value)
        if self._current_light_function == "brightness":
            self.set_component_text(self.COMPONENTS.t_info, txt_value)

    def set_color_info(self, value: int) -> None:
        fnc = self.get_light_function("color")
        if fnc is None:
            return
        self.set_component_text_color(self.COMPONENTS.btn_power, value)
        self.update_color_rect()

    def set_color_temp_info(self, value: int) -> None:
        fnc = self.get_light_function("color_temp")
        if fnc is None:
            return
        # expected value: light_temp_min-light_temp_max -> 0-100
        if value is not None:
            conv_value = round(scale(value, (self._color_temp_max, self._color_temp_min), (0, 100)))
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
        self.set_component_value(self.COMPONENTS.h_color_temp, conv_value)
        if self._current_light_function == "color_temp":
            self.set_component_text(self.COMPONENTS.t_info, txt_value)

    def set_effect_info(self, value: str) -> None:
        fnc = self.get_light_function("effect")
        if fnc is None:
            return
        btn = fnc["btn"]
        if value is not None and value != "None":
            self.set_component_text_color(btn, self.get_color("component_accent"))
        else:
            self.set_component_text_color(btn, self.get_color("component_text"))

    def set_current_light_function(self, fnc: dict | None) -> None:
        functions = self.get_available_light_functions()
        for f in functions:
            if fnc is None:
                break
            if f["name"] == fnc["name"]:
                self._current_light_function = fnc["name"]
                return
        self._current_light_function = None

        if fnc is None:
            self.log(f"Unsetting function {fnc}, current: {self._current_light_function}")
            self._current_light_function = fnc = None
        else:
            self._current_light_function = fnc["name"]
            # check for light function
            if fnc["name"] == "effect" and self._light_item is not None:
                navigation = self.app.controller["navigation"]
                selection = self._light_item.get_item_attr("effect_list", [])
                no_effect = self.translate("No effect")
                effects = []
                for name in selection:
                    value = name
                    if name == "None":
                        name = no_effect
                    effects.append({"value": value, "name": name})
                if len(effects) > 0:
                    navigation.open_panel(
                        SysPanelKey.POPUP_SELECT,
                        title=self.translate("Select effect"),
                        items=effects,
                        selection_callback_fnc=self.callback_effect,
                        close_on_select=True,
                    )

    def update_functions(self, default_function: str | None = None) -> bool:
        functions = self.get_available_light_functions()
        if self._current_light_function is None and default_function is not None:
            self._current_light_function = default_function
        # check current function if it is still available
        names = [fnc["name"] for fnc in functions]
        if self._current_light_function is not None and self._current_light_function not in names:
            self._current_light_function = None

        # set light functions before updating slider values — the set_*_info
        # helpers look the function up in self._light_functions
        self._light_functions = functions
        for fnc in functions:
            if fnc["status"] is False or fnc["val"] is None:
                continue
            # use the info setters so raw entity values (brightness 0-255,
            # color temp in mireds/kelvin) are scaled to the 0-100 sliders
            if fnc["name"] == "brightness":
                self.set_brightness_info(fnc["val"])
            elif fnc["name"] == "color_temp":
                self.set_color_temp_info(fnc["val"])
            elif fnc["name"] == "color":
                self.update_color_rect()

        # find current light function
        light_function = None
        for fnc in self._light_functions:
            if fnc["name"] == self._current_light_function:
                light_function = fnc
                break
        if self.get_item_power() is not None:
            self.update_power_button()
            self.update_light_functions(light_function)
            return True
        else:
            self.update_not_available()
        return False

    def update_light_functions(self, fnc: dict | None) -> None:
        # show function components
        to_show = None
        if fnc is not None:
            if fnc["name"] == "brightness":
                to_show = self.COMPONENTS.h_brightness
            elif fnc["name"] == "color":
                to_show = self.COMPONENTS.pic_color_rect
            elif fnc["name"] == "color_temp":
                to_show = self.COMPONENTS.h_color_temp
            # function info
            if not fnc["show_info"]:
                self.hide_component(self.COMPONENTS.t_info)
        else:
            self.hide_component(self.COMPONENTS.t_info)
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
                btn = getattr(self.COMPONENTS, f"btn_light_fnc_{idx}")
                self.hide_component(btn)
        # function components
        for x in [
            self.COMPONENTS.h_brightness,
            self.COMPONENTS.pic_color_rect,
            self.COMPONENTS.h_color_temp,
        ]:
            if x == to_show:
                self.show_component(x)
            else:
                self.hide_component(x)
        if to_show in (self.COMPONENTS.h_brightness, self.COMPONENTS.h_color_temp):
            self.set_slider_color(to_show)
        if fnc is not None:
            if fnc["show_info"]:
                self.show_component(self.COMPONENTS.t_info)
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

    def update_color_rect(self) -> None:
        if self._current_light_function != "color":
            return
        if self._light_item is None:
            return
        rgb_color = self._light_item.get_item_attr("rgb_color")
        if rgb_color is None:
            return
        # Map RGB to (x, y) position in the rectangle
        pos_x, pos_y = color_to_rect_pos(rgb_color, self.PIC_COLOR_RECT_W, self.PIC_COLOR_RECT_H)
        # refresh picture widget to clear marker
        self.send_cmd(f"ref {self.COMPONENTS.pic_color_rect[0]}")
        if pos_x is not None and pos_y is not None and pos_x > 0 and pos_y > 0:
            self.log(f"Set color rect: {pos_x},{pos_y}")
            pos_x += self.PIC_COLOR_RECT_X
            pos_y += self.PIC_COLOR_RECT_Y
            self.send_cmd("doevents")
            # draw circle
            color = self.get_color("component_pressed")
            self.send_cmd(f"cirs {pos_x},{pos_y},{6},{color}")

    def update_power_button(self) -> None:
        if self._light_item is None:
            return
        # update function button
        if self._light_item.get_item_state() == "on" and self._current_light_function is not None:
            color = self.get_color("component_accent")
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, color=color)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

        # show on / off button only if there is nothing active
        if self._light_item.get_item_state() == "on":
            rgb_color = self._light_item.get_item_attr("rgb_color")
            color = self.parse_color(rgb_color)
        else:
            color = self.get_color("entity_unavailable")
        if self._current_light_function is None:
            self.set_component_text_color(self.COMPONENTS.btn_power, color)
            self.show_component(self.COMPONENTS.btn_power)
        else:
            self.hide_component(self.COMPONENTS.btn_power)

    def update_not_available(self) -> None:
        self.log("update_not_available")
        color = self.get_color("entity_unavailable")
        self.set_component_text_color(self.COMPONENTS.btn_power, color)
        self.show_component(self.COMPONENTS.btn_power)

    # callback

    def callback_light_item(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        self.log(f"Got light item callback: {item}.{attribute}:{new}")
        with self.rec_cmd:
            if attribute == "state":
                if (
                    not self.update_functions(self.DEFAULT_FUNCTION)
                    and self.panel is not None
                    and self.panel.can_show_popup()
                ):
                    navigation = self.app.controller["navigation"]
                    navigation.close_panel()
                    return
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
            elif (attribute == "color_temp_kelvin" and self._show_kelvin) or (
                attribute == "color_temp" and not self._show_kelvin
            ):
                fnc = self.get_light_function("color_temp")
                if fnc is None or fnc["val"] == new:
                    return
                fnc["val"] = new
                self.set_color_temp_info(new)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id != self.FNC_BTN_R_SEC:
            return
        # The right-secondary header button is the power-off icon, shown only when
        # the light is ON.  Always turn off — don't toggle.
        if self._light_item is not None:
            self._light_item.call_item_service("turn_off")

    def callback_light_function_button(
        self, event: HAUIEvent, component: Component
    ) -> None:
        self.log(f"Got light function press: {component}")
        # check for current function
        matches = [f for f in self._light_functions if f["btn"] == component]
        fnc: dict | None = matches[0] if matches else None
        # toggle current function
        if fnc is not None and fnc["name"] == self._current_light_function:
            fnc = None
        self.set_current_light_function(fnc)
        # update components
        with self.rec_cmd:
            for btn in [
                self.COMPONENTS.btn_light_fnc_1,
                self.COMPONENTS.btn_light_fnc_2,
                self.COMPONENTS.btn_light_fnc_3,
                self.COMPONENTS.btn_light_fnc_4,
            ]:
                if btn != component or (fnc and fnc["name"] == "effect"):
                    self.set_component_value(btn, 0)
            # make sure power button is visible if needed
            self.update_power_button()
            self.update_light_functions(fnc)
            # make sure color indicator is shown
            if fnc and fnc["name"] == "color":
                self.update_color_rect()

    def callback_color_rect(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log(f"Got color rect press: {component}-{button_state}")
        if button_state:
            self._touch_track = True
            # will get set to false by touch end

    def callback_power(self, event: HAUIEvent, component: Component) -> None:
        self.log(f"Got power press: {component}")
        # Toggle directly via HA state — no read request round-trip needed
        # because the Nextion button .val is unused (process_power ignores it).
        # The old REQ_VAL approach introduced a race: the ESP32's single
        # request global was overwritten when brightness and power reads
        # arrived in quick succession, causing read_response with the wrong
        # component name (e.g. "bPower" for a brightness read) and an
        # unintended toggle.
        self.process_power(0)

    def callback_effect(self, selection: list) -> None:
        self.log(f"Got effect selection: {selection}")
        if self._light_item is None:
            return
        self._light_item.call_item_service("turn_on", effect=selection)

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        # touch end on color rect
        if event.name == ESPEvent.TOUCH_END:
            if self._touch_track:
                self._touch_track = False
                # Parse TOUCH_END position robustly. The Nextion sends
                # comma-delimited "page_id,comp_id,pos_x,pos_y". Validate
                # length so a format mismatch doesn't crash the page.
                raw = event.as_str()
                pos_x = pos_y = 0
                if raw:
                    parts = raw.split(",")
                    if len(parts) >= 4:
                        try:
                            pos_x = int(parts[-2])
                            pos_y = int(parts[-1])
                        except (ValueError, TypeError):
                            pass
                if pos_x > 0 and pos_y > 0:
                    pos_x -= self.PIC_COLOR_RECT_X
                    pos_y -= self.PIC_COLOR_RECT_Y
                    color = rect_pos_to_color(
                        pos_x, pos_y, self.PIC_COLOR_RECT_W, self.PIC_COLOR_RECT_H
                    )
                    self.process_color(color)

    def process_color(self, color: tuple[int, int, int]) -> None:
        if self._light_item is None:
            return
        current_color = self._light_item.get_item_attr("rgb_color", None)
        if color is not None and self._touch_color != color and current_color != color:
            self.log(f"Processing color value {color}")
            self._touch_color = color
            # Debounce: coalesce rapid color-drag events into one service call
            # after the storm settles (50 ms).  Replaces a fragile threading.Timer
            # whose cancel() could race with the timer firing.
            item = self._light_item
            self.debouncer.call(
                "light_color",
                lambda: item.call_item_service("turn_on", rgb_color=color)
            )

    def process_brightness(self, brightness: int) -> None:
        if not self._in_read_callback:
            self.log(
                f"process_brightness: value={brightness} ignored "
                f"(not from read_response — likely button_state leak)"
            )
            return
        self.log(
            f"Slider brightness value {brightness}"
            f" from component {self.COMPONENTS.h_brightness.name}"
        )
        if self._light_item is None:
            return
        # scale 0-100 to ha brightness range, min 1 to avoid turning off
        brightness_ha = round(scale(brightness, (0, 100), (1, 255)))
        current_brightness = self._light_item.get_item_attr("brightness")
        if current_brightness != brightness_ha:
            self._light_item.call_item_service("turn_on", brightness=brightness_ha)

    def process_color_temp(self, color_temp: int) -> None:
        if not self._in_read_callback:
            self.log(
                f"process_color_temp: value={color_temp} ignored "
                f"(not from read_response — likely button_state leak)"
            )
            return
        self.log(
            f"Slider color_temp value {color_temp}"
            f" from component {self.COMPONENTS.h_color_temp.name}"
        )
        if self._light_item is None:
            return
        # scale 0-100 from slider to color range of lamp
        color_temp = int(
            scale(
                color_temp,
                (0, 100),
                (self._color_temp_max, self._color_temp_min),
            )
        )
        args = {}
        if self._show_kelvin:
            current_color_temp = self._light_item.get_item_attr("color_temp_kelvin")
            args["color_temp_kelvin"] = color_temp
        else:
            current_color_temp = self._light_item.get_item_attr("color_temp")
            args["color_temp"] = color_temp
        if current_color_temp != color_temp:
            self._light_item.call_item_service("turn_on", **args)

    def process_power(self, power: int) -> None:
        self.log(f"Processing power value {power}")
        if self._light_item is None:
            return
        # Toggle based on current HA state.  The `power` parameter is unused
        # (the Nextion button's .val is always 0) — the actual on/off state
        # is read from the entity.  This avoids an unnecessary read request
        # round-trip that created a race with brightness/color_temp reads.
        if self._light_item.get_item_state() == "on":
            self._light_item.call_item_service("turn_off")
        else:
            self._light_item.call_item_service("turn_on")
