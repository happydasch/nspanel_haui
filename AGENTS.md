# AGENTS.md

You are an experienced, pragmatic software engineering AI agent working on **NSPanel HAUI** — a Home Assistant custom integration that replaces the stock Sonoff NSPanel firmware (ESP32 + Nextion touchscreen) with an ESPHome-driven, configurable display UI.

Do not over-engineer. Keep edits minimal. Ask for permission before making an exception to a rule. When this file and `docs/develop/` disagree, the docs are right — fix this file.

## At a glance

- **Python 3.14+** integration, **JavaScript** editor and dashboard card, **no build step** — the integration is installed by copying `custom_components/nspanel_haui/` into Home Assistant and restarting (restart or reload after JS changes too: assets are served from a versioned static path).
- **Home Assistant 2026.11+** (`hacs.json`), `integration_type: hub`, `iot_class: local_push`.
- **Declared dependencies:** only `pydantic>=2.0` and `python-dateutil>=2.8.0`; `requests`, `packaging` and `probatio` ship with HA core.
- **Firmware** in `esphome/` (ESPHome 2026.11+), display sources in `nextion/` (`nspanel_haui.HMI` landscape, `nspanel_haui_portrait.HMI`, each compiled to a `.tft`).
- **Gates:** ruff (100 columns, target `py314`), `mypy` over `custom_components/nspanel_haui`, `pytest tests/` (Node 22+), `node --test 'tests/frontend/*.test.mjs'`, `zensical build --strict` (docs config `mkdocs.yml`).

## Read the docs, don't rediscover

`docs/develop/` is the reference. Open the page before changing an area; this file only holds the rules that must not break.

The developer guide is grouped as **General** (`development`, `hub`, `communication`, `notifications`), **ESPHome & display** (`esphome`, `nextion`, `nextion-editor`, `design`), **Frontend** (`frontend`, `preview`) and **Releases** (`update-process`, `upgrading`, `release`).

| Area | Read |
|------|------|
| Local commands, throwaway HA instances, git hooks, test conventions, code style | `docs/develop/development.md` |
| Hub objects, adapter/threading, panel and page lifecycle, controllers, REST API, status fields | `docs/develop/hub.md` |
| Handshake, heartbeats, reading values from the display | `docs/develop/communication.md` |
| Notifications: queue, delivery paths, timers, presentation | `docs/develop/notifications.md` |
| ESPHome firmware | `docs/develop/esphome.md` |
| Nextion component, HMI editing rules, the `.HMI` file format | `docs/develop/nextion.md`, `docs/develop/nextion-editor.md` |
| Design: fonts, icons, themes, the new-panel workflow | `docs/develop/design.md` |
| Editor architecture, screens and overlays, visual foundations, component inventory, testing | `docs/develop/frontend.md` and the five pages beside it |
| Virtual panel, simulated and live preview, panel cards, dashboard card transport | `docs/develop/preview.md` |
| Firmware/TFT updates, rollout, update settings | `docs/develop/update-process.md` |
| Breaking changes per version, old firmware, rollback | `docs/develop/upgrading.md` |
| Release policy, branches and tags, CI gates, runbook | `docs/develop/release.md` |
| Development scripts | `scripts/README.md` |
| The behavior we promise users | `docs/user/` |

## Commands

```bash
source .venv/bin/activate            # Python 3.14 venv; .venv_docs and .venv_ha also exist
pip install -r requirements-dev.txt  # once per clone
npm ci                               # once per clone, for the frontend type check
make help                            # every shortcut
```

