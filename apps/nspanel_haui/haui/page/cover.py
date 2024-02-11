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
    H_POS = (10, "hPos")

    _title = ""
    _entity = None
    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            self.BTN_FNC_RIGHT_SEC,
        )

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
        self.update_cover_entity()

    # misc

    def set_cover_entity(self, entity):
        self._entity = entity
        if not entity or not entity.has_entity_id():
            return
        # add listener
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_cover_entity)

    def update_cover_entity(self):
        self.set_component_text(self.TXT_TITLE, self._title)
        if self._entity is None:
            return
        entity = self._entity
        state = entity.get_entity_state()
        features = entity.get_entity_attr("supported_features", 0)
        # TODO

    # callback

    def callback_cover_entity(self, entity, attribute, old, new, kwargs):
        if attribute == "state":
            self.start_rec_cmd()
            self.update_cover_entity()
            self.stop_rec_cmd(send_commands=True)
        else:
            self.log(f"Unknown cover entity attribute: {attribute}")
