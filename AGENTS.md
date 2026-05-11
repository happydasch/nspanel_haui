You are an experienced, pragmatic software engineering AI agent. Do not over-engineer a solution when a simple one is possible. Keep edits minimal. If you want an exception to ANY rule, you MUST stop and get permission first.

## Project Overview

**NSPanel HAUI** (HomeAssistant UI) is a Home Assistant custom integration that replaces the stock Sonoff NSPanel firmware with a flexible, configurable display system built on ESPHome.

- **Language:** Python 3.14+ (the integration), JavaScript (the HA Lovelace editor frontend)
- **Hardware:** Sonoff NSPanel (ESP32 + Nextion touchscreen display)
- **Dependencies:** `pydantic>=2.0`, `python-dateutil>=2.8`, `requests>=2.31`, `packaging>=23`
- **Linting:** ruff (`E`, `F`, `W`, `I`, `UP`, `B` rulesets)
- **Type checking:** mypy (targets `haui/` package only)
- **Testing:** pytest (`tests/`)
- **Package:** setuptools (legacy build backend)

### Architecture

Three communication layers:

```
┌──────────────┐     ESPHome  ┌───────────┐    Serial    ┌──────────┐
│ Home Assistant│◄────────────►│   ESP32   │◄───────────►│ Nextion  │
│ (Hub app)    │              │ (ESPHome) │             │ Display  │
└──────────────┘              └───────────┘             └──────────┘
```

The **Hub app** (`NSPanelHAUI` in `nspanel_haui.py`) is the brain - it reads HA entity states, renders display commands, and publishes them via the ESPHome native API. The ESP32 relays commands to the Nextion display over serial and reports touch events back.

Inside the Hub app, components follow a layered structure:

