"""Tests for the editor sidebar panel and static path registration."""

from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

# editor_panel imports these at module level; the tests replace what it binds.
for _name, _attr in {
    "homeassistant.components.frontend": "add_extra_js_url",
    "homeassistant.components.http": "StaticPathConfig",
}.items():
    _mod = types.ModuleType(_name)
    setattr(_mod, _attr, None)
    sys.modules.setdefault(_name, _mod)

from custom_components.nspanel_haui.haui.version import get_version  # noqa: E402
from custom_components.nspanel_haui.web import editor as editor_panel  # noqa: E402


class _FakeHass:
    def __init__(self) -> None:
        self.data: dict = {}
        self.static_paths: list = []
        self.executor_jobs: list = []
        self.http = SimpleNamespace(async_register_static_paths=self._register_static_paths)

    async def _register_static_paths(self, configs) -> None:
        self.static_paths.extend(configs)

    async def async_add_executor_job(self, func, *args):
        self.executor_jobs.append(func)
        return func(*args)


@pytest.fixture
def registered(monkeypatch):
    """Run async_register_frontend against fakes and return what it registered."""
    panels: list[dict] = []
    extra_js: list[str] = []

    async def register_panel(**kwargs) -> None:
        panels.append(kwargs)

    monkeypatch.setattr(
        editor_panel, "panel_custom", SimpleNamespace(async_register_panel=register_panel)
    )
    monkeypatch.setattr(editor_panel, "add_extra_js_url", lambda hass, url: extra_js.append(url))
    monkeypatch.setattr(
        editor_panel,
        "StaticPathConfig",
        lambda url_path, path, cache_headers: SimpleNamespace(
            url_path=url_path, path=path, cache_headers=cache_headers
        ),
    )
    hass = _FakeHass()
    asyncio.run(editor_panel.async_register_frontend(hass))
    return SimpleNamespace(hass=hass, panel=panels[0], extra_js=extra_js)


def test_frontend_urls_carry_the_integration_version(registered):
    """Browsers must fetch new modules after an upgrade, including relative imports."""
    base = f"/nspanel_haui_frontend/{editor_panel._frontend_asset_version()}"

    assert [p.url_path for p in registered.hass.static_paths] == [base]
    assert registered.panel["module_url"] == f"{base}/haui-editor.js"
    assert registered.extra_js == [f"{base}/iconset.js"]


def test_version_is_read_off_the_event_loop(registered):
    """Version and asset digest require file I/O, so both are read off-loop."""
    assert editor_panel._frontend_asset_version in registered.hass.executor_jobs


def test_frontend_asset_version_changes_when_a_served_file_changes(monkeypatch, tmp_path):
    asset = tmp_path / "haui-editor.js"
    asset.write_text("old frontend", encoding="utf-8")
    monkeypatch.setattr(editor_panel, "FRONTEND_DIR", tmp_path)
    old_version = editor_panel._frontend_asset_version()

    asset.write_text("new frontend", encoding="utf-8")
    new_version = editor_panel._frontend_asset_version()

    assert old_version.startswith(f"{get_version()}-")
    assert new_version.startswith(f"{get_version()}-")
    assert new_version != old_version
