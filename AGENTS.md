You are an experienced, pragmatic software engineering AI agent. Do not over-engineer a solution when a simple one is possible. Keep edits minimal. Ask for permission before making an exception to any rule.

## Project Overview

**NSPanel HAUI** (HomeAssistant UI) is a Home Assistant custom integration that replaces the stock Sonoff NSPanel firmware with a flexible, configurable display system built on ESPHome.

- **Language:** Python 3.14+ (integration; `requires-python = ">=3.14"` in `pyproject.toml`, the Python Home Assistant 2026.11 requires; CI runs 3.14), JavaScript (HA Lovelace editor frontend)
- **Hardware:** Sonoff NSPanel (ESP32 + Nextion touchscreen display)
- **Home Assistant:** minimum `2026.11` (declared in the Marketplace metadata; the release that replaced HACS with the built-in Marketplace, which installs the integration as a custom repository); integration type `hub`, IoT class `local_push`
- **Runtime dependencies:** `pydantic>=2.0`, `python-dateutil>=2.8.0` (declared in `manifest.json`); `requests` and `packaging` are also imported by the update controller; both ship with Home Assistant core, so they are not listed in `manifest.json`
- **Linting and formatting:** ruff (`E`, `F`, `W`, `I`, `UP`, `B` rulesets; line length 100; target `py314`); agents must format changed Python code with `ruff format` and verify formatting before finishing
- **Type checking:** mypy (targets `custom_components/nspanel_haui/haui` only)
- **Testing:** pytest (`tests/`) + Node's built-in test runner (`tests/frontend/*.test.mjs`)
- **Package:** setuptools (legacy build backend); no build step — the integration is installed by copying the folder into HA

### Architecture

Three communication layers:

```
┌──────────────┐     ESPHome  ┌───────────┐    Serial    ┌──────────┐
│ Home Assistant│◄────────────►│   ESP32   │◄───────────►│ Nextion  │
│ (Hub app)    │              │ (ESPHome) │             │ Display  │
└──────────────┘              └───────────┘             └──────────┘
```

The **Hub app** (`NSPanelHAUI` in `hub/app.py`) is the brain - it reads HA entity states, renders display commands, and publishes them via the ESPHome native API. The ESP32 relays commands to the Nextion display over serial and reports touch events back.

Inside the Hub app, components follow a layered structure:

- **`HAAdapter`** (`hub/adapter.py`) - bridges HA's async API to the synchronous interface expected by `haui/` core code. All HA calls go through `asyncio.run_coroutine_threadsafe`. Every call from HA into an app (device events, state changes, timers, reloads, services, notify) runs on that app's single worker thread, in order: use `app.dispatch()` (fire-and-forget, from the event loop) or `await app.async_run_on_worker()`, never `hass.async_add_executor_job` with app code. **Blocking work never runs on the worker:** hand HTTP/disk calls to `app.run_off_worker(fn, *args, timeout=…)` (waits for the result, keeps app state single-threaded) or `app.submit_off_worker(fn, on_done=…)` (fire-and-forget, result applied back on the worker). The callable must not touch app state, since it runs on another thread. **Two more exceptions, for liveness traffic only:** `app.run_every(..., on_loop=True)` fires its callback directly on the HA event loop, and `publish_detached()` (controller → `ESPHomeProxy`) sends a command fire-and-forget without the worker. The hub→device heartbeat uses both: the device force-disconnects the hub after two missed 5 s heartbeats and wakes the display when it does, so a worker stalled by a render burst or a slow update check must never delay it. Everything else stays on the worker. The hub-side idle-page timeout belongs to `HAUINavigationController` and uses one worker-thread `run_every` check per second; do not add per-page timeout timers or use a firmware timeout event for page switching.
- **`HAUIBase`** (`haui/abstract/haui_base.py`) - base class for all runtime objects. Provides config access, logging, command batching (`rec_cmd` context manager), and ESPHome send helpers. `HAUIConfigAccess` (`haui/abstract/haui_config_access.py`) is its lighter sibling for data/config wrappers that need no display transport or lifecycle.
- **Controllers** (`haui/controller/`) - ESPHome, connection, navigation, notification, update, gesture. Each is a `HAUIBase` subclass.
- **Pages** (`haui/page/`) - one class per display page type (grid, light, climate, weather, etc.). Each page has a `DESCRIPTOR` class attribute of type `PageDescriptor` (`haui/mapping/descriptor.py`) and a `COMPONENTS` registry of Nextion widgets.
- **Panels** (`haui/abstract/haui_panel.py`) - runtime configuration wrappers for individual panel configs (user-defined panels stored in HA's panel store).
- **Mappings** (`haui/mapping/`) - static registries: `PAGE_MAPPING` (numeric Nextion page ID → page name), `PANEL_MAPPING` (panel type key → `(page_name, page_class)`), `SYS_PANEL_MAPPING` (the fixed system panels) and `POPUP_PANEL_MAPPING` (the popups), colors, icons, constants.
- **Frontend** (`frontend/`) - vanilla JS modules loaded as a Home Assistant Lovelace editor for configuring panels through the HA UI.

## Reference

### Important files

| File | Purpose |
|------|---------|
| `custom_components/nspanel_haui/__init__.py` | HA integration entry point: `async_setup_entry`, config building, panel storage loading |
| `custom_components/nspanel_haui/hub/app.py` | `NSPanelHAUI` class - initializes device config, controllers, panel and page instances |
| `custom_components/nspanel_haui/hub/adapter.py` | `HAAdapter` + `ItemProxy` + `ESPHomeProxy` - bridges HA async API to sync haui core |
| `custom_components/nspanel_haui/config_flow.py` | HA config flow for adding/configuring the integration via the UI |
| `custom_components/nspanel_haui/hub/storage.py` | `PanelStorage` - loads/saves panel configs from HA's internal store |
| `custom_components/nspanel_haui/hub/rollout.py` | `UpdateRollout` - Fleet's **Install updates**: one device at a time, on the event loop, through each app's async update methods only; holds the queued devices' automatic firmware installs; in memory, one per entry |
| `custom_components/nspanel_haui/api/` | REST API views, one module per area: `editor` (translations, panel types, panel templates, colours, icons), `config` (panel store read, per-device settings and panels, device order, devices, YAML, `push_panels`), `status` (device status, notifications, display refresh), `updates` (TFT/firmware installs, local uploads, release lists, update checks, scheduled-install control, the rollout); `common` holds the shared helpers (`ApiError` + `@api_errors`, `running_apps`/`device_app`, `json_object`, `for_each_app`); `register_views` registers `VIEWS` |
| `custom_components/nspanel_haui/hub/esphome_helpers.py` | ESPHome discovery utilities (find HAUI devices in the device registry, resolve their entities) |
| `custom_components/nspanel_haui/web/preview/virtual_panel.py` | Editor live preview in Simulated (sandbox) mode and panel cards: `VirtualNSPanelHAUI` + `VirtualESPHomeProxy` (one second app per device, driven by the browser instead of ESPHome), `VirtualPanelHost` (viewers + isolated card renders) |
| `custom_components/nspanel_haui/web/preview/sandbox.py` | Simulated entity states for the live preview's sandbox mode |
| `custom_components/nspanel_haui/web/websocket.py` | Virtual panel WebSocket commands (`nspanel_haui/virtual_panel/subscribe`, `/event`, `/home`, `/open`, `/idle`, `/reset_sandbox` for the sandbox preview, `/render` for panel cards) and the one-app-per-device host registry |
| `custom_components/nspanel_haui/web/preview/live_panel.py` | Editor live preview in Live mode: `LivePanel` mirrors the device's running app (its display output, checked input) and its WebSocket commands (`nspanel_haui/live_panel/subscribe`, `/event`, `/slider`, `/action`); shares nothing with the sandbox |
| `custom_components/nspanel_haui/web/preview/button_lights.py` | Hardware button lights of the preview frame, shared by the sandbox and live previews |
| `custom_components/nspanel_haui/web/editor.py` | Registers the editor sidebar panel and serves `frontend/` as static files; keep Python files out of `frontend/`, which is served without authentication |
| `custom_components/nspanel_haui/haui/abstract/haui_base.py` | `HAUIBase` - root base class: config access, command sending/batching, logging, lifecycle |
| `custom_components/nspanel_haui/haui/abstract/haui_config_access.py` | `HAUIConfigAccess` - lightweight config/logging base for data wrappers (no display transport) |
| `custom_components/nspanel_haui/haui/abstract/haui_page.py` | `HAUIPage` - page base class: lifecycle hooks, title/colour helpers, items and their state listeners; touch input comes from `TouchInputMixin` |
| `custom_components/nspanel_haui/haui/abstract/component.py` | `Component(NamedTuple)` + `ComponentRegistry` - type-safe page component declarations |
| `custom_components/nspanel_haui/haui/abstract/haui_config.py` | `HAUIConfig` - typed config wrapper around the merged config dict |
| `custom_components/nspanel_haui/haui/abstract/haui_panel.py` | `HAUIPanel` - runtime panel instance (holds items, pages, navigation actions) |
| `custom_components/nspanel_haui/haui/abstract/haui_item.py` | `HAUIItem` - runtime item instance (wraps entity config with display logic) |
| `custom_components/nspanel_haui/haui/abstract/display_interface.py` | `DisplayInterface` + `ESPHomeTransport` - high-level display command API |
| `custom_components/nspanel_haui/haui/abstract/haui_entity.py` | `HAUIEntity` - wraps a single HA entity with config, state listening, service calls |
| `custom_components/nspanel_haui/haui/abstract/haui_event.py` | `HAUIEvent` - event data class for display interactions |
| `custom_components/nspanel_haui/haui/abstract/mixins/` | `ComponentMixin`, `FunctionButtonMixin`, `TouchInputMixin` (release/press callbacks, slider drags, tap-or-swipe buffer, long press back, display reads), `PagedItemsMixin` (paging + debounced item updates for grid/row), `CycleCardsMixin` (the clock/weather cycle cards, fitted to the font) - page behavior mixins |
| `custom_components/nspanel_haui/haui/mapping/panel.py` | `PANEL_MAPPING` and `PAGE_MAPPING` registries; `_build_panel_mapping()`, `SYS_PANEL_MAPPING` and `POPUP_PANEL_MAPPING` |
| `custom_components/nspanel_haui/haui/mapping/descriptor.py` | `PageDescriptor` + `PageOption` metadata and the `_()` translation marker |
| `custom_components/nspanel_haui/haui/option_rules.py` | Field-level rules of a `PageOption` (`required`, `min`, `max`, `domain`, `choices`, `max_items`, colour); `validate_panels` enforces them on new or changed panels. `frontend/option-rules.js` mirrors it: change both with `tests/fixtures/option_rules_cases.json`, which runs through both engines |
| `custom_components/nspanel_haui/haui/mapping/templates.py` | `PANEL_TEMPLATES` - the *Add panel* starter templates: keyless panels whose empty entity slots (`{"item": ""}`) the option rules mark for the user to fill |
| `custom_components/nspanel_haui/haui/mapping/const.py` | String enums and constants: `ESPEvent`, `ESPResponse`, `ESPCommand`, `ESPAction`, `SysPanelKey` (fixed system panel keys), `PopupPanelKey` (popup keys), `NotifType`, `DEFAULT_CONFIG`, `PANEL_CONFIG` |
| `custom_components/nspanel_haui/haui/device.py` | `HAUIDevice` - device instance handling gestures, callbacks, physical buttons |
| `custom_components/nspanel_haui/haui/device_config.py` | `DEVICE_CONFIG` defaults and derived `DEVICE_CONFIG_FIELDS` |
| `custom_components/nspanel_haui/haui/config_models.py` | Pydantic v2 validation (`validate_config`, `validate_device_config`, `validate_panels` + `PanelValidationError`) |
| `custom_components/nspanel_haui/haui/features.py` | Home Assistant feature-bit constants (e.g. `MediaPlayerFeatures`) |
| `custom_components/nspanel_haui/haui/version.py` | `get_version()` - lazily reads the version from `manifest.json` (source of truth); keep `pyproject.toml` in sync |
| `esphome/install.yaml` | ESPHome config for initial device flashing |
| `esphome/nspanel_haui.yaml` | Runtime ESPHome device config |
| `nextion/nspanel_haui.tft` | Nextion display UI file (pre-compiled) |
| `pyproject.toml` | Project metadata, pytest/mypy/ruff configuration |
| `hacs.json` | Marketplace repository metadata (name, minimum Home Assistant version); the Marketplace kept HACS's file format |
| `custom_components/nspanel_haui/manifest.json` | HA integration manifest |

### Important directories

| Directory | Purpose |
|-----------|---------|
| `custom_components/nspanel_haui/haui/abstract/` | Base classes: `HAUIBase`, `HAUIConfigAccess`, `HAUIConfig`, `HAUIEntity`, `HAUIItem`, `HAUIPanel`, `HAUIEvent`, `HAUIPage`, `DisplayInterface`; `mixins/` holds page behavior mixins |
| `custom_components/nspanel_haui/haui/controller/` | Runtime controllers: ESPHome, connection, navigation, notification, update, gesture |
| `custom_components/nspanel_haui/haui/page/` | Display page implementations - one file per panel type (20 page modules, plus the `clock_common.py` helper used by the clock, clocktwo and weather pages) |
| `custom_components/nspanel_haui/haui/mapping/` | Static lookups: `panel.py` (`PANEL_MAPPING`), `page.py` (`PAGE_MAPPING`), `descriptor.py` (`PageDescriptor`), colors, icons, constants |
| `custom_components/nspanel_haui/haui/utils/` | Shared utilities: `color`, `datetime`/CLDR, `debounce`, `icon`, `item`, `locale_data`, `notification_blinker`, `page`, `text`, `value` |
| `custom_components/nspanel_haui/hub/` | Home Assistant-facing runtime: `app.py` (`NSPanelHAUI`), `adapter.py` (`HAAdapter`/`ItemProxy`/`ESPHomeProxy`), `storage.py` (`PanelStorage`), `esphome_helpers.py` (device discovery) |
| `custom_components/nspanel_haui/web/` | Browser-facing surface: `editor.py` (sidebar panel + static assets), `websocket.py` (virtual panel commands) and `preview/` (sandbox, live view, button lights) |
| `custom_components/nspanel_haui/frontend/` | HA Lovelace editor UI (vanilla JS, loaded as a panel); `previews/` holds panel preview renderers |
| `tests/` | Pytest tests (backend) plus Node test-runner tests in `tests/frontend/`; `conftest.py` stubs `homeassistant` and `dateutil`, so no running HA instance is needed |
| `docs/` | Documentation site: `user/` (install, quick start, updating, configuration, panels, device, services, examples, FAQ, troubleshooting) and `develop/` (development, release, update process, design, frontend, communication, notifications, ESPHome, Hub, Nextion); the home page `README.md`, the generated `screens.html` and `cheatsheet.html` and `assets/` stay at the top level |
| `nextion/` | Nextion display assets (TFT file, HMI source, fonts, images) |
| `esphome/` | ESPHome device configuration files (`install.yaml`, runtime/dev configs, `secrets.yaml.example`; copy it to the git-ignored `secrets.yaml` for local builds). Requires ESPHome 2026.10 or later (`min_version` in `nspanel_haui/base.yaml`). `nextion_patch/` is a **temporary vendored patched copy of the stock `nextion` component** (the numeric-response fix, esphome#17744, and the TFT upload `tft_upload_http_buffer_size_tx` option, esphome#21435, both missed the 2026.10.0 release, plus a TFT upload retry fix that is not upstream yet) wired in via `external_components` in `nspanel_haui.yaml` (git source) and the universal/dev configs (local source) — delete the dir + override blocks and bump `min_version` + `requirements-esphome.txt` when a released ESPHome contains every fix listed in `nextion_patch/README.md` |
| `scripts/` | Development utilities: font generation (`font_tools`, `charset`), colour palettes/wheels (`color_palette`, `color_wheel`), spinner generation (`spinner`), background tile generation (`backgrounds`), design grids (`design_grid`), layout tools (`hmi_layout`: HMI geometry patching and virtual-layout export), RGB565 image conversion (`rgb565_image`), Nextion2Text, card gallery with PNG export and the docs screen overview (`preview_gallery`), README images (`readme_images`, writes `docs/assets/readme/`), translation extraction, release version bump (`bump_version`, `bump_tft_version`), local test firmware release (`dev_release`), the release workflows' steps (`release/`: dev version, firmware compile, manifest, dev release notes), the dev docs site URLs (`docs/dev_site.sh`), noVNC bridge to the Nextion Editor VM (`nextion_vnc`) |
| `ref_src/home-assistant/core/` | Home Assistant core checkout - read-only reference for HA API signatures; do not modify |
| `ref_src/home-assistant/frontend/` | Home Assistant frontend source checkout — read-only reference for HA Lovelace UI patterns; do not modify |
| `ref_src/esphome/esphome/` | ESPHome source checkout - read-only reference for ESPHome component/API behavior; do not modify |
| `ref_src/custom_components/` | Read-only reference checkouts of other HA custom integrations (adaptive_lighting, frigate, hacs, localtuya, spook, etc.) - use to study patterns when writing our own integration code; do not modify |

### Reference sources

These are read-only git checkouts of upstream dependencies at recent dev tips; refresh the numbers in the table with `git -C <path> describe --tags --always`.

| Source | Repository | Checkout (`git describe --tags --always`) | Key directories for this project |
|--------|------------|-------------------------------------------|----------------------------------|
| `ref_src/home-assistant/core/` | `home-assistant/core` | `2026.6.0-409-gc6a57bc81a2` | HA integration APIs, config flow patterns, entity platforms |
| `ref_src/home-assistant/frontend/` | `home-assistant/frontend` | `20260527.0-148-g125629ed3` | Lovelace UI patterns, card editor components, custom panel loading |
| `ref_src/esphome/esphome/` | `esphome/esphome` | dev tip (`0fb7cf5aa`) | ESPHome component API, native API client, Nextion display driver |
| `ref_src/custom_components/` | Various | — | Integration patterns from different custom components (snapshot copies, no git) |

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

Activate a virtual environment first. A local dev venv may already exist at `.venv/` (Python 3.14, matching CI); a separate `.venv_docs/` venv is handy for docs builds:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # first time only
```

```bash
# Run backend tests (HA is stubbed; no running instance needed; Node 22+ replays card renders)
pytest tests/

# Run frontend editor tests (Node 22+, no npm dependencies)
node --test 'tests/frontend/*.test.mjs'

# Type-check the editor modules that opt in with // @ts-check (npm ci once per clone)
npm ci
npm run typecheck:frontend

# Format Python code (agents must run this on changed Python files before finishing)
ruff format custom_components/ scripts/ tests/

# Verify Python formatting
ruff format --check custom_components/ scripts/ tests/

# Lint Python code
ruff check custom_components/ scripts/

# Lint with auto-fix
ruff check --fix custom_components/ scripts/

# Type-check the haui core package
mypy

# Build docs strictly (catches broken links and missing files)
pip install -r requirements-docs.txt   # first time only
zensical build --strict

# Regenerate locale JSON after changing t()/translate()/_() strings
python -m scripts.translations.extract_translations

# Install the repository git hooks (once per clone; sets core.hooksPath)
scripts/git_hooks/install.sh
```

The `pre-commit` hook (`scripts/git_hooks/pre-commit`) runs `scripts/hmi_layout/gen_virtual_layout.py`, stages `frontend/virtual/layout_*.json`, `icon_map.json` and `pictures/`, then checks both specs with `scripts/hmi_layout/gen_layout.py --check` (landscape) and `scripts/hmi_layout/gen_layout.py --spec portrait --check`. It exists because a committed HMI change without its regenerated layout silently breaks the editor's previews and card renders.

**CI:** `ci.yml` runs on push/PR to `master` and `dev` and on manual dispatch, with one job per gate; a newer run on the same branch or PR cancels the previous one:
- `tests (3.14)` - installs the dev dependencies (Node 24 included for the card render replay), checks the icon cheatsheet, translations, version sources and the HMI bump, validates the Nextion assets (`verify_nextion`; pytest runs both `gen_layout` spec checks), and runs `pytest tests/`, `ruff format --check custom_components/ scripts/ tests/`, `ruff check custom_components/ scripts/` and `mypy` on Python 3.14
- `frontend` - `npm run typecheck:frontend` and `node --test 'tests/frontend/*.test.mjs'` on Node 24
- `esphome` - runs `esphome config esphome/nspanel_haui_universal.yaml` in its own environment, because ESPHome's cryptography pin conflicts with the dev requirements
- `docs` - builds the docs once per run (`zensical build --strict`); every push or manual dispatch on `master` or `dev` (each Development Firmware run dispatches one on `dev`) uploads the site artifact, and `deploy-docs` reuses it for the pushed branch, builds only the sibling, and deploys Pages with `master` at the root, `dev` under `dev/` (the editor footer's Documentation link opens `dev/` on prerelease versions)
- `hassfest` and `hacs` - validators

Release workflows (not PR checks): `dev-firmware.yml` (`Development Firmware`) publishes a development build as a prerelease when manually dispatched on `dev` (see *Dev releases are tagged with their version*) and commits the version together with the regenerated screen overview as one bot commit (a `screens_only` dispatch regenerates the screens alone), then dispatches `ci.yml` on `dev`, because a push with the workflow's `GITHUB_TOKEN` starts no workflow (that run tests the commit and deploys the docs with the new screens), and `release.yml` builds a stable release from a `v*` tag push (it refuses a `workflow_dispatch` run that is not on a `v*` tag, since only tags carry a firmware manifest).

There is no build step - the integration is installed by copying (or symlinking) `custom_components/nspanel_haui/` into the HA `custom_components` directory and restarting Home Assistant. To run the checkout in a real Home Assistant, use the throwaway instance from `.venv_ha` on `.dev/ha-config` or the Docker one (`compose.yaml`) on `.dev/ha-docker` (all git-ignored; setup, start and reset: `docs/develop/development.md`, *Development instance in a virtual environment* / *in Docker*), and restart HA after Python changes. Frontend assets are served from a versioned static path registered at startup, so restart/reload HA to pick up frontend changes.

**Clean:** remove caches and the built docs site:

```bash
rm -rf site .pytest_cache .ruff_cache .mypy_cache
find . -type d -name __pycache__ -prune -exec rm -rf {} +
```

## Patterns

### Page component declarations

Use `Component` (NamedTuple with `.id` and `.name`) and `ComponentRegistry` instead of raw `(int, str)` tuples for Nextion display widget declarations.

**Base page provides header buttons:**
```python
from typing import ClassVar
from ..abstract.component import Component, ComponentRegistry


class HAUIPage:
    COMPONENTS: ClassVar[ComponentRegistry] = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
    )
```

**Subclass pages extend via `.merge()`:**
```python
class CoverPage(HAUIPage):
    COMPONENTS = HAUIPage.COMPONENTS.merge(
        header=Component(2, "tHeader"),
        title=Component(3, "tTitle"),
        fnc_left_pri=Component(4, "bFncLPri"),
        fnc_left_sec=Component(5, "bFncLSec"),
        fnc_right_pri=Component(6, "bFncRPri"),
        fnc_right_sec=Component(7, "bFncRSec"),
        btn_up=Component(8, "bUp"),
        btn_stop=Component(9, "bStop"),
        btn_down=Component(10, "bDown"),
        h_vert_pos=Component(11, "hVertPos"),
        t_info=Component(12, "tInfo"),
    )
```

`BlankPage` intentionally does **not** merge the base registry — it has no header buttons, so it declares `COMPONENTS = ComponentRegistry(h_blank=Component(1, "hBlank"))`.

**Access pattern:**
```python
self.set_component_text(self.COMPONENTS.title, "Hello")
self.set_component_text(self.COMPONENTS.t_info, "42%")
component.name  # instead of component[1]
component.id  # instead of component[0]
```

**Naming convention:** Use snake_case purpose-based names (e.g., `title`, `btn_up`, `t_time`, `t_main_icon`), not Nextion widget identifiers.

**Method signatures** use `Component` type instead of `tuple[int, str]` or `tuple`:
- `set_component_text(component: Component, text: str)`
- `set_component_value(component: Component, value: int)`
- `add_component_callback(component: Component, callback: Callable)`
- Callback handlers: `def callback(self, event: HAUIEvent, component: Component, button_state: int)`
- Prefer `on_release(component, callback)` for release-only callbacks: it receives `(event, component)` and avoids the `button_state` argument. Use `add_component_callback` only for rare press-event handling that needs `button_state`.

### Adding a new panel type

1. **Inspect the page's widgets** in the Nextion HMI file to find each widget's ID and name (see *Nextion HMI inspection* below).
2. Create a page class in `haui/page/yourpanel.py` that extends `HAUIBase` (or a relevant page base).
3. Define a `COMPONENTS` class attribute using `ComponentRegistry` with `Component` entries for each Nextion widget on the page. Follow snake_case purpose-based naming.
4. Define a `DESCRIPTOR` class attribute of type `PageDescriptor` with at least `type_key`, `page_name`, `page_id`, `label`, `description` and `category` (the `PANEL_CATEGORIES` key — `backgrounds`, `entities`, `grouping` or `tools` — that files the type in the *Add panel* catalog; plus `options`/`item_options` as needed).
5. Import the class in `haui/mapping/panel.py` and add it to the module-level `_page_classes` list.
6. If the panel has configurable options, add `PageOption` entries to `DESCRIPTOR.options` and read them with `self.option(panel, key)`.
7. If it needs a popup variant, set descriptor metadata instead of editing a registry: `popup_alias_for="<parent_type_key>"` for a different class on the same Nextion page, or `can_show_popup=True` for a non-system page (which auto-registers `popup_<page_name>`; the media page is special-cased as `popup_media_player`). System popups are derived from `is_system=True` plus `sys_panel_default["key"]` starting with `popup_`.
8. Document the panel in `docs/user/panels/panel_yourpanel.md`.
9. Set `DESCRIPTOR.page_id`; the editor's shared Nextion-simulator preview resolves the physical page automatically (see *Preview renderer workflow* below).

### Nextion HMI inspection

The display UI is compiled from `nextion/nspanel_haui.HMI` (edited in the Nextion IDE). To see a page's widget IDs, names, attributes, and event code (touch scripts) before writing its Python `ComponentRegistry`, generate a readable text dump with [Nextion2Text](scripts/nextion2text/Nextion2Text.py):

```bash
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui.HMI -o ref_src/nextion-out-visual -d -s -p visual
```

- `-i` — path to the compiled `.HMI` file
- `-o` — output folder, one `.txt` file per Nextion page named after the page; `ref_src/` is git-ignored, safe to regenerate here
- `-d` — clear the output folder first, so stale files from a previous run don't linger
- `-s` — also write a stats summary file (component/event counts)
- `-p visual` — include visual properties (position, size, colors), not just the default non-visual ones; needed to read widget coordinates for preview renderers

Each generated file lists the page's widgets (ID, Nextion name, attributes) and event code (`Preinitialize Event`, `Touch Press Event`, etc.) — use it to map Nextion widget IDs/names to `Component(id, "name")` entries and to see what a button's touch script already does on the device side. Run `python -m scripts.nextion2text.Nextion2Text --help` for the full flag reference.

### Editing the Nextion HMI by script

Geometry and other int attributes of existing widgets can be patched in place by script; everything that changes a block's length (adding/removing widgets, event code, text of another length, pictures, fonts) is Nextion Editor work. `scripts/hmi_layout/gen_layout.py` is the reference implementation (`parse_pages`, `_write_attr`, `block_crc`); it applies a spec module — `landscape_layout.py` (partial refinements of the 480 × 320 layout, default) or `portrait_layout.py` (`--spec portrait`, the complete 320 × 480 layout); extend the spec rather than hand-editing bytes.

**Both HMIs share one definition of components.** The Python `COMPONENTS` registries address `nspanel_haui.HMI` and `nspanel_haui_portrait.HMI` with the same names and ids, so every change to one HMI — a widget added, removed, renamed or re-ordered, an attribute or geometry edit, event code — must be applied to the other as well (geometry and attributes through the sibling spec: `landscape_layout.py` ↔ `portrait_layout.py`). Be extra careful here: a widget that exists in only one HMI breaks that TFT silently at runtime. Run `gen_layout.py --check` for landscape, `gen_layout.py --spec portrait --check` for portrait, and `python -m scripts.verify_nextion.verify_nextion --require-portrait` before calling either HMI done.

**Editing display files:** when editing Nextion display files, use the Nextion Editor via VNC/noVNC. The editor is a Windows GUI application, so drive it over VNC/noVNC on the desktop where it runs; `scripts/nextion_vnc/nextion_vnc.sh` starts the noVNC bridge (VM `192.168.65.2:5900` by default, override with `NEXTION_VNC_HOST`/`NEXTION_VNC_PORT`/`NOVNC_PORT`) and prints the page URL, which connects and scales the screen to the window. Use the editor for anything the script cannot do safely (see above), then follow the workflow below.

Workflow (the editor owns the file while a project is open):

1. **Close the project** in the Nextion Editor (File → Close Project) before writing the HMI. The editor silently re-saves the open project on Close Project and on every project switch, overwriting whatever a script wrote.
2. **Patch**, then prove it: re-dump with Nextion2Text (`-p visual`) and compare every widget against the spec — `gen_layout.py` does this itself and refuses to write on any mismatch. Its `--check` mode reports widgets that exist on only one side *and* attribute values that differ from the spec (alignment, font, …), so a spec-only change cannot pass while the committed HMI still has the old value. The portrait spec names the landscape HMI as its `SIBLING_HMI`: both files must hold the same widgets and every widget's Send Component ID (`sendkey`) is copied from the landscape project — toggle touch settings there, never in the portrait copy. `scripts/verify_nextion/verify_nextion.py --require-portrait` enforces that parity.

**Solid pages paint the theme in Preinitialize, never the hub after the page is shown.** `HAUIPage.prepare_page_load` sends the panel's theme (`HAUIPanel.theme`, defaulting to the device theme) to the `Program.s` globals in `THEME_GLOBALS` (`haui/mapping/color.py`) right before every `goto_page`, and each solid-colour page assigns them to its own `bco` and to every widget colour compiled with a theme colour, so a page never changes colour once it is visible (there is no `cls`). The code is generated from the HMI — `python -m scripts.hmi_layout.gen_virtual_layout --theme-code <page>` — and pasted right after `sendme` in both HMIs; `gen_virtual_layout.py --check` fails while a page's code is missing or stale, so re-paste it whenever a widget compiled with a theme colour changes. The hub therefore never sends these theme colours itself, only colours that follow a widget's state or a panel setting. Everything a page reads while it loads comes from `HAUIPage.page_load_commands(panel)` (the theme, plus a picture page's background); a saved config shows the current panel again on the loaded page only while those commands are unchanged (`is_loaded_for`), so panels with different themes on the same page reload it; otherwise navigation loads the page again.

**The hub reads `tft_version` only from the device-state event.** The ESPHome firmware publishes its device state on `req_device_state` (and — newer firmware — when the Nextion text sensor first reports the version). The hub's boot handshake arrives ~1 s after boot, before the display answered, so the snapshot is empty; the update controller must request a fresh `REQ_DEVICE_STATE` at check time and treat an empty value as *unknown*, not `0.0.0`. Treating empty as old re-installed the TFT after every reboot (#63) — see `custom_components/nspanel_haui/haui/controller/update.py` and `esphome/nspanel_haui/sensor.yaml` (`tft_version.on_value` republishes the state).

**Firmware updates belong to the hub's `HAUI Firmware` entity (`update.py`).** The update controller reads the manifest at the device's `update.firmware_manifest_url` (default: the latest GitHub release's `firmware-manifest.json`; a test panel points it at a local release written by `scripts/dev_release.py`) and flashes a newer firmware through the firmware's `install_firmware_url` action (automatically only with `firmware_auto_update`, default `false`; otherwise via **Install** on the entity). The controller has no synchronous network path: every check, release list and install fetches its inputs with `haui/controller/release_source.py` on the adapter's I/O pool (`start_async_*` → `app.submit_off_worker`) and applies the result on the worker; `release_source` also owns the hub-wide GitHub release cache. `esphome/nspanel_haui/base.yaml` keeps `http_request` + `ota: platform: http_request` for that action; the ESPHome side keeps only its stock dashboard update entity, so the firmware declares no `update:` block of its own. The release workflow generates and attaches `firmware-manifest.json` (name/version/builds[].ota with the absolute .bin URL and md5) for `v*` tags only — a dispatch on a branch is refused before it builds, so devices never see a branch name as a version. Ordering matters: a TFT upload in flight blocks the firmware install, and an in-flight firmware install defers the TFT install; the TFT follows after the device reboots into the new firmware. The automatic-install keys (`firmware_auto_update`, `auto_install`, `install_delay`, `max_attempts`, `retry_interval`) belong to each device's `update` block like every other update setting; there is no hub-wide update setting (`docs/develop/update-process.md`, *Settings*). **The ESPHome web server is optional and not part of the shipped build** — `base.yaml` leaves `web_server` out so HTTP OTA has flash/RAM headroom. `esphome/nspanel_haui_dev.yaml` enables it for local development; a device YAML that includes `nspanel_haui.yaml` as a package enables it by adding a top-level `web_server:` block. Home Assistant's "Visit" link only appears when the component runs.

**Dev releases are tagged with their version.** `.github/workflows/dev-firmware.yml` publishes a development build, dispatched manually on `dev`, as a prerelease whose tag *is* the PEP 440 version (`X.Y.(Z+1).dev<run>`, the commit goes in the release name). Never add a `+local` segment such as `+g<sha>`: AwesomeVersion (Home Assistant and its Marketplace) sorts `0.4.5.dev16+g<sha>` above the final `0.4.5` and above `0.4.5.dev17`, so such a build is never offered its successor. The tag points at a `chore(release)` commit on top of the pushed commit that carries that version in `custom_components/nspanel_haui/manifest.json` (+ `esphome/nspanel_haui/version.yaml`) — the Marketplace downloads the tag's source archive, so tagging the branch commit would ship the stable version. The workflow also pushes that commit back onto `dev`; the next build keeps its `X.Y.Z` base and only a stable manifest (after the master merge-back) moves it to `X.Y.(Z+1)`. The same commit carries the regenerated screen overview (`docs/screens.html`, `docs/assets/screens/`); a `screens_only` dispatch regenerates the screens as a docs-only commit, without a version, tag or release. A dispatched build can move `dev` at any time, so release prep never happens on `dev` — cut `release/X.Y.Z` from `dev` and PR it into `master` (`docs/develop/release.md`, "Branches and cadence"). The workflow keeps only the newest 10 dev prereleases (the Marketplace reads 30 releases; more dev builds would hide the latest stable one). The Marketplace takes the release tag as the available version and the installed tag as the installed one and compares them with AwesomeVersion (PEP 440); the old `dev-<run>-<sha>` tags parsed as `UNKNOWN`, so the comparison fell back to string inequality — an installed dev build kept offering itself as an update and the version list had no usable order. Never reintroduce a non-version tag for a dev release, and keep the tag string byte-identical to the manifest version (`+` build metadata included) so the comparison stays same-strategy. There is no fixed dev manifest URL (the old `dev-latest` release is gone): the hub's `dev` update channel takes the `firmware-manifest.json` of the newest release in the GitHub release list, prereleases included.
3. **Re-open the project** (recent list), look at every page, compile (`Compile`, then `File → TFT file output` → `nextion/nspanel_haui_portrait.tft`) and run `python -m scripts.verify_nextion.verify_nextion --require-portrait`. Done means the editor opened the file without "Version mismatch", every page renders as specified, and the gate passes.

Format reference (what the script relies on):

- The `.HMI` is a container: a table of `<16-byte name, start, size>` entries — `N.pa` page blocks, `N.i`/`N.is` pictures, `N.zi` fonts, `main.HMI` (device settings, incl. the display direction byte at offset 12) and `Program.s`.
- A page block is a 56-byte header (`<I` stamp, size, header size, component count, …), a component table (`<III` per component: offset, size, …) and the components. Every attribute is a record `<u32 len><16-byte name><value>`; ints are little-endian, normally 4 bytes. `objname` and `type` (121 = the page itself) identify a component.
- Safe same-length writes: `x`, `y`, `w`, `h` together with the derived `endx = x + w - 1` / `endy = y + h - 1`, `font`, `isbr` (word wrap), `sendkey` (Send Component ID), colours, and the page component's own `w`/`h`.
- Every page block starts with a content **stamp** the editor validates — a stale stamp fails with "Version mismatch" / "Loading Page Failed". It is `CRC-32 (poly 0x04C11DB7, MSB-first, init 0, no final XOR)` over every byte after the stamp widened to a big-endian u32, plus 40 zero bytes, XOR an unknown length-dependent constant. Same-length edits cancel the constant: `new = old ^ crc(old block) ^ crc(new block)` (`block_crc`). Pictures carry no stamp; the container table has a checksum of its own that is not cracked, so block lengths and offsets stay as the editor wrote them.

### Preview renderer workflow

**A panel card is the hub's own render, replayed.** There is no renderer in the
browser. `nspanel_haui/virtual_panel/render` (`web/websocket.py`) runs
`VirtualPanelHost.async_render` (`web/preview/virtual_panel.py`) on the device's one virtual
app — the app the live preview runs on — and returns `{page, before, commands}`:
what the hub sends before switching to the page (the theme colours and its
picture background, which the page's Preinitialize code reads), then the page's
commands. The card replays
them in the device's order (`buildPreviewDisplay` in `frontend/previews/previewer.js`)
in a `NextionDisplay` built from the real layout (`frontend/virtual/layout_<orientation>.json`
+ `icon_map.json`, regenerated by `scripts/hmi_layout/gen_virtual_layout.py`) and
`<nspanel-simulator-frame>` (`frontend/previews/simulator-frame.js`) scales it to
the card. Entity values, translations, templates, dates, colour overrides and
weather forecasts are therefore the hub's, by construction.

- **Isolation.** A render runs the panel's page through its real lifecycle
  (`prepare_page_load`, `start_panel`, `render_panel`, stop; `_PanelRender`) against
  `_RenderApp`, a view of the shared app whose ESPHome controller records
  display output, whose navigation ignores every action, whose notification
  blinker draws on the render's own page and which makes only service calls
  that return data. A card never moves what a live-preview viewer sees and never
  changes state. Delayed output is collected until the page is quiet for 0.3 s.
- **What is rendered.** A user card sends the editor's panel config (unsaved
  edits included); a system card sends its `key`, and the hub renders the
  device's configured panel (system defaults or saved override,
  `async_configured_panel`). A popup opens with the sample context the preview
  code defines (`web/preview/virtual_panel.py`: an example notification, sample
  choices, a panel to unlock; string values are translated) or, as an entity
  popup (`popup_<page>`, by key), for an entity of its `item` option's domain,
  preferring one that is on (`preview_kwargs()`). The panel editor's preview of
  an entity popup instead passes a random entity of the domain as the render's
  `kwargs` (`context.kwargs`, part of the render key; such a render is not kept
  as the card's last render).
- **When it re-renders.** `previewRenderKey(host)` (hub, device, saved device
  settings and panels, and only the device info a page shows: IP and versions)
  changes the frame's `renderKey`; renders are memoised for 30 s per panel and
  key. Never key on live readings (uptime, RSSI): the editor polls the status
  every 5 s, and each change re-renders every card. A failed render shows the
  hub's error on the card.
- **Change the hub, not the preview.** If a card looks wrong, the device does
  too: fix the page. Where browser and device could only disagree through data
  the browser cannot see, make the hub's output unambiguous instead (for
  example `format_number`: `1012.0` and `1012` print alike).

**One app per device.** `VirtualPanelHost` owns the device's `VirtualNSPanelHAUI`:
sandbox previews attach as viewers (a late viewer gets the current panel redrawn and
the idle/entity state it missed) and cards render on it. Its simulated states are
shared by every sandbox viewer. Live mode is not the app's: each live viewer is a
`web.preview.live_panel.LivePanel` of the device's running app. `web.websocket._Hosts` starts
a host on first use, reloads it on every save (`api.config.push_panels` →
`async_reload_hosts`), stops it after `IDLE_STOP_SECONDS` without a viewer or a
render and on entry unload (`async_stop_hosts`).

**No render, no preview.** A card without a render (no device selected yet, the
editor still loading) shows the loading placeholder; there is no sample
snapshot and no second source of preview content. The one exception is the
card's own last render: `previewer.js` keeps every hub render in `localStorage`
(`haui_lastCardRenders`, newest 200 cards, keyed by hub entry, device, display
model, kind and panel key) and a frame with nothing to show replays it
(`lastPanelRender`) until the hub's new render arrives, so a reload does not
wait for the hub to start the device's virtual app. The kept renders carry the
versioned asset path and are dropped when it changes: a render only replays
in the layout it was drawn for.

**Render test.** `tests/test_card_renders.py` renders a panel of every type and
every system panel through `async_render` with the sample world in
`scripts/preview_gallery/sample_world.py`, for a landscape and a portrait device,
and replays the results with Node (`tests/frontend/replay-renders.mjs`). It fails
when a render is empty, its page is missing from the layout, or the replay raises
a simulator warning the bare page load does not — the hub sent something a card
could not draw. `pytest tests/` therefore needs Node 22+ as well.

**Card gallery.** `scripts/preview_gallery/gen_preview_gallery.py` renders the
same sample cards and shows them in `gallery.html`, which replays them in the
editor's own `<nspanel-simulator-frame>` (a stand-in `<ha-icon>` draws the MDI
webfont from `scripts/font_tools/`): `--serve` serves it on localhost, `--png`
writes one PNG per card at the display's resolution through headless Chrome
(`capture.mjs`, DevTools protocol, Node 22+). Output goes to the git-ignored
`scripts/preview_gallery/out/`. `--docs` writes the same PNGs to
`docs/assets/screens/` plus the overview page `docs/screens.html`; the
`Development Firmware` workflow (`dev-firmware.yml`) runs it in every development
build and commits the result to `dev` with the version when it
changed, or on a `screens_only` dispatch. Renders run at a fixed time
(`time-machine`), so the output is byte-identical between runs; don't edit the
generated files by hand.

```bash
python -m scripts.preview_gallery.gen_preview_gallery --serve   # browse every card
python -m scripts.preview_gallery.gen_preview_gallery --png     # out/png/<orientation>/<card>.png
python -m scripts.preview_gallery.gen_preview_gallery --docs    # docs/assets/screens/ + docs/screens.html
```

**To add a preview for a new panel type**, give `PageDescriptor.page_id` the
correct Nextion page id; a popup that needs context gets its sample in the preview
code (`web/preview/virtual_panel.py`). Add a
sample panel (and the entities it shows) to `scripts/preview_gallery/sample_world.py`.

**Verify coverage** — confirms every exposed panel (user, system, popup alias)
resolves to a physical page present in both generated layouts:
```bash
python -m scripts.check_preview_coverage
```
(covered by `tests/test_preview_coverage.py`, run with the rest of the suite.)

`scripts/_ha_stubs.py` installs the `Home Assistant` import stubs that every
generator (`gen_virtual_layout`, `check_preview_coverage`)
relies on; import it before importing `haui` modules.

### Page lifecycle hook ordering

Pages follow a defined lifecycle when panels are shown. The canonical hook ordering is:

1. **`prepare()`** (optional) — Set the page's per-panel attribute defaults. Called during `__init__()` and again by `set_panel()` before every `start_panel()`, so nothing one panel set carries over to the next panel on the same page instance. Use instead of overriding `__init__()`.
2. **`start_panel(panel)`** (required) — Register callbacks, create items, save state.
3. **`config_panel(panel)`** (rare) — Base class: gives the header buttons `start_panel` registered (`set_function_buttons`) without a function their default one, for `header_panel(panel)` (the unlock popup answers with the guarded panel). Typically not overridden; pages never call `_auto_assign_fncs` themselves.
4. **`before_render_panel(panel)`** (optional) — Return `False` to abort rendering.
5. **`render_panel(panel)`** (required for pages that draw content; the base provides a no-op) — Send display commands.
6. **`after_render_panel(panel, rendered)`** (optional) — Post-render actions.
7. **`stop_panel(panel)`** — Base implementation clears state listeners/callbacks and then calls `_stop_panel(panel)`; subclasses normally do their cleanup in `_stop_panel()`.

Key rules:
- Use `prepare()` instead of `__init__()` for setting default attribute values. No need to call `super().prepare()` — the base implementation is a no-op. Every attribute it sets is reset for each panel, so it must not hold a live timer or listener handle (cancel those in `_stop_panel()`) or a counter a late callback compares against (use a fresh `object()` token instead); state that must outlive a panel belongs on the panel (`panel.set_state`).
- A new Live viewer gets the page as the panel shows it, without any page code running: the page's `load_commands` (what `prepare_page_load` sent), then `HAUIESPHomeController.page_commands()` (every command the page was sent since its `goto_page`, the last write per target). So every display command must go through `send_cmd()` / `set_component_*()`; a page needs no redraw hook for the preview.
- Override `_stop_panel(panel)` instead of `stop_panel(panel)` for per-class cleanup. Do NOT call super — the base `stop_panel()` handles listener cleanup automatically, then calls `_stop_panel()`.
- If you override `stop_panel()` itself (rare), call `super().stop_panel(panel)` so listeners are cleared and `_stop_panel()` still runs.
- A page that must hold firmware auto switches off while it is shown overrides `suspended_auto_switches()` with keys of `AUTO_SWITCHES`. Automatic page switching is a hub-side hold keyed by `AUTO_PAGE_HOLD`, not a firmware switch; `HAUIDevice.apply_auto_switches()` owns only the two firmware switches (settings minus the current page's holds), while navigation enforces `AUTO_PAGE_HOLD` in its inactivity check. A page whose firmware-switch hold changes while shown calls `apply_auto_switches()` (the QR page's big code).
- Read panel options in `start_panel()` with `self.option(panel, key)`: it takes the default from the descriptor's `PageOption` (the one the editor shows, inherited options included), so a page holds no second copy of it; `tests/test_page_options.py` refuses `panel.get()` on a declared option. A saved config runs `start_panel()` again on the loaded page instance. Only `page_load_commands(panel)` runs before the page loads, and it returns commands instead of setting state.
- `set_panel()` sends `start_panel()`, `config_panel()` and `render_panel()` as one batch (and `refresh_panel()` batches `render_panel()`), so they need no `with self.rec_cmd:` of their own; callbacks from state listeners, timers and touches do.

Additional notes:
- `start_page` does **not** exist, neither as a config key nor as a hook — navigation uses `home_panel` from device config, and pages use the panel hooks above.
- Entity ids built from the device name use `self.app.device.get_slug()` (Home Assistant's `slugify`, computed once in `NSPanelHAUI`); don't slug the name by hand.
- `BlankPage` intentionally has no `render_panel()` — it is a blank/idle page used for the idle (automatic page switching) session.

### Config flow and editor settings

- `config_flow.py` creates the single hub entry (user step plus zeroconf/DHCP/integration discovery). There is no options flow.
- Device and panel settings are edited in the sidebar editor (`frontend/`), which calls the REST views in `api/`; panel configs are validated there with `validate_panels` (`haui/config_models.py`).
- `hub/storage.py` (`PanelStorage`) persists panel configs to HA's internal store.

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

### Notifications and device states

Notification delivery has three entry points; the HA service is the recommended one because it carries the full option set.

| Entry point | Options | Notes |
|-------------|---------|-------|
| `nspanel_haui.send_notification` service | title, message, icon, icon_color, sound, persistent, force_show, text_size, timeout | Goes straight to the notification controller; the only path with force-show and the auto-dismiss `timeout` |
| `notify.<device>` / `notify.<device>_persistent_notification` | title, message only | The regular entity queues; the persistent entity sets `persistent`, so it opens immediately and loops the sound. Neither accepts an icon colour, sound, force-show or timeout |
| ESPHome `send_notification` action | title, message, icon, persistent, text_size, icon_color, sound — all required (ESPHome 2026.10 has no optional action variables) | No force-show or timeout fields; the hub defaults a missing `icon_color`/`sound` from older firmware |

Key semantics:

- Notifications auto-dismiss **only** when the service's optional `timeout`
  expires (seconds counted from queueing, so a still-queued entry can expire
  unseen). Otherwise an entry stays in the queue until it is
  dismissed on the panel, replaced by an identical title+message, or cleared.
  The notification queue plays through — when the current popup is dismissed
  while more are queued, the next one opens in its place (`notification._advance_queue`).
  A new force-show notification never rips an open notification popup/list away:
  it waits in the queue instead. This is the "notifications are shown only once"
  regression guard — do not pass a `close_timeout` to queued-notification popups.
- There is no severity: the notification `type` was replaced by `icon_color` and `sound`, and the info/warning/critical presets live in a Home Assistant script (`docs/user/services.md`, *Preset notification script*). `add_notification()` normalises `icon_color` `""` to `None` (the theme's `component_text` colour) and `sound` `"none"` to `""` (silent); any other sound must be in `SOUND_NAMES`.
- `persistent=true` forces the popup open on every path (`force_show = force_show or persistent`) and re-opens it every 60 s until it is dismissed or its timeout expires, also over the idle page. With the device setting `sound_on_notification` on, it also loops its sound every `persistent_sound_interval` seconds. A schedule entry with sound off mutes the sound and keeps the display dark (`wake_for_notification()`), but never drops, delays or hides a notification.
- An empty `icon` shows no icon. `icon_color` colours the icon when one is set. The message goes to `tText` beside the icon, or to the full-width `tTextFull` when there is no icon. Text is fitted with the display fonts' real glyph widths (`fit_text` in `haui/utils/text.py`, widths in `haui/mapping/font_metrics.json`, exported by `gen_virtual_layout`): lines wrap so the display never re-wraps them, a page holds the lines the box is tall and at most the widget's `txt_maxl` bytes, and `auto` picks the largest font that fits one page. `_TEXT_BOXES` in `haui/page/notify.py` must match the HMI widgets (a test checks it).
- Long messages are split into static pages in the detail popup and advance only when the manual next-page header button is pressed; the final page stays visible. The queue selection list shows plain titles.
- Sending a notification with the same title and message as one already queued replaces it: it alerts again (sound included, with `sound_on_notification` on) and the queue advances to it when the current popup closes.

Idle page vs. display state (important): the **idle page** is the configured automatic page switch, tracked by `navigation.idle_panel_active`. It is independent of the firmware's display brightness machine: the display can be off without a page switch, and the idle page can be shown while the display is still on.

- `services.py` `wakeup` calls `navigation.exit_idle_to_prev_or_home(config)` (a no-op when no idle session is active) and `idle` calls `navigation.open_idle_panel(True)`. `open_idle_panel()` is a pure page switch — it never turns the display off — and creates the pre-idle snapshot only when an idle session actually starts.
- Navigation and `function_btn_mixin` actions use the same `open_idle_panel()` / `exit_idle_to_prev_or_home()` API; the `idle_panel` / `idle_panel_extra` / `show_idle_button` config keys are the only names.

Canonical docs: `docs/develop/notifications.md` (queue, delivery paths, timers, presentation), `docs/user/services.md` (service fields and notify entities), `docs/user/device.md` (display states, idle page, waking up), `docs/user/panels/popup_notify.md` (popup presentation).

### Testing

Tests stub `homeassistant` modules via `sys.modules` manipulation in `tests/conftest.py` (with per-test overrides in files like `tests/test_config_flow.py`). Tests do **not** require a running HA instance. Use `unittest.mock` for mocking. Follow the pattern of creating minimal stub classes for HA types like `ConfigFlow`.

When modifying `config_flow.py`, check the corresponding tests in `tests/test_config_flow.py`.

Frontend editor modules are tested with Node's built-in runner in `tests/frontend/` (`*.test.mjs`), using the fake editor host and backend in `tests/frontend/fake-host.mjs`. Tests that import a module depending on Lit must import `tests/frontend/dom-shim.mjs` first.

A frontend module is only type-checked when it starts with `// @ts-check` (`npm run typecheck:frontend`, `jsconfig.json`, `checkJs: false`), so an unmarked module compiles unchecked — mark new `store/`, `api/`, `views/` and data-carrying `ui/` modules. There is no JS formatter: keep the file's existing style (see *Code Style*).

### Config merging

Device settings have one home: the panel store.
- `config_entry.data` holds only the hub name, each device's identity (`name`, optional `esphome_device_id`, built by `hub/esphome_helpers.hub_device_entry`) and `removed_devices`.
- `PanelStorage` holds each device's settings, including `enabled`, and its panels.

`__init__.py:_build_config_dict(entry.data, store, device_name=...)` builds one device's runtime config: identity, then store settings, then `DEVICE_CONFIG` defaults. The result goes to `HAUIConfig` for typed access and validation. Setup builds it once per enabled device. A panel or settings save (`api.config.push_panels`) rebuilds it the same way and applies it with `NSPanelHAUI.reload_config`, so a setting removed from the store falls back to its default. Read a device or update setting without a default of its own (`self.get("key")`): `DEVICE_CONFIG` and `DEFAULT_CONFIG["update"]` are the only defaults, filled in by the config build and again by `HAUIDevice` and the update controller for whatever config they are given, so a call-site default could only disagree with them.

**System panels are identified by key, never by type.** Only the popups can be edited: `haui/mapping/panel.py` maps the fixed system panels (System, Blank, Settings, About) in `SYS_PANEL_MAPPING` (keys: `SysPanelKey`) and the popups (every `popup_*` key, notify/select/unlock included) in `POPUP_PANEL_MAPPING` (keys: `PopupPanelKey`); code that needs every system panel uses `SYS_PANEL_MAPPING | POPUP_PANEL_MAPPING`, and the editor reads the system entry's `editable`. A user panel saved under a popup key (`popup_cover`, `popup_notify`, …) replaces that popup; an edited entity popup is stored with the user type (`popup_cover` → `cover`), and `popup_notify`/`popup_select` have the types `notify`/`select`. System, Blank, Settings and About are fixed: `validate_panels` refuses a panel under their key, `PanelStorage.load` drops a stored one (`drop_fixed_sys_overrides`) and `HAUIConfig._merge_sys_overrides` raises on one. `_merge_sys_overrides` lays the override over the system defaults, keeps it out of navigation and strips `unlock_code`/`close_timeout` from `HUB_DRIVEN_PANELS` (`haui/mapping/const.py`; the editor hides those fields via the system entry's `hub_driven`).