- **`HAAdapter`** (`ha_adapter.py`) - bridges HA's async API to the synchronous interface expected by `haui/` core code. All HA calls go through `asyncio.run_coroutine_threadsafe`.
- **`HAUIBase`** (`haui/abstract/base.py`) - base class for all runtime objects. Provides config access, logging, command batching (`rec_cmd` context manager), and ESPHome send helpers.
- **Controllers** (`haui/controller/`) - ESPHome, connection, navigation, notification, update, gesture. Each is a `HAUIBase` subclass.
- **Pages** (`haui/page/`) - one class per display page type (grid, light, climate, weather, etc.). Each page has a `DESCRIPTOR` class attribute of type `PageDescriptor`.
- **Panels** (`haui/abstract/panel.py`) - runtime configuration wrappers for individual panel configs (user-defined panels stored in HA's panel store).
- **Mappings** (`haui/mapping/`) - static registries: page IDs → page classes, panel type keys → panel classes, colors, icons, constants.
- **Frontend** (`frontend/`) - vanilla JS modules loaded as a Home Assistant Lovelace editor for configuring panels through the HA UI.

## Reference

### Important files

| File | Purpose |
|------|---------|
| `custom_components/nspanel_haui/__init__.py` | HA integration entry point: `async_setup_entry`, config building, panel storage loading |
| `custom_components/nspanel_haui/nspanel_haui.py` | `NSPanelHAUI` class - initializes device config, controllers, panel and page instances |
| `custom_components/nspanel_haui/ha_adapter.py` | `HAAdapter` + `ItemProxy` + `ESPHomeProxy` - bridges HA async API to sync haui core |
| `custom_components/nspanel_haui/config_flow.py` | HA config flow for adding/configuring the integration via the UI |
| `custom_components/nspanel_haui/config_schema.py` | `ConfigSchema` - schema definitions for panel editing (user panel types, edit/action schemas) |
| `custom_components/nspanel_haui/storage.py` | `PanelStorage` - loads/saves panel configs from HA's internal store |
| `custom_components/nspanel_haui/api.py` | REST API views for panel config CRUD, device discovery, device config, and debug |
| `custom_components/nspanel_haui/esphome_helpers.py` | ESPHome discovery utilities (find HAUI devices, service validation) |
| `custom_components/nspanel_haui/haui/abstract/base.py` | `HAUIBase` - root base class: config access, command sending/batching, logging, lifecycle |
| `custom_components/nspanel_haui/haui/abstract/config.py` | `HAUIConfig` - typed config wrapper around the merged config dict |
| `custom_components/nspanel_haui/haui/abstract/panel.py` | `HAUIPanel` - runtime panel instance (holds items, pages, navigation actions) |
| `custom_components/nspanel_haui/haui/abstract/item.py` | `HAUIItem` - runtime item instance (wraps entity config with display logic) |
| `custom_components/nspanel_haui/haui/abstract/display_interface.py` | `DisplayInterface` + `ESPHomeTransport` - high-level display command API |
| `custom_components/nspanel_haui/haui/abstract/entity.py` | `HAUIEntity` - wraps a single HA entity with config, state listening, service calls |
| `custom_components/nspanel_haui/haui/abstract/event.py` | `HAUIEvent` - event data class for display interactions |
| `custom_components/nspanel_haui/haui/mapping/panel.py` | `PANEL_MAPPING` - type_key → (page_name, page_class) registry |
| `custom_components/nspanel_haui/haui/mapping/page.py` | `PAGE_MAPPING` - numeric page_id → page_name mapping |
| `custom_components/nspanel_haui/haui/mapping/const.py` | All constants: `ESP_EVENT`, `ESP_RESPONSE`, `COMPONENT_IDS`, `DEFAULT_CONFIG`, `DEVICE_CONFIG` |
| `custom_components/nspanel_haui/haui/device.py` | `HAUIDevice` - device instance handling gestures, callbacks, physical buttons |
| `custom_components/nspanel_haui/haui/device_config.py` | Device configuration constants and helpers |
| `custom_components/nspanel_haui/haui/config_models.py` | Pydantic models for panel and device config validation |
| `custom_components/nspanel_haui/haui/version.py` | Version string (`__version__`) - keep in sync with `pyproject.toml` and `manifest.json` |
| `esphome/install.yaml` | ESPHome config for initial device flashing |
| `esphome/nspanel_haui.yaml` | Runtime ESPHome device config |
| `nextion/nspanel_haui.tft` | Nextion display UI file (pre-compiled) |
| `pyproject.toml` | Project metadata, pytest/mypy/ruff configuration |
| `hacs.json` | HACS integration metadata |
| `custom_components/nspanel_haui/manifest.json` | HA integration manifest |

### Important directories

| Directory | Purpose |
|-----------|---------|
| `custom_components/nspanel_haui/haui/abstract/` | Base classes: `HAUIBase`, `HAUIConfig`, `HAUIEntity`, `HAUIItem`, `HAUIPanel`, `HAUIEvent`, `DisplayInterface` |
| `custom_components/nspanel_haui/haui/controller/` | Runtime controllers: ESPHome, connection, navigation, notification, update, gesture |
| `custom_components/nspanel_haui/haui/page/` | Display page implementations - one file per panel type |
| `custom_components/nspanel_haui/haui/mapping/` | Static lookups and constants |
| `custom_components/nspanel_haui/haui/utils/` | Shared utilities: color, datetime/CLDR, debounce, entity, icon, locale data, text, value |
| `custom_components/nspanel_haui/frontend/` | HA Lovelace editor UI (vanilla JS, loaded as a panel) |
| `tests/` | Pytest tests - stub out `homeassistant` to run without HA installed |
| `docs/` | User documentation (Install, Config, Panels, FAQ, ESPHome, Hub, Nextion, Communication, Design) |
| `nextion/` | Nextion display assets (TFT file, HMI source, fonts, images) |
| `esphome/` | ESPHome device configuration files |
| `scripts/` | Development utilities: font generation, color palette, translations, image conversion |
| `ref_src/home-assistant/core/` | Home Assistant core checkout - read-only reference for HA API signatures; do not modify |
| `ref_src/home-assistant/frontend/` | Home Assistant frontend source checkout — read-only reference for HA Lovelace UI patterns; do not modify |
| `ref_src/esphome/esphome/` | ESPHome source checkout - read-only reference for ESPHome component/API behavior; do not modify |
| `ref_src/custom_components/` | Read-only reference checkouts of other HA custom integrations (adaptive_lighting, frigate, hacs, localtuya, spook, etc.) - use to study patterns when writing our own integration code; do not modify |

### Reference sources

These are read-only git checkouts of upstream dependencies. All are at recent dev tips.

| Source | Repository | Version | Key directories for this project |
|--------|------------|---------|----------------------------------|
| `ref_src/home-assistant/core/` | `home-assistant/core` | `2026.6.0.dev0` | HA integration APIs, config flow patterns, entity platforms |
| `ref_src/home-assistant/frontend/` | `home-assistant/frontend` | `20260429.0` | Lovelace UI patterns, card editor components, custom panel loading |
| `ref_src/esphome/esphome/` | `esphome/esphome` | `2026.5.0-dev` | ESPHome component API, native API client, Nextion display driver |
| `ref_src/custom_components/` | Various | — | Integration patterns from hacs, adaptive_lighting, frigate, localtuya, spook, etc. (snapshot copies, no git) |

#### Frontend reference (`ref_src/home-assistant/frontend/`)

When referencing HA Lovelace UI patterns, the key paths are:

| Path | What to use it for |
|------|--------------------|
| `src/panels/lovelace/cards/` | Card type implementations — study how HA's built-in cards (light, climate, thermostat, entities, etc.) structure their editor UI, config validation, and rendering |
| `src/panels/lovelace/editor/` | Editor patterns — card editor, view editor, section editor, and config elements |
| `src/panels/lovelace/entity-rows/` | Entity row patterns — how HA renders individual entity rows in auto-generated cards |
| `src/panels/lovelace/components/` | Reusable Lovelace editor components like `hui-action-editor.ts`, `hui-entity-editor.ts` |
| `src/util/custom-panel/` | How HA loads custom panel integrations — `load-custom-panel.ts` and `create-custom-panel-element.ts` show the expected lifecycle for custom panel JavaScript |
| `src/data/lovelace/` | Data layer types and config validation |

## Essential Commands

Activate the virtual environment first:

```bash
source .venv/bin/activate
```

```bash
# Run tests
pytest tests/

# Lint Python code
ruff check custom_components/

# Lint with auto-fix
ruff check --fix custom_components/

# Type-check the haui core package
mypy

# Install dev dependencies
pip install -r requirements-dev.txt
```

**CI:** Two workflows run on push/PR to `master` and `dev`:
- `tests.yml` - runs `pytest tests/` and `ruff check custom_components/` on Python 3.12 & 3.13
- `validate.yml` - runs `hassfest` and `hacs` validators

There is no build step - the integration is installed by copying `custom_components/nspanel_haui/` into the HA `custom_components` directory.

## Patterns

### Adding a new panel type

1. Create a page class in `haui/page/yourpanel.py` that extends `HAUIBase` (or a relevant page base).
2. Define a `DESCRIPTOR` class attribute of type `PageDescriptor` with at least `type_key`, `page_name`, `label`, and `description`.
3. Import the class in `haui/mapping/panel.py` and add it to the `_page_classes` list inside `_build_panel_mapping()`.
4. If the panel has configurable options, add `OptionDescriptor` entries to `DESCRIPTOR.options`.
5. If it needs a popup variant, add a `popup_<SOMETHING>` alias in the `popup_aliases` dict.
6. Document the panel in `docs/panels/panel_yourpanel.md`.

### Config flow and schema

- `config_flow.py` handles the UI wizard for adding/configuring the integration.
- `config_schema.py` (`ConfigSchema`) defines form schemas for the panel editor (entity pickers, options, type-specific fields). Configuration is validated at the schema level before reaching the backend.
- `storage.py` (`PanelStorage`) persists panel configs to HA's internal store.

### Command batching

Use the `rec_cmd` context manager in page code to batch display commands into a single send:

```python
with self.rec_cmd:
    self.set_component_text(comp_id, "Hello")
    self.set_component_value(comp_val, 42)
    self.send_cmd("click button1,1")
```

Commands within a batch are deduplicated - only the last write to each target is sent.

### Display transport

All display commands go through `DisplayInterface` → `ESPHomeTransport`. Pages call `self.send_cmd()` (or `self.set_component_text/value()`) which delegates to `self.display.send_cmd()`. Do not call the ESPHome controller directly for display commands.

### Testing

Tests stub `homeassistant` modules via `sys.modules` manipulation (see `tests/test_config_flow.py`). Tests do **not** require a running HA instance. Use `unittest.mock` for mocking. Follow the pattern of creating minimal stub classes for HA types like `ConfigFlow`, `OptionsFlowWithConfigEntry`, etc.

When modifying `config_flow.py` or `config_schema.py`, check the corresponding tests in `tests/test_config_flow.py`.

### Config merging

The runtime config is built by merging three layers in `__init__.py:_build_config_dict()`:
1. `config_entry.data` - connection + device identity (device names, ESPHome API config)
2. `config_entry.options` - runtime toggles
3. `PanelStorage` - panel definitions per device

The merged dict is passed to `HAUIConfig` which provides typed access. Store (panel storage) values win over `config_entry.data` defaults.

### Locale/translations

The project uses hardcoded CLDR locale data (see `haui/utils/locale_data.py`) instead of depending on Babel. Date formatting uses inline locale data in `haui/utils/datetime.py`. Display text translations use lookup tables in `haui/utils/text.py`.

## Code Style

- **Line length:** 100 characters (configured in `pyproject.toml`)
- **Python version:** 3.14+ (use `from __future__ import annotations` for deferred evaluation)
- **Imports:** sorted with `ruff` (`I` rule), use `from __future__ import annotations` in all modules
- **Type annotations:** use `TYPE_CHECKING` for circular import avoidance; prefer concrete types
- **Naming:** `NSPanelHAUI` for the top-level app class, `HAUI` prefix for abstract/core classes; page classes use `SuffixPage` naming (e.g., `GridPage`, `ClimatePage`)
- **Docstrings:** Google-style docstrings with `Args:`/`Returns:` sections
- **Logging:** use `_LOGGER = logging.getLogger(__name__)` at module level; use `self.log()` and `self.debug_log()` in `HAUIBase` subclasses

## Anti-patterns

- **Don't call HA APIs directly from `haui/` code** - always go through `self.app` (the `NSPanelHAUI`/`HAAdapter` instance). The adapter bridges async HA calls to the synchronous thread the haui core runs on.
- **Don't call the ESPHome controller directly for display commands** - use `self.send_cmd()`, `self.set_component_text()`, or `self.set_component_value()` which go through `DisplayInterface`.
- **Don't add `asyncio` code in `haui/` core** - the core runs synchronously on an executor thread. All async bridging happens in `HAAdapter`.
- **Don't commit to `ref_src/`** - `ref_src/home-assistant/core/`, `ref_src/home-assistant/frontend/`, `ref_src/esphome/esphome/`, and `ref_src/custom_components/` are read-only reference checkouts. Use them only for discovering HA / ESPHome API signatures and studying integration patterns.
- **Don't add comments that restate the code** - comments should explain _why_, not _what_. See the core AGENTS.md guideline.
- **Don't use silent fallbacks or defaults** - prefer failing loudly over swallowing errors or guessing a fallback value. A crash or exception is easier to debug than a silently wrong behavior caused by a default. Only use fallbacks when the call site explicitly chooses to handle the failure gracefully, and even then, log at warning level.

## Commit and Pull Request Guidelines

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): message`

Common types seen in this repo: `fix`, `feat`, `refactor`, `docs`, `test`, `style`, `chore`.

Common scopes: `frontend`, `esphome`, `device`, `grid`, `ui`, `clocktwo`.

Example: `fix(esphome): include device name in discovery fallback`

### Before committing

1. **Keep docs in sync** — after any code change, check the `docs/` directory for files related to what you changed and update them to reflect the new behavior, options, schemas, or defaults. Outdated docs are bugs.
2. Run `pytest tests/` - all tests must pass
3. Run `ruff check custom_components/` - no lint errors
4. Run `mypy` - no new type errors in `haui/`
5. If you changed config flow logic, ensure `test_config_flow.py` covers the change
6. If your changes affect documented behavior (new options, changed defaults, new panel type features, etc.), update the corresponding docs in `docs/` to match

### Pull requests

- Target the `dev` branch for feature work, `master` for hotfixes
- Describe what changed, why, and how it was tested
- Reference related issues or PRs
