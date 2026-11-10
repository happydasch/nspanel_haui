/**
 * NSPanel HAUI - Colors dialog.
 *
 * Lets users override the global color palette for a device. A live preview
 * at the top mirrors how the colors look on the panel (header, content text,
 * component buttons, entity dots) and updates as colors are picked. Below it,
 * all colors are shown at once, grouped by role (Header, Content, Component,
 * Entity). Groups are collapsible — click a group title to collapse/expand it.
 * Domain colors (weather/alarm/climate) are fixed constants and not shown here.
 *
 * Communicates changes via CustomEvent:
 *   @dialog-save — detail: { overrides: { key: rgb565_int, ... }, scheme: "dark" | "light" }
 *   @dialog-closed
 */
import { html, nothing } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { rgb565ToHex, hexToRgb565 } from '../color-utils.js';
import { t } from '../localize.js';

/* ── shared scheme data from the backend ───────────────────────────────── */

let _colorDefaults = null;

async function ensureColorDefaults(api) {
  if (_colorDefaults) return;
  _colorDefaults = await api.editor.colorDefaults();
}

export function getColorScheme(schemeId, schemes) {
  const scheme = schemes?.[schemeId];
  if (!scheme) throw new Error(`Unknown color scheme: ${schemeId}`);
  return scheme.colors;
}

const BUILTIN_SCHEME_LABELS = {
  dark: t("Dark Color"),
  light: t("Light Color"),
  white: t("White"),
  black: t("Black"),
};


/* Groups: [key, friendly label]. All swatches use the same rounded-rectangle shape. */
function getColorGroups() {
  return [
    {
      name: t("Header"),
      description: t("Colors for the top bar: background, title text, and accent icons."),
      keys: [
        ["header_background", t("Background")],
        ["header_text", t("Text")],
        ["header_accent", t("Accent")],
      ],
    },
    {
      name: t("Content"),
      description: t("Colors for the main page area: background and text at various states."),
      keys: [
        ["background", t("Background")],
        ["text", t("Text")],
        ["text_inactive", t("Text (inactive)")],
        ["text_disabled", t("Text (disabled)")],
      ],
    },
    {
      name: t("Component"),
      description: t("Colors for interactive buttons and controls."),
      keys: [
        ["component_background", t("Background")],
        ["component_text", t("Text")],
        ["component_active", t("Active")],
        ["component_active_dark", t("Active (dark)")],
        ["component_accent", t("Accent")],
        ["component_pressed", t("Pressed")],
      ],
    },
    {
      name: t("Entity"),
      description: t("Colors for entity state indicators (on, off, unavailable)."),
      keys: [
        ["entity_on", t("On")],
        ["entity_off", t("Off")],
        ["entity_unavailable", t("Unavailable")],
      ],
    },
  ];
}

function getIconColorGroups(icons, variant) {
  const labels = {
    default: t("Default"), clear_night: t("Clear night"), sunny: t("Sunny"),
    partlycloudy: t("Partly cloudy"), windy: t("Windy"), windy_variant: t("Windy variant"),
    rainy: t("Rainy"), pouring: t("Pouring"), lightning: t("Lightning"),
    lightning_rainy: t("Lightning rainy"), hail: t("Hail"), snowy: t("Snowy"),
    snowy_rainy: t("Snowy rainy"), armed: t("Armed"), disarmed: t("Disarmed"),
    arming: t("Arming"), auto: t("Auto"), heat_cool: t("Heat/cool"),
    heat: t("Heat"), off: t("Off"), cool: t("Cool"), dry: t("Dry"), fan_only: t("Fan only"),
  };
  const domains = {
    weather: [t("Weather"), t("Colors for weather state icons.")],
    alarm: [t("Alarm"), t("Colors for alarm state icons.")],
    climate: [t("Climate"), t("Colors for climate state icons.")],
  };
  return Object.entries(domains).map(([domain, [name, description]]) => ({
    name,
    description,
    keys: Object.keys(icons?.[variant]?.[domain] || {}).map((state) => [
      `icons.${domain}.${state}`,
      labels[state] || state,
    ]),
  }));
}

/* ── dialog component ────────────────────────────────────────────────── */

class ColorsDialog extends HauiDialog {
  static get properties() {
    return {
      overrides: { type: Object },
      scheme: { type: String },
      schemeId: { type: String },
      iconVariant: { type: String },
      entryId: { type: String },
      panels: { type: Array },
      api: { type: Object },
    };
  }