### Locale/translations

The project uses hardcoded CLDR locale data (see `haui/utils/locale_data.py`) instead of depending on Babel. Date formatting uses inline locale data in `haui/utils/datetime.py`. Display text translations use lookup tables in `haui/utils/text.py`, backed by JSON files in `haui/locale/*.json` (component + text sections).

**Translation extraction workflow:**

1. After adding, removing, or changing any `t()` / `host._t()` (frontend JS), `self.translate()` (Python), or `_()` (descriptor) call, run:

   ```bash
   python -m scripts.translations.extract_translations
   ```

   This scans `custom_components/nspanel_haui/` (Python) and `frontend/` (JS) for string-literal calls, then syncs `haui/locale/*.json`: adds new keys (English text as the value in `en.json`, empty string in other languages), removes keys no longer referenced anywhere, and prints an added/removed count per language file.
2. Fill in the empty values the run added to non-`en` locale files (or hand the new `en.json` keys to a translator).
3. Commit the updated `haui/locale/*.json` files together with the code change that introduced the strings.

`scripts/translations/merge_translations.py` is a secondary helper for merging a completed `scripts/translations/translate.json` batch back into `haui/locale/*.json` without clobbering existing entries — for external translation-service round trips, not needed for routine local development.

## Frontend Rules

The sidebar editor (`custom_components/nspanel_haui/frontend/`) is one static custom panel: no build step, no framework beyond the vendored Lit, no runtime dependency, and Home Assistant's own theme. `docs/develop/frontend.md` holds the architecture, the screens and the component inventory — read it before a UI change. The rules below are what a change must not break; they mirror how the shipped code already reads.