| Target | Does |
|--------|------|
| `make -j4 check` | the whole local gate: tests, format check, lint, both type checks, strict docs build, version and generated-file checks |
| `make test`, `make test-integration`, `make test-frontend` | both suites; the backend one replays card renders through Node |
| `make format`, `make lint`, `make typecheck`, `make typecheck-frontend` | `ruff format` / `ruff check` / `mypy` / `tsc` over the `// @ts-check` modules |
| `make docs` | `zensical build --strict` |
| `make hmi-check` / `make screens-check` | both HMI specs, generated layouts and preview coverage / the docs screen PNGs |
| `make esphome-config` | universal ESPHome config (needs `requirements-esphome.txt`; conflicts with the dev environment) |
| `make esphome-compile` / `make esphome-size` | compile a firmware config (`CONFIG=esphome/nspanel_haui_dev.yaml` for the dev one) and check the image against its app partition |
| `make ha-venv-setup` → `make ha-venv-start`, `make ha-docker-up` | throwaway Home Assistant instances under the git-ignored `.dev/` |

Raw commands, for a single check:

```bash
pytest tests/                                   # Home Assistant is stubbed in tests/conftest.py
node --test 'tests/frontend/*.test.mjs'
npm run typecheck:frontend
ruff format custom_components/ scripts/ tests/
ruff check custom_components/ scripts/
mypy
python -m scripts.translations.extract_translations   # after any t(), _t(), translate() or _() change
scripts/git_hooks/install.sh                    # once per clone; sets core.hooksPath
```

- Run Python tools as modules from the repository root (`python -m scripts.hmi_layout.gen_layout --check`).
- The pre-commit hook regenerates the virtual layouts and stages them, then checks both layout specs: a committed HMI without its regenerated layout breaks every preview.

## Where things live

Everything below lives under `custom_components/nspanel_haui/` unless noted.

- **`hub/`** — Home Assistant-facing runtime: `app.py` (`NSPanelHAUI`, one per enabled device, a composition hub with no business logic), `adapter.py` (`HAAdapter`, `ItemProxy`, `ESPHomeProxy`), `storage.py` (`PanelStorage`), `esphome_helpers.py`.
- **`haui/`** — the synchronous core (never imports `homeassistant`, never uses `asyncio`): `abstract/` (base classes and `mixins/`), `controller/` (esphome, connection, navigation, notification, update + `release_source`, gesture), `page/`, `mapping/` (registries, colours, icons, `font_metrics.json`), `utils/`, `config_models.py`, `schedule.py`, `option_rules.py`.
- **`api/`** — admin REST views (`editor`, `config`, `themes`, `panel_edits`, `status`, `updates`); **`web/`** — `editor.py` (sidebar panel + serves `frontend/`), `websocket.py`, `card.py`, `preview/`.
- **Platforms at the integration root:** `notify.py`, `update.py` (two update entities per panel), `repairs.py`, `diagnostics.py`, `system_health.py`, `services.py`, `config_flow.py` (the only way in; there is no options flow — settings live in the editor).
- **`frontend/`** — one static custom panel plus the dashboard card: `app/`, `store/`, `api/`, `views/`, `ui/`, `dialogs/`, `previews/`, `virtual/`, `styles/`, `card/`.

## Threading

Every call into an app — device events, state changes, timers, reloads, actions, notify — runs on that app's single worker thread, in order.

- From the event loop use `app.dispatch()` (fire-and-forget) or `await app.async_run_on_worker()`. Never `hass.async_add_executor_job` with app code.
- Blocking work (HTTP, disk) never runs on the worker: `app.run_off_worker(fn, *args, timeout=…)` waits for the result, `app.submit_off_worker(fn, on_done=…)` applies it back on the worker. The callable must not touch app state.
- Only liveness traffic bypasses the worker: `run_every(..., on_loop=True)` and `publish_detached()`. The 5 s hub→device heartbeat uses both, because the device force-disconnects after two missed beats.
- Once an app has stopped, `dispatch()` drops the callback and `async_run_on_worker()` raises `AppStoppedError`.
- Never wait for an app's worker from code the worker may be blocked on (a service handler app code can call with `blocking=True`): queue it with `dispatch()`, or the worker deadlocks.

## Non-negotiables

