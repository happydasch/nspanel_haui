import asyncio
import datetime
import threading
from collections.abc import Callable
from typing import Any, TypedDict

from homeassistant.util import slugify

from ..haui.abstract.haui_base import HAUIBase
from ..haui.abstract.haui_config import HAUIConfig
from ..haui.controller.connection import HAUIConnectionController
from ..haui.controller.esphome import HAUIESPHomeController
from ..haui.controller.gesture import HAUIGestureController
from ..haui.controller.navigation import HAUINavigationController
from ..haui.controller.notification import HAUINotificationController
from ..haui.controller.update import HAUIUpdateController
from ..haui.device import HAUIDevice
from ..haui.device_config import DEVICE_CONFIG_FIELDS
from ..haui.mapping.color import Theme, ThemeLibrary
from ..haui.mapping.const import ESPEvent, NotifEvent
from ..haui.mapping.panel import PAGE_MAPPING
from ..haui.version import get_integration_version, integration_version_mismatch
from .adapter import HAAdapter


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
        self.theme_library: ThemeLibrary
        self.theme: Theme
        self._runtime_device_name: str = runtime_device_name
        # entity-id slug of the device name, computed with HA's own slugify so
        # haui/ builds the same ids HA assigns (haui/ must not import homeassistant)
        self.device_slug: str = slugify(runtime_device_name)
        self._ha_device_id: str | None = ha_device_id
        self._last_panel_update: str | None = None
        self._tick_subscribers: dict[str, set[Callable]] = {}
        self._tick_timers: dict[str, str] = {}
        self._preview_state_subscribers: set[Callable[[dict[str, Any]], None]] = set()
        self._preview_output_subscribers: set[Callable[[str, Any], None]] = set()
        self._preview_state_lock = threading.Lock()
        # update requests waiting for their answer (event loop only)
        self._update_requests: set[asyncio.Future[dict[str, Any]]] = set()

    def _apply_themes(self, device_cfg: dict, themes: dict[str, dict] | None = None) -> None:
        """Build the theme library and select the device's default theme."""
        palettes = themes if themes is not None else self.device_config.get("themes")
        self.theme_library = ThemeLibrary(palettes, device_cfg["theme_variant"])
        self.theme = self.theme_library.theme(device_cfg["theme_id"])

    def initialize(self) -> None:
        self.device_config = HAUIConfig(self, self._config_args)
        device_cfg = self.device_config.get("device")
        self._apply_themes(device_cfg)
        self.device = self._create_device(device_cfg)

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
        # The notification controller no longer has a dedicated config section
        # (re_alert_interval was replaced by PERSISTENT_ALERT_INTERVAL).
        self.controller["notification"] = HAUINotificationController(
            self, self.device_config.get("notification", {})
        )
        self.controller["update"] = self._create_update_controller(self.device_config.get("update"))
        self.controller["gesture"] = HAUIGestureController(self, self.device_config.get("gesture"))

        self.log(
            "Initialized controllers: "
            "esphome, connection, navigation, notification, update, gesture"
        )

        self.start()

    def _create_device(self, config: dict[str, Any]) -> HAUIDevice:
        # Overridden by the editor's virtual panel, which has no firmware
        # switches of its own to drive.
        return HAUIDevice(self, config)

    def _create_update_controller(self, config: dict[str, Any]) -> HAUIUpdateController:
        # Overridden by the editor's virtual panel, which must never check for
        # or install firmware/TFT updates.
        return HAUIUpdateController(self, config)

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

        with self._preview_state_lock:
            self._preview_state_subscribers.clear()
            self._preview_output_subscribers.clear()
        if self.device:
            self.device.stop()
        for controller in self.controller.values():
            if isinstance(controller, HAUIBase):
                controller.stop()
        # The stopped worker answers no update request still waiting.
        self._loop.call_soon_threadsafe(self._fail_update_requests)

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
        changed_auto_settings: set[str] = set()
        if self.device:
            auto_settings = {f"use_{key}" for key in ("auto_dimming", "auto_display_off")}
            changed_auto_settings = {
                key for key in auto_settings if self.device.get(key) != device_cfg[key]
            }
            for field in DEVICE_CONFIG_FIELDS:
                self.device.config[field] = device_cfg[field]
        self._apply_themes(device_cfg, new_config.get("themes"))

        self.device_config._panels = new_config._panels
        self.device_config._panels_by_id = new_config._panels_by_id
        self.device_config._panels_by_key = new_config._panels_by_key
        self.log("Device config and panels reloaded from store")

        # Restart device button-entity listeners so they pick up updated
        # button_left_entity / button_right_entity from the new config.
        if self.device:
            self.device._cancel_callbacks()
            self.device._register_callbacks()
            # Only explicit auto-toggle setting changes write those switches;
            # config reloads and reconnects leave automation-owned state alone.
            self.device.sync_config_to_device(changed_auto_settings)

        # Refresh navigation controller panel references
        nav_ctrl = self.controller.get("navigation")
        if nav_ctrl is not None:
            nav_ctrl.reload_panels()

        update_ctrl = self.controller.get("update")
        if update_ctrl is not None:
            update_cfg = new_config.get("update")
            if isinstance(update_cfg, dict):
                update_ctrl.reload_options(update_cfg)

    def refresh_display(self) -> None:
        """Re-render the currently displayed panel on this device.

        This triggers a full refresh of the current panel's display commands
        without reloading config or re-registering callbacks.
        """
        nav_ctrl = self.controller.get("navigation")
        if nav_ctrl is None:
            self.log("Cannot refresh display: no navigation controller")
            return
        nav_ctrl.refresh_panel()
        self.log("Display refreshed")

    async def _async_update_request(self, method: str, **kwargs: Any) -> dict[str, Any]:
        """Await an updater operation whose network stage completes off-worker."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        def _finish(result: dict[str, Any]) -> None:
            def _set_result() -> None:
                if not future.done():
                    future.set_result(result)

            loop.call_soon_threadsafe(_set_result)

        def _start() -> None:
            getattr(self.controller["update"], method)(on_complete=_finish, **kwargs)

        self._update_requests.add(future)
        try:
            await self.async_run_on_worker(_start)
            return await future
        finally:
            self._update_requests.discard(future)

    def _fail_update_requests(self) -> None:
        """End the update requests still waiting: a stopped app answers none (event loop)."""
        for future in self._update_requests:
            if not future.done():
                future.set_exception(
                    RuntimeError("The device's app stopped before the update request finished")
                )

    async def async_list_tft_releases(self) -> dict[str, Any]:
        """List TFT releases without waiting for network work on the device worker."""
        return await self._async_update_request("start_async_list_tft_releases")

    async def async_list_firmware_releases(self) -> dict[str, Any]:
        """List firmware releases without waiting for network work on the device worker."""
        return await self._async_update_request("start_async_list_firmware_releases")

    async def async_check_for_update(self) -> dict[str, Any]:
        """Refresh update offers and return when the worker applies the fetch result."""
        return await self._async_update_request(
            "start_async_check",
            force_refresh=True,
            allow_auto_install=False,
            include_notice=True,
        )

    async def async_install_tft(
        self, version: str | None = None, url: str | None = None
    ) -> dict[str, Any]:
        """Install TFT after resolving its manifest off-worker."""
        return await self._async_update_request("start_async_tft_install", version=version, url=url)

    def start_async_tft_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Queue a TFT install from app-worker code without blocking it."""
        self.controller["update"].start_async_tft_install(version, url, on_complete)

    async def async_install_firmware(
        self, version: str | None = None, url: str | None = None
    ) -> dict[str, Any]:
        """Install firmware after resolving network artifacts off-worker."""
        return await self._async_update_request(
            "start_async_firmware_install", version=version, url=url
        )

    def start_async_firmware_install(
        self,
        version: str | None,
        url: str | None,
        on_complete: Callable[[dict[str, Any]], None],
    ) -> None:
        """Queue a firmware install from app-worker code without blocking it."""
        self.controller["update"].start_async_firmware_install(version, url, on_complete)

    async def async_update_state(self) -> dict[str, Any]:
        """The update controller's state, as the status endpoint reports it."""
        return await self.async_run_on_worker(self.controller["update"].get_update_state)

    async def async_update_snapshot(self) -> dict[str, Any]:
        """The update controller's full snapshot (connection, firmware, display)."""
        return await self.async_run_on_worker(self.controller["update"].get_update_snapshot)

    async def async_set_rollout_hold(self, hold: bool) -> None:
        """Hold (or release) automatic firmware installs while a hub rollout runs."""
        await self.async_run_on_worker(self.controller["update"].set_rollout_hold, hold)

    async def async_update_control(self, action: str, seconds: int | None = None) -> dict[str, Any]:
        """Start now or defer the scheduled automatic firmware install.

        Raises:
            ValueError: Nothing is scheduled, or the action or duration is unknown
                (see ``HAUIUpdateController.control_scheduled``).
        """
        return await self.async_run_on_worker(
            self.controller["update"].control_scheduled, action, seconds
        )

    def publish_display_update(self) -> None:
        """Fire the current TFT update state for the "HAUI Display" entity."""
        self.controller["update"].publish_display_update()

    def publish_firmware_update(self) -> None:
        """Fire the current firmware update state for the "HAUI Firmware" entity."""
        self.controller["update"].publish_firmware_update()

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
            # The key the editor's simulated preview opens the same panel with.
            "current_panel": page.panel.get("key", "") if page and page.panel else "",
            "logs": self.get_status_logs()[-50:],
            # Panel Doctor: versions + health summary
            "integration_version": get_integration_version(),
        }

        # Device info from the device config
        device_config = self.device_config.get("device", {}) if self.device_config else {}
        runtime_info = self.device.device_info if self.device else {}

        result["integration_version_mismatch"] = integration_version_mismatch(
            result["integration_version"], runtime_info.get("yaml_version") or ""
        )

        # TFT update state (manual installs from the editor)
        update_ctrl = self.controller.get("update")
        if update_ctrl is not None:
            result["update"] = update_ctrl.get_update_state()

        result["device_info"] = {
            "name": self._runtime_device_name or device_config.get("name", self.name),
            "tft_version": runtime_info.get("tft_version") or "",
            "tft_required_version": runtime_info.get("tft_required_version") or "",
            "yaml_version": runtime_info.get("yaml_version") or "",
            "ip": "",
            "ssid": "",
            "rssi": None,
            "last_panel_update": self._last_panel_update,
            "last_connection": (
                datetime.datetime.fromtimestamp(
                    conn.last_connection_time, tz=datetime.UTC
                ).isoformat()
                if conn and conn.last_connection_time
                else None
            ),
            # Panel Doctor: health readings for the diagnostics surface.
            "last_disconnect_reason": (conn.last_disconnect_reason if conn else None),
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
            "display_state": self.device.display_state if self.device else None,
        }
        result["idle_page"] = nav.idle_status() if nav is not None else None
        result["connection_health"] = conn.health() if conn else None

        # Active state listeners on the current page
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

    def subscribe_preview_state(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Subscribe to the small set of physical state used by the live preview.

        Callbacks run on the app worker and must return quickly without waiting
        for this app or touching its state.
        """
        with self._preview_state_lock:
            self._preview_state_subscribers.add(callback)

        def unsubscribe() -> None:
            with self._preview_state_lock:
                self._preview_state_subscribers.discard(callback)

        return unsubscribe

    def publish_preview_state(self, state: dict[str, Any]) -> None:
        """Publish a physical page/device-state snapshot to preview subscribers."""
        with self._preview_state_lock:
            subscribers = tuple(self._preview_state_subscribers)
        for callback in subscribers:
            try:
                callback(dict(state))
            except Exception as exc:
                self.log(f"Error notifying live-preview state subscriber: {exc}", level="ERROR")

    def subscribe_preview_output(self, callback: Callable[[str, Any], None]) -> Callable[[], None]:
        """Subscribe to display output generated by this physical app."""
        with self._preview_state_lock:
            self._preview_output_subscribers.add(callback)

        def unsubscribe() -> None:
            with self._preview_state_lock:
                self._preview_output_subscribers.discard(callback)

        return unsubscribe

    def publish_preview_output(self, command: str, value: Any) -> None:
        """Publish a display command to attached Live-preview mirrors."""
        with self._preview_state_lock:
            subscribers = tuple(self._preview_output_subscribers)
        for callback in subscribers:
            try:
                callback(command, list(value) if isinstance(value, list) else value)
            except Exception as exc:
                self.log(f"Error notifying live-preview output subscriber: {exc}", level="ERROR")

    def get_preview_state(self) -> dict[str, Any]:
        """Return the current page and display state for a live-preview mirror."""
        navigation = self.controller["navigation"]
        page = navigation.page
        return {
            "page": page.page_id if page is not None else None,
            "idle": navigation.idle_panel_active,
            "display_state": self.device.display_state,
            "connected": self.controller["connection"].is_connected,
        }

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

        if event.name in (ESPEvent.DISPLAY_STATE, ESPEvent.PAGE):
            self.publish_preview_state({**self.get_preview_state(), "event": event.name})
        elif event.name in (NotifEvent.NOTIF_ADD, NotifEvent.NOTIF_REMOVE, NotifEvent.NOTIF_CLEAR):
            # The sandbox preview mirrors the queue (web/preview/virtual_panel.py).
            self.publish_preview_state({**self.get_preview_state(), "event": "notifications"})

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
        self.publish_preview_state({**self.get_preview_state(), "event": "connection"})