### Where code goes

| Directory | Owns | Rule |
|-----------|------|------|
| `app/` | `shell.js` (the element and its lifecycle), `router.js` | Wires collaborators; no data fetching, no formatting |
| `store/` | `store.js` (one observable store), `controller.js` (Lit reactive controller) | Only store actions write shared state; one poller per scope |
| `api/` | `client.js` (one namespaced client), `types.js` (`@typedef`s) | REST/WebSocket transport only; no rendering, no state |
| `views/` | One render entry per screen region (`renderFleetView`, `renderDeviceView`, `renderPanelList`, `panelCatalog`, `notificationsView`) | Prepared data in, callbacks out; no transport, no store |
| `ui/` | Reusable template components — the visual inventory in `docs/develop/frontend.md` | Data in, callbacks out; no transport, no store |
| `dialogs/`, `previews/`, `virtual/`, the element-based views (`workspace.js`, `device-settings.js`, `panel-editor.js`) | Dialog surfaces, the hub-render replay, the Nextion simulator, surfaces that have not migrated to a render function | Use the client, never raw `fetch` |
| `styles/` | Shared `css` fragments composed by `styles.js` or adopted by their owning custom element | One module per surface; shared rules, not per-call-site one-offs |

**A view or a component never reaches into the shell, the store or the API.** It gets prepared data and `on*` callbacks; the shell maps those to store actions. `ui/` and `views/` import nothing from `store/` or `api/` today — keep it that way, and add new shared state as a store field plus an action before wiring any component to it.

