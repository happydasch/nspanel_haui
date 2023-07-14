import datetime
import threading

from ..const import ESP_REQUEST, ESP_RESPONSE
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..config import HAUIConfigEntity

from . import HAUIPage


class MediaPage(HAUIPage):

    '''
    Supported features for media player:
    https://github.com/home-assistant/core/blob/dev/homeassistant/components/media_player/const.py
    PAUSE = 1                   (0x0001)
    SEEK = 2                    (0x0002)
    VOLUME_SET = 4              (0x0004)
    VOLUME_MUTE = 8             (0x0008)
    PREVIOUS_TRACK = 16         (0x0010)
    NEXT_TRACK = 32             (0x0020)
    TURN_ON = 128               (0x0080)
    TURN_OFF = 256              (0x0100)
    PLAY_MEDIA = 512            (0x0200)
    VOLUME_STEP = 1024          (0x0400)
    SELECT_SOURCE = 2048        (0x0800)
    STOP = 4096                 (0x1000)
    CLEAR_PLAYLIST = 8192       (0x2000)
    PLAY = 16384                (0x4000)
    SHUFFLE_SET = 32768         (0x8000)
    SELECT_SOUND_MODE = 65536   (0x00010000)
    BROWSE_MEDIA = 131072       (0x00020000)
    REPEAT_SET = 262144         (0x00040000)
    GROUPING = 524288           (0x00080000)
    MEDIA_ENQUEUE = 2097152     (0x00200000)
    '''

    ICO_PLAY = get_icon('play')
    ICO_PAUSE = get_icon('pause')
    ICO_STOP = get_icon('stop')
    ICO_PREV = get_icon('skip-previous')
    ICO_NEXT = get_icon('skip-next')
    # repeat icons
    ICO_REPEAT = get_icon('repeat')
    ICO_REPEAT_ONE = get_icon('repeat-once')
    ICO_REPEAT_OFF = get_icon('repeat-off')
    # shuffle icons
    ICO_SHUFFLE = get_icon('shuffle')
    ICO_SHUFFLE_DISABLED = get_icon('shuffle-disabled')
    # volume icons
    ICO_VOLUME_DOWN = get_icon('volume-minus')
    ICO_VOLUME_UP = get_icon('volume-plus')
    # misc
    ICO_SELECT_SOURCE = get_icon('speaker')
    ICO_SELECT_PLAYLIST = get_icon('playlist-music')
    ICO_SELECT_TRACK = get_icon('playlist-play')

    # common components
    TXT_TITLE = (2, 'tTitle')
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, 'bFncLPri'), (4, 'bFncLSec')
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, 'bFncRPri'), (6, 'bFncRSec')
    # basic info
    TXT_MEDIA_ICON, TXT_MEDIA_TITLE, TXT_MEDIA_INTERPRET = (7, 'tIcon'), (8, 'tMTitle'), (9, 'tMInterpret')
    # control
    BTN_SHUFFLE, BTN_PREV, BTN_PLAY = (10, 'bShuffle'), (11, 'bPrev'), (12, 'bPlay')
    BTN_NEXT, BTN_REPEAT = (13, 'bNext'), (14, 'bRepeat')
    BTN_VOL_DOWN, BTN_VOL_UP, SLD_VOL = (15, 'bVolDown'), (16, 'bVolUp'), (17, 'hVolume')
    # m entities
    M1_BTN, M1_ICO, M1_NAME, M1_OVL = (18, 'm1Btn'), (19, 'm1Icon'), (20, 'm1Name'), (21, 'm1Overlay')
    M2_BTN, M2_ICO, M2_NAME, M2_OVL = (22, 'm2Btn'), (23, 'm2Icon'), (24, 'm2Name'), (25, 'm2Overlay')
    M3_BTN, M3_ICO, M3_NAME, M3_OVL = (26, 'm3Btn'), (27, 'm3Icon'), (28, 'm3Name'), (29, 'm3Overlay')
    # progress bar
    J_PROGRESS = (30, 'jProgress')

    SCROLLING_INTERVAL = 0.5
    PROGRESS_INTERVAL = 0.5

    # panel

    def start_panel(self, panel):
        # set function buttons
        media_state_btn = {
            'fnc_component': self.BTN_FNC_RIGHT_SEC,
            'fnc_id': self.FNC_BTN_R_SEC,
            'fnc_name': 'media_state',
            'fnc_args': {
                'icon': self.ICO_STOP,
                'color': COLORS['component_accent'],
                'visible': False
            }
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI, self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI, media_state_btn)
        # set title and entity
        title = panel.get_title(self.translate('Media'))
        entity = None
        entity_id = panel.get('entity_id')
        if entity_id:
            entity = HAUIConfigEntity(self.app, {'entity': entity_id})
        entities = panel.get_entities()
        if len(entities):
            entity = entities[0]
        if entity is not None:
            title = entity.get_entity_attr('friendly_name', title)
            self.set_media_entity(entity)
        self._media_entity = entity
        self._title = title
        self._media_title = ''
        self._media_interpret = ''
        self._media_channel = ''
        self._timer_progress = None
        self._timer_scrolling = None

    def render_panel(self, panel):
        self.update_media_entity()

    def stop_panel(self, panel):
        if self._timer_progress is not None:
            self._timer_progress.cancel()
            self._timer_progress = None
        if self._timer_scrolling is not None:
            self._timer_scrolling.cancel()
            self._timer_scrolling = None

    # misc

    def set_media_entity(self, entity):
        self._media_entity = entity
        if not entity or not entity.has_entity_id():
            return
        supported_features = entity.get_entity_attr('supported_features', 0)
        # add listener
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity)
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='media_title')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='media_artist')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='media_channel')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='volume_level')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='is_volume_muted')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='repeat')
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity, attribute='shuffle')
        # play button
        play = False
        if supported_features & 0x0001 or supported_features & 0x4000:
            play = True
        self.set_function_component(
            self.BTN_PLAY, self.BTN_PLAY[1], 'media_play',
            icon=self.ICO_PLAY,
            color=COLORS['component_active'],
            visible=play)
        # volume buttons
        volume_visible = False
        if supported_features & 0x0004:
            volume_visible = True
        self.set_function_component(
            self.BTN_VOL_DOWN, self.BTN_VOL_DOWN[1], 'volume_down',
            icon=self.ICO_VOLUME_DOWN,
            color=COLORS['component_active'],
            visible=volume_visible)
        self.set_function_component(
            self.BTN_VOL_UP, self.BTN_VOL_UP[1], 'volume_up',
            icon=self.ICO_VOLUME_UP,
            color=COLORS['component_active'],
            visible=volume_visible)
        self.set_function_component(
            self.SLD_VOL, self.SLD_VOL[1], 'set_volume',
            visible=volume_visible)
        # prev button
        prev_track = False
        if supported_features & 0x0010:
            prev_track = True
        self.set_function_component(
            self.BTN_PREV, self.BTN_PREV[1], 'media_prev',
            icon=self.ICO_PREV,
            color=COLORS['component_active'],
            visible=prev_track)
        # next button
        next_track = False
        if supported_features & 0x0020:
            next_track = True
        self.set_function_component(
            self.BTN_NEXT, self.BTN_NEXT[1], 'media_next',
            icon=self.ICO_NEXT,
            color=COLORS['component_active'],
            visible=next_track)
        # shuffle button
        shuffle = False
        if supported_features & 0x8000:
            shuffle = True
        self.set_function_component(
            self.BTN_SHUFFLE, self.BTN_SHUFFLE[1], 'media_shuffle',
            icon=self.ICO_SHUFFLE_DISABLED,
            color=COLORS['component_active'],
            visible=shuffle)
        # repeat button
        repeat = False
        if supported_features & 0x00040000:
            repeat = True
        self.set_function_component(
            self.BTN_REPEAT, self.BTN_REPEAT[1], 'media_repeat',
            icon=self.ICO_REPEAT_OFF,
            color=COLORS['component_active'],
            visible=repeat)
        # progress bar
        # visibility will be set by timer calls when media is playing
        self.set_function_component(
            self.J_PROGRESS, self.J_PROGRESS[1], 'progress',
            color=COLORS['text_inactive'],
            back_color=COLORS['text_disabled'],
            value=0)
        # add media buttons
        self.set_media_button(1, self.ICO_SELECT_SOURCE, self.translate('Source'), False)
        self.add_component_callback(self.M1_OVL, self.callback_select_source)
        self.set_media_button(2, self.ICO_SELECT_PLAYLIST, self.translate('Playlist'), False)
        self.add_component_callback(self.M2_OVL, self.callback_select_playlist)
        self.set_media_button(3, self.ICO_SELECT_TRACK, self.translate('Track'), False)
        self.add_component_callback(self.M3_OVL, self.callback_select_track)

    def set_media_button(self, idx, icon, name, visible=True):
        m_btn = getattr(self, f'M{idx}_BTN')
        m_ico = getattr(self, f'M{idx}_ICO')
        m_name = getattr(self, f'M{idx}_NAME')
        m_ovl = getattr(self, f'M{idx}_OVL')
        for x in [m_btn, m_ico, m_name, m_ovl]:
            self.show_component(x) if visible else self.hide_component(x)
        self.set_component_text(m_ico, icon)
        self.set_component_text(m_name, name)

    def update_media_title(self):
        title = self._title
        if self._media_entity:
            entity = self._media_entity
            # media channel
            media_channel = entity.get_entity_attr('media_channel')
            if media_channel:
                title = media_channel
        self.set_component_text(self.TXT_TITLE, title)

    def update_media_entity(self):
        self.update_media_title()
        # media details
        self.update_media_info()
        self.update_media_controls()
        self.update_volume()
        self.update_progress()
        # power button
        self.update_power_button()

    def update_media_info(self):
        if self._media_entity is None:
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        media_title = entity.get_entity_attr('media_title', '')
        media_interpret = entity.get_entity_attr('media_artist', '')
        media_channel = entity.get_entity_attr('media_channel', '')
        if state == 'playing':
            if not media_title:
                media_title = self.translate('Unknown Title')
            if not media_interpret:
                if media_channel:
                    media_interpret = media_channel
                else:
                    media_interpret = self.translate('Unknown Interpret')
        self._media_title = media_title
        if len(self._media_title) > 20:
            self._media_title = f'{self._media_title} {get_icon("minus")} '
        self._media_interpret = media_interpret
        if len(self._media_interpret) > 30:
            self._media_interpret = f'{self._media_interpret} {get_icon("minus")} '
        self._media_channel = media_channel
        self.set_component_text(self.TXT_MEDIA_ICON, entity.get_icon())
        self.set_component_text_color(self.TXT_MEDIA_ICON, entity.get_color())
        self.set_component_text(self.TXT_MEDIA_TITLE, media_title)
        self.set_component_text(self.TXT_MEDIA_INTERPRET, media_interpret)
        if self._timer_scrolling is None:
            self._scrolling_text()

    def _scrolling_text(self):
        if len(self._media_title) > 20:
            self._media_title = self._media_title[1:] + self._media_title[0]
            self.set_component_text(self.TXT_MEDIA_TITLE, self._media_title)
        if len(self._media_interpret) > 30:
            self._media_interpret = self._media_interpret[1:] + self._media_interpret[0]
            self.set_component_text(self.TXT_MEDIA_INTERPRET, self._media_interpret)
        if self.is_started():
            if self._timer_scrolling:
                self._timer_scrolling.cancel()
            self._timer_scrolling = threading.Timer(self.SCROLLING_INTERVAL, self._scrolling_text)
            self._timer_scrolling.start()

    def update_media_controls(self):
        if self._media_entity is None:
            for fnc_id in [
                self.BTN_SHUFFLE[1], self.BTN_PREV[1], self.BTN_PLAY[1], self.BTN_NEXT[1],
                self.BTN_REPEAT[1], self.BTN_VOL_DOWN[1], self.BTN_VOL_UP[1]
            ]:
                self.update_function_component(fnc_id, visible=False)
            self.update_function_component(self.SLD_VOL[1], visible=False)
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        supported_features = entity.get_entity_attr('supported_features', 0)
        queue_position = entity.get_entity_attr('queue_position', 0)
        queue_size = entity.get_entity_attr('queue_size', 0)
        # shuffle
        if supported_features & 0x8000:
            icon = None
            touch_enabled = queue_size > 0
            color, color_pressed, back_color, back_color_pressed = self.get_button_colors(queue_size > 1)
            shuffle = entity.get_entity_attr('shuffle')
            if shuffle is False:
                icon = self.ICO_SHUFFLE_DISABLED
            elif shuffle is True:
                icon = self.ICO_SHUFFLE
            self.update_function_component(
                self.BTN_SHUFFLE[1], visible=True, icon=icon, touch=touch_enabled,
                color=color, color_pressed=color_pressed, back_color_pressed=back_color_pressed)
        else:
            self.update_function_component(self.BTN_SHUFFLE[1], visible=False)
        # repeat
        if supported_features & 0x00040000:
            icon = None
            touch_enabled = queue_size > 0
            color, color_pressed, back_color, back_color_pressed = self.get_button_colors(queue_size > 0)
            repeat = entity.get_entity_attr('repeat')
            if repeat == 'all':
                icon = self.ICO_REPEAT
            elif repeat == 'one':
                icon = self.ICO_REPEAT_ONE
            elif repeat == 'off':
                icon = self.ICO_REPEAT_OFF
            self.update_function_component(
                self.BTN_REPEAT[1], visible=True, icon=icon, touch=touch_enabled,
                color=color, color_pressed=color_pressed, back_color_pressed=back_color_pressed)
        else:
            self.update_function_component(self.BTN_REPEAT[1], visible=False)
        # play, pause
        if supported_features & 0x4000 or supported_features & 0x0001:
            play_icon = self.ICO_PAUSE if state == 'playing' else self.ICO_PLAY
            self.update_function_component(self.BTN_PLAY[1], visible=True, icon=play_icon)
        else:
            self.update_function_component(self.BTN_PLAY[1], visible=False)
        # prev
        if supported_features & 0x0010:
            prev_enabled = False
            if queue_position > 1:
                prev_enabled = True
            color, color_pressed, back_color, back_color_pressed = self.get_button_colors(prev_enabled)
            self.update_function_component(
                self.BTN_PREV[1], visible=True, touch=prev_enabled,
                color=color, color_pressed=color_pressed, back_color_pressed=back_color_pressed)
        else:
            self.update_function_component(self.BTN_PREV[1], visible=False)
        # next
        if supported_features & 0x0020:
            next_enabled = False
            if queue_position < queue_size:
                next_enabled = True
            color, color_pressed, back_color, back_color_pressed = self.get_button_colors(next_enabled)
            self.update_function_component(
                self.BTN_NEXT[1], visible=True, touch=next_enabled,
                color=color, color_pressed=color_pressed, back_color_pressed=back_color_pressed)
        else:
            self.update_function_component(self.BTN_NEXT[1], visible=False)

    def update_volume(self):
        if self._media_entity is None:
            return
        entity = self._media_entity
        volume = int(entity.get_entity_attr('volume_level', 0) * 100)
        self.update_function_component(self.SLD_VOL[1], value=volume)
        self.update_function_component(self.BTN_VOL_DOWN[1], visible=True)
        self.update_function_component(self.BTN_VOL_UP[1], visible=True)

    def update_progress(self):
        if self._media_entity is None:
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        media_duration = entity.get_entity_attr('media_duration', 0)
        media_position = entity.get_entity_attr('media_position', 0)
        media_position_updated_at = entity.get_entity_attr('media_position_updated_at', '')
        if media_position_updated_at:
            media_position_updated_at = datetime.datetime.fromisoformat(media_position_updated_at).timestamp()
            now = datetime.datetime.now().timestamp()
            media_position += now - media_position_updated_at
        if media_duration > 0 and media_position > 0 and state == 'playing':
            progress = int(media_position / (media_duration / 100))
            self.update_function_component(self.J_PROGRESS[1], visible=True, value=progress)
        else:
            self.update_function_component(self.J_PROGRESS[1], visible=False)
        if self.is_started():
            if self._timer_progress:
                self._timer_progress.cancel()
            self._timer_progress = threading.Timer(self.PROGRESS_INTERVAL, self.update_progress)
            self._timer_progress.start()

    def update_power_button(self):
        if self._media_entity is None:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        supported_features = entity.get_entity_attr('supported_features', 0)
        # power switch supported
        if supported_features & 0x0100:
            icon = self.ICO_ENTITY_POWER
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, icon=icon)
        elif state == 'playing':
            icon = self.ICO_STOP
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, icon=icon)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    # callback

    def callback_function_component(self, fnc_id, fnc_name):
        if self._media_entity is None:
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        if fnc_name == 'media_state':
            if state == 'playing':
                entity.call_entity_service('media_stop')
            else:
                entity.call_entity_service('toggle')
        elif fnc_name == 'media_shuffle':
            suffle = not entity.get_entity_attr('shuffle', False)
            entity.call_entity_service('shuffle_set', shuffle=suffle)
        elif fnc_name == 'media_prev':
            entity.call_entity_service('media_previous_track')
        elif fnc_name == 'media_play':
            entity.call_entity_service('media_play_pause')
        elif fnc_name == 'media_next':
            entity.call_entity_service('media_next_track')
        elif fnc_name == 'media_repeat':
            repeat = entity.get_entity_attr('repeat')
            if repeat == 'off':
                repeat = 'all'
            elif repeat == 'all':
                repeat = 'one'
            else:
                repeat = 'off'
            entity.call_entity_service('repeat_set', repeat=repeat)
        elif fnc_name == 'volume_down':
            entity.call_entity_service('volume_down')
        elif fnc_name == 'volume_up':
            entity.call_entity_service('volume_up')
        elif fnc_name == 'set_volume':
            self.send_mqtt(
                ESP_REQUEST['req_component_int'], self.SLD_VOL[1], force=True)

    def callback_select_source(self, event, component, button_state):
        self.log(f'Got select source callback: {component}-{button_state}')

    def callback_select_playlist(self, event, component, button_state):
        self.log(f'Got select playlist callback: {component}-{button_state}')

    def callback_select_track(self, event, component, button_state):
        self.log(f'Got track callback: {component}-{button_state}')

    def callback_media_entity(self, entity, attribute, old, new, kwargs):
        if attribute == 'state':
            self.update_media_entity()
        elif attribute in ['media_title', 'media_artist', 'media_channel']:
            self.update_media_title()
            self.update_media_info()
            self.update_media_controls()
        elif attribute in ['shuffle', 'repeat']:
            self.update_media_controls()
        elif attribute in ['volume_level', 'is_volume_muted']:
            self.update_volume()
        else:
            self.log(f'Unknown media entity attribute: {attribute}')

    # event

    def process_event(self, event):
        super().process_event(event)
        # requested values
        if event.name == ESP_RESPONSE['res_component_int']:
            data = event.as_json()
            name = data.get('name', '')
            value = int(data.get('value', 0))
            if name == self.SLD_VOL[1]:
                self.process_volume(value)

    def process_volume(self, volume):
        # value between 0 and 1 as float
        volume_level = volume / 100
        self._media_entity.call_entity_service('volume_set', volume_level=volume_level)

    def process_power(self, power):
        if self._media_entity.get_entity_state() == 'on':
            self._media_entity.call_entity_service('media_play')
        else:
            self._media_entity.call_entity_service('turn_on')


class PopupMediaPage(MediaPage):

    def before_render_panel(self, panel):
        entity = self._media_entity
        # if a invalid entity is provided, return false
        # to prevent panel from rendering
        navigation = self.app.controller['navigation']
        if entity is None or not entity.has_entity_id() or not entity.has_entity():
            self.log('No entity for popup media provided')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_type() != 'media_player':
            self.log(f'Entity {entity.get_entity_id()} is not a media entity')
            navigation.close_panel()
            return False
        elif entity is not None and entity.get_entity_state() == 'unavailable':
            self.log(f'Entity {entity.get_entity_id()} is not available')
            navigation.close_panel()
            return False
        return True