  constructor() {
    super();
    this.overrides = {};
    this.scheme = "dark";
    this.schemeId = "dark";
    this.entryId = "";
    this.panels = [];
    this.iconVariant = "dark";
    this._colors = {};
    this._icons = {};
    this._schemes = {};
    this._builtins = {};
    this._customSchemes = {};
    this._loading = false;
    this._resetOverrides = false;
    this._schemeName = "";
    this._nameAction = "";
    this._schemeError = "";
    this._schemeNotice = "";
    this._autoSchemeId = "";
    this._keepSchemeColors = false;
    this._edited = false;
  }

  willUpdate(changed) {
    if ((changed.has("open") && this.open) || changed.has("entryId")) {
      this._loading = true;
      this._loadSchemes();
      this._resetOverrides = false;
      this._edited = false;
    } else if (changed.has("schemeId") && this._keepSchemeColors) {
      // _customizeScheme() keeps the palette being edited; rebuilding would drop the change.
      this._keepSchemeColors = false;
    } else if (changed.has("overrides") || changed.has("schemeId")) {
      this._rebuildColors();
    }
  }

  async _loadSchemes() {
    this._autoSchemeId = "";
    this._schemeNotice = "";
    this._keepSchemeColors = false;
    try {
      await ensureColorDefaults(this.api);
      const data = await this.api.editor.colorSchemes(this.entryId);
      this._builtins = data.builtins || {};
      this._customSchemes = data.schemes || {};
      this._schemes = { ...this._builtins, ...this._customSchemes };
      if (!this._schemes[this.schemeId]) this.schemeId = "dark";
      this.iconVariant = this.scheme === "light" ? "light" : "dark";
      this._rebuildColors();
    } catch (_err) {
      this._schemeError = t("Unable to load color schemes.");
    } finally {
      this._loading = false;
      this.requestUpdate();
    }
  }

  updated(changed) {
    if (changed.has("open") && this.open) {
      this.renderRoot.querySelectorAll("details.config-section").forEach((d) => {
        d.removeAttribute("open");
      });
    }
  }

  _schemeData() {
    return this._schemes[this.schemeId] || this._builtins.dark;
  }

  _rebuildColors() {
    const scheme = this._schemeData();
    if (!scheme) return;
    this._colors = { ...scheme.colors };
    this._icons = JSON.parse(JSON.stringify(scheme.icons));
    this._edited = false;
  }

  _selectedScheme() {
    return this.schemeId;
  }

  /**
   * Copy the selected built-in scheme into a new custom scheme so edits can be
   * saved. The copy holds the palette before the change; the change itself is
   * then tracked as a modification.
   */
  _customizeScheme() {
    if (!this._isBuiltin()) return;
    const label = this._schemeData().name;
    const names = new Set(Object.values(this._schemes).map((scheme) => scheme.name.toLowerCase()));
    let name = `${label} (custom)`;
    for (let suffix = 2; names.has(name.toLowerCase()); suffix += 1) {
      name = `${label} (custom ${suffix})`;
    }
    let id = `${this.schemeId}-custom`;
    for (let suffix = 2; this._schemes[id]; suffix += 1) {
      id = `${this.schemeId}-custom-${suffix}`;
    }
    const scheme = {
      name,
      colors: { ...this._colors },
      icons: JSON.parse(JSON.stringify(this._icons)),
    };
    this._schemes = { ...this._schemes, [id]: scheme };
    this._keepSchemeColors = true;
    this.schemeId = id;
    this._autoSchemeId = id;
    this._schemeNotice = t('Created the custom scheme "{name}" from the selected built-in scheme.').replace("{name}", name);
  }

  _applyScheme(schemeId) {
    if (!this._schemes[schemeId]) return;
    this._keepSchemeColors = false;
    if (this._autoSchemeId && this._autoSchemeId !== schemeId) {
      const schemes = { ...this._schemes };
      delete schemes[this._autoSchemeId];
      this._schemes = schemes;
      this._autoSchemeId = "";
      this._schemeNotice = "";
    }
    this.schemeId = schemeId;
    this._schemeError = "";
    this._rebuildColors();
    this.requestUpdate();
  }

  _legacyOverrideCount() {
    const fields = new Set([
      "text_color", "back_color", "color_pressed", "back_color_pressed", "power_color",
      "keypad_bg_color", "keypad_text_color", "arm_button_color", "arm_button_back_color",
      "disarm_button_color", "disarm_button_back_color", "off_color", "letter_color", "special_color",
    ]);
    let count = Object.keys(this.overrides || {}).length;
    const visit = (value) => {
      if (Array.isArray(value)) {
        value.forEach(visit);
      } else if (value && typeof value === "object") {
        for (const [key, child] of Object.entries(value)) {
          if (fields.has(key)) count++;
          else visit(child);
        }
      }
    };
    visit(this.panels);
    return count;
  }

