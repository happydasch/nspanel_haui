"""Serialize panel-store changes with Home Assistant's config-entry lifecycle."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Collection, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from ..const import DOMAIN
from ..hub.storage import empty_store, enabled_device_names, finish_panel_write, panel_store
from .common import ApiError, get_apps

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class PanelEdit:
    """One read-modify-save operation, including any in-place runtime apply."""

    def __init__(self, hass: Any, entry: ConfigEntry) -> None:
        self._hass = hass
        self.entry = entry
        self._store = panel_store(hass, entry.entry_id)
        self.reload_idle = False

    async def load(self) -> dict[str, Any]:
        return await self._store.async_load() or empty_store()

    async def save(
        self,
        data: dict[str, Any],
        *,
        apply: bool = True,
        devices: Collection[str] | None = None,
        entry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        async def commit() -> dict[str, Any]:
            await self._store.async_save(data)
            if entry_data is not None:
                # The entry update listener reloads after the store is committed.
                self._hass.config_entries.async_update_entry(self.entry, data=entry_data)
            if apply:
                return await self._apply(data, devices)
            return {"status": "ok"}

        return await finish_panel_write(commit())

    async def _apply(self, data: dict[str, Any], devices: Collection[str] | None) -> dict[str, Any]:
        hass, entry = self._hass, self.entry
        entry_id = entry.entry_id
        from ..web.preview.live_panel import async_reload_viewers
        from ..web.websocket import async_reload_hosts

        apps = get_apps(hass, entry_id)
        if apps is None:
            await async_reload_hosts(hass, entry_id, data)
            return {"status": "ok"}

        if not apps or set(enabled_device_names(entry.data, data)) != set(apps):
            await async_reload_hosts(hass, entry_id, data)
            if apps:
                hass.config_entries.async_schedule_reload(entry_id)
            else:
                self.reload_idle = True
            return {"status": "ok", "reloaded": True}

        from .. import _build_config_dict

        for name in apps if devices is None else devices:
            app = apps.get(name)
            if app is None or not app.device_config:
                continue
            try:
                cfg = _build_config_dict(entry.data, data, device_name=name)
                await app.async_run_on_worker(app.reload_config, cfg)
            except Exception:
                _LOGGER.exception(
                    "Failed to push panel update to device '%s' for %s", name, entry_id
                )

        # Home-card button tracking reads the physical workers' updated config.
        await async_reload_hosts(hass, entry_id, data)
        await async_reload_viewers(hass, entry_id)
        return {"status": "ok"}


@asynccontextmanager
async def edit_panels(hass: Any, entry_id: str) -> AsyncGenerator[PanelEdit]:
    """Keep reads, writes and in-place applies in order, even across entry setup."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ApiError("Config entry not found", 404)
    async with entry.setup_lock:
        if hass.config_entries.async_get_entry(entry_id) is not entry:
            raise ApiError("Config entry not found", 404)
        edit = PanelEdit(hass, entry)
        try:
            yield edit
        except asyncio.CancelledError:
            if edit.reload_idle:
                hass.config_entries.async_schedule_reload(entry_id)
            raise

    # A full reload takes this same lock and reads the latest saved snapshot.
    if edit.reload_idle and hass.config_entries.async_get_entry(entry_id) is entry:
        await hass.config_entries.async_reload(entry_id)
