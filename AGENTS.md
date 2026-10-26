You are an experienced, pragmatic software engineering AI agent. Do not over-engineer a solution when a simple one is possible. Keep edits minimal. Ask for permission before making an exception to any rule.

## Project Overview

**NSPanel HAUI** (HomeAssistant UI) is a Home Assistant custom integration that replaces the stock Sonoff NSPanel firmware with a flexible, configurable display system built on ESPHome.

- **Language:** Python 3.14+ (integration; `requires-python = ">=3.14"` in `pyproject.toml`, the Python Home Assistant 2026.5 requires; CI runs 3.14), JavaScript (HA Lovelace editor frontend)
- **Hardware:** Sonoff NSPanel (ESP32 + Nextion touchscreen display)
- **Home Assistant:** minimum `2026.5` (`hacs.json`); integration type `hub`, IoT class `local_push`
- **Runtime dependencies:** `pydantic>=2.0`, `python-dateutil>=2.8.0` (declared in `manifest.json`); `requests` and `packaging` are also imported by the update controller; both ship with Home Assistant core, so they are not listed in `manifest.json`
- **Linting:** ruff (`E`, `F`, `W`, `I`, `UP`, `B` rulesets; line length 100; target `py314`)
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

The **Hub app** (`NSPanelHAUI` in `nspanel_haui.py`) is the brain - it reads HA entity states, renders display commands, and publishes them via the ESPHome native API. The ESP32 relays commands to the Nextion display over serial and reports touch events back.

Inside the Hub app, components follow a layered structure:

- **`HAAdapter`** (`ha_adapter.py`) - bridges HA's async API to the synchronous interface expected by `haui/` core code. All HA calls go through `asyncio.run_coroutine_threadsafe`. Every call from HA into an app (device events, state changes, timers, reloads, services, notify) runs on that app's single worker thread, in order: use `app.dispatch()` (fire-and-forget, from the event loop) or `await app.async_run_on_worker()`, never `hass.async_add_executor_job` with app code.
- **`HAUIBase`** (`haui/abstract/haui_base.py`) - base class for all runtime objects. Provides config access, logging, command batching (`rec_cmd` context manager), and ESPHome send helpers. `HAUIConfigAccess` (`haui/abstract/haui_config_access.py`) is its lighter sibling for data/config wrappers that need no display transport or lifecycle.
- **Controllers** (`haui/controller/`) - ESPHome, connection, navigation, notification, update, gesture. Each is a `HAUIBase` subclass.
- **Pages** (`haui/page/`) - one class per display page type (grid, light, climate, weather, etc.). Each page has a `DESCRIPTOR` class attribute of type `PageDescriptor` (`haui/mapping/descriptor.py`) and a `COMPONENTS` registry of Nextion widgets.
- **Panels** (`haui/abstract/haui_panel.py`) - runtime configuration wrappers for individual panel configs (user-defined panels stored in HA's panel store).
- **Mappings** (`haui/mapping/`) - static registries: `PAGE_MAPPING` (numeric Nextion page ID → page name), `PANEL_MAPPING` (panel type key → `(page_name, page_class)`), `SYS_PANEL_MAPPING`, colors, icons, constants.
- **Frontend** (`frontend/`) - vanilla JS modules loaded as a Home Assistant Lovelace editor for configuring panels through the HA UI.

## Reference

### Important files

| File | Purpose |
|------|---------|
| `custom_components/nspanel_haui/__init__.py` | HA integration entry point: `async_setup_entry`, config building, panel storage loading |
| `custom_components/nspanel_haui/nspanel_haui.py` | `NSPanelHAUI` class - initializes device config, controllers, panel and page instances |
| `custom_components/nspanel_haui/ha_adapter.py` | `HAAdapter` + `ItemProxy` + `ESPHomeProxy` - bridges HA async API to sync haui core |
| `custom_components/nspanel_haui/config_flow.py` | HA config flow for adding/configuring the integration via the UI |
| `custom_components/nspanel_haui/storage.py` | `PanelStorage` - loads/saves panel configs from HA's internal store |
| `custom_components/nspanel_haui/api.py` | REST API views: translations, device status, panel types/colors/config CRUD, device config/YAML, icon search, display updates |
| `custom_components/nspanel_haui/esphome_helpers.py` | ESPHome discovery utilities (find HAUI devices, service validation) |
| `custom_components/nspanel_haui/editor_panel.py` | Registers the editor sidebar panel and serves `frontend/` as static files; keep Python files out of `frontend/`, which is served without authentication |
| `custom_components/nspanel_haui/haui/abstract/haui_base.py` | `HAUIBase` - root base class: config access, command sending/batching, logging, lifecycle |
| `custom_components/nspanel_haui/haui/abstract/haui_config_access.py` | `HAUIConfigAccess` - lightweight config/logging base for data wrappers (no display transport) |
| `custom_components/nspanel_haui/haui/abstract/haui_page.py` | `HAUIPage` - page base class: lifecycle hooks, component callbacks, header/button helpers |
| `custom_components/nspanel_haui/haui/abstract/component.py` | `Component(NamedTuple)` + `ComponentRegistry` - type-safe page component declarations |
| `custom_components/nspanel_haui/haui/abstract/haui_config.py` | `HAUIConfig` - typed config wrapper around the merged config dict |
| `custom_components/nspanel_haui/haui/abstract/haui_panel.py` | `HAUIPanel` - runtime panel instance (holds items, pages, navigation actions) |
| `custom_components/nspanel_haui/haui/abstract/haui_item.py` | `HAUIItem` - runtime item instance (wraps entity config with display logic) |
| `custom_components/nspanel_haui/haui/abstract/display_interface.py` | `DisplayInterface` + `ESPHomeTransport` - high-level display command API |
| `custom_components/nspanel_haui/haui/abstract/haui_entity.py` | `HAUIEntity` - wraps a single HA entity with config, state listening, service calls |
| `custom_components/nspanel_haui/haui/abstract/haui_event.py` | `HAUIEvent` - event data class for display interactions |
| `custom_components/nspanel_haui/haui/abstract/mixins/` | `ComponentMixin`, `FunctionButtonMixin`, `PagedItemsMixin` (paging + debounced item updates for grid/row) - page behavior mixins |
| `custom_components/nspanel_haui/haui/mapping/panel.py` | `PANEL_MAPPING` and `PAGE_MAPPING` registries; `_build_panel_mapping()` and `SYS_PANEL_MAPPING` |
| `custom_components/nspanel_haui/haui/mapping/descriptor.py` | `PageDescriptor` + `PageOption` metadata and the `_()` translation marker |
| `custom_components/nspanel_haui/haui/mapping/const.py` | String enums and constants: `ESPEvent`, `ESPResponse`, `ESPCommand`, `ESPAction`, `SysPanelKey`, `NotifType`, `DEFAULT_CONFIG`, `PANEL_CONFIG` |
| `custom_components/nspanel_haui/haui/device.py` | `HAUIDevice` - device instance handling gestures, callbacks, physical buttons |
| `custom_components/nspanel_haui/haui/device_config.py` | `DEVICE_CONFIG` defaults and derived `DEVICE_CONFIG_FIELDS` |
| `custom_components/nspanel_haui/haui/config_models.py` | Pydantic v2 validation (`validate_config`, `validate_device_config`, `validate_panels`) |
| `custom_components/nspanel_haui/haui/features.py` | Home Assistant feature-bit constants (e.g. `MediaPlayerFeatures`) |
| `custom_components/nspanel_haui/haui/version.py` | `get_version()` - lazily reads the version from `manifest.json` (source of truth); keep `pyproject.toml` in sync |
| `esphome/install.yaml` | ESPHome config for initial device flashing |
| `esphome/nspanel_haui.yaml` | Runtime ESPHome device config |
| `nextion/nspanel_haui.tft` | Nextion display UI file (pre-compiled) |
| `pyproject.toml` | Project metadata, pytest/mypy/ruff configuration |
| `hacs.json` | HACS integration metadata |
| `custom_components/nspanel_haui/manifest.json` | HA integration manifest |

### Important directories

| Directory | Purpose |
|-----------|---------|
| `custom_components/nspanel_haui/haui/abstract/` | Base classes: `HAUIBase`, `HAUIConfigAccess`, `HAUIConfig`, `HAUIEntity`, `HAUIItem`, `HAUIPanel`, `HAUIEvent`, `HAUIPage`, `DisplayInterface`; `mixins/` holds page behavior mixins |
| `custom_components/nspanel_haui/haui/controller/` | Runtime controllers: ESPHome, connection, navigation, notification, update, gesture |
| `custom_components/nspanel_haui/haui/page/` | Display page implementations - one file per panel type (20 modules) |
| `custom_components/nspanel_haui/haui/mapping/` | Static lookups: `panel.py` (`PANEL_MAPPING`), `page.py` (`PAGE_MAPPING`), `descriptor.py` (`PageDescriptor`), colors, icons, constants |
| `custom_components/nspanel_haui/haui/utils/` | Shared utilities: `color`, `datetime`/CLDR, `debounce`, `icon`, `item`, `locale_data`, `notification_blinker`, `page`, `text`, `value` |
| `custom_components/nspanel_haui/frontend/` | HA Lovelace editor UI (vanilla JS, loaded as a panel); `previews/` holds panel preview renderers |
| `tests/` | Pytest tests (backend) plus Node test-runner tests in `tests/frontend/`; `conftest.py` stubs `homeassistant` and `dateutil`, so no running HA instance is needed |
| `docs/` | User documentation: install, configuration, panels, FAQ, ESPHome, Hub, Nextion, Communication, Design, development, troubleshooting |
| `nextion/` | Nextion display assets (TFT file, HMI source, fonts, images) |
| `esphome/` | ESPHome device configuration files (`install.yaml`, runtime/dev configs, `secrets.yaml.example`; copy it to the git-ignored `secrets.yaml` for local builds). Requires ESPHome 2026.10 or later (`min_version` in `nspanel_haui/base.yaml`) |
| `scripts/` | Development utilities: font generation (`gen_fonts`, `gen_char`), color palettes/wheels, spinner generation, background tile generation (`gen_backgrounds`), editor design grids (`gen_grid`), RGB565 image conversion, Nextion2Text, preview generator, translation extraction, portrait HMI geometry patcher (`gen_portrait`) |
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

Activate a virtual environment first. A local dev venv may already exist at `.venv/` (Python 3.13; CI uses 3.14); a separate `.venv_docs/` venv is handy for docs builds:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # first time only
```

```bash
# Run backend tests (HA is stubbed; no running instance needed)
pytest tests/

# Run frontend editor tests (Node 22+, no npm dependencies)
node --test 'tests/frontend/*.test.mjs'

# Lint Python code
ruff check custom_components/

# Lint with auto-fix (this is also the only formatting step; there is no separate formatter in CI)
ruff check --fix custom_components/

# Type-check the haui core package
mypy

# Build docs strictly (catches broken links and missing files)
pip install -r requirements-docs.txt   # first time only
mkdocs build --strict

# Regenerate locale JSON after changing t()/translate()/_() strings
python scripts/translations/extract_translations.py
```

**CI:** Three workflows run on push/PR to `master` and `dev`:
- `tests.yml` - installs dev + docs dependencies, builds docs (`mkdocs build --strict`), runs `pytest tests/`, `ruff check custom_components/` and `mypy` on Python 3.14, and runs the frontend tests on Node 24
- `validate.yml` - runs `hassfest` and `hacs` validators (also on a daily schedule)
- `docs.yml` - builds docs and deploys to GitHub Pages on `master` when `docs/**` or `mkdocs.yml` changes

There is no build step - the integration is installed by copying (or symlinking) `custom_components/nspanel_haui/` into the HA `custom_components` directory and restarting Home Assistant. There is no separate development server; restart HA after Python changes. Frontend assets are served from a versioned static path registered at startup, so restart/reload HA to pick up frontend changes.

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
component.name   # instead of component[1]
component.id     # instead of component[0]
```

**Naming convention:** Use snake_case purpose-based names (e.g., `title`, `btn_up`, `t_time`, `t_main_icon`), not Nextion widget identifiers.

**Method signatures** use `Component` type instead of `tuple[int, str]` or `tuple`:
- `set_component_text(component: Component, text: str)`
- `set_component_value(component: Component, value: int)`
- `add_component_callback(component: Component, callback: Callable, drag: bool = False)`
- Callback handlers: `def callback(self, event: HAUIEvent, component: Component, button_state: int)`
- Prefer `on_release(component, callback)` for release-only callbacks: it receives `(event, component)` and avoids the `button_state` argument. Use `add_component_callback` only for rare press-event handling that needs `button_state`.

### Adding a new panel type

1. **Inspect the page's widgets** in the Nextion HMI file to find each widget's ID and name (see *Nextion HMI inspection* below).
2. Create a page class in `haui/page/yourpanel.py` that extends `HAUIBase` (or a relevant page base).
3. Define a `COMPONENTS` class attribute using `ComponentRegistry` with `Component` entries for each Nextion widget on the page. Follow snake_case purpose-based naming.
4. Define a `DESCRIPTOR` class attribute of type `PageDescriptor` with at least `type_key`, `page_name`, `page_id`, `label`, and `description` (plus `options`/`item_options` as needed).
5. Import the class in `haui/mapping/panel.py` and add it to the module-level `_page_classes` list.
6. If the panel has configurable options, add `PageOption` entries to `DESCRIPTOR.options`.
7. If it needs a popup variant, set descriptor metadata instead of editing a registry: `popup_alias_for="<parent_type_key>"` for a different class on the same Nextion page, or `can_show_popup=True` for a non-system page (which auto-registers `popup_<page_name>`; the media page is special-cased as `popup_media_player`). System popups are derived from `is_system=True` plus `sys_panel_default["key"]` starting with `popup_`.
8. Document the panel in `docs/panels/panel_yourpanel.md`.
9. **Add a preview renderer** for the editor grid view (see *Preview renderer workflow* below).

### Nextion HMI inspection

The display UI is compiled from `nextion/nspanel_haui.HMI` (edited in the Nextion IDE). To see a page's widget IDs, names, attributes, and event code (touch scripts) before writing its Python `ComponentRegistry`, generate a readable text dump with [Nextion2Text](scripts/nextion2text/Nextion2Text.py):

```bash
python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui.HMI -o ref_src/nextion-out-visual -d -s -p visual
```

- `-i` — path to the compiled `.HMI` file
- `-o` — output folder, one `.txt` file per Nextion page named after the page; `ref_src/` is git-ignored, safe to regenerate here
- `-d` — clear the output folder first, so stale files from a previous run don't linger
- `-s` — also write a stats summary file (component/event counts)
- `-p visual` — include visual properties (position, size, colors), not just the default non-visual ones; needed to read widget coordinates for preview renderers

Each generated file lists the page's widgets (ID, Nextion name, attributes) and event code (`Preinitialize Event`, `Touch Press Event`, etc.) — use it to map Nextion widget IDs/names to `Component(id, "name")` entries and to see what a button's touch script already does on the device side. Run `python scripts/nextion2text/Nextion2Text.py --help` for the full flag reference.

### Editing the Nextion HMI by script

Geometry and other int attributes of existing widgets can be patched in place by script; everything that changes a block's length (adding/removing widgets, event code, text of another length, pictures, fonts) is Nextion Editor work. `scripts/gen_portrait/gen_portrait.py` is the reference implementation (`parse_pages`, `_write_attr`, `block_crc`); it applies a spec module — `portrait_layout.py` (complete 320 × 480 layout) or `landscape_layout.py` (partial refinements of the 480 × 320 layout, `--spec landscape_layout`); extend the spec rather than hand-editing bytes.

**Both HMIs share one definition of components.** The Python `COMPONENTS` registries address `nspanel_haui.HMI` and `nspanel_haui_portrait.HMI` with the same names and ids, so every change to one HMI — a widget added, removed, renamed or re-ordered, an attribute or geometry edit, event code — must be applied to the other as well (geometry and attributes through the sibling spec: `landscape_layout.py` ↔ `portrait_layout.py`). Be extra careful here: a widget that exists in only one HMI breaks that TFT silently at runtime. Run `gen_portrait.py --check` for both specs and `python scripts/verify_nextion/verify_nextion.py --require-portrait` before calling either HMI done.

**Editing display files:** when editing Nextion display files, use the Nextion Editor via VNC/noVNC. The editor is a Windows GUI application, so drive it over VNC/noVNC on the desktop where it runs. Use the editor for anything the script cannot do safely (see above), then follow the workflow below.

Workflow (the editor owns the file while a project is open):

1. **Close the project** in the Nextion Editor (File → Close Project) before writing the HMI. The editor silently re-saves the open project on Close Project and on every project switch, overwriting whatever a script wrote.
2. **Patch**, then prove it: re-dump with Nextion2Text (`-p visual`) and compare every widget against the spec — `gen_portrait.py` does this itself and refuses to write on any mismatch, and its `--check` mode reports widgets that exist on only one side. The portrait spec names the landscape HMI as its `SIBLING_HMI`: both files must hold the same widgets and every widget's Send Component ID (`sendkey`) is copied from the landscape project — toggle touch settings there, never in the portrait copy. `scripts/verify_nextion/verify_nextion.py --require-portrait` enforces that parity.
3. **Re-open the project** (recent list), look at every page, compile (`Compile`, then `File → TFT file output` → `nextion/nspanel_haui_portrait.tft`) and run `python scripts/verify_nextion/verify_nextion.py --require-portrait`. Done means the editor opened the file without "Version mismatch", every page renders as specified, and the gate passes.

Format reference (what the script relies on):

- The `.HMI` is a container: a table of `<16-byte name, start, size>` entries — `N.pa` page blocks, `N.i`/`N.is` pictures, `N.zi` fonts, `main.HMI` (device settings, incl. the display direction byte at offset 12) and `Program.s`.
- A page block is a 56-byte header (`<I` stamp, size, header size, component count, …), a component table (`<III` per component: offset, size, …) and the components. Every attribute is a record `<u32 len><16-byte name><value>`; ints are little-endian, normally 4 bytes. `objname` and `type` (121 = the page itself) identify a component.
- Safe same-length writes: `x`, `y`, `w`, `h` together with the derived `endx = x + w - 1` / `endy = y + h - 1`, `font`, `isbr` (word wrap), `sendkey` (Send Component ID), colours, and the page component's own `w`/`h`.
- Every page block starts with a content **stamp** the editor validates — a stale stamp fails with "Version mismatch" / "Loading Page Failed". It is `CRC-32 (poly 0x04C11DB7, MSB-first, init 0, no final XOR)` over every byte after the stamp widened to a big-endian u32, plus 40 zero bytes, XOR an unknown length-dependent constant. Same-length edits cancel the constant: `new = old ^ crc(old block) ^ crc(new block)` (`block_crc`). Pictures carry no stamp; the container table has a checksum of its own that is not cracked, so block lengths and offsets stay as the editor wrote them.

### Preview renderer workflow

The editor shows a visual preview of each panel in the grid view. Each panel type can register a custom preview renderer; if none is registered, a fallback (icon only) is used.

**Existing renderers** live in `frontend/previews/*.js`, registered in `frontend/panel-previews.js`. Common visual primitives (`simItemTile`, `simSlider`, `simSliderVertical`) are available in `frontend/previews/primitives.js`.

**To add a preview renderer for a new panel type:**

1. **Generate a stub** using the generator script:
   ```bash
   python scripts/gen_preview/gen_preview.py --type <type_key>
   ```
   This creates `frontend/previews/<type_key>.js` with a placeholder renderer that lists all Nextion components and panel options as comments.

2. **Fill in the visual layout** — edit `frontend/previews/<type_key>.js` to replace the placeholder with actual visual content using primitives from `primitives.js` and classes from `styles/preview/common.js`. Use existing renderers (e.g. `grid.js`, `clock.js`) as reference.

3. **Add preview CSS** if the renderer needs styles beyond what `common.js` provides: create `frontend/styles/preview/<type_key>.js` exporting a Lit `css` tagged template, then import and reference it in `frontend/styles/panel-preview-styles.js`.

   Previews follow the device's `display_model`: `renderPanelPreview` (`previews/registry.js`) stamps `portrait` on every result and the card chrome (`panel-card.js`) draws the 320 × 480 frame with the function buttons in a bottom bar. Write the landscape markup as the default and put the portrait re-flow (grid 2 × 3, stacked row controls, …) under `.pg-card-preview--portrait` in the type's style module; a renderer whose structure differs branches on `isPortraitDevice(host)` from `previews/utils.js`. Check the preview with a portrait device selected before finishing.

4. **Register the renderer** — the generator already added the import and registration line in `frontend/panel-previews.js`. If creating manually, add:
   ```javascript
   import { render<TypeName>Preview } from './previews/<type_key>.js';
   // ... then in the registration block:
   registerPanelPreview('<type_key>', render<TypeName>Preview);
   ```

5. **Verify coverage** — run the generator's check mode to confirm no types are missing:
   ```bash
   python scripts/gen_preview/gen_preview.py --check-missing
   ```

**Generator reference:**
```bash
# Generate stubs for all missing types
python scripts/gen_preview/gen_preview.py --all

# Check which types are missing renderers
python scripts/gen_preview/gen_preview.py --check-missing

# Dry-run (print to stdout instead of writing files)
python scripts/gen_preview/gen_preview.py --type <type_key> --dry-run
```

**How it works:** The generator reads each page class's `COMPONENTS` (ComponentRegistry) and `DESCRIPTOR` metadata from Python, then produces a JS stub file with documented widget IDs and option keys for the developer to fill in manually (visual layout is an HTML/CSS design task that cannot be inferred from widget tuples alone).

### Page lifecycle hook ordering

Pages follow a defined lifecycle when panels are shown. The canonical hook ordering is:

1. **`prepare()`** (optional) — Set instance attribute defaults. Called during `__init__()`, automatically. Use instead of overriding `__init__()`.
2. **`start_panel(panel)`** (required) — Register callbacks, create items, save state.
3. **`config_panel(panel)`** (rare) — Auto button setup via base class. Typically not overridden.
4. **`before_render_panel(panel)`** (optional) — Return `False` to abort rendering.
5. **`render_panel(panel)`** (required for pages that draw content; the base provides a no-op) — Send display commands.
6. **`after_render_panel(panel, rendered)`** (optional) — Post-render actions.
7. **`stop_panel(panel)`** — Base implementation clears state listeners/callbacks and then calls `_stop_panel(panel)`; subclasses normally do their cleanup in `_stop_panel()`.

Key rules:
- Use `prepare()` instead of `__init__()` for setting default attribute values. No need to call `super().prepare()` — the base implementation is a no-op.
- Override `_stop_panel(panel)` instead of `stop_panel(panel)` for per-class cleanup. Do NOT call super — the base `stop_panel()` handles listener cleanup automatically, then calls `_stop_panel()`.
- If you override `stop_panel()` itself (rare), call `super().stop_panel(panel)` so listeners are cleared and `_stop_panel()` still runs.
- Use `_save_auto_state()` / `_restore_auto_state()` helpers (available on `HAUIPage`) instead of manually saving/restoring `auto_dimming`, `auto_page`, and `auto_display_off` in popup overlays.

Additional notes:
- `start_page` does **not** exist, neither as a config key nor as a hook — navigation uses `home_panel` from device config, and pages use the panel hooks above.
- Entity ids built from the device name use `self.app.device.get_slug()` (Home Assistant's `slugify`, computed once in `NSPanelHAUI`); don't slug the name by hand.
- `BlankPage` intentionally has no `render_panel()` — it is a blank/idle page used for the idle (automatic page switching) session.

### Config flow and editor settings

- `config_flow.py` creates the single hub entry (user step plus zeroconf/DHCP/integration discovery). There is no options flow.
- Device and panel settings are edited in the sidebar editor (`frontend/`), which calls the REST views in `api.py`; panel configs are validated there with `validate_panels` (`haui/config_models.py`).
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

### Notifications and device states

Notification delivery has three entry points; the HA service is the recommended one because it carries the full option set.

| Entry point | Options | Notes |
|-------------|---------|-------|
| `nspanel_haui.send_notification` service | title, message, icon, type, persistent, force_show, text_size | Goes straight to the notification controller; carries severity (`type`) and force-show |
| `notify.<device>` / `notify.<device>_persistent_notification` | title, message only | The regular entity queues; the persistent entity always opens immediately (force-show) and loops the sound. Neither accepts a configurable severity or force-show |
| ESPHome `send_notification` action | title, message, icon + optional persistent / text_size | No severity or force-show fields |

Key semantics:

- Notifications **never auto-dismiss**: an entry stays in the queue until it is
  dismissed on the panel, replaced by an identical title+message, or cleared.
  The notification queue plays through — when the current popup is dismissed
  while more are queued, the next one opens in its place (`notification._advance_queue`).
  A new force-show notification never rips an open notification popup/list away:
  it waits in the queue instead. This is the "notifications are shown only once"
  regression guard — do not pass a `close_timeout` to queued-notification popups.
- `persistent=true` loops the sound until the notification is dismissed, and opens the popup immediately (the service forces it; the ESPHome action does not). While the idle page is shown, only a `critical` persistent notification forces its popup over it; other severities wait for the user to return to a real panel — the timer keeps running, so the alert resumes when the idle page is exited.
- An empty `icon` falls back to a severity default (`info` → `mdi:information-outline`, `warning` → `mdi:alert-outline`, `critical` → `mdi:alert-octagon-outline`). `critical` also plays the `alert` sound instead of `notification`.
- Long messages scroll horizontally (marquee) in the detail popup; the queue selection list shows plain titles.
- Sending a notification with the same title and message as one already queued replaces it: the sound replays and the queue advances to it when the current popup closes.

Idle page vs. display state (important): the **idle page** is the configured automatic page switch, tracked by `navigation.idle_panel_active`. It is independent of the firmware's display brightness machine: the display can be off without a page switch, and the idle page can be shown while the display is still on.

- `services.py` `wakeup` calls `navigation.exit_idle_to_prev_or_home(config)` (a no-op when no idle session is active) and `idle` calls `navigation.open_idle_panel(True)`. `open_idle_panel()` is a pure page switch — it never turns the display off — and creates the pre-idle snapshot only when an idle session actually starts.
- Navigation and `function_btn_mixin` actions use the same `open_idle_panel()` / `exit_idle_to_prev_or_home()` API; the `idle_panel` / `idle_panel_extra` / `show_idle_button` config keys are the only names.

Canonical docs: `docs/services.md` (service fields and notify entities), `docs/device.md` (display states, idle page, waking up), `docs/panels/popup_notify.md` (popup presentation).

### Testing

Tests stub `homeassistant` modules via `sys.modules` manipulation in `tests/conftest.py` (with per-test overrides in files like `tests/test_config_flow.py`). Tests do **not** require a running HA instance. Use `unittest.mock` for mocking. Follow the pattern of creating minimal stub classes for HA types like `ConfigFlow`.

When modifying `config_flow.py`, check the corresponding tests in `tests/test_config_flow.py`.

Frontend editor modules are tested with Node's built-in runner in `tests/frontend/` (`*.test.mjs`), using the fake editor host and backend in `tests/frontend/fake-host.mjs`. Tests that import a module depending on Lit must import `tests/frontend/dom-shim.mjs` first.

### Config merging

Device settings have one home: the panel store.
- `config_entry.data` holds only the hub name, each device's identity (`name`, optional `esphome_device_id`, built by `esphome_helpers.hub_device_entry`) and `removed_devices`.
- `PanelStorage` holds each device's settings, including `enabled`, and its panels.

`__init__.py:_build_config_dict(entry.data, store, device_name=...)` builds one device's runtime config: identity, then store settings, then `DEVICE_CONFIG` defaults. The result goes to `HAUIConfig` for typed access and validation. Setup builds it once per enabled device. A panel or settings save (`api._push_panels`) rebuilds it the same way and applies it with `NSPanelHAUI.reload_config`, so a setting removed from the store falls back to its default.

### Locale/translations

The project uses hardcoded CLDR locale data (see `haui/utils/locale_data.py`) instead of depending on Babel. Date formatting uses inline locale data in `haui/utils/datetime.py`. Display text translations use lookup tables in `haui/utils/text.py`, backed by JSON files in `haui/locale/*.json` (component + text sections).

**Translation extraction workflow:**

1. After adding, removing, or changing any `t()` / `host._t()` (frontend JS), `self.translate()` (Python), or `_()` (descriptor) call, run:

   ```bash
   python scripts/translations/extract_translations.py
   ```

   This scans `custom_components/nspanel_haui/` (Python) and `frontend/` (JS) for string-literal calls, then syncs `haui/locale/*.json`: adds new keys (English text as the value in `en.json`, empty string in other languages), removes keys no longer referenced anywhere, and prints an added/removed count per language file.
2. Fill in the empty values the run added to non-`en` locale files (or hand the new `en.json` keys to a translator).
3. Commit the updated `haui/locale/*.json` files together with the code change that introduced the strings.

`scripts/translations/merge_translations.py` is a secondary helper for merging a completed `scripts/translations/translate.json` batch back into `haui/locale/*.json` without clobbering existing entries — for external translation-service round trips, not needed for routine local development.

## SOLID Principles

This codebase follows SOLID principles. Preserve these patterns when adding or modifying code.

### Single Responsibility Principle (SRP)

Each class owns exactly one concern. Do not add unrelated responsibilities.

| Class | Responsibility | File |
|-------|---------------|------|
| `NSPanelHAUI` | Top-level composition: wires controllers, device, and config together | `nspanel_haui.py` |
| `HAAdapter` | Bridges HA's async API → synchronous interface for haui/ core | `ha_adapter.py` |
| `ESPHomeProxy` | Sends commands to ESP32 via Native API, listens for device events | `ha_adapter.py` |
| `ItemProxy` | Synchronous wrapper around a single HA entity's state/attributes/services | `ha_adapter.py` |
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
    AboutPage, AlarmPage, ..., WeatherPage,  # ← add new class here
]

def _build_panel_mapping() -> dict[str, tuple[str, type]]:
    mapping = {}
    for cls in _page_classes:                     # open for new entries
        d = getattr(cls, "DESCRIPTOR", None)
        if d is not None:
            mapping[d.type_key] = (d.page_name, cls)
    return mapping
```

**Extending components** on a page subclass:
```python
class MyPage(HAUIPage):
    COMPONENTS = HAUIPage.COMPONENTS.merge(   # extend, don't redefine
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
page.render_panel(panel)      # works for GridPage, ClimatePage, LightPage, etc.
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
class HAUIPage(FunctionButtonMixin, ComponentMixin, HAUIBase):
    ...
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
- **Don't put Python files in `frontend/`** - that directory is served as unauthenticated static files; keep only browser assets there. Python modules that register or serve the frontend live outside it (see `editor_panel.py`).

## Commit and Pull Request Guidelines

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): message`

Common types seen in this repo: `fix`, `feat`, `refactor`, `docs`, `test`, `style`, `chore`.

Scopes seen in history include `haui`, `pages`, `frontend`, `esphome`, `device-management`, `mkdocs`, `install-flow`, `nextion`, `icons`, `panels`, `services`, and `release`. Recent commits are mixed — use Conventional Commits for new work.

Example: `fix(esphome): include device name in discovery fallback`

### Before committing

1. **Keep docs in sync** — after any code change, check the `docs/` directory for files related to what you changed and update them to reflect the new behavior, options, schemas, or defaults. Outdated docs are bugs.
2. **Verify docs build** — after updating docs, install `requirements-docs.txt` and run `mkdocs build --strict` from the project root to catch broken links, missing files, or rendering errors. The build must succeed (CI runs the same command).
3. Run `pytest tests/` — all tests must pass.
4. Run `node --test 'tests/frontend/*.test.mjs'` when touching `frontend/` — all tests must pass.
5. Run `ruff check custom_components/` — no lint errors.
6. Run `mypy` — no type errors in `haui/`.
7. If you changed config flow logic, ensure `tests/test_config_flow.py` covers the change.
8. If your changes affect documented behavior (new options, changed defaults, new panel type features, etc.), update the corresponding docs in `docs/` to match.
9. Breaking changes must be documented in `docs/upgrading.md` and the CHANGELOG's "Breaking changes" section.

### Pull requests

- Target the `dev` branch for feature work, `master` for hotfixes
- Describe what changed, why, and how it was tested
- Include a screenshot or short recording for frontend/display changes
- Reference related issues or PRs
- PRs must pass all three CI workflows (`tests`, `validate`, `docs`) before merge; run the local checks above first