  _isBuiltin() {
    return Object.hasOwn(this._builtins, this.schemeId);
  }

  _getHex(key) {
    const [, domain, state] = key.split(".");
    const value = key.startsWith("icons.")
      ? this._icons?.[this.iconVariant]?.[domain]?.[state]
      : this._colors[key];
    return value !== undefined ? rgb565ToHex(value) : "#000000";
  }

  _isModified(key) {
    const scheme = this._schemeData();
    const [, domain, state] = key.split(".");
    const value = key.startsWith("icons.")
      ? this._icons?.[this.iconVariant]?.[domain]?.[state]
      : this._colors[key];
    const original = key.startsWith("icons.")
      ? scheme?.icons?.[this.iconVariant]?.[domain]?.[state]
      : scheme?.colors?.[key];
    return value !== original;
  }

  _changedCount() {
    let count = 0;
    for (const key of Object.keys(this._colors)) if (this._isModified(key)) count++;
    for (const variant of ["dark", "light"]) {
      for (const [domain, states] of Object.entries(this._icons[variant] || {})) {
        for (const state of Object.keys(states)) {
          if (this._icons[variant][domain][state] !== this._schemeData().icons[variant][domain][state]) count++;
        }
      }
    }
    return count;
  }

  _onColorChange(key, e) {
    this._customizeScheme();
    const value = hexToRgb565(e.target.value);
    if (key.startsWith("icons.")) {
      const [, domain, state] = key.split(".");
      this._icons = {
        ...this._icons,
        [this.iconVariant]: {
          ...this._icons[this.iconVariant],
          [domain]: { ...this._icons[this.iconVariant][domain], [state]: value },
        },
      };
    } else {
      this._colors = { ...this._colors, [key]: value };
    }
    this._edited = true;
    this.requestUpdate();
  }

  _resetColor(key) {
    const scheme = this._schemeData();
    if (key.startsWith("icons.")) {
      const [, domain, state] = key.split(".");
      this._icons = {
        ...this._icons,
        [this.iconVariant]: {
          ...this._icons[this.iconVariant],
          [domain]: {
            ...this._icons[this.iconVariant][domain],
            [state]: scheme.icons[this.iconVariant][domain][state],
          },
        },
      };
    } else {
      this._colors = { ...this._colors, [key]: scheme.colors[key] };
    }
    this._edited = true;
    this._edited = true;
    this.requestUpdate();
  }

  _resetAll() {
    const scheme = this._schemeData();
    this._colors = { ...scheme.colors };
    this._icons = JSON.parse(JSON.stringify(scheme.icons));
    this._resetOverrides = true;
    this._edited = true;
    this.requestUpdate();
  }

  async _persistSchemes(schemes) {
    try {
      const data = await this.api.editor.saveColorSchemes(this.entryId, { version: 1, schemes });
      this._customSchemes = data.schemes || {};
      this._schemes = { ...this._builtins, ...this._customSchemes };
      this._schemeError = "";
      this._autoSchemeId = "";
      this._schemeNotice = "";
      if (!this._schemes[this.schemeId]) {
        this.schemeId = "dark";
        this._rebuildColors();
      }
      this.requestUpdate();
      return true;
    } catch (_err) {
      this._schemeError = t("Unable to save color schemes. Check for duplicate names or schemes in use.");
      this.requestUpdate();
      return false;
    }
  }

  _startNameAction(action) {
    this._nameAction = action;
    this._schemeName = action === "rename" ? this._schemeData().name : "";
    this._schemeError = "";
  }

  async _saveNamedScheme() {
    const name = this._schemeName.trim();
    if (!name || name.length > 64) {
      this._schemeError = t("Enter a name up to 64 characters.");
      this.requestUpdate();
      return;
    }
    const schemes = { ...this._customSchemes };
    let id = this.schemeId;
    if (this._nameAction === "save-as") {
      id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      if (!id || this._schemes[id] || Object.values(this._schemes).some((s) => s.name.toLowerCase() === name.toLowerCase())) {
        this._schemeError = t("A color scheme with this name already exists.");
        this.requestUpdate();
        return;
      }
    }
    schemes[id] = {
      name,
      colors: { ...this._colors },
      icons: JSON.parse(JSON.stringify(this._icons)),
    };
    if (await this._persistSchemes(schemes)) {
      this.schemeId = id;
      this._edited = false;
      this._nameAction = "";
      this.requestUpdate();
    }
  }

