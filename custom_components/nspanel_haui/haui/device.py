from __future__ import annotations

import time
from copy import deepcopy
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from .abstract.haui_base import HAUIBase
from .abstract.haui_event import HAUIEvent
from .controller.notification import Notification
from .device_config import DEVICE_CONFIG, is_portrait_model
from .mapping.const import AUTO_SWITCHES, ESPAction, ESPEvent, NotifEvent
from .mapping.panel import PANEL_MAPPING, POPUP_PANEL_MAPPING, SYS_PANEL_MAPPING
from .schedule import ScheduleEntry, active_entry, next_boundary
from .utils.item import default_service
from .utils.value import number_state

if TYPE_CHECKING:
    from ..hub.app import NSPanelHAUI
from .mapping.const import SysPanelKey

# Ignore touch events left over from the touch that opened the idle page:
# the ESP32 can publish a duplicate touch_start ~1 s later, which would
# otherwise dismiss the just-opened page.  1.5 s covers that lag.
IDLE_TOUCH_GRACE_WINDOW: float = 1.5

# The native Nextion touch_start ("1") decides the wake; the poller's duplicate
# ("") is ignored unless the native event was lost within this window.
TOUCH_DUPLICATE_WINDOW: float = 1.5

# The startup sound plays only while uptime stays under this value; a missing
# uptime key (older firmware) plays anyway.
STARTUP_SOUND_MAX_UPTIME_SECONDS = 120

# The firmware's Display Model select options, landscape first
# (esphome/nspanel_haui/select.yaml), indexed by HAUIDevice.is_portrait.
DISPLAY_MODEL_OPTIONS: tuple[str, str] = ("Landscape", "Portrait")


