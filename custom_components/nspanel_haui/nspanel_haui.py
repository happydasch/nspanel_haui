import datetime
from collections.abc import Callable
from typing import Any, TypedDict

from homeassistant.util import slugify

from .ha_adapter import HAAdapter
from .haui.abstract.haui_base import HAUIBase
from .haui.abstract.haui_config import HAUIConfig
from .haui.controller.connection import HAUIConnectionController
from .haui.controller.esphome import HAUIESPHomeController
from .haui.controller.gesture import HAUIGestureController
from .haui.controller.navigation import HAUINavigationController
from .haui.controller.notification import HAUINotificationController
from .haui.controller.update import HAUIUpdateController
from .haui.device import HAUIDevice
from .haui.device_config import DEVICE_CONFIG_FIELDS
from .haui.mapping.color import ColorTheme
from .haui.mapping.panel import PAGE_MAPPING
from .haui.version import get_version


class ControllerDict(TypedDict, total=True):
    esphome: HAUIESPHomeController
    connection: HAUIConnectionController
    navigation: HAUINavigationController
    notification: HAUINotificationController
    update: HAUIUpdateController
    gesture: HAUIGestureController


class NSPanelHAUI(HAAdapter):
    """NSPanel HAUI integration entry point.

    Inherits HAAdapter so all haui sub-components receive a compatible API surface via self.app.
    Prepared for future migration to HA config entries.
    """

    def __init__(
        self,
        hass: Any,
        name: str,
        config_args: dict,
        runtime_device_name: str = "",
        ha_device_id: str | None = None,
    ) -> None:
        super().__init__(hass, name)
        self._config_args = config_args
        self.controller: ControllerDict = {}  # type: ignore[typeddict-item]
        self.device_config: HAUIConfig
        self.device: HAUIDevice
        self._runtime_device_name: str = runtime_device_name
        # entity-id slug of the device name, computed with HA's own slugify so
        # haui/ builds the same ids HA assigns (haui/ must not import homeassistant)
        self.device_slug: str = slugify(runtime_device_name)
        self._ha_device_id: str | None = ha_device_id
        self._last_panel_update: str | None = None
        self._tick_subscribers: dict[str, set[Callable]] = {}
        self._tick_timers: dict[str, str] = {}

    def initialize(self) -> None:
        self.device_config = HAUIConfig(self, self._config_args)
        self.device = HAUIDevice(self, self.device_config.get("device"))

        # color overrides from device config
        overrides: dict[str, int] = (
            self.device_config.get("device", {}).get("color_overrides", {})
        ) or {}
        self._color_theme: ColorTheme = ColorTheme(overrides)

        # The runtime device name comes from the constructor (set by async_setup_entry).
        # We don't pick devices[0] anymore — each app drives exactly one device.
        device_name = self._runtime_device_name
        if not device_name:
            device_name = self.device_config.get("device", {}).get("name", "")
        if not device_name:
            device_name = self._config_args.get("name", "")

        self._runtime_device_name = device_name
        self.device_slug = slugify(device_name)

        esp_api = self.get_plugin_api(
            "ESPHome", device_name=device_name, device_id=self._ha_device_id
        )

        esp_config: dict[str, Any] = {
            "devices": self.device_config.get("devices", []),
            "device_name": device_name,
        }
        self.controller["esphome"] = HAUIESPHomeController(
            self, esp_config, esp_api, self.callback_event
        )
        self.controller["connection"] = HAUIConnectionController(
            self, self.device_config.get("connection"), self.callback_connection
        )
        self.controller["navigation"] = HAUINavigationController(
            self, self.device_config.get("navigation")
        )
        self.controller["notification"] = HAUINotificationController(
            self, self.device_config.get("notification")
        )
        self.controller["update"] = HAUIUpdateController(self, self.device_config.get("update"))
        self.controller["gesture"] = HAUIGestureController(self, self.device_config.get("gesture"))

        self.log(
            "Initialized controllers: "
            "esphome, connection, navigation, notification, update, gesture"
        )

        self.start()

    # lifecycle

    def start(self) -> None:
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.start()
        self.device.start()

    def stop(self) -> None:
        # Cancel shared tick timers
        for _cadence, timer_id in list(self._tick_timers.items()):
            self.cancel_timer(timer_id)
        self._tick_timers.clear()
        self._tick_subscribers.clear()

        if self.device:
            self.device.stop()
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.stop()

        # Belt-and-suspenders: cancel any HA handles that controllers
        # missed in their own stop_part cleanup.
        HAAdapter.stop(self)

    # shared tick timers (minute / hour / day cadences)

    def subscribe_tick(self, cadence: str, callback: Callable) -> None:
        """Register a callback for a device-wide tick cadence.

        Cadences: ``"minute"`` (60 s, fires on the minute), ``"hour"``
        (3600 s, fires on the hour).

        The shared timer starts when the first subscriber registers and
        stops when the last subscriber unregisters.
        """
        if cadence not in self._tick_subscribers:
            self._tick_subscribers[cadence] = set()
        self._tick_subscribers[cadence].add(callback)

        if cadence not in self._tick_timers:

            def _dispatch(cb_args: dict) -> None:
                for cb in list(self._tick_subscribers.get(cadence, set())):
                    cb(cb_args)

            # Align the first fire to the next minute/hour boundary so the
            # display updates on the clock tick, not 60s after registration.
            now = datetime.datetime.now()
            if cadence == "minute":
                secs = 60 - now.second
                self._tick_timers[cadence] = self.run_minutely(_dispatch, f"now+{secs}")
            elif cadence == "hour":
                secs = 3600 - (now.minute * 60 + now.second)
                self._tick_timers[cadence] = self.run_hourly(_dispatch, f"now+{secs}")

    def unsubscribe_tick(self, cadence: str, callback: Callable) -> None:
        """Unregister a callback previously added via :meth:`subscribe_tick`."""
        subs = self._tick_subscribers.get(cadence)
        if subs:
            subs.discard(callback)
            if not subs and cadence in self._tick_timers:
                self.cancel_timer(self._tick_timers.pop(cadence))

    # config reload (called by the API when panels or device settings are saved)

    def reload_config(self, cfg: dict) -> None:
        """Apply a rebuilt runtime config without a full restart.

        ``cfg`` comes from the same builder as startup (``_build_config_dict``
        in ``__init__.py``), so device settings and panels get the same merge,
        defaults and validation; a setting removed from the store falls back to
        its default. Controllers keep running; the device settings, colors and
        panels are replaced.
        """
        if not self.device_config:
            return

        new_config = HAUIConfig(self, cfg)
        device_cfg = new_config.get("device")
        if self.device:
            for field in DEVICE_CONFIG_FIELDS:
                self.device.config[field] = device_cfg[field]
        self._color_theme = ColorTheme(device_cfg.get("color_overrides") or {})

        self.device_config._panels = new_config._panels
        self.device_config._panels_by_id = new_config._panels_by_id
        self.device_config._panels_by_key = new_config._panels_by_key
        self.log("Device config and panels reloaded from store")

        # Restart device button-entity listeners so they pick up updated
        # button_left_entity / button_right_entity from the new config.
        if self.device:
            self.device._cancel_callbacks()
            self.device._register_callbacks()
            # Push the settings to the device's ESPHome switches and numbers
            # (relay mode, button interaction, auto-* and timeouts) right away.
            self.device.sync_config_to_device()

        # Refresh navigation controller panel references
        nav_ctrl = self.controller.get("navigation")
        if nav_ctrl is not None:
            nav_ctrl.reload_panels()

        # Restart update controller timer with new interval
        update_ctrl = self.controller.get("update")
        if update_ctrl is not None:
            update_ctrl.stop_part()
            update_ctrl.start_part()

    def update_display(self) -> None:
        """Re-render the currently displayed panel on this device.

        This triggers a full refresh of the current panel's display commands
        without reloading config or re-registering callbacks.
        """
        nav_ctrl = self.controller.get("navigation")
        if nav_ctrl is None:
            self.log("Cannot update display: no navigation controller")
            return
        nav_ctrl.refresh_panel()
        self.log("Display updated")

    def install_tft(self, version: str | None = None) -> None:
        """Trigger a TFT install for this device, on its worker thread.

        Called via ``async_run_on_worker`` from the REST API; ``version``
        defaults to the version the firmware needs (``yaml_version``).

        Args:
            version (str | None): Release version to install
        """
        update_ctrl = self.controller.get("update")
        if update_ctrl is None:
            self.log("Cannot install TFT: no update controller", level="WARNING")
            return
        update_ctrl.install_tft(version)

    # status endpoint support

    @staticmethod
    def _format_current_page(page) -> str:
        """Format the current page info for the status display."""
        if not page:
            return "none"
        page_id = page.page_id
        page_name = str(PAGE_MAPPING.get(page_id, page_id))
        if not page.panel:
            return page_name
        return f"{page.panel.get('key', '')} ({page.panel.get_type()})"

    def get_device_status(self) -> dict:
        """Return live device status for the frontend info strip and dialogs."""
        conn = self.controller["connection"]
        nav = self.controller.get("navigation")
        page = nav.page if nav else None

        result: dict = {
            "connected": conn.is_connected if conn else False,
            "connection_state": conn.connection_state.value if conn else "unknown",
            "current_page": self._format_current_page(page),
            "logs": self.get_status_logs()[-50:],
            # Panel Doctor: versions + health summary
            "integration_version": get_version(),
        }

        # Device info from the device config
        device_config = self.device_config.get("device", {}) if self.device_config else {}
        runtime_info = self.device.device_info if self.device else {}

        # TFT update state (manual installs from the editor)
        update_ctrl = self.controller.get("update")
        if update_ctrl is not None:
            result["update"] = update_ctrl.get_update_state()

        # Read network info from HA entities only (no stale fallback).
        from .esphome_helpers import read_network_entities

        nw = read_network_entities(self.hass, self._runtime_device_name or "", self.find_entity_id)

        result["device_info"] = {
            "name": self._runtime_device_name or device_config.get("name", self.name),
            "tft_version": runtime_info.get("tft_version") or "",
            "yaml_version": runtime_info.get("yaml_version") or "",
            "ip": nw["ip"],
            "ssid": nw["ssid"],
            "rssi": nw["rssi"],
            "last_panel_update": self._last_panel_update,
            "last_connection": (
                datetime.datetime.fromtimestamp(
                    conn.last_connection_time, tz=datetime.UTC
                ).isoformat()
                if conn and conn.last_connection_time
                else None
            ),
            # Panel Doctor: health readings for the diagnostics surface.
            "last_disconnect_reason": (
                conn.last_disconnect_reason if conn else None
            ),
            "disconnected_since": (
                datetime.datetime.fromtimestamp(
                    conn.disconnected_since, tz=datetime.UTC
                ).isoformat()
                if conn and conn.disconnected_since
                else None
            ),
            "connection_uptime": (
                int(datetime.datetime.now(tz=datetime.UTC).timestamp() - conn.last_connection_time)
                if conn and conn.is_connected and conn.last_connection_time
                else None
            ),
            "idle_page_active": bool(nav.idle_panel_active) if nav else False,
        }

        # ESPHome transport info
        esphome_ctrl = self.controller.get("esphome")
        if esphome_ctrl:
            result["esphome"] = {
                "device_names": esphome_ctrl._device_names,
                "transport": "esphome",
            }

        # Active state listeners on the current page
        nav = self.controller.get("navigation")
        active_listeners = []
        if nav is not None and nav.page is not None:
            meta = getattr(nav.page, "_listener_meta", {})
            for handle, entry in meta.items():
                active_listeners.append(
                    {
                        "handle": handle,
                        "item_id": entry.get("item_id", ""),
                        "attribute": entry.get("attribute"),
                        "callback_name": entry.get("callback_name", ""),
                    }
                )
        result["active_listeners"] = active_listeners
        result["active_listener_count"] = len(active_listeners)

        # Active timers (run_every / run_minutely / run_hourly / run_in)
        active_timers = []
        for handle in list(self._timer_handles):
            meta = self._timer_meta.get(handle, {})
            active_timers.append(
                {
                    "handle": handle,
                    "callback_name": meta.get("callback_name", "?"),
                    "type": meta.get("type", "?"),
                    "interval": meta.get("interval"),
                }
            )
        result["active_timers"] = active_timers
        result["active_timer_count"] = len(active_timers)

        return result

    # callbacks

    def callback_event(self, event: Any) -> None:
        import traceback

        self.log(
            f"Event dispatch: name={event.name} value={str(event.value)[:120]}",
            level="DEBUG",
        )

        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                try:
                    controller.process_event(event)
                except Exception:
                    self.log(
                        f"Error processing event {event.name} in {type(controller).__name__}:\n"
                        f"{traceback.format_exc()}",
                        level="ERROR",
                    )
        try:
            self.device.process_event(event)
        except Exception:
            self.log(
                f"Error processing event {event.name} in device:\n{traceback.format_exc()}",
                level="ERROR",
            )

    def callback_connection(self, connected: bool) -> None:
        self.log(f"Device connection status: {connected}")
        self.device.on_connection_changed(connected)
        self.controller["update"].on_connection_changed(connected)
        self.fire_event(
            "nspanel_haui.connection_changed",
            {
                "device": self.device.get_name(),
                "connected": connected,
            },
        )