  async _deleteScheme() {
    const schemes = { ...this._customSchemes };
    delete schemes[this.schemeId];
    if (await this._persistSchemes(schemes)) {
      this.schemeId = "dark";
      this._rebuildColors();
    }
  }

  _exportSchemes() {
    const blob = new Blob([JSON.stringify({ version: 1, schemes: this._customSchemes }, null, 2)], {
      type: "application/json",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "nspanel-haui-color-schemes.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async _importSchemes(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = JSON.parse(await file.text());
      if (imported.version !== 1 || !imported.schemes || typeof imported.schemes !== "object") {
        throw new Error("invalid scheme file");
      }
      const existingNames = new Set(Object.values(this._schemes).map((scheme) => scheme.name.toLowerCase()));
      for (const [id, scheme] of Object.entries(imported.schemes)) {
        if (this._schemes[id] || existingNames.has(String(scheme.name).toLowerCase())) {
          this._schemeError = t("Import has a color scheme name or ID that already exists.");
          this.requestUpdate();
          return;
        }
        existingNames.add(String(scheme.name).toLowerCase());
      }
      await this._persistSchemes({ ...this._customSchemes, ...imported.schemes });
    } catch (_err) {
      this._schemeError = t("Invalid color scheme file.");
      this.requestUpdate();
    }
  }

  async _dispatchSave() {
    if (!this._isBuiltin() && this._edited) {
      const schemes = {
        ...this._customSchemes,
        [this.schemeId]: {
          name: this._schemeData().name,
          colors: { ...this._colors },
          icons: JSON.parse(JSON.stringify(this._icons)),
        },
      };
      if (!(await this._persistSchemes(schemes))) return;
      this._edited = false;
    }
    this._emit("dialog-save", {
      schemeId: this.schemeId,
      resetOverrides: this._resetOverrides,
      scheme: this.scheme,
    });
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
            <span class="cp-pv-title">${t("Living Room")}</span>
            <span class="cp-pv-hicons">
              <ha-icon icon="mdi:home" style="color:${c("header_text")}"></ha-icon>
              <ha-icon icon="mdi:bell" style="color:${c("header_accent")}"></ha-icon>
            </span>
          </div>
          <div class="cp-pv-body">
            <div class="cp-pv-texts">
              <span style="color:${c("text")}">${t("Text")}</span>
              <span style="color:${c("text_inactive")}">${t("Inactive")}</span>
              <span style="color:${c("text_disabled")}">${t("Disabled")}</span>
            </div>
            <div class="cp-pv-comps">
              <span
                class="cp-pv-btn"
                style="background:${c("component_background")};color:${c("component_text")}"
              >${t("Component")}</span>
              <span
                class="cp-pv-btn"
                style="background:${c("component_pressed")};color:${c("component_text")}"
              >${t("Pressed")}</span>
              <span
                class="cp-pv-btn"
                style="background:${c("component_active")};color:${c("component_text")}"
              >${t("Active")}</span>
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
              <span class="cp-pv-ent"><i style="background:${c("entity_on")}"></i>${t("On")}</span>
              <span class="cp-pv-ent"><i style="background:${c("entity_off")}"></i>${t("Off")}</span>
              <span class="cp-pv-ent"><i style="background:${c("entity_unavailable")}"></i>${t("Unavailable")}</span>
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
                          title="${t("Reset to default")}"
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
    const loading = this._loading || !_colorDefaults;
    const changed = loading ? 0 : this._changedCount();
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title=${loading ? t("Device Colors") : nothing}
      >
        ${loading
          ? html`<div class="dialog-body" style="padding: 32px; text-align: center;">
              ${t("Loading default colors...")}
            </div>`
          : html`
        ${dialogHeader(t("Device Colors"), this._dispatchClose, this._renderPreview())}
        <div class="dialog-body">
          <p class="config-section-intro" style="margin: 0 0 4px;">
            ${t("A color scheme defines shared page, entity, weather, alarm, and climate colors.")}
          </p>
          <div class="cp-scheme">
            <label for="cp-scheme">${t("Color scheme")}</label>
            <select
              id="cp-scheme"
              class="native-select"
              .value=${this._selectedScheme()}
              @change=${(e) => this._applyScheme(e.target.value)}
            >
              ${Object.entries(this._schemes).map(([id, scheme]) => html`
                <option value=${id} ?selected=${id === this._selectedScheme()}>${BUILTIN_SCHEME_LABELS[id] || scheme.name}</option>
              `)}
            </select>
          </div>
          <div class="cp-scheme">
            <label for="cp-icon-scheme">${t("Default icon color variant")}</label>
            <select
              id="cp-icon-scheme"
              class="native-select"
              .value=${this.scheme}
              @change=${(e) => { this.scheme = e.target.value; this.requestUpdate(); }}
            >
              <option value="dark">${t("Dark background")}</option>
              <option value="light">${t("Light background")}</option>
            </select>
          </div>
          <div class="cp-scheme">
            <label for="cp-icon-variant">${t("Edit icon colors for")}</label>
            <select
              id="cp-icon-variant"
              class="native-select"
              .value=${this.iconVariant}
              @change=${(e) => { this.iconVariant = e.target.value; this.requestUpdate(); }}
            >
              <option value="dark">${t("Dark backgrounds")}</option>
              <option value="light">${t("Light backgrounds")}</option>
            </select>
          </div>
          ${this._schemeNotice ? html`<p class="config-section-intro" role="status">${this._schemeNotice}</p>` : nothing}
          ${this._isBuiltin()
            ? html`<p class="config-section-intro">${t("Built-in schemes cannot be edited. Changing a color creates a custom scheme.")}</p>`
            : nothing}
          <div class="cp-scheme-actions">
            <ha-button variant="neutral" appearance="plain" @click=${() => this._startNameAction("save-as")}>${t("Save as")}</ha-button>
            ${!this._isBuiltin()
              ? html`
                  <ha-button variant="neutral" appearance="plain" @click=${() => this._startNameAction("rename")}>${t("Rename")}</ha-button>
                  <ha-button variant="neutral" appearance="plain" @click=${this._deleteScheme}>${t("Delete")}</ha-button>
                `
              : nothing}
            <ha-button variant="neutral" appearance="plain" @click=${this._exportSchemes}>${t("Export")}</ha-button>
            <label class="cp-import-label">
              <span>${t("Import")}</span>
              <input type="file" accept="application/json,.json" @change=${this._importSchemes} />
            </label>
          </div>
          ${this._nameAction
            ? html`
                <div class="cp-scheme-name">
                  <input
                    type="text"
                    maxlength="64"
                    .value=${this._schemeName}
                    @input=${(e) => { this._schemeName = e.target.value; }}
                    aria-label=${t("Color scheme name")}
                  />
                  <ha-button variant="brand" @click=${this._saveNamedScheme}>${t("Save")}</ha-button>
                  <ha-button variant="neutral" appearance="plain" @click=${() => { this._nameAction = ""; }}>${t("Cancel")}</ha-button>
                </div>
              `
            : nothing}
          ${this._schemeError ? html`<p class="cp-scheme-error" role="alert">${this._schemeError}</p>` : nothing}
          ${this._legacyOverrideCount() > 0
            ? html`
                <p class="config-section-intro">
                  ${t("Existing device or panel color overrides still take precedence until they are reset.")}
                </p>
                <label class="cp-reset-overrides">
                  <input
                    type="checkbox"
                    .checked=${this._resetOverrides}
                    @change=${(e) => { this._resetOverrides = e.target.checked; }}
                  />
                  ${t("Reset existing device and panel color overrides when applying this scheme")}
                </label>
              `
            : nothing}
          ${getColorGroups().map((group, idx) => this._renderGroup(group, idx))}
          ${getIconColorGroups(this._icons, this.iconVariant).map((group, idx) => this._renderGroup(group, idx))}
        </div>

        <div slot="footer" class="footer-wrapper">
          <div class="footer-toggle-wrapper">
            <ha-button
              variant="neutral"
              appearance="plain"
              .disabled=${changed === 0 && this._legacyOverrideCount() === 0}
              @click=${this._resetAll}
            >
              ${t("Reset device overrides")}
            </ha-button>
            ${changed > 0
              ? html`<span class="footer-changed">${t("{count} changed").replace("{count}", changed)}</span>`
              : nothing}
          </div>
          <ha-dialog-footer>
            <ha-button
              slot="secondaryAction"
              variant="neutral"
              appearance="plain"
              @click=${this._dispatchClose}
            >
              ${t("Cancel")}
            </ha-button>
            <ha-button
              slot="primaryAction"
              variant="brand"
              .disabled=${!this._schemeData()}
              @click=${this._dispatchSave}
            >
              ${this._resetOverrides
                ? t("Apply scheme and reset custom colors")
                : t("Apply scheme")}
            </ha-button>
          </ha-dialog-footer>
        </div>
        `}
      </ha-dialog>
    `;
  }
}

customElements.define("nspanel-dialog-colors", ColorsDialog);
export { ColorsDialog };