class HAUIDevice(HAUIBase):
    """A NSPanel device: device callbacks, physical buttons and gesture input."""

    def __init__(self, app: NSPanelHAUI, config: dict | None = None) -> None:
        """Initialize the device; missing settings take their DEVICE_CONFIG default."""
        super().__init__(app, {**deepcopy(DEVICE_CONFIG), **(config or {})})
        self.device_info: dict = {}
        # While the display is off, the first touch only wakes it (see
        # check_wakeup); armed on idle-page open and on display "off".
        self._first_touch_consumed = False
        # Last visible display_state timestamp; a wake touch that reaches the
        # hub after the display-on event is consumed within the duplicate window.
        self._display_on_ts: float = 0.0
        # Deadline until residual touches of the idle-page trigger are ignored.
        self._idle_touch_grace_until = 0.0
        # Last native touch_start; the poller duplicate is ignored within the
        # duplicate window, but used as a fallback when the native event was lost.
        self._last_native_touch_ts: float = 0.0
        self._initial_connect_done = False
        self._btn_left_info: dict[str, Any] = {
            "item_id": None,
        }
        self._btn_right_info: dict[str, Any] = {
            "item_id": None,
        }
        self._persistent_sound_handle: str | None = None
        self._schedule_timer: str | None = None

    # prepare and update

    def _check_config(self) -> None:
        """Checks if the configuration is valid.

        Raises:
            ValueError: Missing values in config
        """
        config = self.app.device_config
        # check if all sys_panels are valid
        chk_sys_panels = [x.get("key") for x in config.get("sys_panels", [])]
        for panel_key in SYS_PANEL_MAPPING | POPUP_PANEL_MAPPING:
            if panel_key not in chk_sys_panels:
                raise ValueError(f"Missing sys_panel {panel_key} in config")
        for panel in config.get_panels():
            if panel.get_type() not in PANEL_MAPPING:
                raise ValueError(f"Panel type {panel.get_type()} not supported")
        self.log(f"Loaded {len(config.get_panels())} panels")

    def _register_callbacks(self) -> None:
        """Resolves the relay entity each physical button toggles."""
        for side in ("left", "right"):
            button = getattr(self, f"_btn_{side}_info")
            entity_id = self.get(f"button_{side}_entity", None)
            if not entity_id:
                name = f"Relay {side.title()}"
                entity_id = self._resolve_esp_entity("switch", name)
            button["item_id"] = entity_id

    def _cancel_callbacks(self) -> None:
        """Forgets the resolved button entities."""
        for i in ["left", "right"]:
            getattr(self, f"_btn_{i}_info")["item_id"] = None

    def _resolve_esp_entity(self, domain: str, name: str) -> str | None:
        """Resolve a built-in ESPHome entity on this device by its authored name."""
        return self.find_esphome_entity_id(domain, name)

    def _sync_config_switch(
        self,
        hub_key: str,
        switch_entity_id: str | None,
        hub_value: bool | None = None,
        reason: str = "",
    ) -> None:
        """Apply a deliberate config value to its corresponding ESPHome switch."""
        if not switch_entity_id or not self.app.item_exists(switch_entity_id):
            return
        if hub_value is None:
            hub_value = self.get(hub_key, True)
        item = self.app.get_item(switch_entity_id)
        state = item.get_state()
        if state not in ("on", "off"):
            return
        if hub_value and state == "off":
            self.log(f"Syncing {switch_entity_id} ON ({reason or f'hub config {hub_key}=True'})")
            item.turn_on()
        elif not hub_value and state == "on":
            self.log(f"Syncing {switch_entity_id} OFF ({reason or f'hub config {hub_key}=False'})")
            item.turn_off()

    def _sync_changed_auto_switch_settings(self, changed_settings: set[str]) -> None:
        """Apply changed automatic-switch settings; a schedule owns display-off."""
        for setting in changed_settings:
            switch_key = setting.removeprefix("use_")
            if switch_key == "auto_display_off" and self.get("schedule"):
                continue
            if switch_key in AUTO_SWITCHES:
                self._sync_config_switch(
                    setting,
                    self._resolve_esp_entity("switch", AUTO_SWITCHES[switch_key]),
                    reason="Settings changed",
                )

    def _sun_time(self, event: str, day: date) -> datetime | None:
        """Local time of a sun event; None where the sun does not rise or set that day."""
        point = self.app.get_sun_time(event, day)
        if point is None:
            self.log(
                f"No {event} on {day} at this location; schedule entries using it are inactive",
                level="WARNING",
            )
        return point

    def _schedule_entries(self) -> list[ScheduleEntry]:
        return [ScheduleEntry.from_config(entry) for entry in self.get("schedule")]

    def _active_schedule_entry(self) -> ScheduleEntry | None:
        """The schedule entry whose window contains now, if any."""
        entries = self._schedule_entries()
        if not entries:
            return None
        return active_entry(entries, self.app.now(), self._sun_time)

    def _sync_number(self, value: float | int | None, entity_name: str, reason: str = "") -> None:
        """Write a value to one of the device's ESPHome numbers when it differs."""
        entity_id = self._resolve_esp_entity("number", entity_name)
        if value is None or not entity_id or not self.app.item_exists(entity_id):
            return
        item = self.app.get_item(entity_id)
        current = number_state(item.get_state())
        if current is not None and current != value:
            detail = f" ({reason})" if reason else ""
            self.log(f"Syncing {entity_id} to {value}{detail}")
            item.set_state(state=value)

    def _sync_select(self, option: str, entity_name: str, reason: str = "") -> None:
        """Select an option on one of the device's ESPHome selects when it differs."""
        entity_id = self._resolve_esp_entity("select", entity_name)
        if not entity_id or not self.app.item_exists(entity_id):
            return
        item = self.app.get_item(entity_id)
        current = item.get_state()
        # An unknown or unavailable entity has no option to compare against yet.
        if current in (None, "", "unknown", "unavailable") or current == option:
            return
        detail = f" ({reason})" if reason else ""
        self.log(f"Syncing {entity_id} to {option}{detail}")
        item.call_service("select_option", option=option)

    def _sync_button_interaction(self) -> None:
        """Keep ``reset_interaction_on_button`` aligned with its ESPHome switch."""
        self._sync_config_switch(
            "reset_interaction_on_button",
            self._resolve_esp_entity("switch", "Use Button Interaction"),
        )

    def _sync_relay_config(self) -> None:
        """Sync ``use_relay_left``/``use_relay_right`` with the ESPHome switches."""
        self._sync_config_switch(
            "use_relay_left",
            self._resolve_esp_entity("switch", "Use Relay Left"),
        )
        self._sync_config_switch(
            "use_relay_right",
            self._resolve_esp_entity("switch", "Use Relay Right"),
        )

    # part
    def _sync_behavior_config(self) -> None:
        """Sync timeouts and brightness from the active schedule entry or the settings.

        A schedule owns the display-off switch and writes it on every sync.
        """
        entry = self._active_schedule_entry()

        def value(key: str) -> float | int | None:
            """The active entry's value for ``key``, else the device setting."""
            if entry is not None:
                entry_value = getattr(entry, key)
                if entry_value is not None:
                    return entry_value
            return self.get(key, None)

        self._sync_number(value("timeout_dimming"), "Timeout Dimming")
        self._sync_number(value("timeout_display_off"), "Timeout Display-Off")
        self._sync_number(value("brightness"), "Brightness Full")
        self._sync_number(value("brightness_dim"), "Brightness Dimmed")
        self._sync_number(value("duration_dimming"), "Duration Dimming")
        if self.get("schedule"):
            self._sync_config_switch(
                "use_auto_display_off",
                self._resolve_esp_entity("switch", AUTO_SWITCHES["auto_display_off"]),
                hub_value=entry.display_off if entry else None,
                reason="Schedule",
            )
        self._sync_display_model()

    def _sync_display_model(self) -> None:
        """Sync the firmware's gesture size with the display model."""
        self._sync_select(
            DISPLAY_MODEL_OPTIONS[self.is_portrait],
            "Display Model",
            reason=f"display_model={self.display_model!r}",
        )

    @property
    def display_model(self) -> str:
        """The configured display model (``eu`` or ``us``), lower-cased."""
        return str(self.get("display_model")).lower()

    @property
    def is_portrait(self) -> bool:
        """Whether this device runs the rotated portrait TFT layout."""
        return is_portrait_model(self.display_model)

    # part

    def sync_config_to_device(self, changed_auto_settings: set[str] | None = None) -> None:
        """Apply config and explicitly changed switch settings.

        Automatic switches otherwise follow their live ESPHome state.
        """
        self._sync_button_interaction()
        self._sync_relay_config()
        self._sync_changed_auto_switch_settings(changed_auto_settings or set())
        self._sync_behavior_config()
        self._arm_schedule_timer()

    def start_part(self) -> None:
        """Starts the part."""
        self.log("Device is starting")
        self._check_config()
        self._register_callbacks()
        self.sync_config_to_device()

    def stop_part(self) -> None:
        """Stops the part."""
        self.log("Device is stopping")
        self._cancel_callbacks()
        self._cancel_timer("_schedule_timer")
        self._stop_persistent_sound()

    # public

    def set_device_info(self, device_info: dict, append: bool = True) -> None:
        """Sets devices related vars from a dict.

        Args:
            device_info (dict): dict with device info vars
            append (bool, optional): Append or replace values. Defaults to True (append).
        """
        if append:
            self.device_info = {**self.device_info, **device_info}
        else:
            self.device_info = device_info

    # ------------------------------------------------------------------
    # Sleep / display-state predicates — the single source of truth
    # ------------------------------------------------------------------

    @property
    def display_state(self) -> str:
        """Display brightness state reported by the firmware: "on", "dim", "off", or unknown.

        Empty until the firmware reports one, which is not "off": a panel that has
        not answered yet may well be lit, and this used to answer "off" for a fact
        nobody had - so anything that stops work on a dark display (the camera
        stream) stopped before the first handshake, and every surface that shows
        the state showed "Off" for a panel it knew nothing about.
        """
        return str(self.device_info.get("display_state") or "")

    @property
    def display_visible(self) -> bool:
        """Whether the display is visible to the user ("on" or "dim")."""
        return self.display_state in ("on", "dim")

    @property
    def sleeping(self) -> bool:
        """Whether the idle page is shown; independent of display brightness."""
        navigation = self.app.controller.get("navigation")
        return bool(navigation is not None and navigation.idle_panel_active)

    def on_idle_page_opened(self) -> None:
        """Arm the first-touch guard when the idle page opens.

        Only a dark display needs a wake touch before the idle page can be left.
        """
        self._first_touch_consumed = not self.display_visible

    # ------------------------------------------------------------------
    # Connection state — delegates to connection controller
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the device connection is fully established."""
        conn = self.app.controller.get("connection")
        return conn.is_connected if conn else False

    def on_connection_changed(self, connected: bool) -> None:
        """Open System on first connect, restore the panel on reconnect, reset idle state on
        disconnect.

        The first-connect guard keeps every reconnect from navigating to System
        and then home.
        """
        self.log(f"Device connected: {connected}")
        navigation = self.app.controller.get("navigation")
        if navigation is None:
            return
        # Cancel stale navigation timeouts so they cannot fire after reconnect.
        navigation.cancel_timeouts()
        if connected:
            navigation.prepare_resume()
            self.sync_config_to_device()
            if self.get("sound_on_startup"):
                uptime = self.device_info.get("uptime")
                if uptime is None or uptime < STARTUP_SOUND_MAX_UPTIME_SECONDS:
                    self.play_sound("startup")
            # Only the first connection opens System; a reconnect restores the
            # user's panel.  open_panel blocks on the ESPHome API, so run it
            # through run_in to keep heartbeat events flowing.
            if not self._initial_connect_done:
                navigation.open_panel(SysPanelKey.SYS_SYSTEM)
                self._initial_connect_done = True
            else:
                panel = navigation.get_current_panel()
                nav_panel = navigation.get_current_nav_panel()
                if panel is not None and nav_panel is not None and panel.id == nav_panel.id:
                    # Current panel is the nav panel - re-open it directly
                    self.app.run_in(
                        lambda _: navigation.open_panel(panel.id, force=True),
                        0,
                    )
                elif nav_panel is not None:
                    self.app.run_in(
                        lambda _: navigation.open_panel(nav_panel.id, force=True),
                        0,
                    )
                else:
                    navigation.open_home_panel()
        else:
            # Reset idle-session state on disconnect so stale flags do not
            # trigger navigation or wake handling during reconnection.  Touch
            # guards are reset too - the next interaction starts on a clean
            # slate.
            navigation.mark_awake()
            self._first_touch_consumed = False
            self._idle_touch_grace_until = 0.0

    def _sounds_muted(self) -> bool:
        """Whether the active schedule entry mutes sounds."""
        entry = self._active_schedule_entry()
        return entry is not None and not entry.sound

    def _arm_schedule_timer(self) -> None:
        """Arm a timer for the next moment a schedule entry starts or ends."""
        self._cancel_timer("_schedule_timer")
        entries = self._schedule_entries()
        if not entries:
            return
        now = self.app.now()
        boundary = next_boundary(entries, now, self._sun_time)
        if boundary is None:
            # No sunrise or sunset up to tomorrow: look again once the next day is in reach.
            delay = 24 * 3600.0
        else:
            # Timestamps, not the difference of the two: datetimes sharing a time
            # zone subtract as wall-clock times and miss a daylight saving change.
            delay = boundary.timestamp() - now.timestamp()
        self._schedule_timer = self.app.run_in(self._schedule_boundary_callback, max(delay, 1))

    def _schedule_boundary_callback(self, _kwargs: Any) -> None:
        """A schedule boundary passed: apply the now-active settings and re-arm."""
        self._schedule_timer = None
        self._sync_behavior_config()
        self._arm_schedule_timer()

    # public

    def wake_for_notification(self) -> None:
        """Wake the display for a notification that opened on its own.

        A schedule entry with sound off keeps the display dark.
        """
        if self._sounds_muted():
            self.log("Schedule mutes sounds — not waking the display", level="DEBUG")
            return
        self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")

    def get_locale(self) -> str:
        """Returns the device locale.

        Returns:
            str: Locale
        """
        return self.get("locale")

    def get_time_format(self) -> str:
        """The device's strftime time format, falling back to the hub default."""
        value = self.get("time_format")
        if value:
            return value
        return self.app.device_config.get("time_format")

    def get_date_format(self) -> str:
        """The device's strftime date format, falling back to the hub default."""
        value = self.get("date_format")
        if value:
            return value
        return self.app.device_config.get("date_format")

    def get_date_format_locale(self) -> str:
        """The device's locale date pattern, empty when a date format is set."""
        if self.get("date_format"):
            return ""
        value = self.get("date_format_locale")
        if value:
            return value
        return self.app.device_config.get("date_format_locale")

    def get_slug(self) -> str:
        """The device name slugified like Home Assistant entity ids."""
        return self.app.device_slug

    def get_name(self) -> str:
        """Returns the device name.

        Returns:
            str: Device name
        """
        # the per-device name is resolved by NSPanelHAUI.initialize()
        return self.app._runtime_device_name or self.get("name")

    def toggle_left_button_state(self) -> None:
        """Runs the left button's action: its relay or its entity's default service."""
        self._toggle_button_state("left")

    def toggle_right_button_state(self) -> None:
        """Runs the right button's action: its relay or its entity's default service."""
        self._toggle_button_state("right")

    def play_sound(self, name: str) -> None:
        """Play a sound; a schedule entry with sound off suppresses it."""
        if self._sounds_muted():
            self.log(f"Schedule mutes sounds — suppressing sound '{name}'", level="DEBUG")
            return
        self.app.controller["esphome"].esphome.publish(ESPAction.PLAY_SOUND, name)

    # callback

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process event.

        Args:
            event (HAUIEvent): Event
        """
        # Live event keys share the handshake's unprefixed names.
        key = event.name.removeprefix("esphome.")
        self.device_info[key] = event.value
        # a touch is the sole driver of the idle-page exit decision
        if event.name == ESPEvent.TOUCH_START:
            if self._idle_touch_grace_active():
                self.log("Ignoring residual touch_start after idle-page open")
                return
            # Native touch_start ("1") decides the wake; the poller's duplicate
            # ("") is ignored within the duplicate window unless the native
            # event was lost.
            now = time.monotonic()
            if event.value == "1":
                self._last_native_touch_ts = now
                self.check_wakeup()
            elif now - self._last_native_touch_ts > TOUCH_DUPLICATE_WINDOW:
                self.check_wakeup()
        # Re-arm the wake guard when the display goes "off"; visible states
        # record the transition so a wake touch arriving after the display-state
        # event is consumed within the duplicate window.
        elif event.name == ESPEvent.DISPLAY_STATE:
            if event.value == "off":
                self._first_touch_consumed = True
            elif event.value in ("on", "dim"):
                self._display_on_ts = time.monotonic()
        elif event.name in (ESPEvent.BUTTON_LEFT, ESPEvent.BUTTON_RIGHT):
            side = "left" if event.name == ESPEvent.BUTTON_LEFT else "right"
            if event.value == "1":  # pressed
                # Press: ESPHome records the interaction; the toggle stays on
                # release so a held button does not spam toggles.
                if self.get("reset_interaction_on_button"):
                    self.check_wakeup()
            elif event.value == "0":  # released
                self._on_button_release(side)
        # process notification events
        elif event.name == NotifEvent.NOTIF_ADD:
            if not isinstance(event.value, Notification):
                raise TypeError(f"Notification event value must be a Notification: {event.value!r}")
            if self.get("sound_on_notification"):
                if event.value.persistent:
                    # Starts even while sounds are muted; the loop goes silent
                    # until that entry ends.
                    self._start_persistent_sound()
                elif event.value.sound:
                    if self._sounds_muted():
                        self.log(
                            "Schedule mutes sounds — suppressing notification sound",
                            level="DEBUG",
                        )
                    else:
                        self.play_sound(event.value.sound)
        elif event.name in (NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR):
            # Stop as soon as no audible persistent notification remains; a
            # silent persistent entry must not keep the loop alive.
            if not self._persistent_sound():
                self._stop_persistent_sound()

    def arm_idle_touch_grace(self) -> None:
        """Ignore residual touches from the touch that opened the idle page."""
        self._idle_touch_grace_until = time.monotonic() + IDLE_TOUCH_GRACE_WINDOW

    def _idle_touch_grace_active(self) -> bool:
        """Whether a TOUCH_START falls inside the armed grace window.

        Only while the idle page is actually open.
        """
        if not self.sleeping:
            return False
        return time.monotonic() < self._idle_touch_grace_until

    def reset_interaction_timer(self) -> None:
        """Reset the firmware's interaction timer without changing the current page."""
        self.app.controller["esphome"].esphome.publish(ESPAction.RESET_LAST_INTERACTION, "0")

    def check_wakeup(self) -> None:
        """Exit the idle page on a touch or button press.

        A visible display leaves on the first touch; a dark one wakes on the
        first and exits on the second.  A hardware button does both in one press.
        """
        navigation = self.app.controller.get("navigation")
        if navigation is None or not self.sleeping:
            return
        if not navigation.panel:
            return

        if self.display_visible:
            # A visible display needs one touch; a wake touch that reaches the
            # hub after the display-on event is consumed within the window.
            if (
                self._first_touch_consumed
                and time.monotonic() - self._display_on_ts <= TOUCH_DUPLICATE_WINDOW
            ):
                self._first_touch_consumed = False
                self.log("Not exiting idle page, just woke up")
                return
            self._first_touch_consumed = False
            navigation.exit_idle_to_prev_or_home(self.config)
            return

        # Display is "off" (or not yet known): the first touch only wakes the
        # display; the second touch exits.
        if self._first_touch_consumed:
            self._first_touch_consumed = False
            self.log("Not exiting idle page, just woke up")
            return
        navigation.exit_idle_to_prev_or_home(self.config)

    def _on_button_release(self, side: str) -> None:
        """Handle a hardware-button release: run the button action, then finish the wake."""
        reset = self.get("reset_interaction_on_button")
        getattr(self, f"toggle_{side}_button_state")()
        if reset:
            self.check_wakeup()

    def _toggle_button_state(self, side: str) -> None:
        button = getattr(self, f"_btn_{side}_info")
        entity_id = button["item_id"]
        if not entity_id or not self.app.item_exists(entity_id):
            if self.get(f"button_{side}_entity", None):
                return
            entity_id = self._resolve_esp_entity("switch", f"Relay {side.title()}")
            button["item_id"] = entity_id
        if not entity_id or not self.app.item_exists(entity_id):
            return
        if self.get(f"use_relay_{side}", True):
            return
        item = self.app.get_item(entity_id)
        # A domain with no entry of its own (climate, media_player, siren, …)
        # keeps the plain toggle it had before.
        item.call_service(default_service(entity_id.split(".", 1)[0], item.get_state()) or "toggle")

    def _persistent_sound(self) -> str:
        """The first queued audible persistent notification's sound."""
        notifications = self.app.controller["notification"].get_notifications()
        return next((n.sound for n in notifications if n.persistent and n.sound), "")

    def _play_persistent_sound(self) -> None:
        """Play one round of the persistent alert, unless the schedule mutes sounds."""
        if self._sounds_muted():
            return
        sound = self._persistent_sound()
        if sound:
            self.play_sound(sound)

    def _persistent_sound_callback(self, kwargs: Any) -> None:
        if self._persistent_sound():
            self._play_persistent_sound()
        else:
            self._stop_persistent_sound()

    def _start_persistent_sound(self) -> None:
        if self._persistent_sound_handle is not None:
            return
        if not self._persistent_sound():
            return
        interval = self.get("persistent_sound_interval")
        self._play_persistent_sound()
        self._persistent_sound_handle = self.app.run_every(
            self._persistent_sound_callback, f"now+{interval}", interval
        )

    def _stop_persistent_sound(self) -> None:
        self._cancel_timer("_persistent_sound_handle")
