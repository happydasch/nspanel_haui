/**
 * NSPanel HAUI - Editor - Colors dialog.
 *
 * Allows per-device color overrides. Users see a palette-style grid grouped
 * by category (Default, Weather, Item, Alarm, Climate). Each color is edited
 * with a native #rrggbb color picker; the RGB565 value is shown for reference.
 *
 * Communicates changes via CustomEvent:
 *   @dialog-save — detail: { overrides: { key: rgb565_int, ... } }
 *   @dialog-closed
 */
import { LitElement, html, css } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

/* ── built-in COLORS palette (fetched from haui/mapping/color.py) ──────── */

/** Cached default color values, fetched once from the backend API. */
let _colorDefaults = null;

async function ensureColorDefaults(hass) {
  if (_colorDefaults) return;
  const resp = await hass.fetchWithAuth("/api/nspanel_haui/color_defaults");
  _colorDefaults = await resp.json();
}

const COLOR_GROUPS = [
  {
    name: "Header",
    keys: [
      "header_background", "header_text", "header_accent",
    ],
  },
  {
    name: "Content",
    keys: [
      "background", "text", "text_inactive", "text_disabled",
    ],
  },
  {
    name: "Component",
    keys: [
      "component_text", "component_pressed", "component_active",
      "component_accent", "component_background",
    ],
  },
  {
    name: "Weather",
    keys: [
      "weather_default", "weather_clear_night", "weather_sunny",
      "weather_partlycloudy", "weather_windy", "weather_windy_variant",
      "weather_rainy", "weather_pouring", "weather_lightning",
      "weather_lightning_rainy", "weather_hail", "weather_snowy",
      "weather_snowy_rainy",
    ],
  },
  {
    name: "Entity",
    keys: ["entity_on", "entity_off", "entity_unavailable"],
  },
  {
    name: "Alarm",
    keys: ["alarm_armed", "alarm_disarmed", "alarm_arming"],
  },
  {
    name: "Climate",
    keys: [
      "climate_auto", "climate_heat_cool", "climate_heat",
      "climate_off", "climate_cool", "climate_dry", "climate_fan_only",
    ],
  },
];

/* ── color conversion helpers ────────────────────────────────────────── */

function rgb565ToHex(v) {
  const r = (v >> 11) & 0x1f;
  const g = (v >> 5) & 0x3f;
  const b = v & 0x1f;
  const rr = Math.round((r * 255) / 31);
  const gg = Math.round((g * 255) / 63);
  const bb = Math.round((b * 255) / 31);
  return "#"
    + rr.toString(16).padStart(2, "0")
    + gg.toString(16).padStart(2, "0")
    + bb.toString(16).padStart(2, "0");
}

function hexToRgb565(hex) {
  const raw = hex.replace("#", "");
  const rr = parseInt(raw.slice(0, 2), 16);
  const gg = parseInt(raw.slice(2, 4), 16);
  const bb = parseInt(raw.slice(4, 6), 16);
  const r = Math.round((rr * 31) / 255);
  const g = Math.round((gg * 63) / 255);
  const b = Math.round((bb * 31) / 255);
  return (r << 11) | (g << 5) | b;
}

/* ── human-friendly label for each key ────────────────────────────────── */

const LABELS = {
  // header
  header_background: "Header (background)",
  header_text: "Header (text)",
  header_accent: "Header (accent)",
  // text
  background: "Background",
  text: "Text",
  text_inactive: "Text (inactive)",
  text_disabled: "Text (disabled)",
  // component
  component_text: "Component (text)",
  component_pressed: "Component (pressed)",
  component_active: "Component (active)",
  component_accent: "Component (accent)",
  component_background: "Component (background)",
  // weather
  weather_default: "Default",
  weather_clear_night: "Clear night",
  weather_sunny: "Sunny",
  weather_partlycloudy: "Partly cloudy",
  weather_windy: "Windy",
  weather_windy_variant: "Windy variant",
  weather_rainy: "Rainy",
  weather_pouring: "Pouring",
  weather_lightning: "Lightning",
  weather_lightning_rainy: "Lightning rainy",
  weather_hail: "Hail",
  weather_snowy: "Snowy",
  weather_snowy_rainy: "Snowy rainy",
  // entity
  entity_on: "On",
  entity_off: "Off",
  entity_unavailable: "Unavailable",
  // alarm
  alarm_armed: "Armed",
  alarm_disarmed: "Disarmed",
  alarm_arming: "Arming",
  // climate
  climate_auto: "Auto",
  climate_heat_cool: "Heat / Cool",
  climate_heat: "Heat",
  climate_off: "Off",
  climate_cool: "Cool",
  climate_dry: "Dry",
  climate_fan_only: "Fan only",
};

/* ── dialog component ────────────────────────────────────────────────── */

class ColorsDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      overrides: { type: Object },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles, css`
    .footer-wrapper {
      display: flex;
      align-items: center;
      width: 100%;
    }
    .footer-toggle-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
    }
    .color-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 6px;
    }
    .color-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
    }
    .color-swatch {
      width: 28px;
      height: 28px;
      border-radius: 4px;
      border: 1px solid var(--divider-color, #ccc);
      flex-shrink: 0;
    }
    .color-label {
      flex: 1;
      min-width: 0;
      font-size: 0.85em;
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .color-input-wrap {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }
    .color-input-wrap input[type="color"] {
      width: 32px;
      height: 28px;
      padding: 0;
      border: 1px solid var(--divider-color, #ccc);
      border-radius: 4px;
      cursor: pointer;
      background: none;
    }
    .color-rgb565 {
      font-size: 0.75em;
      color: var(--secondary-text-color, #666);
      min-width: 44px;
      text-align: right;
      font-family: monospace;
    }
  `];

  constructor() {
    super();
    this.open = false;
    this.overrides = {};
    this._colors = {};
    this._loading = false;
  }

  willUpdate(changed) {
    if ((changed.has("open") && this.open) || changed.has("overrides")) {
      if (!_colorDefaults) {
        this._loading = true;
        ensureColorDefaults(this.hass).then(() => {
          this._loading = false;
          this._rebuildColors();
          this.requestUpdate();
        });
        this._colors = {};
      } else {
        this._rebuildColors();
      }
    }
  }

  _rebuildColors() {
    if (!_colorDefaults) {
      this._colors = {};
      return;
    }
    const cols = {};
    for (const [k, v] of Object.entries(_colorDefaults)) {
      cols[k] = this.overrides?.[k] ?? v;
    }
    this._colors = cols;
  }

  _getHex(key) {
    const v = this._colors[key];
    return v !== undefined ? rgb565ToHex(v) : "#000000";
  }

  _onColorChange(key, e) {
    const hex = e.target.value;
    const rgb565 = hexToRgb565(hex);
    this._colors = { ...this._colors, [key]: rgb565 };
    this.requestUpdate();
  }

  _resetColor(key) {
    this._colors = { ...this._colors, [key]: _colorDefaults[key] };
    this.requestUpdate();
  }

  _resetAll() {
    const cols = {};
    for (const [k, v] of Object.entries(_colorDefaults)) {
      cols[k] = v;
    }
    this._colors = cols;
    this.requestUpdate();
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchSave() {
    // Only include values that differ from defaults
    const overrides = {};
    for (const [k, v] of Object.entries(this._colors)) {
      if (v !== _colorDefaults[k]) {
        overrides[k] = v;
      }
    }
    this.dispatchEvent(
      new CustomEvent("dialog-save", { detail: { overrides } })
    );
  }

  render() {
    if (!this.hass) return "";
    if (this._loading || !_colorDefaults) {
      return html`
        <ha-dialog
          .open=${this.open}
          @closed=${this._dispatchClose}
          header-title="Device Colors"
        >
          <div class="dialog-body" style="padding: 32px; text-align: center;">
            Loading default colors…
          </div>
        </ha-dialog>
      `;
    }

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title="Device Colors"
        .preventScrimClose=${true}
      >
        <div class="dialog-body">
          <p class="config-section-intro">
            Customize the display color palette for this device. Changes are
            sent to the device on the next panel render. Only colors that
            differ from defaults are saved.
          </p>

          ${COLOR_GROUPS.map((group) => html`
            <details class="config-section">
              <summary>${group.name} (${group.keys.length})</summary>
              <div class="config-section-body">
                <div class="color-grid">
                  ${group.keys.map((key) => html`
                    <div class="color-item">
                      <div
                        class="color-swatch"
                        style="background:${this._getHex(key)}"
                      ></div>
                      <span class="color-label" title="${key}">${LABELS[key] || key}</span>
                      <div class="color-input-wrap">
                        <input
                          type="color"
                          .value=${this._getHex(key)}
                          @input=${(e) => this._onColorChange(key, e)}
                          title="${key}"
                        />
                        <span class="color-rgb565">${this._colors[key]}</span>
                        <ha-icon-button
                          title="Reset to default"
                          @click=${() => this._resetColor(key)}
                          style="--mdc-icon-button-size:24px;--mdc-icon-size:14px;"
                        >
                          <ha-icon icon="mdi:undo-variant"></ha-icon>
                        </ha-icon-button>
                      </div>
                    </div>
                  `)}
                </div>
              </div>
            </details>
          `)}
        </div>

        <div slot="footer" class="footer-wrapper">
          <div class="footer-toggle-wrapper">
            <ha-button
              variant="neutral"
              appearance="plain"
              @click=${this._resetAll}
            >
              Reset all
            </ha-button>
          </div>
          <ha-dialog-footer>
            <ha-button
              slot="secondaryAction"
              variant="neutral"
              appearance="plain"
              @click=${this._dispatchClose}
            >
              Cancel
            </ha-button>
            <ha-button
              slot="primaryAction"
              variant="brand"
              @click=${this._dispatchSave}
            >
              Save
            </ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }
}

customElements.define("ha-dialog-colors", ColorsDialog);
export { ColorsDialog };
