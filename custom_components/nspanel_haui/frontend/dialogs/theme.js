/*
 * Theme sidebar body. The shell supplies the sidebar frame and its title;
 * this component edits the shared theme library and this device's selection.
 */
import { html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { rgb565ToHex, hexToRgb565 } from '../color-utils.js';
import { t } from '../localize.js';
import { renderSelect } from '../form-fields.js';
import { sidebarFooterStyles } from '../styles/sidebar-footer.js';
import { themeSelectorStyles } from '../styles/theme-selector-styles.js';
import { themeSidebarStyles } from '../styles/theme-sidebar-styles.js';
import { themeSelector } from '../ui/theme-selector.js';
import { emptyState } from '../ui/empty-state.js';
import {
  builtinThemeLabel,
  downloadThemes,
  parseThemeFile,
  themeIdFromName,
  uniqueThemeId,
  uniqueThemeName,
} from '../theme-library.js';

/* ── shared theme data from the backend ───────────────────────────────── */

let _themeDefaults = null;

async function ensureColorDefaults(api) {
  if (_themeDefaults) return;
  _themeDefaults = await api.editor.colorDefaults();
}

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

class ThemeSidebar extends HauiDialog {
  static styles = [
    ...HauiDialog.styles,
    sidebarFooterStyles,
    themeSelectorStyles,
    themeSidebarStyles,
  ];

  static get properties() {
    return {
      themeVariant: { type: String },
      themeId: { type: String },
      iconVariant: { type: String },
      entryId: { type: String },
      api: { type: Object },
    };
  }

  constructor() {
    super();
    this.themeVariant = "dark";
    this.themeId = "dark";
    this.entryId = "";
    this.iconVariant = "dark";
    this._colors = {};
    this._icons = {};
    this._themes = {};
    this._builtins = {};
    this._customThemes = {};
    this._loading = false;
    this._themeName = "";
    this._nameAction = "";
    this._themeError = "";
    this._themeNotice = "";
    this._autoThemeId = "";
    this._keepThemeColors = false;
    this._edited = false;
  }

  willUpdate(changed) {
    if ((changed.has("open") && this.open) || changed.has("entryId")) {
      this._loading = true;
      this._originalThemeId = this.themeId;
      this._originalThemeVariant = this.themeVariant;
      this._loadThemes();
      this._edited = false;
    } else if (changed.has("themeId") && this._keepThemeColors) {
      // _customizeTheme() keeps the palette being edited; rebuilding would drop the change.
      this._keepThemeColors = false;
    } else if (changed.has("themeId")) {
      this._rebuildColors();
    }
  }

  async _loadThemes() {
    this._autoThemeId = "";
    this._themeNotice = "";
    this._keepThemeColors = false;
    try {
      await ensureColorDefaults(this.api);
      const data = await this.api.editor.themes(this.entryId);
      this._builtins = data.builtins || {};
      this._customThemes = data.themes || {};
      this._themes = { ...this._builtins, ...this._customThemes };
      if (!this._themes[this.themeId]) this.themeId = "dark";
      this.iconVariant = this.themeVariant === "light" ? "light" : "dark";
      this._rebuildColors();
    } catch (_err) {
      this._themeError = t("Unable to load color themes.");
    } finally {
      this._loading = false;
      this.requestUpdate();
    }
  }

  updated(changed) {
    if (changed.has("open") && this.open) {
      this.renderRoot.querySelectorAll("details.haui-config-section").forEach((d) => {
        d.removeAttribute("open");
      });
    }
  }

  _themeData() {
    return this._themes[this.themeId] || this._builtins.dark;
  }

  _rebuildColors() {
    const theme = this._themeData();
    if (!theme) return;
    this._colors = { ...theme.colors };
    this._icons = JSON.parse(JSON.stringify(theme.icons));
    this._edited = false;
  }

  /**
   * Copy the selected built-in theme into a new custom theme so edits can be
   * saved. The copy holds the palette before the change; the change itself is
   * then tracked as a modification.
   */
  _customizeTheme() {
    if (!this._isBuiltin()) return;
    const name = uniqueThemeName(this._themes, this._themeData().name);
    const id = uniqueThemeId(this._themes, this.themeId);
    const theme = {
      name,
      colors: { ...this._colors },
      icons: JSON.parse(JSON.stringify(this._icons)),
    };
    this._themes = { ...this._themes, [id]: theme };
    this._keepThemeColors = true;
    this.themeId = id;
    this._autoThemeId = id;
    this._themeNotice = t('Created the custom theme "{name}" from the selected built-in theme.').replace("{name}", name);
  }

  _applyTheme(themeId) {
    if (!this._themes[themeId]) return;
    this._keepThemeColors = false;
    if (this._autoThemeId && this._autoThemeId !== themeId) {
      const themes = { ...this._themes };
      delete themes[this._autoThemeId];
      this._themes = themes;
      this._autoThemeId = "";
      this._themeNotice = "";
    }
    this.themeId = themeId;
    this._themeError = "";
    this._rebuildColors();
    this.requestUpdate();
  }

  _isBuiltin() {
    return Object.hasOwn(this._builtins, this.themeId);
  }

  _getHex(key) {
    const [, domain, state] = key.split(".");
    const value = key.startsWith("icons.")
      ? this._icons?.[this.iconVariant]?.[domain]?.[state]
      : this._colors[key];
    return value !== undefined ? rgb565ToHex(value) : "#000000";
  }

  _getDisplayHex(key) {
    return this._getHex(key);
  }

  _isModified(key) {
    const theme = this._themeData();
    const [, domain, state] = key.split(".");
    const value = key.startsWith("icons.")
      ? this._icons?.[this.iconVariant]?.[domain]?.[state]
      : this._colors[key];
    const original = key.startsWith("icons.")
      ? theme?.icons?.[this.iconVariant]?.[domain]?.[state]
      : theme?.colors?.[key];
    return value !== original;
  }

  _changedCount() {
    let count = 0;
    for (const key of Object.keys(this._colors)) if (this._isModified(key)) count++;
    const themes = this._themeData();
    for (const variant of ["dark", "light"]) {
      for (const [domain, states] of Object.entries(this._icons[variant] || {})) {
        for (const state of Object.keys(states)) {
          if (this._icons[variant][domain][state] !== themes.icons?.[variant]?.[domain]?.[state]) count++;
        }
      }
    }
    if (this.themeId !== this._originalThemeId) count++;
    if (this.themeVariant !== this._originalThemeVariant) count++;
    return count;
  }

  _onColorChange(key, e) {
    const value = hexToRgb565(e.target.value);
    this._customizeTheme();
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
    const theme = this._themeData();
    if (key.startsWith("icons.")) {
      const [, domain, state] = key.split(".");
      this._icons = {
        ...this._icons,
        [this.iconVariant]: {
          ...this._icons[this.iconVariant],
          [domain]: {
            ...this._icons[this.iconVariant][domain],
            [state]: theme.icons[this.iconVariant][domain][state],
          },
        },
      };
    } else {
      this._colors = { ...this._colors, [key]: theme.colors[key] };
    }
    this._edited = true;
    this.requestUpdate();
  }

  _resetTheme() {
    const theme = this._themeData();
    this._colors = { ...theme.colors };
    this._icons = JSON.parse(JSON.stringify(theme.icons));
    this._edited = true;
    this.requestUpdate();
  }

  async _persistThemes(themes) {
    try {
      const data = await this.api.editor.saveThemes(this.entryId, { version: 1, themes });
      this._customThemes = data.themes || {};
      this._themes = { ...this._builtins, ...this._customThemes };
      this._themeError = "";
      this._autoThemeId = "";
      this._themeNotice = "";
      if (!this._themes[this.themeId]) {
        this.themeId = "dark";
        this._rebuildColors();
      }
      this.requestUpdate();
      return true;
    } catch (_err) {
      this._themeError = t("Unable to save color themes. Check for duplicate names or themes in use.");
      this.requestUpdate();
      return false;
    }
  }

  _startNameAction(action) {
    this._nameAction = action;
    this._themeName = action === "rename" ? this._themeData().name : "";
    this._themeError = "";
    this.requestUpdate();
  }

  async _saveNamedTheme() {
    const name = this._themeName.trim();
    if (!name || name.length > 64) {
      this._themeError = t("Enter a name up to 64 characters.");
      this.requestUpdate();
      return;
    }
    const themes = { ...this._customThemes };
    let id = this.themeId;
    if (this._nameAction === "save-as") {
      id = themeIdFromName(name);
      if (!id || this._themes[id] || Object.values(this._themes).some((s) => s.name.toLowerCase() === name.toLowerCase())) {
        this._themeError = t("A color theme with this name already exists.");
        this.requestUpdate();
        return;
      }
    }
    themes[id] = {
      name,
      colors: { ...this._colors },
      icons: JSON.parse(JSON.stringify(this._icons)),
    };
    if (await this._persistThemes(themes)) {
      this.themeId = id;
      this._edited = false;
      this._nameAction = "";
      this.requestUpdate();
    }
  }

  async _deleteTheme() {
    const themes = { ...this._customThemes };
    delete themes[this.themeId];
    if (await this._persistThemes(themes)) {
      this.themeId = "dark";
      this._rebuildColors();
    }
  }

  _exportSelectedTheme() {
    const theme = this._themeData();
    downloadThemes({
      [this.themeId]: {
        name: theme.name,
        colors: { ...this._colors },
        icons: JSON.parse(JSON.stringify(this._icons)),
      },
    }, `nspanel-haui-${this.themeId}.json`);
  }

  async _importThemes(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const imported = parseThemeFile(await file.text());
      const existingNames = new Set(Object.values(this._themes).map((theme) => theme.name.toLowerCase()));
      for (const [id, theme] of Object.entries(imported)) {
        if (this._themes[id] || existingNames.has(String(theme.name).toLowerCase())) {
          this._themeError = t("Import has a color theme name or ID that already exists.");
          this.requestUpdate();
          return;
        }
        existingNames.add(String(theme.name).toLowerCase());
      }
      await this._persistThemes({ ...this._customThemes, ...imported });
    } catch (_err) {
      this._themeError = t("Invalid color theme file.");
      this.requestUpdate();
    }
  }

  async _dispatchSave() {
    if (!this._isBuiltin() && this._edited) {
      const themes = {
        ...this._customThemes,
        [this.themeId]: {
          name: this._themeData().name,
          colors: { ...this._colors },
          icons: JSON.parse(JSON.stringify(this._icons)),
        },
      };
      if (!(await this._persistThemes(themes))) return;
      this._edited = false;
    }
    this._emit("dialog-save", {
      themeId: this.themeId,
      themeVariant: this.themeVariant,
    });
  }

  _renderPreview() {
    const c = (k) => this._getDisplayHex(k);
    return html`
      <div class="haui-theme-preview">
        <div class="haui-theme-preview-card" style="--vp-theme-background:${c("background")}">
          <div
            class="haui-theme-preview-header"
            style="--vp-theme-header-background:${c("header_background")};--vp-theme-header-text:${c("header_text")}"
          >
            <span class="haui-theme-preview-title">${t("Living Room")}</span>
            <span class="haui-theme-preview-hicons">
              <ha-icon icon="mdi:home" style="--vp-theme-icon-color:${c("header_text")}"></ha-icon>
              <ha-icon icon="mdi:bell" style="--vp-theme-icon-color:${c("header_accent")}"></ha-icon>
            </span>
          </div>
          <div class="haui-theme-preview-body">
            <div class="haui-theme-preview-texts">
              <span style="--vp-theme-text-color:${c("text")}">${t("Text")}</span>
              <span style="--vp-theme-text-color:${c("text_inactive")}">${t("Inactive")}</span>
              <span style="--vp-theme-text-color:${c("text_disabled")}">${t("Disabled")}</span>
            </div>
            <div class="haui-theme-preview-comps">
              <span
                class="haui-theme-preview-btn"
                style="--vp-theme-component-background:${c("component_background")};--vp-theme-component-text:${c("component_text")}"
              >${t("Component")}</span>
              <span
                class="haui-theme-preview-btn"
                style="--vp-theme-component-background:${c("component_pressed")};--vp-theme-component-text:${c("component_text")}"
              >${t("Pressed")}</span>
              <span
                class="haui-theme-preview-btn"
                style="--vp-theme-component-background:${c("component_active")};--vp-theme-component-text:${c("component_text")}"
              >${t("Active")}</span>
              <div
                class="haui-theme-preview-slider"
                style="--vp-theme-slider-background:${c("component_active")}"
              >
                <span
                  class="haui-theme-preview-slider-hdl"
                  style="--vp-theme-slider-handle:${c("component_active_dark")}"
                ></span>
              </div>
              <ha-icon
                class="haui-theme-preview-accent"
                icon="mdi:star"
                style="--vp-theme-accent:${c("component_accent")}"
              ></ha-icon>
            </div>
            <div class="haui-theme-preview-entities" style="--vp-theme-entity-text:${c("text")}">
              <span class="haui-theme-preview-ent"><i style="--vp-theme-entity-color:${c("entity_on")}"></i>${t("On")}</span>
              <span class="haui-theme-preview-ent"><i style="--vp-theme-entity-color:${c("entity_off")}"></i>${t("Off")}</span>
              <span class="haui-theme-preview-ent"><i style="--vp-theme-entity-color:${c("entity_unavailable")}"></i>${t("Unavailable")}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderGroup(group) {
    return html`
      <section class="haui-theme-color-group">
        <h3>${group.name}</h3>
        ${group.description
          ? html`<p class="haui-config-section-intro">${group.description}</p>`
          : nothing}
        <div class="haui-color-items">
          ${group.keys.map(([key, label]) => {
            const color = this._getHex(key);
            const modified = this._isModified(key);
            return html`
              <div class="haui-color-item ${modified ? "is-mod" : ""}">
                <label
                  class="haui-color-swatch"
                  style="--vp-color-swatch:${color}"
                  title="${label} — ${color}"
                >
                  <input
                    type="color"
                    .value=${color}
                    aria-label=${label}
                    @input=${(e) => this._onColorChange(key, e)}
                  />
                </label>
                <span class="haui-color-name">${label}</span>
                ${modified
                  ? html`
                      <ha-icon-button
                        class="haui-color-reset"
                        title="${t("Revert to theme color")}"
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
      </section>
    `;
  }

  render() {
    if (!this.hass) return "";
    const isLoading = this._loading || !_themeDefaults;
    if (isLoading) {
      return html`<div class="haui-theme-sidebar">
        ${emptyState({ message: t("Loading default colors..."), iconName: null, className: 'haui-empty-state-compact' })}
      </div>`;
    }
    const changed = this._changedCount();
    return html`
      <div class="haui-theme-sidebar">
        ${this._renderPreview()}
        <div class="haui-dialog-body">
          <section class="haui-theme-section" aria-label=${t("Theme")}>
            <p class="haui-config-section-intro">
              ${t("Choose a predefined theme or create a custom theme for this device.")}
            </p>
            ${themeSelector({
              builtins: this._builtins,
              custom: this._customThemes,
              selectedId: this.themeId,
              label: t("Color theme"),
              builtinLabel: builtinThemeLabel,
              onSelect: (id) => this._applyTheme(id),
              actions: this._isBuiltin() ? [] : [
                { label: t("Duplicate"), iconName: "duplicate", onClick: () => this._startNameAction("save-as") },
                { label: t("Rename"), iconName: "edit", onClick: () => this._startNameAction("rename") },
                { label: t("Delete"), iconName: "delete", danger: true, onClick: () => this._deleteTheme() },
              ],
              onNew: () => this._startNameAction("save-as"),
              onExport: () => this._exportSelectedTheme(),
              onImport: (event) => this._importThemes(event),
              notice: this._themeNotice,
              error: this._themeError,
              nameAction: this._nameAction,
              themeName: this._themeName,
              onNameInput: (value) => { this._themeName = value; },
              onSaveName: () => this._saveNamedTheme(),
              onCancelName: () => { this._nameAction = ""; this.requestUpdate(); },
            })}
          </section>

          <details class="haui-config-section">
            <summary>${t("Icon colors")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Colors the display uses for weather, alarm and climate state icons.")}
              </p>
              <div class="haui-field">
                <label for="cp-icon-theme">${t("Default icon color variant")}</label>
                ${renderSelect("cp-icon-theme", this.themeVariant, [
                  { value: "dark", label: t("Dark background") },
                  { value: "light", label: t("Light background") },
                ], (value) => { this.themeVariant = value; })}
              </div>
              <div class="haui-field">
                <label for="cp-icon-variant">${t("Edit icon colors for")}</label>
                ${renderSelect("cp-icon-variant", this.iconVariant, [
                  { value: "dark", label: t("Dark backgrounds") },
                  { value: "light", label: t("Light backgrounds") },
                ], (value) => { this.iconVariant = value; })}
              </div>
              ${getIconColorGroups(this._icons, this.iconVariant).map((group) => this._renderGroup(group, "theme"))}
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Theme colors")}</summary>
            <div class="haui-config-section-body">
              ${this._isBuiltin()
                ? html`<p class="haui-config-section-intro">${t("Built-in themes cannot be edited. Changing a color creates a custom theme.")}</p>`
                : nothing}
              <p class="haui-config-section-intro">
                ${t("Changes update the selected theme and are shared by devices using it.")}
              </p>
              ${getColorGroups().map((group) => this._renderGroup(group))}
            </div>
          </details>
        </div>

        <div class="haui-footer-wrapper">
          <div class="haui-footer-toggle-wrapper">
            <ha-button
              variant="neutral"
              appearance="plain"
              .disabled=${changed === 0}
              @click=${this._resetTheme}
            >
              ${t("Reset theme")}
            </ha-button>
            ${changed > 0
              ? html`<span class="haui-footer-changed">${t("{count} changed").replace("{count}", changed)}</span>`
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
              .disabled=${!this._themeData()}
              @click=${this._dispatchSave}
            >
              ${t("Apply theme")}
            </ha-button>
          </ha-dialog-footer>
        </div>
      </div>
    `;
  }
}

customElements.define("nspanel-theme-sidebar", ThemeSidebar);
