from __future__ import annotations

import datetime
import threading
from typing import Any

from ..abstract.event import HAUIEvent
from ..abstract.item import HAUIItem
from ..abstract.panel import HAUIPanel
from ..features import MediaPlayerFeatures
from ..mapping.color import COLORS
from ..mapping.const import ESPRequest, ESPResponse
from ..mapping.descriptor import PageDescriptor, PageOption
from ..utils.icon import get_icon
from ..utils.text import trim_text
from . import HAUIPage


class MediaPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="media",
        page_name="media",
        label="Media Player",
        description="Media player controls with track info and volume.",
        options=[
            PageOption(
                key="item", kind="item", domain="media_player", label="Media player item"
            ),
            PageOption(
                key="sonos_favorites",
                kind="item",
                domain="sensor",
                label="Sonos favorites sensor",
            ),
            PageOption(
                key="sonos_favorites_in_source",
                kind="bool",
                default=False,
                label="Show Sonos favorites in source list",
            ),
            PageOption(
                key="media_favorites",
                kind="list_str",
                default=[],
                label="Media favorites (one per line, format: name|content_id|content_type)",
            ),
            PageOption(
                key="group_items",
                kind="list_str",
                default=[],
                label="Group items (one item_id per line)",
            ),
        ],
    )

    """
    https://developers.home-assistant.io/docs/core/item/media-player

    Supported features for media player:
    https://github.com/home-assistant/core/blob/dev/homeassistant/components/media_player/const.py
    """

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

    SCROLLING_INTERVAL = 0.5
    PROGRESS_INTERVAL = 0.5

    # panel

    def start_page(self) -> None:
        self._title = ""
        self._items: list[HAUIItem] = []
        self._media_item: HAUIItem | None = None
        self._group_items: list = []
        self._sonos_favorites: HAUIItem | None = None
        self._sonos_favorites_in_source = False
        self._media_favorites: list = []
        self._media_title = ""
        self._media_interpret = ""
        self._media_channel = ""
        self._timer_progress: threading.Timer | None = None
        self._timer_scrolling: threading.Timer | None = None

    def start_panel(self, panel: HAUIPanel) -> None:
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
        # sonos favorites item
        sonos_favorites = None
        sonos_favorites_id = panel.get("sonos_favorites")
        if sonos_favorites_id:
            self.log(f"setting sonos_favorites {sonos_favorites_id}")
            sonos_favorites = HAUIItem(self.app, {"item": sonos_favorites_id})
        self._sonos_favorites = sonos_favorites
        # sonos favorites in source popup
        self._sonos_favorites_in_source = panel.get(
            "sonos_favorites_in_source", self._sonos_favorites_in_source
        )
        # media favorites
        media_favorites = panel.get("media_favorites", [])
        self._media_favorites = media_favorites
        # set group items
        group_items = []
        temp_group_items = panel.get("group_items", [])
        if len(temp_group_items) > 0:
            for group_item in temp_group_items:
                haui_item = HAUIItem(self.app, {"item": group_item})
                group_items.append(haui_item)
        self._group_items = group_items
        # set item
        item = None
        entity_id = panel.get("item_id")
        if entity_id:
            item = HAUIItem(self.app, {"item": entity_id})
        items = panel.get_items()
        if len(items) > 0:
            first_item = items.pop(0)
            if item is None:
                item = first_item
        self._items = items
        self.set_media_item(item)
        # set title
        title = panel.get_title(self.translate("Media"))
        if item is not None:
            title = item.get_item_attr("friendly_name", title)
        self._title = title

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_media_item()

    def stop_panel(self, panel: HAUIPanel) -> None:
        super().stop_panel(panel)
        while self._handles:
            self.remove_item_listener(self._handles.pop())
        if self._timer_progress is not None:
            self._timer_progress.cancel()
            self._timer_progress = None
        if self._timer_scrolling is not None:
            self._timer_scrolling.cancel()
            self._timer_scrolling = None

    # misc

    def _scrolling_text(self) -> None:
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

    def set_media_item(self, item: HAUIItem | None) -> None:
        self._media_item = item
        if not item or not item.has_item_id():
            return
        supported_features = item.get_item_attr("supported_features", 0)
        # Single listener on all attributes: HA batches media metadata updates
        # (title, artist, position, ...) into one state_changed event where the
        # primary state often stays "playing", which caused per-attribute
        # listeners to miss song changes on streaming sources like Sonos.
        self.add_item_listener(
            item.get_item_id(), self.callback_media_entity, attribute="all"
        )
        # media icon
        source = False
        if supported_features & MediaPlayerFeatures.SELECT_SOURCE:
            source = True
        if source:
            self.add_component_callback(self.TXT_MEDIA_ICON, self.callback_select_source)
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
        source_list = item.get_item_attr("source_list", [])
        if (
            supported_features & MediaPlayerFeatures.SELECT_SOURCE
            and len(source_list) > 0
            or (self._sonos_favorites is not None and self._sonos_favorites_in_source is True)
        ):
            source = True
        self.set_media_button(1, self.ICO_SELECT_SOURCE, self.translate("Source"), source)
        self.add_component_callback(self.M1_OVL, self.callback_select_source)
        # group button
        group = False
        group_list = item.get_item_attr("group_list", [])
        if supported_features & MediaPlayerFeatures.GROUPING and len(group_list) > 0:
            group = True
        self.set_media_button(2, self.ICO_SELECT_GROUP, self.translate("Group"), group)
        self.add_component_callback(self.M2_OVL, self.callback_select_group)
        # media button
        media = False
        if len(self._media_favorites) > 0 or (
            self._sonos_favorites is not None and self._sonos_favorites_in_source is False
        ):
            media = True
        self.set_media_button(3, self.ICO_SELECT_MEDIA, self.translate("Media"), media)
        self.add_component_callback(self.M3_OVL, self.callback_select_media)

    def set_media_button(self, idx: int, icon: str, name: str, visible: bool = True) -> None:
        m_btn = getattr(self, f"M{idx}_BTN")
        m_ico = getattr(self, f"M{idx}_ICO")
        m_name = getattr(self, f"M{idx}_NAME")
        m_ovl = getattr(self, f"M{idx}_OVL")
        for x in [m_btn, m_ico, m_name, m_ovl]:
            self.show_component(x) if visible else self.hide_component(x)
        self.set_component_text(m_ico, icon)
        self.set_component_text(m_name, name)

    def update_media_title(self) -> None:
        title = self._title
        if self._media_item:
            item = self._media_item
            # media channel
            media_channel = item.get_item_attr("media_channel")
            if media_channel:
                title = media_channel
        self.set_component_text(self.TXT_TITLE, title)

    def update_media_item(self) -> None:
        self.update_media_title()
        # media details
        self.update_media_info()
        self.update_media_controls()
        self.update_volume()
        self.update_progress()
        # power button
        self.update_power_button()

    def update_media_info(self) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        state = item.get_item_state()
        media_title = item.get_item_attr("media_title", "")
        media_interpret = item.get_item_attr("media_artist", "")
        media_channel = item.get_item_attr("media_channel", "")
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
            self._media_title = f"{self._media_title} {get_icon('minus')} "
        self._media_interpret = media_interpret
        if len(self._media_interpret) > 30:
            self._media_interpret = f"{self._media_interpret} {get_icon('minus')} "
        self._media_channel = media_channel
        self.set_component_text(self.TXT_MEDIA_ICON, item.get_icon())
        self.set_component_text_color(self.TXT_MEDIA_ICON, item.get_color())
        self.set_component_text(self.TXT_MEDIA_TITLE, media_title)
        self.set_component_text(self.TXT_MEDIA_INTERPRET, media_interpret)
        if self._timer_scrolling is None:
            self._scrolling_text()

    def update_media_controls(self) -> None:
        if self._media_item is None:
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
        item = self._media_item
        state = item.get_item_state()
        supported_features = item.get_item_attr("supported_features", 0)
        queue_position = item.get_item_attr("queue_position", 0)
        queue_size = item.get_item_attr("queue_size", 0)
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
            shuffle = item.get_item_attr("shuffle")
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
            repeat = item.get_item_attr("repeat")
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
            self.update_function_component(self.BTN_PLAY[1], visible=True, icon=play_icon)
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

    def update_volume(self) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        supported_features = item.get_item_attr("supported_features", 0)
        volume = int(item.get_item_attr("volume_level", 0) * 100)
        volume_visible = False
        if supported_features & MediaPlayerFeatures.VOLUME_SET:
            volume_visible = True
        self.update_function_component(self.SLD_VOL[1], value=volume, visible=volume_visible)
        self.update_function_component(self.BTN_VOL_DOWN[1], visible=volume_visible)
        self.update_function_component(self.BTN_VOL_UP[1], visible=volume_visible)

    def update_progress(self) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        state = item.get_item_state()
        media_duration = item.get_item_attr("media_duration", 0)
        media_position = item.get_item_attr("media_position", 0)
        media_position_updated_at = item.get_item_attr("media_position_updated_at", "")
        if media_position_updated_at:
            media_position_updated_at = datetime.datetime.fromisoformat(
                media_position_updated_at
            ).timestamp()
            now = datetime.datetime.now().timestamp()
            media_position += now - media_position_updated_at
        if media_duration > 0 and media_position > 0 and state == "playing":
            progress = int(media_position / (media_duration / 100))
            self.update_function_component(self.J_PROGRESS[1], visible=True, value=progress)
        else:
            self.update_function_component(self.J_PROGRESS[1], visible=False)
        if self.is_started():
            if self._timer_progress:
                self._timer_progress.cancel()
            self._timer_progress = threading.Timer(self.PROGRESS_INTERVAL, self.update_progress)
            self._timer_progress.start()

    def update_power_button(self) -> None:
        if self._media_item is None:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
            return
        item = self._media_item
        state = item.get_item_state()
        supported_features = item.get_item_attr("supported_features", 0)
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

    def callback_media_entity(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: Any
    ) -> None:
        with self.rec_cmd:
            self.update_media_item()

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        state = item.get_item_state()
        if fnc_name == "media_state":
            if state == "playing":
                item.call_item_service("media_stop")
            else:
                item.call_item_service("toggle")
        elif fnc_name == "media_shuffle":
            suffle = not item.get_item_attr("shuffle", False)
            item.call_item_service("shuffle_set", shuffle=suffle)
        elif fnc_name == "media_prev":
            item.call_item_service("media_previous_track")
        elif fnc_name == "media_play":
            item.call_item_service("media_play_pause")
        elif fnc_name == "media_next":
            item.call_item_service("media_next_track")
        elif fnc_name == "media_repeat":
            repeat = item.get_item_attr("repeat")
            if repeat == "off":
                repeat = "all"
            elif repeat == "all":
                repeat = "one"
            else:
                repeat = "off"
            item.call_item_service("repeat_set", repeat=repeat)
        elif fnc_name == "volume_down":
            item.call_item_service("volume_down")
        elif fnc_name == "volume_up":
            item.call_item_service("volume_up")
        elif fnc_name == "set_volume":
            self.send_esphome(ESPRequest.REQ_VAL, self.SLD_VOL[1], force=True)

    def callback_select_source(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        navigation = self.app.controller["navigation"]
        source_list = self._media_item.get_item_attr("source_list", [])
        source = self._media_item.get_item_attr("source", "")
        selection = []
        # add source list
        for name in source_list:
            selection.append({"value": name, "name": name})
        # add sonos favorites
        if self._sonos_favorites is not None and self._sonos_favorites_in_source is True:
            items = self._sonos_favorites.get_item_attr("items", {})
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

    def callback_select_media(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        navigation = self.app.controller["navigation"]
        selection = []
        # add sonos favorites
        if self._sonos_favorites is not None and self._sonos_favorites_in_source is False:
            items = self._sonos_favorites.get_item_attr("items", {})
            for name in items.values():
                value = f"sonos_favorites:{name}"
                selection.append({"value": value, "name": trim_text(name, 14)})
        # add media favorites
        for item in self._media_favorites:
            content_type = item.get("content_type", "music")
            content_id = item.get("content_id")
            name = item.get("name", content_id)
            if content_id is not None:
                value = f"media_favorites:{content_type}:{content_id}"
                selection.append({"value": value, "name": trim_text(name, 14)})
        # show popup
        if len(selection) > 0:
            navigation.open_popup(
                "popup_select",
                title=self.translate("Select media"),
                items=selection,
                select_mode="default",
                selection_callback_fnc=self.callback_media,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no media items found")
            self.log(
                f"No media items found page_config={self.config},"
                f" panel_type={self.panel.get_type() if self.panel is not None else 'unknown'}"
            )

    def callback_select_group(self, event: HAUIEvent, component: tuple, button_state: int) -> None:
        self.log(f"Got group callback: {component}-{button_state}")
        if self._media_item is None:
            return
        group_members = self._media_item.get_item_attr("group_members", [])
        navigation = self.app.controller["navigation"]
        item_map = {}
        items = []
        # collect all items for group
        for value in group_members:
            item_map[value] = HAUIItem(self.app, {"item": value})
        # collect all items defined by items
        for item in self._items:
            if item.get_item_id() not in item_map:
                item_map[item.get_item_id()] = item
        # collect all items defined by group items
        for item in self._group_items:
            if item.get_item_id() not in item_map:
                item_map[item.get_item_id()] = item
        # generate selection items
        for entity_id, item in item_map.items():
            self.log(f"{entity_id} - {item.get_name()}")
            items.append({"value": entity_id, "name": item.get_name()})
        # show popup
        if len(items) > 0:
            navigation.open_popup(
                "popup_select",
                title=self.translate("Select group members"),
                items=items,
                selected=group_members,
                multiple=True,
                select_mode="default",
                selection_callback_fnc=self.callback_group,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no media items found")
            self.log(
                f"No media items found page_config={self.config},"
                f" panel_type={self.panel.get_type() if self.panel is not None else 'unknown'}"
            )

    def callback_source(self, selection: str) -> None:
        self.log(f"Got source selection: {selection}")
        if self._media_item is None:
            return
        self._media_item.call_item_service("select_source", source=selection)

    def callback_media(self, selection: str) -> None:
        self.log(f"Got media selection: {selection}")
        if self._media_item is None:
            return
        if selection.startswith("sonos_favorites:"):
            source = selection.split(":", maxsplit=1)[-1]
            self._media_item.call_item_service("select_source", source=source)
        elif selection.startswith("media_favorites:"):
            media_info = selection.split(":", maxsplit=2)
            content_type = media_info[1]
            content_id = media_info[2]
            self._media_item.call_item_service(
                "play_media",
                media_content_type=content_type,
                media_content_id=content_id,
            )

    def callback_group(self, selection: list) -> None:
        self.log(f"Got group selection: {selection}")
        if self._media_item is None:
            return
        group_members = self._media_item.get_item_attr("group_members", [])
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
            self._media_item.call_item_service("join", group_members=list(selection))
        if len(removed_group_members) > 0:
            for entity_id in removed_group_members:
                item = HAUIItem(self.app, {"item": entity_id})
                item.call_item_service("unjoin")

    # event

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)
        # requested values
        if event.name == ESPResponse.RES_VAL:
            data = event.as_json()
            name = data.get("name", "")
            value = int(data.get("value", 0))
            if name == self.SLD_VOL[1]:
                self.process_volume(value)

    def process_volume(self, volume: int) -> None:
        if self._media_item is None:
            return
        # value between 0 and 1 as float
        volume_level = volume / 100
        self._media_item.call_item_service("volume_set", volume_level=volume_level)

    def process_power(self, power: int) -> None:
        if self._media_item is None:
            return
        if self._media_item.get_item_state() == "on":
            self._media_item.call_item_service("media_play")
        else:
            self._media_item.call_item_service("turn_on")