**Every displayed value has a real source** — the store, a status poll, a hub render or an API response. Never show a fabricated fact the prototype invented (availability percentages, spark bars, per-device activity, a "mostly healthy" line, placeholder counts, made-up update or node fields); when the data is missing, show the explicit empty or unknown state. The hash route is the single source of truth for the screen: user navigation pushes history, normalizing an invalid route replaces it, and unsaved drafts stay out of the URL.

**Custom elements are the exception, not the pattern.** Pure render functions are the default; define an element only for the editor shell, a dialog surface, the preview workspace, the panel editor, device settings or the simulator frame. Element names are `nspanel-*` (`tests/frontend/element-names.test.mjs` enforces the namespace), file names are kebab-case, one element per file.

### Writing a component (`ui/`)

- One exported function, camelCase, taking a single options object: `export function deviceRow({ name, device, status, onOpen, onMenu })`. Small primitives may take a positional `(text, tone, className)`.
- Callbacks are `on<Thing>`, optional and invoked as `onThing?.(value)`: `onSelect`, `onClose`, `onDismiss`, `onClick`, `onReorderDevices`. Never mutate the argument object; compute and return.
- Return an `html` template (from `lit-import.js`) or a pure helper value. Use `nothing` — not `''` — for "no attribute, no element".
- Compose from the primitives instead of re-declaring markup: `button`/`iconButton`/`addButton`/`backButton`/`expandToggle`, `badge`/`countBadge`/`statusDot`, `surface`/`sectionHeading`, `segmented`, `sortHandle`, `emptyState`, `popover`/`menuItem`/`menuSeparator`, `icon`, `infoTile`, `sidebarFrame`/`modalSidebar`, `previewStage`. A missing variant is added to the primitive (with its test), not forked in the view.
- Icons: `icon('name')` maps the short names in `ui/icon.js` to `mdi:*`. Add the short name to that table instead of inlining `mdi:` strings.
- Class names are `haui-*`, block-then-part (`haui-panel-row`, `haui-panel-row-actions`); state classes are `is-*` (`is-dragging`, `is-drop-target`, `is-resizing`) or an existing modifier (`active`, `open`).
- Every new `store/`, `api/` and `views/` module and every `ui/` module that carries real data starts with `// @ts-check` and JSDoc `@typedef`s. The type check only covers files that opt in, so an unmarked module is unchecked.
- A new primitive needs a semantic assertion in `tests/frontend/ui-primitives.test.mjs` (use the real-DOM helpers in `tests/frontend/support/`) and keeps a demo in `tests/frontend/ui-primitives-preview.js` for manual review.

