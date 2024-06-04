from ..mapping.const import ESP_REQUEST, ESP_RESPONSE, ESP_EVENT
from ..mapping.color import COLORS
from ..features import CoverFeatures
from ..config import HAUIConfigEntity
from . import HAUIPage


class CoverPage(HAUIPage):
    # https://developers.home-assistant.io/docs/core/entity/cover

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")

    # cover buttons
    BTN_UP, BTN_STOP, BTN_DOWN = (7, "bUp"), (8, "bStop"), (9, "bDown")
    H_VERT_POS = (10, "hVertPos")
    # info
    TXT_INFO = (11, "tInfo")

    _title = ""
    _cover_entity = None

    # panel

    def start_panel(self, panel):
        # set component callbacks
        self.add_component_callback(self.H_VERT_POS, self.callback_cover_pos)
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )
        # set light function button callbacks
        for btn in [
            self.BTN_UP,
            self.BTN_STOP,
            self.BTN_DOWN
        ]:
            self.add_component_callback(btn, self.callback_cover_buttons)
        # set entity
        entity = None
        entity_id = panel.get("entity_id")
        if entity_id:
            entity = HAUIConfigEntity(self.app, {"entity": entity_id})
        self.set_cover_entity(entity)

        # set title
        title = panel.get_title(self.translate("Cover"))
        if entity is not None:
            title = entity.get_entity_attr("friendly_name", title)
        self._title = title

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, self._title)
        self.update_cover_entity()

    # misc

    def set_cover_entity(self, entity):
        self._cover_entity = entity
        if not entity or not entity.has_entity_id():
            return
        supported_features = entity.get_entity_attr("supported_features", 0)
        current_position = entity.get_entity_attr("current_position", 0)
        # add listener
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_cover_entity)
        # up button
        visible = False
        if supported_features & CoverFeatures.OPEN:
            visible = True
        self.set_function_component(self.BTN_UP, self.BTN_UP[1], visible=visible, color=COLORS["component_active"])
        # stop button
        visible = False
        if supported_features & CoverFeatures.STOP:
            visible = True
        self.set_function_component(self.BTN_STOP, self.BTN_STOP[1], visible=visible, color=COLORS["component_active"])
        # down button
        visible = False
        if supported_features & CoverFeatures.CLOSE:
            visible = True
        self.set_function_component(self.BTN_DOWN, self.BTN_DOWN[1], visible=visible, color=COLORS["component_active"])
        # slider
        visible = False
        if supported_features & CoverFeatures.SET_POSITION:
            visible = True
        self.set_function_component(self.H_VERT_POS, self.H_VERT_POS[1], value=current_position, visible=visible)

    def update_cover_entity(self):
        self.set_component_text(self.TXT_TITLE, self._title)
        self.update_cover_controls()
        self.update_cover_info()

    def update_cover_info(self):
        if self._cover_entity is None:
            return
        entity = self._cover_entity
        current_position = entity.get_entity_attr("current_position", 0)
        self.set_component_text(self.TXT_INFO, f"{current_position}%")

    def update_cover_controls(self):
        if self._cover_entity is None:
            return
        entity = self._cover_entity
        state = entity.get_entity_state()
        supported_features = entity.get_entity_attr("supported_features", 0)
        current_position = entity.get_entity_attr("current_position", 0)

        # up button
        if supported_features & CoverFeatures.OPEN:
            touch_enabled = current_position < 100
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.BTN_UP[1],
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_UP[1], visible=False)
        # stop button
        if supported_features & CoverFeatures.STOP:
            touch_enabled = state in ["opening", "closing"]
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.BTN_STOP[1],
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_STOP[1], visible=False)
        # down button
        if supported_features & CoverFeatures.CLOSE:
            touch_enabled = current_position > 0
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(touch_enabled)
            self.update_function_component(
                self.BTN_DOWN[1],
                visible=True,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_DOWN[1], visible=False)
        # slider
        if supported_features & CoverFeatures.SET_POSITION:
            self.update_function_component(self.H_VERT_POS[1], value=current_position, visible=True)
        else:
            self.update_function_component(self.H_VERT_POS[1], visible=False)

    # callback

    def callback_cover_entity(self, entity, attribute, old, new, kwargs):
        if attribute in ["state", "current_position"]:
            self.start_rec_cmd()
            self.update_cover_entity()
            self.stop_rec_cmd(send_commands=True)
        else:
            self.log(f"Unknown cover entity attribute: {attribute}")

    def callback_cover_pos(self, event, component, button_state):
        if button_state:
            return
        self.log(f"Got cover pos press: {component}-{button_state}")
        self.send_mqtt(ESP_REQUEST["req_val"], self.H_VERT_POS[1], force=True)

    def callback_cover_buttons(self, event, component, button_state):
        if component == self.BTN_UP:
            self._cover_entity.call_entity_service("open_cover")
        elif component == self.BTN_STOP:
            self._cover_entity.call_entity_service("stop_cover")
        elif component == self.BTN_DOWN:
            self._cover_entity.call_entity_service("close_cover")

    # event

    def process_event(self, event):
        super().process_event(event)
        # requested values
        if event.name == ESP_RESPONSE["res_val"]:
            data = event.as_json()
            name = data.get("name", "")
            value = int(data.get("value", 0))
            if name == self.H_VERT_POS[1]:
                self.process_cover_pos(value)

    def process_cover_pos(self, pos):
        self._cover_entity.call_entity_service("set_cover_position", position=pos)
