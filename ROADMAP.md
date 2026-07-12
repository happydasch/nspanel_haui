# Roadmap

Development trajectory from **v0.3.1** toward **v1.0**.

---

## v0.4 — Device & Update overhaul

### Firmware binary distribution

| Item | Priority | Scope |
|------|----------|-------|
| Build a universal `.bin` decoupled from the device name so users can flash any NSPanel without editing YAML | Now | `esphome/` |
| Add a dedicated flashing/installation page to the docs site | Now | `docs/` |
| Publish pre-built firmware binaries alongside each release | Now | CI / GitHub Releases |
| Provide a discrete `.bin` download link in the integration config flow | Next | `__init__.py`, `api.py` |

### Sensor simplification

| Item | Priority | Scope |
|------|----------|-------|
| Reduce the number of exposed ESPHome sensors to a minimal, curated set | Now | `esphome/`, `entity/` |
| Expose the current display page as a **string sensor** for automation triggers | Now | `esphome/`, `hub/` |
| Audit all sensors: remove bleed-through from template sensors, rename non-obvious ones | Next | `esphome/` |

### TFT transfer speed

| Item | Priority | Scope |
|------|----------|-------|
| Investigate the 112 kbps transfer bottleneck to the Nextion display | Later | `esphome/` |
| Evaluate potential speed-ups (higher baud rate, chunked writes, display-side decompression) | Later | `esphome/` |

### Update workflow

| Item | Priority | Scope |
|------|----------|-------|
| Surface OTA / TFT update progress in the frontend (real‑time progress bar or log panel) | Next | `frontend/`, `update.py` |
| Allow triggering firmware + TFT updates from the device page in HA | Next | `frontend/`, `api.py` |
| Add integration‑level tests for the update pipeline so regressions are caught early | Next | `tests/` |

---

## v0.5 — Frontend maturity

### Device manager

| Item | Priority | Scope |
|------|----------|-------|
| Design a dedicated device manager view showing all NSPanels on the network at a glance | Next | `frontend/` |
| Show device status (online/offline, firmware version, IP, signal strength) | Next | `frontend/`, `api.py` |
| Allow multi‑device operations: bulk update, re‑order panels across devices | Later | `frontend/` |

### Page / Panel management

| Item | Priority | Scope |
|------|----------|-------|
| Improve the panel list view — drag‑to‑reorder, inline rename, duplicate panel | Next | `frontend/` |
| Preview thumbnails for every panel type in the grid view (close gaps from the preview renderer generator) | Next | `frontend/previews/` |
| Add a "create from template" flow for common panel configurations | Later | `frontend/` |

### Editor UI polish

| Item | Priority | Scope |
|------|----------|-------|
| Form validation feedback (inline errors, required‑field indicators) | Next | `frontend/` |
| Entity picker with search and domain filter | Next | `frontend/` |
| Toast notifications for save/delete/error events | Next | `frontend/` |
| Keyboard‑navigable modals and consistent focus management | Later | `frontend/` |
| Accessibility pass — labelled form controls, ARIA attributes, colour contrast | Later | `frontend/` |

---

## v0.6 — Features & integrations

### New panel types

| Item | Priority | Scope |
|------|----------|-------|
| Camera panel — display an RTSP/MJPEG stream on the NSPanel | Next | `haui/page/`, `nextion/` |
| Scene panel — one‑tap scene activation with optional feedback | Next | `haui/page/`, `frontend/` |
| Button bank — configurable grid of push‑buttons for any service call | Next | `haui/page/`, `frontend/` |
| Thermostat panel — integrated climate control with setpoint adjustment | Later | `haui/page/`, `frontend/` |
| Energy monitor — live power/gas/water consumption from HA sensors | Later | `haui/page/`, `frontend/` |

### Action triggers & conditional visibility

| Item | Priority | Scope |
|------|----------|-------|
| Trigger HA automations / scripts from a panel button (beyond entity service calls) | Next | `haui/abstract/`, `frontend/` |
| Conditional visibility for panel items (show/hide based on entity state) | Next | `haui/abstract/`, `frontend/` |
| Add a popup action runner that executes a sequence of steps (e.g. toggle light → wait → set scene) | Later | `haui/page/` |

### Platform maturity

| Item | Priority | Scope |
|------|----------|-------|
| Python 3.14 compatibility audit of all `haui/` code | Now | `haui/` |
| Add a developer devcontainer / quick‑start script for new contributors | Next | `.devcontainer/`, `scripts/` |
| Stabilise the REST API surface before v1.0 (version prefix, consistent response shapes) | Next | `api.py` |
| ESPHome component tests that verify sensor/button/cover entities compile and behave | Later | `esphome/` tests |

---

## v1.0 — Stable release

| Item | Priority | Scope |
|------|----------|-------|
| All known bugs with the `bug` label closed | — | cross‑repo |
| CHANGELOG.md written, covering every release from 0.1.0 through 1.0 | — | root |
| Complete translation baseline for `en.json` — no untranslated keys | — | `haui/locale/` |
| Second language (German) at ≥90 % coverage as a quality signal | — | `haui/locale/` |
| HACS default integration status (no longer "custom repository") | Next | `hacs.json`, repo settings |
| Published on PyPI / HA add‑on registry (if applicable) | Later | CI / release |
| API docs published alongside user docs | Now | `docs/api.md` |
| Final branding pass: icons, screenshots, README hero image | Now | root assets |

---

## Prior releases

| Version | Summary |
|---------|---------|
| **0.1.x** | Initial integration — ESPHome firmware + basic grid panel, config flow |
| **0.2.x** | Page system: light, climate, cover, media, weather panels. Notifications, gestures, dimming. Editor UI for panel configuration |
| **0.3.x** | ClockTwo, vacuum, alarm, QR panels. Multi‑device support. Panel storage rewrite. Locale/translation framework |

---

*This roadmap is a living document. Priorities shift as the project grows — open an issue or start a discussion to propose changes.*