### Text, states and accessibility

- Every user-facing string goes through `t('literal')`; the extractor only finds string literals. Interpolate with `t('Install updates ({count})').replace('{count}', String(count))` — never a template literal, never concatenation.
- No hardcoded English label, `title`, `aria-label`, toast or error text. Numbers, IPs, versions and entity ids are data, not text.
- A control is a native `<button>` with a label. An icon-only control uses `iconButton({ label })` so the accessible name sits on the button, not the glyph; decorative icons keep the `icon()` `aria-hidden` default.
- Colour is never the only cue: attach text to a tone (`badge`) and give a `statusDot` its label. Transient failures are announced with `role="alert"`, not with a colour change.
- Keep the keyboard path intact: `aria-expanded`/`aria-controls` on popover triggers, `aria-pressed` on segmented options, `trapTab` inside modal sidebars, focus restored to the trigger after close. Use native buttons, links, inputs and `<details>/<summary>` where they fit, and make a hover preview keyboard reachable too.
- Empty, loading, stale and error are first-class states: `emptyState` when there is nothing to show, `?disabled=${…}` described by a title/label when an action is unavailable, explicit "unknown"/"not reported" text instead of a false value.

### Styling

The source of truth is `docs/develop/frontend.md` → *Visual foundations*: measured values from the prototype, not a second theme. Use what already exists before adding a value.

- **Theme, not a palette.** Every colour is a Home Assistant variable with a fallback (`var(--primary-color, #03a9f4)`, `var(--card-background-color, #fff)`, `var(--divider-color, …)`, `var(--state-icon-color, …)`). HAUI-owned meanings (status tones, surfaces, focus, shadows, screen/bezel, hardware LEDs, Wi-Fi good, live preview and card shapes) are aliased only in `styles/tokens.js`; use those aliases instead of declaring `--haui-*` elsewhere.
- **No raw colour** in style rules except on-fill white/black (`#fff`/`#000` and `#0003` shadows), the documented `--haui-wifi-good` green, and literals that define the central screen/bezel/device tokens in `styles/tokens.js`. No copied colour ramps or `prefers-color-scheme` overrides.
- **Type.** Use the 10/12/13/14/16/20/24px ladder with weights 400/500/600. Reuse `--haui-text-eyebrow`, `--haui-text-caption`, `--haui-text-label`, `--haui-text-body`, `--haui-text-title`, `--haui-text-display`, `.haui-eyebrow` or the matching typography utility in `styles.js`. Identifiers — node names, panel keys, IPs, firmware and TFT versions — use `.haui-text-mono` / `var(--haui-mono)`.
- **Spacing** uses 4/8/12/16/20/24/28/32/40px (`--haui-space-*`); **radius** uses `--haui-radius-control` (8px), `--haui-card-radius` (12px), `--haui-radius-pill` or `--haui-radius-round`. **Elevation** uses `--haui-shadow-card` for cards and `--haui-shadow-overlay` for overlays.
- **Icons** are Home Assistant `<ha-icon>` (MDI names through `icon()`), sized with `--mdc-icon-size`: 18px default, 14–16px compact. Never build an SVG `<use>` sprite; it cannot cross shadow roots.
- **Motion** is short and purposeful: 120–150ms for hover/colour/fade, with the scrim/sidebar entrance at its defined 140/180ms. Every animation and transition pairs with a `prefers-reduced-motion` rule.
- **Focus** uses the shared visible `--haui-focus-ring` and `--haui-focus-offset`; never suppress a focus ring, and never rely on hover alone: wrap hover-only affordances in `@media (hover: hover)` and give them a keyboard path.
- **Responsive root** is the `:host` container (`editorContainerStyles` in `styles.js`, `container-name: haui-editor`) because a descendant container query cannot reach outside the shadow tree. Query it as `@container haui-editor (max-width: …)` on the ladder 1120 / 980 / 870 / 720 / 600 / 560px. A card that must react to its own width declares its own named container (`.haui-panel-info { container: haui-panel-info / inline-size; }`) and queries that name. `@media` is for user preference and the legacy full-screen phone rules.
- **Layout lives in `styles/`.** Inline `style=` is only for a computed custom property or a value the stylesheet cannot know (sidebar width, preview scale, a palette swatch preview) — never for spacing or positioning that belongs in a fragment.
- **Compose fragments in `styles.js`**: shared fragments feed `dialogStyles`, which feeds `editorStyles`; `styles/content.js` is a fragment, not another aggregator. Component-local styles should only own layout unique to that element. The stdlib guard `scripts/check_frontend_styles.py` and `tests/test_frontend_styles.py` verify the scale, raw colors, token ownership, selector uniqueness, fragment adoption and reduced-motion overrides.
- **Two wrappers are fixed by the docs, not by a view.** A sidebar opens at 380px, resizes between 320px and the window minus 120px, shares one width persisted as `haui_sidebarWidth`, and becomes a full-screen page at ≤600px (`ui/sidebar.js`). The editor footer stays after the screen content on every state — loading, error and empty included — and keeps `renderFooter()` and its `.editor-footer` markup verbatim (`toolbar.js`); its version, Dev badge, GitHub and Documentation links are not moved into a menu. Do not re-implement either.