- **Home Assistant access only through `self.app`**; display commands only through `send_cmd()` / `send_cmds()` / `set_component_text()` / `set_component_value()` (`DisplayInterface` → `DisplayTransport`), never the ESPHome controller.
- **Settings with a declared default are read, not defaulted:** `DEVICE_CONFIG` and `DEFAULT_CONFIG["update"]` are the only defaults, so read with `self.get("key")`; a call-site default can only disagree with them.
- **Panel options come from the descriptor:** `self.option(panel, key)` in `start_panel()`; `panel.get()` on a declared option is refused by a test.
- **`prepare()` for per-panel attribute defaults, `_stop_panel()` for cleanup** (no `super()` there). Everything `prepare()` sets is reset per panel, so no live timer, listener handle or late-callback counter belongs in it — use a fresh `object()` token; state that outlives a panel goes on the panel.
- **Every display command goes through the page API** so a newly attached Live viewer can be replayed the page (`load_commands` + `page_commands()`). A page needs no redraw hook.
- **`set_panel()` batches `start_panel` + `config_panel` + `render_panel`** (`refresh_panel()` batches `render_panel`); callbacks from state listeners, timers and touches need `with self.rec_cmd:`, which keeps the last write per target.
- **System panels are identified by key, never by type.** System, Blank, Settings and About are fixed; only popups can be overridden, and a user panel saved under a popup key replaces that popup without becoming a navigation target.
- **Solid pages paint the theme in Preinitialize, never afterwards** — the hub only sends `THEME_GLOBALS` to `Program.s` before `goto_page`, plus the body foregrounds in `haui/mapping/theme_foregrounds.py`. Re-paste generated theme code, never hand-edit it.
- **Both HMIs carry the same widgets** — same names, ids, order, event code. A widget in one HMI only breaks that TFT silently at runtime; geometry goes through `scripts/hmi_layout/` specs and `make hmi-check` proves parity.
- **`tft_version` is read only from the device-state event**, and empty means *unknown*, never `0.0.0` — treating it as old re-installed the TFT after every reboot (#63).
- **A notification is never dropped, delayed or hidden:** auto-dismiss only through the service's `timeout`, the queue plays through (`_advance_queue`), a persistent one re-opens every 60 s, and queued-notification popups get no `close_timeout`.
- **A card or thumbnail is the hub's own render, replayed.** No renderer in the browser, no second preview path, and never key a render on live readings (uptime, RSSI) — the 5 s status poll would re-render every card.
- **No Python files in `frontend/`** — it is served without authentication. The card's WebSocket commands in `web/card.py` stay the only WebSocket commands without `require_admin`: they read and lead to no input path.
- **A dev release tag is the PEP 440 version itself** (`X.Y.(Z+1).dev<run>`) and byte-identical to the version the image reports — that version reaches the build as `esphome -s yaml_version …`, so it is *not* written into `manifest.json`, which keeps the released version. Never add a `+local`/`+g<sha>` segment, which AwesomeVersion sorts above its own successors.
- **Keep the two copies of a shared default in one commit:** `frontend/constants.js` mirrors Python (`haui/device_config.py`, …), and `haui/option_rules.py` mirrors `frontend/option-rules.js` (`tests/fixtures/option_rules_cases.json` runs through both).

## Display and page code

Hook order — `page_load_commands` → `prepare` → `start_panel` → `config_panel` → `before_render_panel` → `render_panel` → `after_render_panel` → `stop_panel` → `_stop_panel` (semantics in `docs/develop/hub.md#panel`).

- A new panel type: dump the page (`python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui.HMI -o ref_src/nextion-out-visual -d -s -p visual`), write `haui/page/<type>.py` with `COMPONENTS` (`merge()`, snake_case purpose names) and a `DESCRIPTOR`, add the class to `_page_classes` in `haui/mapping/panel.py`, document it in `docs/user/panels/`, and extend `scripts/preview_gallery/sample_world.py`. Never edit a mapping by hand; popups come from descriptor metadata.
- `start_page` does not exist — neither as a config key nor as a hook. `BlankPage` deliberately has no `render_panel()`.
- Entity ids built from the device name use `self.app.device.get_slug()`.
- HMI work: close the Nextion project before a script writes the file, put same-length geometry/attribute edits in the layout spec, toggle `sendkey` in the landscape project only, then compile both TFTs and advance `tft_version` (`python -m scripts.bump_tft_version`). Guide: `docs/develop/nextion-editor.md`.
- `_TEXT_BOXES` in `haui/page/notify.py` must match the HMI widgets; text is fitted with real glyph widths (`fit_text`, `font_metrics.json`) so the display never re-wraps it.

## Editor and dashboard card (`frontend/`)

Read the `docs/develop/frontend*.md` pages before a UI change; these are the rules that change must not break.

- **Where code goes:** `app/` wires collaborators; `store/` holds observable state its actions write, one poller per scope; `api/` is the only transport; `views/` and `ui/` are pure render functions (prepared data in, `on*` callbacks out, nothing from `store/` or `api/`); `styles/` holds the CSS fragments composed by `styles.js`.
- **Every displayed value has a real source**; missing data shows an explicit empty/unknown state, never a fabricated fact. The hash route is the single source of truth for the screen.
- **Elements are the exception** (shell, dialogs, preview workspace, panel editor, device settings, simulator frame, card): `nspanel-*` names, one element per kebab-case file.
- **Compose the primitives in `frontend/ui/`** instead of re-declaring markup; a missing variant is added to the primitive with its test, not forked in a view.
- **Text** goes through `t('literal')` / `host._t` — a literal only — and is interpolated with `t('Install updates ({count})').replace('{count}', String(count))`. No hardcoded label, `title`, `aria-label` or toast. Translations arrive after the module is imported, so generated text (the presets in `presets.js`, the device settings' option lists in `constants.js`) is built per call, never at module level — a catalog built at import keeps its English names for the whole session.
- **Accessibility:** native `<button>` with a label, colour never the only cue, `role="alert"` for transient failures, `role="status"` for polled state, focus rings kept, a keyboard path for every hover-only affordance.
- **Styling:** HA variables with fallbacks, HAUI meanings only as tokens in `styles/tokens.js`, the type/spacing/radius ladder from the docs, container queries (`@container haui-editor`) instead of media queries, inline `style=` only for a computed custom property, every animation paired with `prefers-reduced-motion`. `scripts/check_frontend_styles.py` enforces this.
- **Overlays:** one anchored popover (`ui/popover.js` + `data-overlay-anchor`), sidebars through `sidebarFrame`/`modalSidebar`, dialogs on `dialogs/haui-dialog.js`, and a new overlay kind declared in `store/store.js`.
- **No build step, bundler, framework or runtime dependency:** no `node_modules` import, no CDN URL, no second Lit copy.

## Tests

- Assert at the boundaries — display commands (`app.cmds`), HA calls, return values, DOM semantics — not internals or copy.
- Backend: build the real object on the fake app in `tests/support/page_app.py` and drive it through `set_panel`; extend that fake instead of copying it. One test file per module (`test_page_<type>.py`, `test_<module>.py`); never pin a constant or key list, and never test that something removed stays removed. Conventions: `docs/develop/development.md#backend-tests`.
- `tests/test_page_commands_golden.py` pins feature-gated pages; regenerate only for an intended change (`PAGE_COMMANDS_REGEN=1`). `tests/test_card_renders.py` renders and replays every panel — an empty render or a missing layout page fails.
- Frontend: import `./support/browser.mjs` before DOM/Lit, render via `support/render.mjs`, query via `support/queries.mjs`, fixtures from `support/hass.mjs` and `tests/frontend/fake-host.mjs`. A new primitive needs a semantic assertion in `ui-primitives.test.mjs` and a demo in `ui-primitives-preview.js`.
- Generated assets have guards (`test_gen_layout`, `test_bump_version`, `test_preview_coverage`, `test_frontend_styles`); a stale locale file fails `make generated-check`.

## Code style

- 100 columns, Python 3.14, ruff `E,F,W,I,UP,B`; start new modules with `from __future__ import annotations`; imports sorted.
- `NSPanelHAUI` for the top-level app, `HAUI` prefix for core abstractions, `SuffixPage` for page classes, snake_case purpose names for components.
- Google-style docstrings (`Args:`/`Returns:`); `_LOGGER` plus `self.log()` / `self.debug_log()`.
- Comments explain *why*; a comment that restates the next line is noise.
- Fail loudly: raise instead of swallowing, and avoid fallback values that hide a bug — a call site that degrades must log at warning level.
- JavaScript: no formatter or linter — match the file (2-space indent, single quotes, semicolons, trailing commas, `const`/`let`, `.js` imports, Lit templates, JSDoc `@typedef`s). Opt into typing with `// @ts-check`.

## Anti-patterns

- Display logic, entity access or HA calls in a controller or `NSPanelHAUI` instead of the right abstract class; a hand-edited mapping; base-class logic where a subclass override suffices.
- Breaking the lifecycle contract: cleanup in `stop_panel()` instead of `_stop_panel()`, a missing `super().stop_panel()`, overriding `__init__()` instead of `prepare()`.
- A concrete transport where `DisplayTransport` would do; `asyncio.run_coroutine_threadsafe` outside `HAAdapter`/`ESPHomeProxy`.
- A fallback for a setting that has a declared default.
- A second popover, sidebar, dialog frame, button, chip or card style; a second preview renderer; a forked copy of a shared UI idea.
- Building DOM by hand in the editor (`innerHTML`, `insertAdjacentHTML`, manual creation) — return `html` templates; only `frontend/virtual/` renders display output.
- Fetching outside `api/` (no `fetch`, `hass.fetchWithAuth`, `callWS`, `subscribeMessage` in views, components, dialogs or the shell).
- Laying out with viewport media queries or inline `style=`; a non-literal `t()` argument; a hardcoded user-facing string.
- A widget, geometry edit or event code that reaches only one HMI; a theme colour sent after a page is shown.
- Keying a preview on live readings, synthesising display output in JS, or "fixing" a card in the browser; a Python file in `frontend/`.
- Editing `ref_src/`.

## Commits and pull requests

Conventional Commits (`type(scope): message`); PR titles use the same format and stay under 100 characters. Two long-lived branches: `dev` is the integration branch and the repository default, where small changes land directly and features/fixes arrive as a PR (`--base dev`) merged with a merge commit; `master` is stable-only and moves only through a `dev` → `master` promotion PR whose ruleset needs the six always-running checks green. Tag that merge commit `vX.Y.Z`, then merge `master` back into `dev` so the branches converge; hotfixes branch from `master` and are merged back the same way. **No workflow ever pushes to a branch**: the release workflow only publishes a tag, and a development build reports its version through `esphome -s` instead of committing it. Full cycle: `docs/develop/release.md`.

- Fill in `.github/pull_request_template.md` (what changed, why, how it was tested, unverified device checks); add a screenshot or recording for frontend or display changes; reference the issues involved.
- All CI jobs must pass: `tests (3.14)`, `frontend`, `esphome`, `docs`, `hassfest`, `hacs`.
- Do not open a pull request unless the user asked for one.

## Before you finish

1. Docs in sync with the change (option, default, schema, behavior), then `make docs`.
2. The gates you touched are green: `make format-check lint typecheck test typecheck-frontend`, or `make -j4 check` for everything. Firmware changes also need `make esphome-compile` and `make esphome-size`.
3. HMI or TFT changed? Both HMIs updated, `tft_version` advanced, `make hmi-check` and the card-render tests green.
4. Strings changed? `extract_translations` run and `haui/locale/*.json` committed with the code.
5. User-visible behavior changed? One `CHANGELOG.md` line with its issue/PR link; breaking changes also in `docs/user/update.md`, long form in `.github/release-notes/<tag>.md`.
6. `ruff format` on every Python file you touched — CI fails on a formatting diff.

