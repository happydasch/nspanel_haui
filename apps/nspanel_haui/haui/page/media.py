from ..helper.icon import get_icon
from ..config import HAUIConfigEntity
from . import HAUIPage


class MediaPage(HAUIPage):

    ICO_SHUFFLE = get_icon('shuffle')
    ICO_SHUFFLE_DISABLED = get_icon('shuffle-disabled')
    ICO_PLAY = get_icon('play')
    ICO_PAUSE = get_icon('pause')
    ICO_PREV = get_icon('skip-previous')
    ICO_NEXT = get_icon('skip-next')

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # basic info
    BTN_ICON, TXT_NAME, TXT_INTERPRET = (7, 'bIcon'), (8, 'tName'), (9, 'tInterpret')
    # control
    BTN_SHUFFLE, BTN_PREV, BTN_PLAY_PAUSE = (10, 'bShuffle'), (11, 'bPrev'), (12, 'bPlayPause')
    BTN_NEXT, BTN_STOP = (13, 'bNext'), (14, 'bStop')
    BTN_VOL_DOWN, SLIDER_VOLUME, BTN_VOL_UP = (15, 'bVolDown'), (16, 'hVolume'), (17, 'bVolUp')
    # entities
    B1_ENTITY, B2_ENTITY, B3_ENTITY = (18, 'bEntity1'), (19, 'bEntity2'), (20, 'bEntity3')
    B4_ENTITY, B5_ENTITY = (21, 'bEntity4'), (22, 'bEntity5')
    # power button
    BTN_POWER = (23, 'bPower')

    # panel

    def start_panel(self, panel):
        # set function buttons
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, self.BTN_FNC_RIGHT_SEC)
        self.log(f'START MEDIA PANEL {panel.get_entities()[0].get_entity().attributes}')

        self._media_entity = None
        entities = panel.get_entities()
        if len(entities):
            self.set_media_entity(entities[0])

    def render_panel(self, panel):
        self.set_component_text(self.TXT_TITLE, panel.get_title())
        self.update_media_entity()

    # misc

    def set_media_entity(self, entity):
        self._media_entity = entity
        if not entity or not entity.has_entity_id():
            return
        self.add_entity_listener(
            entity.get_entity_id(),
            self.callback_media_entity,
            attribute='all')

    def update_media_entity(self):
        if self._media_entity is None:
            return
        name = self._media_entity.get_entity_attr('media_title', self.translate('Unknown Title'))
        interpret = self._media_entity.get_entity_attr('media_artist', self.translate('Unknown Interpret'))
        self.set_component_text(self.TXT_NAME, name)
        self.set_component_text(self.TXT_INTERPRET, interpret)

    # callback

    def callback_media_entity(self, entity, attribute, old, new, kwargs):
        self.log(f'Got media entity callback: {entity}.{attribute}:{new}')
        self.update_media_entity()


class PopupMediaPage(MediaPage):

    def before_render_panel(self, panel):
        entity = None
        entity_id = panel.get('entity_id')
        if entity_id:
            entity = HAUIConfigEntity(self.app, {'entity': entity_id})
        # check if the provided entity is valid
        # if a invalid entity is provided, return false
        # to prevent panel from rendering
        navigation = self.app.controller['navigation']
        if entity is None or not entity.has_entity_id() or not entity.has_entity():
            self.log('No entity for popup media provided')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_type() != 'media':
            self.log(f'Entity {entity.get_entity_id()} is not a media entity')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_state() == 'unavailable':
            self.log(f'Entity {entity.get_entity_id()} is not available')
            navigation.close_panel()
            return False
        self.set_media_entity(entity)
        return True
