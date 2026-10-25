from __future__ import annotations

import datetime
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_entity import HAUIEntity
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_item import HAUIItem
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..features import MediaPlayerFeatures as F
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption, _
from ..mapping.icons import (
    ICO_NEXT,
    ICO_PAUSE,
    ICO_PLAY,
    ICO_POWER,
    ICO_PREV,
    ICO_REPEAT,
    ICO_REPEAT_OFF,
    ICO_REPEAT_ONE,
    ICO_SELECT_GROUP,
    ICO_SELECT_MEDIA,
    ICO_SELECT_SOURCE,
    ICO_SHUFFLE,
    ICO_SHUFFLE_DISABLED,
    ICO_STOP,
    ICO_VOLUME_DOWN,
    ICO_VOLUME_UP,
)
from ..utils.icon import get_icon
from ..utils.text import trim_text


class MediaPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="media",
        page_name="media",
        page_id=14,
        label=_("Media Player"),
        description=_("Media player controls with track info and volume."),
        options=[
            PageOption(
                key="item",
                kind="item",
                domain="media_player",
                description=_("Media player entity to control playback and volume."),
                section=_("Media Player"),
            ),
            PageOption(
                key="sonos_favorites",
                kind="item",
                domain="sensor",
                description=_("Sensor entity containing Sonos favorites data."),
                section=_("Media Player"),
            ),
            PageOption(
                key="group_items",
                kind="list_entities",
                domain="media_player",
                default=[],
                label=_("Group media player entities"),
                description=(
                    "Additional media player entity IDs to group as a multi-room speaker set."
                ),
                section=_("Groups"),
            ),
            PageOption(
                key="media_favorites",
                kind="list_items",
                default=[],
                label=_("Media favorites"),
                description=_("Media content IDs shown in the media selector."),
                section=_("Favorites"),
            ),
            PageOption(
                key="sonos_favorites_in_source",
                kind="bool",
                default=False,
                label=_("Sonos favorites in source list"),
                description=("Iterpret favorites as sonos favorites."),
                section=_("Favorites"),
            ),
        ],
        can_show_popup=True,
        icon="mdi:music",
    )

    COMPONENTS = ComponentRegistry(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        t_icon=Component(8, "tIcon"),
        t_m_title=Component(9, "tMTitle"),
        t_m_interpret=Component(10, "tMInterpret"),
        btn_shuffle=Component(11, "bShuffle"),
        btn_prev=Component(12, "bPrev"),
        btn_play=Component(13, "bPlay"),
        btn_next=Component(14, "bNext"),
        btn_repeat=Component(15, "bRepeat"),
        btn_vol_down=Component(16, "bVolDown"),
        btn_vol_up=Component(17, "bVolUp"),
        h_volume=Component(18, "hVolume"),
        m1_btn=Component(19, "m1Btn"),
        m1_icon=Component(20, "m1Icon"),
        m1_name=Component(21, "m1Name"),
        m1_overlay=Component(22, "m1Overlay"),
        m2_btn=Component(23, "m2Btn"),
        m2_icon=Component(24, "m2Icon"),
        m2_name=Component(25, "m2Name"),
        m2_overlay=Component(26, "m2Overlay"),
        m3_btn=Component(27, "m3Btn"),
        m3_icon=Component(28, "m3Icon"),
        m3_name=Component(29, "m3Name"),
        m3_overlay=Component(30, "m3Overlay"),
        btn_power=Component(31, "bPower"),
        j_progress=Component(32, "jProgress"),
    )

    _REPEAT_ICONS = {"all": ICO_REPEAT, "one": ICO_REPEAT_ONE, "off": ICO_REPEAT_OFF}

    _SIMPLE_SERVICES = {
        "media_prev": "media_previous_track",
        "media_play": "media_play_pause",
        "media_next": "media_next_track",
        "volume_down": "volume_down",
        "volume_up": "volume_up",
    }

    SCROLLING_INTERVAL = 0.5
    PROGRESS_INTERVAL = 0.5

    # panel

    @staticmethod
    def _looks_like_entity_id(value: str) -> bool:
        return value.startswith("media_player.") and "." in value

    def prepare(self) -> None:
        self._title = ""
        self._media_item: HAUIItem | None = None
        self._group_items: list[str] = []
        self._sonos_favorites: HAUIItem | None = None
        self._sonos_favorites_in_source = False
        self._media_favorites: list[str] = []
        self._media_title = ""
        self._media_interpret = ""
        self._handle_scrolling: str | None = None
        self._handle_progress: str | None = None

    def start_panel(self, panel: HAUIPanel) -> None:
        # debug: trace panel config for media/override debugging
        self.log(
            f"MediaPage.start_panel: key={panel.get('key', None)!r} type={panel.get_type()!r} "
            f"sonos_favorites={panel.get('sonos_favorites', None)!r} "
            f"media_favorites={panel.get('media_favorites', None)!r} "
            f"sonos_favorites_in_source={panel.get('sonos_favorites_in_source', None)!r} "
            f"item_id={panel.get('item_id', None)!r} item={panel.get('item', None)!r}",
            level="DEBUG",
        )
        # set function buttons
        media_state_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "media_state",
            "fnc_args": {
                "icon": ICO_STOP,
                "color": self.get_color("header_accent"),
                "visible": False,
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            media_state_btn,
        )
        # the volume slider is a drag control: swipes are suppressed while it
        # is dragged and its value is read once the touch ends
        self.bind_slider(self.COMPONENTS.h_volume, self.process_volume)
        self._sonos_favorites = self._item_from_ref(panel.get("sonos_favorites", None))
        # sonos favorites in source popup
        self._sonos_favorites_in_source = panel.get(
            "sonos_favorites_in_source", self._sonos_favorites_in_source
        )
        # media favorites and group items — plain entity ID strings from config
        self._media_favorites = self._entity_ids(panel.get("media_favorites", []))
        self._group_items = self._entity_ids(panel.get("group_items", []))
        # set item
        item = self._item_from_ref(panel.get("item_id", None) or panel.get("item", None))
        self.set_media_item(item)
        # set title
        self._title = self._panel_title(panel, item, self.translate("Media"))

        # auto-assign function types to header buttons
        self._auto_assign_fncs(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_media_item()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        if self._handle_progress is not None:
            self.app.cancel_timer(self._handle_progress)
            self._handle_progress = None
        if self._handle_scrolling is not None:
            self.app.cancel_timer(self._handle_scrolling)
            self._handle_scrolling = None

    # misc

    def _scrolling_text(self, _data: dict | None = None) -> None:
        if len(self._media_title) > 20:
            self._media_title = self._media_title[1:] + self._media_title[0]
            self.set_component_text(self.COMPONENTS.t_m_title, self._media_title)
        if len(self._media_interpret) > 30:
            self._media_interpret = self._media_interpret[1:] + self._media_interpret[0]
            self.set_component_text(self.COMPONENTS.t_m_interpret, self._media_interpret)

    def set_media_item(self, item: HAUIItem | None) -> None:
        self._media_item = item
        if not item or not item.has_item_id():
            return
        # Single listener on all attributes: HA batches media metadata updates
        # (title, artist, position, ...) into one state_changed event where the
        # primary state often stays "playing", which caused per-attribute
        # listeners to miss song changes on streaming sources like Sonos.
        self.add_item_listener(item.get_item_id(), self.callback_media_entity, attribute="all")
        # media icon
        if item.supports(F.SELECT_SOURCE):
            self.on_release(self.COMPONENTS.t_icon, self.callback_select_source)
        # play and volume buttons
        self._register_feature_buttons(
            item,
            (
                (self.COMPONENTS.btn_play, "media_play", ICO_PLAY, F.PAUSE | F.PLAY),
                (
                    self.COMPONENTS.btn_vol_down,
                    "volume_down",
                    ICO_VOLUME_DOWN,
                    F.VOLUME_SET,
                ),
                (self.COMPONENTS.btn_vol_up, "volume_up", ICO_VOLUME_UP, F.VOLUME_SET),
            ),
        )
        self.set_function_component(
            self.COMPONENTS.h_volume,
            self.COMPONENTS.h_volume.name,
            "set_volume",
            visible=item.supports(F.VOLUME_SET),
        )
        # track, shuffle and repeat buttons
        self._register_feature_buttons(
            item,
            (
                (self.COMPONENTS.btn_prev, "media_prev", ICO_PREV, F.PREVIOUS_TRACK),
                (self.COMPONENTS.btn_next, "media_next", ICO_NEXT, F.NEXT_TRACK),
                (
                    self.COMPONENTS.btn_shuffle,
                    "media_shuffle",
                    ICO_SHUFFLE_DISABLED,
                    F.SHUFFLE_SET,
                ),
                (self.COMPONENTS.btn_repeat, "media_repeat", ICO_REPEAT_OFF, F.REPEAT_SET),
            ),
        )
        # progress bar
        # visibility will be set by timer calls when media is playing
        self.set_function_component(
            self.COMPONENTS.j_progress,
            self.COMPONENTS.j_progress[1],
            "progress",
            color=self.get_color("text_inactive"),
            back_color=self.get_color("text_disabled"),
            value=0,
        )
        # source button
        source_list = item.get_item_attr("source_list", [])
        source = bool(
            item.supports(F.SELECT_SOURCE)
            and len(source_list) > 0
            or (self._sonos_favorites is not None and self._sonos_favorites_in_source is True)
        )
        self.set_media_button(1, ICO_SELECT_SOURCE, self.translate("Source"), source)
        self.on_release(self.COMPONENTS.m1_overlay, self.callback_select_source)
        # group button
        group = bool(item.supports(F.GROUPING) and (self._get_group_members() or self._group_items))
        self.set_media_button(2, ICO_SELECT_GROUP, self.translate("Group"), group)
        self.on_release(self.COMPONENTS.m2_overlay, self.callback_select_group)
        # media button
        media = False
        if len(self._media_favorites) > 0 or (
            self._sonos_favorites is not None and self._sonos_favorites_in_source is False
        ):
            media = True
        self.set_media_button(3, ICO_SELECT_MEDIA, self.translate("Media"), media)
        self.on_release(self.COMPONENTS.m3_overlay, self.callback_select_media)

    def _register_feature_buttons(self, item: HAUIItem, buttons: tuple) -> None:
        """Registers (component, fnc_name, icon, feature flags) buttons, visible when supported."""
        color = self.get_color("component_active")
        for component, fnc_name, icon, flags in buttons:
            self.set_function_component(
                component,
                component.name,
                fnc_name,
                icon=icon,
                color=color,
                visible=item.supports(flags),
            )

    def _get_group_members(self) -> list[str]:
        """Return the player's current group members.

        HA reports ``group_members`` as ``None`` for a grouping-capable player
        that isn't part of a group.
        """
        if self._media_item is None:
            return []
        return self._media_item.get_item_attr("group_members") or []

    def set_media_button(self, idx: int, icon: str, name: str, visible: bool = True) -> None:
        m_btn = getattr(self.COMPONENTS, f"m{idx}_btn")
        m_ico = getattr(self.COMPONENTS, f"m{idx}_icon")
        m_name = getattr(self.COMPONENTS, f"m{idx}_name")
        m_ovl = getattr(self.COMPONENTS, f"m{idx}_overlay")
        for x in [m_btn, m_ico, m_name, m_ovl]:
            if visible:
                self.show_component(x)
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
        self.set_component_text(self.COMPONENTS.title, title)

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
        self.set_component_text(self.COMPONENTS.t_icon, item.get_icon())
        self.set_component_text_color(self.COMPONENTS.t_icon, item.get_color())
        self.set_component_text(self.COMPONENTS.t_m_title, media_title)
        self.set_component_text(self.COMPONENTS.t_m_interpret, media_interpret)
        if self._handle_scrolling is None:
            # Start repeating scrolling timer (replaces threading.Timer)
            self._handle_scrolling = self.app.run_every(
                self._scrolling_text, 0, self.SCROLLING_INTERVAL
            )

    def update_media_controls(self) -> None:
        if self._media_item is None:
            for fnc_id in [
                self.COMPONENTS.btn_shuffle[1],
                self.COMPONENTS.btn_prev[1],
                self.COMPONENTS.btn_play[1],
                self.COMPONENTS.btn_next[1],
                self.COMPONENTS.btn_repeat[1],
                self.COMPONENTS.btn_vol_down[1],
                self.COMPONENTS.btn_vol_up[1],
            ]:
                self.update_function_component(fnc_id, visible=False)
            self.update_function_component(self.COMPONENTS.h_volume[1], visible=False)
            return
        item = self._media_item
        state = item.get_item_state()
        # controls are enabled by supported_features alone: queue position and
        # size are Sonos-only attributes, so other players have no queue info
        colors = self.button_color_args(True)
        # shuffle
        shuffle = item.get_item_attr("shuffle")
        shuffle_icon = None
        if shuffle is False:
            shuffle_icon = ICO_SHUFFLE_DISABLED
        elif shuffle is True:
            shuffle_icon = ICO_SHUFFLE
        self.update_supported_component(
            self.COMPONENTS.btn_shuffle.name,
            item.supports(F.SHUFFLE_SET),
            icon=shuffle_icon,
            **colors,
        )
        # repeat
        self.update_supported_component(
            self.COMPONENTS.btn_repeat.name,
            item.supports(F.REPEAT_SET),
            icon=self._REPEAT_ICONS.get(item.get_item_attr("repeat")),
            **colors,
        )
        # play, pause
        self.update_supported_component(
            self.COMPONENTS.btn_play.name,
            item.supports(F.PLAY | F.PAUSE),
            icon=ICO_PAUSE if state == "playing" else ICO_PLAY,
        )
        # prev, next
        self.update_supported_component(
            self.COMPONENTS.btn_prev.name, item.supports(F.PREVIOUS_TRACK), **colors
        )
        self.update_supported_component(
            self.COMPONENTS.btn_next.name, item.supports(F.NEXT_TRACK), **colors
        )

    def update_volume(self) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        volume = int(item.get_item_attr("volume_level", 0) * 100)
        volume_visible = item.supports(F.VOLUME_SET)
        self.set_slider_color(self.COMPONENTS.h_volume)
        self.update_function_component(
            self.COMPONENTS.h_volume[1], value=volume, visible=volume_visible
        )
        self.update_function_component(self.COMPONENTS.btn_vol_down[1], visible=volume_visible)
        self.update_function_component(self.COMPONENTS.btn_vol_up[1], visible=volume_visible)

    def update_progress(self, _data: dict | None = None) -> None:
        if self._media_item is None:
            return
        item = self._media_item
        state = item.get_item_state()
        media_duration = item.get_item_attr("media_duration", 0)
        media_position = item.get_item_attr("media_position", 0)
        media_position_updated_at = item.get_item_attr("media_position_updated_at", "")
        if isinstance(media_position_updated_at, datetime.datetime):
            media_position_updated_at = media_position_updated_at.timestamp()
            now = datetime.datetime.now().timestamp()
            media_position += now - media_position_updated_at
        elif media_position_updated_at:
            media_position_updated_at = datetime.datetime.fromisoformat(
                media_position_updated_at
            ).timestamp()
            now = datetime.datetime.now().timestamp()
            media_position += now - media_position_updated_at
        if media_duration > 0 and media_position > 0 and state == "playing":
            progress = int(media_position / (media_duration / 100))
            self.update_function_component(
                self.COMPONENTS.j_progress[1], visible=True, value=progress
            )
        else:
            self.update_function_component(self.COMPONENTS.j_progress[1], visible=False)
        # Start the repeating progress timer (replaces threading.Timer) if not
        # already running.  Started lazily here so the timer only ticks when
        # there is an active media panel.
        if self.is_started() and self._handle_progress is None:
            self._handle_progress = self.app.run_every(
                self.update_progress, 0, self.PROGRESS_INTERVAL
            )

    def update_power_button(self) -> None:
        if self._media_item is None:
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
            return
        item = self._media_item
        state = item.get_item_state()
        # power switch supported
        if item.supports(F.TURN_ON):
            icon = ICO_POWER
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True, icon=icon)
        elif state == "playing":
            icon = ICO_STOP
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
        elif fnc_name == "media_repeat":
            repeat = item.get_item_attr("repeat")
            if repeat == "off":
                repeat = "all"
            elif repeat == "all":
                repeat = "one"
            else:
                repeat = "off"
            item.call_item_service("repeat_set", repeat=repeat)
        elif fnc_name in self._SIMPLE_SERVICES:
            item.call_item_service(self._SIMPLE_SERVICES[fnc_name])

    def callback_select_source(self, event: HAUIEvent, component: Component) -> None:
        if self._media_item is None:
            return
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
            navigation.open_panel(
                SysPanelKey.POPUP_SELECT,
                title=self.translate("Select source"),
                selected=source,
                items=selection,
                select_mode="default",
                selection_callback_fnc=self.callback_source,
                close_on_select=True,
            )
        else:
            self.log("Skipping popup, no source items found")

    def callback_select_media(self, event: HAUIEvent, component: Component) -> None:
        navigation = self.app.controller["navigation"]
        selection = []
        # add sonos favorites
        if self._sonos_favorites is not None and self._sonos_favorites_in_source is False:
            items = self._sonos_favorites.get_item_attr("items", {})
            for name in items.values():
                value = f"sonos_favorites:{name}"
                selection.append({"value": value, "name": trim_text(name, 14)})
        # add media favorites. Entity IDs keep the legacy metadata lookup; other
        # strings are treated as media content IDs with the default music type.
        for favorite in self._media_favorites:
            content_id = favorite
            content_type = "music"
            name = favorite.rsplit("/", maxsplit=1)[-1]
            if self._looks_like_entity_id(favorite):
                entity = HAUIEntity(self.app, favorite)
                content_id = entity.get_entity_attr("media_content_id", favorite)
                content_type = entity.get_entity_attr("media_content_type", "music")
                name = entity.get_entity_attr("friendly_name", favorite)
            if content_id:
                value = f"media_favorites:{content_type}:{content_id}"
                selection.append({"value": value, "name": trim_text(name, 14)})
            else:
                self.log(f"Skipping media favorite {favorite}: no media_content_id")
        # show popup
        if len(selection) > 0:
            navigation.open_panel(
                SysPanelKey.POPUP_SELECT,
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

    def callback_select_group(self, event: HAUIEvent, component: Component) -> None:
        self.log(f"Got group callback: {component}")
        if self._media_item is None:
            return
        group_members = self._get_group_members()
        navigation = self.app.controller["navigation"]
        item_map = {}
        items = []
        # collect all items for group
        for value in group_members:
            item_map[value] = HAUIEntity(self.app, value)
        # collect all items defined by group items — plain entity ID strings
        for entity_id in self._group_items:
            if entity_id not in item_map:
                item_map[entity_id] = HAUIEntity(self.app, entity_id)
        # generate selection items
        for entity_id, entity in item_map.items():
            name = entity.get_entity_attr("friendly_name", entity_id)
            self.log(f"{entity_id} - {name}")
            items.append({"value": entity_id, "name": name})
        # show popup
        if len(items) > 0:
            navigation.open_panel(
                SysPanelKey.POPUP_SELECT,
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
        group_members = self._get_group_members()
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
                entity = HAUIEntity(self.app, entity_id)
                entity.call_entity_service("unjoin")

    # event

    def process_volume(self, volume: int) -> None:
        self.log(f"Slider volume value {volume}")
        if self._media_item is None:
            return
        # value between 0 and 1 as float
        volume_level = volume / 100
        self._media_item.call_item_service("volume_set", volume_level=volume_level)
