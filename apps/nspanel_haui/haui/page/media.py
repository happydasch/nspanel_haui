import datetime
import threading

from ..mapping.const import ESP_REQUEST, ESP_RESPONSE
from ..mapping.color import COLORS
from ..helper.icon import get_icon
from ..config import HAUIConfigEntity
from ..features import MediaPlayerFeatures

from . import HAUIPage


class MediaPage(HAUIPage):

    """
    https://developers.home-assistant.io/docs/core/entity/media-player

    Supported features for media player:
    https://github.com/home-assistant/core/blob/dev/homeassistant/components/media_player/const.py
    """

    ICO_PLAY = get_icon("mdi:play")
    ICO_PAUSE = get_icon("mdi:pause")
    ICO_STOP = get_icon("mdi:stop")
    ICO_PREV = get_icon("mdi:skip-previous")
    ICO_NEXT = get_icon("mdi:skip-next")
    # repeat icons
    ICO_REPEAT = get_icon("mdi:repeat")
    ICO_REPEAT_ONE = get_icon("mdi:repeat-once")
    ICO_REPEAT_OFF = get_icon("mdi:repeat-off")
    # shuffle icons
    ICO_SHUFFLE = get_icon("mdi:shuffle")
    ICO_SHUFFLE_DISABLED = get_icon("mdi:shuffle-disabled")
    # volume icons
    ICO_VOLUME_DOWN = get_icon("mdi:volume-minus")
    ICO_VOLUME_UP = get_icon("mdi:volume-plus")
    # misc
    ICO_SELECT_SOURCE = get_icon("mdi:speaker")
    ICO_SELECT_MEDIA = get_icon("mdi:playlist-music")
    ICO_SELECT_GROUP = get_icon("mdi:group")

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # basic info
    TXT_MEDIA_ICON, TXT_MEDIA_TITLE, TXT_MEDIA_INTERPRET = (
        (7, "tIcon"),
        (8, "tMTitle"),
        (9, "tMInterpret"),
    )
    # control
    BTN_SHUFFLE, BTN_PREV, BTN_PLAY = (10, "bShuffle"), (11, "bPrev"), (12, "bPlay")
    BTN_NEXT, BTN_REPEAT = (13, "bNext"), (14, "bRepeat")
    BTN_VOL_DOWN, BTN_VOL_UP, SLD_VOL = (
        (15, "bVolDown"),
        (16, "bVolUp"),
        (17, "hVolume"),
    )
    # m entities
    M1_BTN, M1_ICO, M1_NAME, M1_OVL = (
        (18, "m1Btn"),
        (19, "m1Icon"),
        (20, "m1Name"),
        (21, "m1Overlay"),
    )
    M2_BTN, M2_ICO, M2_NAME, M2_OVL = (
        (22, "m2Btn"),
        (23, "m2Icon"),
        (24, "m2Name"),
        (25, "m2Overlay"),
    )
    M3_BTN, M3_ICO, M3_NAME, M3_OVL = (
        (26, "m3Btn"),
        (27, "m3Icon"),
        (28, "m3Name"),
        (29, "m3Overlay"),
    )
    # power button
    BTN_POWER = (30, "bPower")
    # progress bar
    J_PROGRESS = (31, "jProgress")

    SCROLLING_INTERVAL = 0.5
    PROGRESS_INTERVAL = 0.5

    _title = ""
    _entities = []
    _media_entity = None
    _group_entities = []
    _sonos_favorites = None
    _sonos_favorites_in_source = False
    _media_favorites = []
    _media_title = ""
    _media_interpret = ""
    _media_channel = ""
    _timer_progress = None
    _timer_scrolling = None

    # panel

    def start_panel(self, panel):
        # set function buttons
        media_state_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "media_state",
            "fnc_args": {
                "icon": self.ICO_STOP,
                "color": COLORS["component_accent"],
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            media_state_btn,
        )
        # sonos favorites entity
        sonos_favorites = None
        sonos_favorites_id = panel.get("sonos_favorites")
        if sonos_favorites_id:
            self.log(f"setting sonos_favorites {sonos_favorites_id}")
            sonos_favorites = HAUIConfigEntity(self.app, {"entity": sonos_favorites_id})
        self._sonos_favorites = sonos_favorites
        # sonos favorites in source popup
        self._sonos_favorites_in_source = panel.get(
            "sonos_favorites_in_source", self._sonos_favorites_in_source
        )
        # media favorites
        media_favorites = panel.get("media_favorites", [])
        self._media_favorites = media_favorites
        # set group entities
        group_entities = []
        temp_group_entities = panel.get("group_entities", [])
        if len(temp_group_entities) > 0:
            for group_entity in temp_group_entities:
                haui_entity = HAUIConfigEntity(self.app, {"entity": group_entity})
                group_entities.append(haui_entity)
        self._group_entities = group_entities
        # set entity
        entity = None
        entity_id = panel.get("entity_id")
        if entity_id:
            entity = HAUIConfigEntity(self.app, {"entity": entity_id})
        entities = panel.get_entities()
        if len(entities) > 0:
            first_entity = entities.pop(0)
            if entity is None:
                entity = first_entity
        self._entities = entities
        self.set_media_entity(entity)
        # set title
        title = panel.get_title(self.translate("Media"))
        if entity is not None:
            title = entity.get_entity_attr("friendly_name", title)
        self._title = title

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
            self._timer_scrolling = threading.Timer(
                self.SCROLLING_INTERVAL, self._scrolling_text
            )
            self._timer_scrolling.start()

    def set_media_entity(self, entity):
        self._media_entity = entity
        if not entity or not entity.has_entity_id():
            return
        supported_features = entity.get_entity_attr("supported_features", 0)
        # add listener
        self.add_entity_listener(entity.get_entity_id(), self.callback_media_entity)
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_media_entity, attribute="media_title"
        )
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_media_entity, attribute="media_artist"
        )
        self.add_entity_listener(
            entity.get_entity_id(),
            self.callback_media_entity,
            attribute="media_channel",
        )
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_media_entity, attribute="volume_level"
        )
        self.add_entity_listener(
            entity.get_entity_id(),
            self.callback_media_entity,
            attribute="is_volume_muted",
        )
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_media_entity, attribute="repeat"
        )
        self.add_entity_listener(
            entity.get_entity_id(), self.callback_media_entity, attribute="shuffle"
        )
        # media icon
        source = False
        if supported_features & MediaPlayerFeatures.SELECT_SOURCE:
            source = True
        if source:
            self.add_component_callback(
                self.TXT_MEDIA_ICON, self.callback_select_source
            )
        # play button
        play = False
        if (
            supported_features & MediaPlayerFeatures.PAUSE
            or supported_features & MediaPlayerFeatures.PLAY
        ):
            play = True
        self.set_function_component(
            self.BTN_PLAY,
            self.BTN_PLAY[1],
            "media_play",
            icon=self.ICO_PLAY,
            color=COLORS["component_active"],
            visible=play,
        )
        # volume buttons
        volume_visible = False
        if supported_features & MediaPlayerFeatures.VOLUME_SET:
            volume_visible = True
        self.set_function_component(
            self.BTN_VOL_DOWN,
            self.BTN_VOL_DOWN[1],
            "volume_down",
            icon=self.ICO_VOLUME_DOWN,
            color=COLORS["component_active"],
            visible=volume_visible,
        )
        self.set_function_component(
            self.BTN_VOL_UP,
            self.BTN_VOL_UP[1],
            "volume_up",
            icon=self.ICO_VOLUME_UP,
            color=COLORS["component_active"],
            visible=volume_visible,
        )
        self.set_function_component(
            self.SLD_VOL, self.SLD_VOL[1], "set_volume", visible=volume_visible
        )
        # prev button
        prev_track = False
        if supported_features & MediaPlayerFeatures.PREVIOUS_TRACK:
            prev_track = True
        self.set_function_component(
            self.BTN_PREV,
            self.BTN_PREV[1],
            "media_prev",
            icon=self.ICO_PREV,
            color=COLORS["component_active"],
            visible=prev_track,
        )
        # next button
        next_track = False
        if supported_features & MediaPlayerFeatures.NEXT_TRACK:
            next_track = True
        self.set_function_component(
            self.BTN_NEXT,
            self.BTN_NEXT[1],
            "media_next",
            icon=self.ICO_NEXT,
            color=COLORS["component_active"],
            visible=next_track,
        )
        # shuffle button
        shuffle = False
        if supported_features & MediaPlayerFeatures.SHUFFLE_SET:
            shuffle = True
        self.set_function_component(
            self.BTN_SHUFFLE,
            self.BTN_SHUFFLE[1],
            "media_shuffle",
            icon=self.ICO_SHUFFLE_DISABLED,
            color=COLORS["component_active"],
            visible=shuffle,
        )
        # repeat button
        repeat = False
        if supported_features & MediaPlayerFeatures.REPEAT_SET:
            repeat = True
        self.set_function_component(
            self.BTN_REPEAT,
            self.BTN_REPEAT[1],
            "media_repeat",
            icon=self.ICO_REPEAT_OFF,
            color=COLORS["component_active"],
            visible=repeat,
        )
        # progress bar
        # visibility will be set by timer calls when media is playing
        self.set_function_component(
            self.J_PROGRESS,
            self.J_PROGRESS[1],
            "progress",
            color=COLORS["text_inactive"],
            back_color=COLORS["text_disabled"],
            value=0,
        )
        # source button
        source = False
        if supported_features & MediaPlayerFeatures.SELECT_SOURCE or (
            self._sonos_favorites is not None
            and self._sonos_favorites_in_source is True
        ):
            source = True
        self.set_media_button(
            1, self.ICO_SELECT_SOURCE, self.translate("Source"), source
        )
        self.add_component_callback(self.M1_OVL, self.callback_select_source)
        # group button
        group = False
        if supported_features & MediaPlayerFeatures.GROUPING:
            group = True
        self.set_media_button(2, self.ICO_SELECT_GROUP, self.translate("Group"), group)
        self.add_component_callback(self.M2_OVL, self.callback_select_group)
        # media button
        media = False
        if len(self._media_favorites) > 0 or (
            self._sonos_favorites is not None
            and self._sonos_favorites_in_source is False
        ):
            media = True
        self.set_media_button(3, self.ICO_SELECT_MEDIA, self.translate("Media"), media)
        self.add_component_callback(self.M3_OVL, self.callback_select_media)

    def set_media_button(self, idx, icon, name, visible=True):
        m_btn = getattr(self, f"M{idx}_BTN")
        m_ico = getattr(self, f"M{idx}_ICO")
        m_name = getattr(self, f"M{idx}_NAME")
        m_ovl = getattr(self, f"M{idx}_OVL")
        for x in [m_btn, m_ico, m_name, m_ovl]:
            self.show_component(x) if visible else self.hide_component(x)
        self.set_component_text(m_ico, icon)
        self.set_component_text(m_name, name)

    def update_media_title(self):
        title = self._title
        if self._media_entity:
            entity = self._media_entity
            # media channel
            media_channel = entity.get_entity_attr("media_channel")
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
        media_title = entity.get_entity_attr("media_title", "")
        media_interpret = entity.get_entity_attr("media_artist", "")
        media_channel = entity.get_entity_attr("media_channel", "")
        if state == "playing":
            if not media_title:
                media_title = self.translate("Unknown Title")
            if not media_interpret:
                if media_channel:
                    media_interpret = media_channel
                else:
                    media_interpret = self.translate("Unknown Interpret")
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

    def update_media_controls(self):
        if self._media_entity is None:
            for fnc_id in [
                self.BTN_SHUFFLE[1],
                self.BTN_PREV[1],
                self.BTN_PLAY[1],
                self.BTN_NEXT[1],
                self.BTN_REPEAT[1],
                self.BTN_VOL_DOWN[1],
                self.BTN_VOL_UP[1],
            ]:
                self.update_function_component(fnc_id, visible=False)
            self.update_function_component(self.SLD_VOL[1], visible=False)
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        supported_features = entity.get_entity_attr("supported_features", 0)
        queue_position = entity.get_entity_attr("queue_position", 0)
        queue_size = entity.get_entity_attr("queue_size", 0)
        # shuffle
        if supported_features & MediaPlayerFeatures.SHUFFLE_SET:
            icon = None
            touch_enabled = queue_size > 0
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(queue_size > 1)
            shuffle = entity.get_entity_attr("shuffle")
            if shuffle is False:
                icon = self.ICO_SHUFFLE_DISABLED
            elif shuffle is True:
                icon = self.ICO_SHUFFLE
            self.update_function_component(
                self.BTN_SHUFFLE[1],
                visible=True,
                icon=icon,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_SHUFFLE[1], visible=False)
        # repeat
        if supported_features & MediaPlayerFeatures.REPEAT_SET:
            icon = None
            touch_enabled = queue_size > 0
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(queue_size > 0)
            repeat = entity.get_entity_attr("repeat")
            if repeat == "all":
                icon = self.ICO_REPEAT
            elif repeat == "one":
                icon = self.ICO_REPEAT_ONE
            elif repeat == "off":
                icon = self.ICO_REPEAT_OFF
            self.update_function_component(
                self.BTN_REPEAT[1],
                visible=True,
                icon=icon,
                touch=touch_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_REPEAT[1], visible=False)
        # play, pause
        if (
            supported_features & MediaPlayerFeatures.PLAY
            or supported_features & MediaPlayerFeatures.PAUSE
        ):
            play_icon = self.ICO_PAUSE if state == "playing" else self.ICO_PLAY
            self.update_function_component(
                self.BTN_PLAY[1], visible=True, icon=play_icon
            )
        else:
            self.update_function_component(self.BTN_PLAY[1], visible=False)
        # prev
        if supported_features & MediaPlayerFeatures.PREVIOUS_TRACK:
            prev_enabled = False
            if queue_position > 1:
                prev_enabled = True
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(prev_enabled)
            self.update_function_component(
                self.BTN_PREV[1],
                visible=True,
                touch=prev_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_PREV[1], visible=False)
        # next
        if supported_features & MediaPlayerFeatures.NEXT_TRACK:
            next_enabled = False
            if queue_position < queue_size:
                next_enabled = True
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(next_enabled)
            self.update_function_component(
                self.BTN_NEXT[1],
                visible=True,
                touch=next_enabled,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
            )
        else:
            self.update_function_component(self.BTN_NEXT[1], visible=False)

    def update_volume(self):
        if self._media_entity is None:
            return
        entity = self._media_entity
        supported_features = entity.get_entity_attr("supported_features", 0)
        volume = int(entity.get_entity_attr("volume_level", 0) * 100)
        volume_visible = False
        if supported_features & MediaPlayerFeatures.VOLUME_SET:
            volume_visible = True
        self.update_function_component(
            self.SLD_VOL[1], value=volume, visible=volume_visible
        )
        self.update_function_component(self.BTN_VOL_DOWN[1], visible=volume_visible)
        self.update_function_component(self.BTN_VOL_UP[1], visible=volume_visible)

    def update_progress(self):
        if self._media_entity is None:
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        media_duration = entity.get_entity_attr("media_duration", 0)
        media_position = entity.get_entity_attr("media_position", 0)
        media_position_updated_at = entity.get_entity_attr(
            "media_position_updated_at", ""
        )
        if media_position_updated_at:
            media_position_updated_at = datetime.datetime.fromisoformat(
                media_position_updated_at
            ).timestamp()
            now = datetime.datetime.now().timestamp()
            media_position += now - media_position_updated_at
        if media_duration > 0 and media_position > 0 and state == "playing":
            progress = int(media_position / (media_duration / 100))
            self.update_function_component(
                self.J_PROGRESS[1], visible=True, value=progress
            )
        else:
            self.update_function_component(self.J_PROGRESS[1], visible=False)
        if self.is_started():
            if self._timer_progress:
                self._timer_progress.cancel()
            self._timer_progress = threading.Timer(
                self.PROGRESS_INTERVAL, self.update_progress
            )
            self._timer_progress.start()

    def update_power_button(self):
        if self._media_entity is None:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        supported_features = entity.get_entity_attr("supported_features", 0)
        # power switch supported
        if supported_features & MediaPlayerFeatures.TURN_ON:
            icon = self.ICO_ENTITY_POWER
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, icon=icon)
        elif state == "playing":
            icon = self.ICO_STOP
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, icon=icon)
        else:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    # callback

    def callback_media_entity(self, entity, attribute, old, new, kwargs):
        if attribute == "state":
            self.update_media_entity()
        elif attribute in ["media_title", "media_artist", "media_channel"]:
            self.update_media_title()
            self.update_media_info()
            self.update_media_controls()
        elif attribute in ["shuffle", "repeat"]:
            self.update_media_controls()
        elif attribute in ["volume_level", "is_volume_muted"]:
            self.update_volume()
        else:
            self.log(f"Unknown media entity attribute: {attribute}")

    def callback_function_component(self, fnc_id, fnc_name):
        if self._media_entity is None:
            return
        entity = self._media_entity
        state = entity.get_entity_state()
        if fnc_name == "media_state":
            if state == "playing":
                entity.call_entity_service("media_stop")
            else:
                entity.call_entity_service("toggle")
        elif fnc_name == "media_shuffle":
            suffle = not entity.get_entity_attr("shuffle", False)
            entity.call_entity_service("shuffle_set", shuffle=suffle)
        elif fnc_name == "media_prev":
            entity.call_entity_service("media_previous_track")
        elif fnc_name == "media_play":
            entity.call_entity_service("media_play_pause")
        elif fnc_name == "media_next":
            entity.call_entity_service("media_next_track")
        elif fnc_name == "media_repeat":
            repeat = entity.get_entity_attr("repeat")
            if repeat == "off":
                repeat = "all"
            elif repeat == "all":
                repeat = "one"
            else:
                repeat = "off"
            entity.call_entity_service("repeat_set", repeat=repeat)
        elif fnc_name == "volume_down":
            entity.call_entity_service("volume_down")
        elif fnc_name == "volume_up":
            entity.call_entity_service("volume_up")
        elif fnc_name == "set_volume":
            self.send_mqtt(ESP_REQUEST["req_val"], self.SLD_VOL[1], force=True)

    def callback_select_source(self, event, component, button_state):
        navigation = self.app.controller["navigation"]
        source_list = self._media_entity.get_entity_attr("source_list", [])
        source = self._media_entity.get_entity_attr("source", "")
        selection = []
        # add source list
        for name in source_list:
            selection.append({"value": name, "name": name})
        # add sonos favorites
        if (
            self._sonos_favorites is not None
            and self._sonos_favorites_in_source is True
        ):
            items = self._sonos_favorites.get_entity_attr("items", {})
            for name in items.values():
                selection.append({"value": name, "name": name})
        # show popup
        if len(selection) > 0:
            navigation.open_popup(
                "popup_select",
                title=self.translate("Select source"),
                selected=source,
                items=selection,
                select_mode="default",
                selection_callback_fnc=self.callback_source,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no source items found")

    def callback_select_media(self, event, component, button_state):
        navigation = self.app.controller["navigation"]
        selection = []
        # add sonos favorites
        if (
            self._sonos_favorites is not None
            and self._sonos_favorites_in_source is False
        ):
            items = self._sonos_favorites.get_entity_attr("items", {})
            for name in items.values():
                value = f"sonos_favorites:{name}"
                selection.append({"value": value, "name": name})
        # add media favorites
        for item in self._media_favorites:
            content_type = item.get("content_type", "music")
            content_id = item.get("content_id")
            name = item.get("name", content_id)
            if content_id is not None:
                value = f"media_favorites:{content_type}:{content_id}"
                selection.append({"value": value, "name": name})
        # show popup
        if len(selection) > 0:
            navigation.open_popup(
                "popup_select",
                title=self.translate("Select media"),
                items=selection,
                select_mode="full",
                selection_callback_fnc=self.callback_media,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no media items found")
            self.log(f"No media items found {self._config}, {self.panel.get_config()}")

    def callback_select_group(self, event, component, button_state):
        self.log(f"Got group callback: {component}-{button_state}")
        group_members = self._media_entity.get_entity_attr("group_members", [])
        navigation = self.app.controller["navigation"]
        entities = {}
        items = []
        # collect all entities for group
        for value in group_members:
            entities[value] = HAUIConfigEntity(self.app, {"entity": value})
        # collect all entities defined by entities
        for entity in self._entities:
            if entity.get_entity_id() not in entities:
                entities[entity.get_entity_id()] = entity
        # collect all entities defined by group entities
        for entity in self._group_entities:
            if entity.get_entity_id() not in entities:
                entities[entity.get_entity_id()] = entity
        # generate selection items
        for entity_id, entity in entities.items():
            self.log(f"{entity_id} - {entity.get_name()}")
            items.append({"value": entity_id, "name": entity.get_name()})
        # show popup
        if len(items) > 0:
            navigation.open_popup(
                "popup_select",
                title=self.translate("Select group members"),
                items=items,
                selected=group_members,
                multiple=True,
                select_mode="full",
                selection_callback_fnc=self.callback_group,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no media items found")
            self.log(f"No media items found {self._config}, {self.panel.get_config()}")

    def callback_source(self, selection):
        self.log(f"Got source selection: {selection}")
        self._media_entity.call_entity_service("select_source", source=selection)

    def callback_media(self, selection):
        self.log(f"Got media selection: {selection}")
        if selection.startswith("sonos_favorites:"):
            source = selection.split(":", maxsplit=1)[-1]
            self._media_entity.call_entity_service("select_source", source=source)
        elif selection.startswith("media_favorites:"):
            media_info = selection.split(":", maxsplit=2)
            content_type = media_info[1]
            content_id = media_info[2]
            self._media_entity.call_entity_service(
                "media_play",
                media_content_type=content_type,
                media_content_id=content_id,
            )

    def callback_group(self, selection):
        self.log(f"Got group selection: {selection}")
        group_members = self._media_entity.get_entity_attr("group_members", [])
        # look for new group members
        new_group_members = []
        for value in selection:
            if value not in group_members:
                new_group_members.append(value)
        # look for removed group members
        removed_group_members = []
        for value in group_members:
            if value not in selection:
                removed_group_members.append(value)
        self.log(
            f"Group members: {group_members}"
            f" to join: {new_group_members}"
            f" to unjoin: {removed_group_members}"
        )
        # update group members
        if len(new_group_members) > 0:
            self._media_entity.call_entity_service(
                "join", group_members=list(selection)
            )
        if len(removed_group_members) > 0:
            for entity_id in removed_group_members:
                entity = HAUIConfigEntity(self.app, {"entity": entity_id})
                entity.call_entity_service("unjoin")

    # event

    def process_event(self, event):
        super().process_event(event)
        # requested values
        if event.name == ESP_RESPONSE["res_val"]:
            data = event.as_json()
            name = data.get("name", "")
            value = int(data.get("value", 0))
            if name == self.SLD_VOL[1]:
                self.process_volume(value)

    def process_volume(self, volume):
        # value between 0 and 1 as float
        volume_level = volume / 100
        self._media_entity.call_entity_service("volume_set", volume_level=volume_level)

    def process_power(self, power):
        if self._media_entity.get_entity_state() == "on":
            self._media_entity.call_entity_service("media_play")
        else:
            self._media_entity.call_entity_service("turn_on")