### Overlays

- One anchored popover implementation: `ui/popover.js`. A trigger carries `data-overlay-anchor=${overlayAnchor(kind, subject)}`; the shell places it, closes it on Escape/outside click and restores focus. Do not write a second positioned popover.
- Sidebars use `modalSidebar`/`sidebarFrame` (`ui/sidebar.js`), which own width, scroll containment, Tab trapping and focus, and become a full-screen page at ≤600px.
- Only one anchored popover is open at a time; a modal sidebar may carry one topmost popover. Escape closes the topmost layer first, then the sidebar, and returns from Device to Fleet only when no overlay is open. An outside click closes only the active popover. Closing restores focus to the trigger, and focus survives renders and saves.
- Legacy dialogs build on `dialogs/haui-dialog.js` (`HauiDialog`: `hass`/`open` properties, `open`-gated rendering, `dialog-closed` events) and render HA's `ha-dialog`. Do not start a new dialog surface without both.
- Overlay kinds are declared in `store/store.js` (`ANCHORED_OVERLAY_KINDS`, `SIDEBAR_OVERLAY_KINDS`, `DEVICE_OPTION_OVERLAY_KINDS`); a new overlay adds its kind there and opens through a store action, so one overlay replaces the previous instead of stacking by accident.

### Home Assistant integration

- Every REST and WebSocket call goes through `api/client.js` (`api.entries`, `api.panels`, `api.devices`, `api.status`, `api.notifications`, `api.updates`, `api.editor`, `api.preview`, `api.ha`, `api.yaml`). No `hass.fetchWithAuth`, `callWS`, `subscribeMessage` or `fetch` outside `api/`; the simulator sessions in `virtual/` are the one exception, as they own their subscriptions.
- The shell owns `hass` and passes it down; the client takes a `getHass` callback so it never holds a stale object.
- HA elements the editor renders but does not own (`ha-dialog`, `ha-dialog-footer`, `ha-card`, `ha-alert`) are listed in `ha-elements.js`, and the shell waits for them before rendering. Add any new HA element to that list.
- Defaults duplicated from Python (`frontend/constants.js`: `DEVICE_CONFIG_DEFAULTS`, `LOCALE_OPTIONS`, `LOG_LEVEL_OPTIONS`, `DISPLAY_MODEL_OPTIONS`, `GESTURE_NAMES`, `GESTURE_ACTIONS`, `DEFAULT_FIRMWARE_MANIFEST_URL`, `FIRMWARE_UPDATE_CHANNELS`) carry a *Mirrors … in Python* comment naming the source (`haui/device_config.py`, …). Change both sides in the same commit.

### Preview and card renders

A card and a thumbnail are the hub's own render replayed (see *Preview renderer workflow*): the browser has no renderer and must not gain one. Do not add a second preview path, synthesise display output in JS, or key a render on live readings (uptime, RSSI). The preview context is explicit — `{ entryId, device, deviceConfig, panels, theme, deviceInfo, api }` — and `previews/previewer.js`/`previews/simulator-frame.js` depend on that object, not on the editor element. If a card looks wrong, the device does too: fix the page.

### Verifying a frontend change

```bash
npm ci                                  # once per clone; includes happy-dom for real-DOM tests
npm run typecheck:frontend              # modules marked // @ts-check
node --test 'tests/frontend/*.test.mjs' # Node 22+
pytest tests/                           # the card-render replay runs here too
```

Tests live in `tests/frontend/`. Import `support/browser.mjs` before browser-dependent modules, render through `support/render.mjs`, and query the resulting DOM with `support/queries.mjs`; `support/hass.mjs` and `fake-host.mjs` provide backend fixtures. See `docs/develop/frontend.md` → *Testing* for the decision table and assertion boundaries: test behavior and semantics, not presentation, copy, template internals, or private fields. New primitives need a semantic assertion in `ui-primitives.test.mjs` and a demo in `ui-primitives-preview.js`.

## SOLID Principles

This codebase follows SOLID principles. Preserve these patterns when adding or modifying code.

### Single Responsibility Principle (SRP)

Each class owns exactly one concern. Do not add unrelated responsibilities.

| Class | Responsibility | File |
|-------|---------------|------|
| `NSPanelHAUI` | Top-level composition: wires controllers, device, and config together | `hub/app.py` |
| `HAAdapter` | Bridges HA's async API → synchronous interface for haui/ core | `hub/adapter.py` |
| `ESPHomeProxy` | Sends commands to ESP32 via Native API, listens for device events | `hub/adapter.py` |
| `ItemProxy` | Synchronous wrapper around a single HA entity's state/attributes/services | `hub/adapter.py` |
| `HAUIBase` | Config access, command batching, display transport, logging, lifecycle | `haui/abstract/haui_base.py` |
| `HAUIConfig` | Merges config layers, instantiates/validates `HAUIPanel` objects | `haui/abstract/haui_config.py` |
| `HAUIPanel` | Wraps one panel's config: title, type, button visibility, navigation state | `haui/abstract/haui_panel.py` |
| `HAUIEntity` | Synchronous entity access: state, attributes, service calls, display-value helpers | `haui/abstract/haui_entity.py` |
| `HAUIItem` | Wraps one item (entity or internal action) within a panel | `haui/abstract/haui_item.py` |
| `HAUIEvent` | Event value parsing (int/str/json accessors) | `haui/abstract/haui_event.py` |
| `DisplayInterface` | High-level display commands (`send_cmd`, `send_cmds`, `set_component_text`, `set_component_value`) | `haui/abstract/display_interface.py` |
| `ESPHomeTransport` | Low-level wiring: pushes commands to the ESPHome controller | `haui/abstract/display_interface.py` |
| `ComponentRegistry` | Declares and merges Nextion widget descriptors for a page | `haui/abstract/component.py` |
| Controllers | One concern per controller: connection, navigation, ESPHome, gesture, notification, update | `haui/controller/` |

**Pattern:** `NSPanelHAUI` is a composition hub — it creates controllers and delegates, it does not implement business logic. Keep it that way.

**Anti-pattern:** Adding display logic, entity access, or HA API calls directly to a controller or `NSPanelHAUI`. Delegate to the appropriate abstract class instead.

### Open/Closed Principle (OCP)

Classes are **open for extension, closed for modification**. The panel type system is the textbook example.

**Adding a new panel type** (open for extension):
1. Create a page class in `haui/page/yourpage.py` with a `DESCRIPTOR` (type `PageDescriptor`) and `COMPONENTS` (type `ComponentRegistry`)
2. Import it in `haui/mapping/panel.py` and add it to the `_page_classes` list
3. The `_build_panel_mapping()` function automatically registers it in `PANEL_MAPPING` by reading `DESCRIPTOR.type_key`
4. Popup aliases are derived from descriptor metadata — no manual registration needed

```python
# mapping/panel.py — closed for modification of registration logic
_page_classes: list[type] = [
    AboutPage,
    AlarmPage,
    ...,
    WeatherPage,  # ← add new class here
]


def _build_panel_mapping() -> dict[str, tuple[str, type]]:
    mapping = {}
    for cls in _page_classes:  # open for new entries
        d = getattr(cls, "DESCRIPTOR", None)
        if d is not None:
            mapping[d.type_key] = (d.page_name, cls)
    return mapping
```

**Extending components** on a page subclass:
```python
class MyPage(HAUIPage):
    COMPONENTS = HAUIPage.COMPONENTS.merge(  # extend, don't redefine
        title=Component(2, "tTitle"),
        my_slider=Component(7, "hSlider"),
    )
```

**Lifecycle hooks** use the Template Method pattern — subclasses override specific methods without changing the base's orchestration:
- `render_panel` → `before_render_panel` / `after_render_panel`
- `start_panel` → `_stop_panel` for cleanup
- `start` / `stop` → `start_part` / `stop_part`

**Anti-pattern:** Modifying `_build_panel_mapping()` or `PANEL_MAPPING` directly for each new panel type. Adding logic to base classes when a subclass override suffices.

### Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types. All page classes implement the same lifecycle protocol:

```python
# Navigation controller treats any page identically
page.render_panel(panel)  # works for GridPage, ClimatePage, LightPage, etc.
page.start_panel(panel)
page.stop_panel(panel)
```

**Rules:**
- Implement the lifecycle hooks (`prepare()`, `start_panel()`, `render_panel()`, `stop_panel()`) with the same semantics
- `BlankPage` is a **documented intentional exception** — it has no `render_panel()` and is used only for the idle page
- Controllers are iterated polymorphically in `NSPanelHAUI.start()` / `stop()` — each must implement `start()` and `stop()` from `HAUIBase`

**Anti-pattern:** Breaking the lifecycle contract in a subclass (e.g., returning unexpected types from `render_panel()`, or not calling `super().stop_panel()` in cleanup).

### Interface Segregation Principle (ISP)

Many specific interfaces are better than one general interface. The codebase uses three patterns:

**1. Mixins for page behavior:**
```python
class HAUIPage(TouchInputMixin, FunctionButtonMixin, ComponentMixin, HAUIBase): ...
```
Each mixin depends only on a small set of expected attributes, not the full `HAUIPage` surface. The `if TYPE_CHECKING:` block in each mixin declares only what it needs:

```python
class ComponentMixin:
    if TYPE_CHECKING:
        app: NSPanelHAUI
        _callbacks: list[tuple[Component, Callable]]

        def send_cmd(self, cmd: str) -> None: ...
        def log(self, msg: str, **kwargs: Any) -> None: ...
        def render_template(self, template: str, parse_icons: bool = True) -> str: ...
```

**2. Single-method Protocols:**
```python
@runtime_checkable
class DisplayTransport(Protocol):
    def send(self, command: str, value: str | list[str]) -> None: ...
```

**3. Minimal data classes:**
- `HAUIEvent` — 3 small accessor methods (int/str/json)
- `Component` — NamedTuple with `.id` and `.name`
- `ComponentRegistry` — widget declaration + `.merge()` only

**Pattern:** When a class needs behavior from multiple domains, prefer multiple targeted mixins over one fat base class. When defining a dependency, prefer a Protocol with the minimum methods needed.

**Anti-pattern:** Adding methods to a mixin that require new attributes from the host class without declaring them in `TYPE_CHECKING`. Creating a single "god" interface that every component must implement.

