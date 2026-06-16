/**
 * NSPanel HAUI - Editor - Colors dialog.
 *
 * Lets users override the global color palette for a device. A live preview
 * at the top mirrors how the colors look on the panel (header, content text,
 * component buttons, entity dots) and updates as colors are picked. Below it,
 * all colors are shown at once, grouped by role (Header, Content, Component,
 * Entity). Groups are collapsible — click a group title to collapse/expand it.
 * Domain colors (weather/alarm/climate) are fixed constants and not shown here.
 *
 * Communicates changes via CustomEvent:
 *   @dialog-save — detail: { overrides: { key: rgb565_int, ... } }
 *   @dialog-closed
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { dialogHeader } from './dialog-header.js';
import { rgb565ToHex, hexToRgb565 } from '../color-utils.js';

/* ── built-in COLORS palette (fetched from haui/mapping/color.py) ──────── */

/** Cached default color values, fetched once from the backend API. */
let _colorDefaults = null;

async function ensureColorDefaults(hass) {
  if (_colorDefaults) return;
  const resp = await hass.fetchWithAuth("/api/nspanel_haui/color_defaults");
  _colorDefaults = await resp.json();
}

/* Groups: [key, friendly label]. All swatches use the same rounded-rectangle shape. */
const COLOR_GROUPS = [
  {
    name: "Header",
    description: "Colors for the top bar: background, title text, and accent icons.",
    keys: [
      ["header_background", "Background"],
      ["header_text", "Text"],
      ["header_accent", "Accent"],
    ],
  },
  {
    name: "Content",
    description: "Colors for the main page area: background and text at various states.",
    keys: [
      ["background", "Background"],
      ["text", "Text"],
      ["text_inactive", "Text (inactive)"],
      ["text_disabled", "Text (disabled)"],
    ],
  },
  {
    name: "Component",
    description: "Colors for interactive buttons and controls.",
    keys: [
      ["component_background", "Background"],
      ["component_text", "Text"],
      ["component_active", "Active"],
      ["component_active_dark", "Active (dark)"],
      ["component_accent", "Accent"],
      ["component_pressed", "Pressed"],
    ],
  },
  {
    name: "Entity",
    description: "Colors for entity state indicators (on, off, unavailable).",
    keys: [
      ["entity_on", "On"],
      ["entity_off", "Off"],
      ["entity_unavailable", "Unavailable"],
    ],
  },
];

/* ── dialog component ────────────────────────────────────────────────── */

class ColorsDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      overrides: { type: Object },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

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

  updated(changed) {
    if (changed.has("open") && this.open) {
      // Close all sections — don't remember open state between dialog sessions.
      this.renderRoot.querySelectorAll("details.config-section").forEach((d) => {
        d.removeAttribute("open");
      });
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

  _isModified(key) {
    return _colorDefaults && this._colors[key] !== _colorDefaults[key];
  }

  _changedCount() {
    if (!_colorDefaults) return 0;
    let n = 0;
    for (const [k, v] of Object.entries(this._colors)) {
      if (v !== _colorDefaults[k]) n++;
    }
    return n;
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

  _renderPreview() {
    const c = (k) => this._getHex(k);
    return html`
      <div class="cp-preview">
        <div class="cp-pv-card" style="background:${c("background")}">
          <div
            class="cp-pv-header"
            style="background:${c("header_background")};color:${c("header_text")}"
          >
            <span class="cp-pv-title">Living Room</span>
            <span class="cp-pv-hicons">
              <ha-icon icon="mdi:home" style="color:${c("header_text")}"></ha-icon>
              <ha-icon icon="mdi:bell" style="color:${c("header_accent")}"></ha-icon>
            </span>
          </div>
          <div class="cp-pv-body">
            <div class="cp-pv-texts">
              <span style="color:${c("text")}">Text</span>
              <span style="color:${c("text_inactive")}">Inactive</span>
              <span style="color:${c("text_disabled")}">Disabled</span>
            </div>
            <div class="cp-pv-comps">
              <span
                class="cp-pv-btn"
                style="background:${c("component_background")};color:${c("component_text")}"
              >Component</span>
              <span
                class="cp-pv-btn"
                style="background:${c("component_pressed")};color:${c("component_text")}"
              >Pressed</span>
              <span
                class="cp-pv-btn"
                style="background:${c("component_active")};color:${c("component_text")}"
              >Active</span>
              <div
                class="cp-pv-slider"
                style="background:${c("component_active")}"
              >
                <span
                  class="cp-pv-slider-hdl"
                  style="background:${c("component_active_dark")};border-color:${c("component_active_dark")}"
                ></span>
              </div>
              <ha-icon
                class="cp-pv-accent"
                icon="mdi:star"
                style="color:${c("component_accent")}"
              ></ha-icon>
            </div>
            <div class="cp-pv-entities" style="color:${c("text")}">
              <span class="cp-pv-ent"><i style="background:${c("entity_on")}"></i>On</span>
              <span class="cp-pv-ent"><i style="background:${c("entity_off")}"></i>Off</span>
              <span class="cp-pv-ent"><i style="background:${c("entity_unavailable")}"></i>Unavailable</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderGroup(group, idx) {
    return html`
      <details class="config-section">
        <summary>${group.name}</summary>
        <div class="config-section-body">
          ${group.description
            ? html`<p class="config-section-intro">${group.description}</p>`
            : ""}
          <div class="cp-items">
            ${group.keys.map(([key, label]) => {
              const mod = this._isModified(key);
              return html`
                <div class="cp-item ${mod ? "is-mod" : ""}">
                  <label
                    class="cp-sw"
                    style="background:${this._getHex(key)}"
                    title="${label} — ${this._getHex(key)}"
                  >
                    <input
                      type="color"
                      .value=${this._getHex(key)}
                      @input=${(e) => this._onColorChange(key, e)}
                    />
                  </label>
                  <span class="cp-name">${label}</span>
                  ${mod
                    ? html`
                        <ha-icon-button
                          class="cp-reset"
                          title="Reset to default"
                          @click=${() => this._resetColor(key)}
                        >
                          <ha-icon icon="mdi:undo-variant"></ha-icon>
                        </ha-icon-button>
                      `
                    : nothing}
                </div>
              `;
            })}
          </div>
        </div>
      </details>
    `;
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

    const changed = this._changedCount();
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        .preventScrimClose=${true}
      >
        ${dialogHeader("Device Colors", this._dispatchClose, this._renderPreview())}
        <div class="dialog-body">
          <p class="config-section-intro" style="margin: 0 0 4px;">
            Tap a swatch to change a color — the preview above updates live.
            Only changed colors are saved.
          </p>
          ${COLOR_GROUPS.map((group, idx) => this._renderGroup(group, idx))}
        </div>

        <div slot="footer" class="footer-wrapper">
          <div class="footer-toggle-wrapper">
            <ha-button
              variant="neutral"
              appearance="plain"
              .disabled=${changed === 0}
              @click=${this._resetAll}
            >
              Reset all
            </ha-button>
            ${changed > 0
              ? html`<span class="footer-changed">${changed} changed</span>`
              : nothing}
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