### Dependency Inversion Principle (DIP)

High-level code should depend on abstractions, not concretions. The codebase enforces this at three layers:

**Layer 1: `haui/` core depends on `HAAdapter`, not on HA directly**

All `haui/` classes receive a reference via `self.app` and use only the synchronous interface defined by `HAAdapter`. The `haui/` package has **zero direct imports from `homeassistant`** — zero `asyncio` usage, zero HA API calls. All HA bridging happens in `HAAdapter` / `ESPHomeProxy`:

```python
# haui_entity.py — never touches HA async API directly
class HAUIEntity:
    def get_entity(self) -> Any:
        if self.has_entity():
            return self._app.get_item(self._entity_id)  # synchronous bridge method
        return None
```

**Layer 2: Display pipeline depends on a Protocol**

```python
@dataclass
class DisplayInterface:
    transport: DisplayTransport  # ← Protocol, not ESPHomeTransport

    def send_cmd(self, cmd: str) -> None:
        self.transport.send(ESPCommand.SEND_COMMAND, cmd)
```

Page code calls `self.send_cmd()` / `self.set_component_text()` which delegates through `HAUIBase` → `DisplayInterface` → `DisplayTransport` Protocol. Neither `HAUIBase` nor pages know about `ESPHomeTransport` or the ESPHome controller.

**Layer 3: Controllers are wired by composition, not by inheritance**

```python
# NSPanelHAUI — composition hub
self.controller["esphome"] = HAUIESPHomeController(self, ...)
self.controller["navigation"] = HAUINavigationController(self, ...)
```

**Rules:**
- All HA calls go through `self.app.*` bridge methods on `HAAdapter`
- Display commands go through `self.send_cmd()` / `self.set_component_text()` / `self.set_component_value()` — never through the ESPHome controller directly
- No `asyncio` usage in `haui/` core
- When depending on a collaborator, depend on a Protocol or abstract class, not a concrete implementation

**Anti-pattern:** Importing `homeassistant` modules in `haui/` package code. Calling `asyncio.run_coroutine_threadsafe` outside `HAAdapter`/`ESPHomeProxy`. Passing concrete transport classes where a Protocol would work.

## Code Style

- **Line length:** 100 characters (configured in `pyproject.toml`)
- **Python version:** 3.14+ (`requires-python = ">=3.14"`; ruff targets `py314`). Most modules start with `from __future__ import annotations`; keep that convention in new modules.
- **Imports:** sorted with `ruff` (`I` rule); standard library, third-party, then local imports.
- **Type annotations:** use `TYPE_CHECKING` for circular import avoidance; prefer concrete types
- **Naming:** `NSPanelHAUI` for the top-level app class, `HAUI` prefix for abstract/core classes; page classes use `SuffixPage` naming (e.g., `GridPage`, `ClimatePage`)
- **Docstrings:** Google-style docstrings with `Args:`/`Returns:` sections
- **Logging:** use `_LOGGER = logging.getLogger(__name__)` at module level; use `self.log()` and `self.debug_log()` in `HAUIBase` subclasses
- **JavaScript:** there is no JS formatter or linter — match the surrounding file: 2-space indent, single quotes, semicolons, trailing commas in multi-line object literals and argument lists, `const`/`let` (never `var`), and `import … from '…'` with the `.js` extension. Lit templates and JSDoc `@typedef`s instead of TypeScript. See *Frontend rules*.

## Anti-patterns

- **Don't call HA APIs directly from `haui/` code** - always go through `self.app` (the `NSPanelHAUI`/`HAAdapter` instance). The adapter bridges async HA calls to the synchronous thread the haui core runs on.
- **Don't call the ESPHome controller directly for display commands** - use `self.send_cmd()`, `self.set_component_text()`, or `self.set_component_value()` which go through `DisplayInterface`.
- **Don't add `asyncio` code in `haui/` core** - the core runs synchronously on the app's worker thread. All async bridging happens in `HAAdapter`.
- **Don't wait for an app's worker from code that the worker itself may be blocked on** - e.g. a service or notify handler that app code can call with `blocking=True`. Queue such work with `app.dispatch()` instead, or the worker deadlocks.
- **Don't modify `ref_src/`** - `ref_src/home-assistant/core/`, `ref_src/home-assistant/frontend/`, `ref_src/esphome/esphome/`, and `ref_src/custom_components/` are read-only reference checkouts (and `ref_src/` is git-ignored). Use them only for discovering HA / ESPHome API signatures and studying integration patterns.
- **Don't add comments that restate the code** - comments should explain _why_, not _what_. If a comment would only repeat the next line, delete it; if it explains a non-obvious constraint or trade-off, keep it.
- **Prefer exception over silent swallow** - raise an exception instead of catching and ignoring errors. A crash or exception is easier to debug than a silently wrong behavior.
- **Avoid fallbacks** - prefer not use fallback values or defaults. They mask bugs and produce wrong behavior silently. Only use a fallback when the call site explicitly chooses to handle the failure gracefully, and even then, log at warning level.
- **Don't pass non-literal expressions to `t()` or `host._t()`** - translation extraction tools parse source code for `t('literal string')`. If `t()` receives a variable, template literal, or conditional expression instead of a string literal, the string will never be found by extraction and won't be translated. For dynamic values, use the `.replace('{placeholder}', value)` pattern: `t('Hello {name}').replace('{name}', userName)`.
- **Don't hardcode user-facing strings** - any string visible in the UI must go through `t()` (from `localize.js`) or `host._t()`. This includes `title` attributes on buttons, toast messages, status messages, and Error fallback strings.
- **Don't put Python files in `frontend/`** - that directory is served as unauthenticated static files; keep only browser assets there. Python modules that register or serve the frontend live outside it (see `web/editor.py`).
- **Don't build DOM by hand in the editor** - no `innerHTML`, `insertAdjacentHTML` or manual element creation for rendered content; return `html` templates from `ui/`/`views/` so Lit owns the DOM (the simulator's own display code in `frontend/virtual/` is the only place that renders display output).
- **Don't fetch outside `api/`** - no `fetch`, `hass.fetchWithAuth`, `callWS` or `subscribeMessage` in views, components, dialogs or the shell; add a method to the namespaced client.
- **Don't add a second copy of a shared UI idea** - no new popover, sidebar, dialog frame, button, chip or card style, and no new renderer for a panel preview. Extend the existing primitive in `ui/` (and its test) instead of forking it in one view.
- **Don't style layout with viewport media queries or inline styles** - use the `@container haui-editor` ladder and the `styles/` fragments; `style=` is only for a computed CSS custom property or a value the stylesheet cannot know.
- **Don't introduce a build step, bundler, framework or runtime dependency into `frontend/`** - no `node_modules` import, no CDN URL, no second Lit copy; the panel must load from a plain folder copy with no network access.

## Commit and Pull Request Guidelines

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): message`

PR titles must follow the same format: begin with a lowercase type such as
`feat`, `fix`, or `docs`, then an optional `(scope)` and a colon. Keep the
entire title to **100 characters or fewer**, including the type and scope.
For example, use `feat(editor): live preview of the panel`, not
`Live preview of the panel` or `feat/editor-live-preview`.

Common types seen in this repo: `fix`, `feat`, `refactor`, `docs`, `test`, `style`, `chore`.

Scopes seen in history include `haui`, `pages`, `frontend`, `esphome`, `device-management`, `mkdocs`, `install-flow`, `nextion`, `icons`, `panels`, `services`, and `release`. Recent commits are mixed — use Conventional Commits for new work.

Example: `fix(esphome): include device name in discovery fallback`

### Before committing

1. **Keep docs in sync** — after any code change, check the `docs/` directory for files related to what you changed and update them to reflect the new behavior, options, schemas, or defaults. Outdated docs are bugs.
2. **Verify docs build** — after updating docs, install `requirements-docs.txt` and run `zensical build --strict` from the project root to catch broken links, missing files, or rendering errors. The build must succeed (CI runs the same command).
3. Run `pytest tests/` — all tests must pass.
4. Run `npm ci` once per clone, then `node --test 'tests/frontend/*.test.mjs'` and `npm run typecheck:frontend` when touching `frontend/` — all tests must pass and marked modules must type-check. If a test needs editing only because markup or copy moved, remove the presentation assertion instead of changing it.
5. Run `ruff format` on changed Python files, then `ruff format --check custom_components/ scripts/ tests/` — all Python files must be formatted.
6. Run `ruff check custom_components/ scripts/` — no lint errors.
7. Run `mypy` — no type errors in `haui/`.
8. If you changed config flow logic, ensure `tests/test_config_flow.py` covers the change.
9. If your changes affect documented behavior (new options, changed defaults, new panel type features, etc.), update the corresponding docs in `docs/` to match.
10. Breaking changes must be documented in `docs/user/update.md` and the CHANGELOG's "Breaking changes" section.
11. Write each `CHANGELOG.md` entry as one line (what changed, plus its issue/PR link); the full description goes into the release notes, `.github/release-notes/<tag>.md` (`docs/develop/release.md`, step 5).

### Branches and pull requests

`master` is release-only — never commit to it directly. It takes `release/X.Y.Z`
branches cut from `dev` (and hotfixes) only; Pages deploys from it and Marketplace users
install from its releases. A ruleset blocks direct pushes, force-pushes and
deletion there, so a release has to go through a PR with green CI. Squash-merge
release PRs (`gh pr merge <n> --squash`) with a clean body (`--body
"Release prep for X.Y.Z"` or `--body ""`): `master` gains one commit per
release, named after the PR title, and the tag points at that commit. The
default squash body lists the PR's commits, and the dev-firmware bot commits up
to `0.5.0.dev62` carry a `[skip ci]` trailer; GitHub scans the tagged commit's
whole message, so a `[skip ci]` there makes it skip the `v*` tag push and
`release.yml` never starts (`gh workflow run release.yml --ref vX.Y.Z`
recovers). The scan covers prose too: never quote the literal marker in a
commit message. Never open that PR from `dev` itself: a dispatched build can
move `dev` under it (see "Dev releases are tagged with their version" above).
`dev` is the integration branch and the target for all day-to-day work;
`master` is the repository's default branch, so new PRs default to it — open
day-to-day PRs with `--base dev`. The full cycle lives in
`docs/develop/release.md` ("Branches and cadence").

- Branch features off `dev` and open the PR against `dev`
- Release prep happens on `release/X.Y.Z` cut from `dev`; PR it into `master`
- Hotfixes branch off `master`; after the release, merge `master` back into `dev`
- Fill in `.github/pull_request_template.md`: what changed, why, how it was tested (commands run, and any device check still unverified), plus its checklist
- Include a screenshot or short recording for frontend/display changes
- Reference related issues or PRs
- PRs must pass all CI jobs (`tests (3.14)`, `frontend`, `esphome`, `docs`, `hassfest`, `hacs`) before merge; run the local checks above first
