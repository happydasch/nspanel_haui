/**
 * NSPanel HAUI - Device settings view.
 *
 * Renders the device settings in the Device sidebar: a grid with one tile per
 * group on the landing, and the group a tile opens. Every group edits the same
 * draft - schedule entries, gestures and the theme choice included - so the one
 * footer Save applies all of it.
 */
import { html, css, nothing } from '../lit-import.js';
import { dateFormatOptions, displayModelOptions, LOCALE_OPTIONS, logLevelOptions, timeFormatOptions } from '../constants.js';
import { SETTINGS_SECTIONS, settingsSection } from '../device-settings-sections.js';
import { renderEntityPicker } from '../haui-entity.js';
import { renderField, renderNumberInput, renderSelect, renderToggle, renderToggleField } from '../form-fields.js';
import { HauiDialog } from '../dialogs/haui-dialog.js';
import { t } from '../localize.js';
import { sidebarFooterStyles } from '../styles/sidebar-footer.js';
import { themeOptions } from '../theme-library.js';
import { idlePanelConfig, idlePanelKeys, resolveIdleKeys } from '../panel-roles.js';
import { panelPills } from '../ui/panel-pills.js';
import { gestureSection } from '../ui/gesture-section.js';
import { scheduleSection } from '../ui/schedule-section.js';
import { settingsTile } from '../ui/settings-tile.js';

/**
 * Render a toggle row used within the device config form.
 * Uses native toggle checkbox via renderToggle.
 */
function checkbox(host, id, key, cfg, label, hint = "") {
  return renderToggleField({
    id,
    checked: Boolean(cfg[key]),
    label,
    hint,
    onChange: (checked) => {
      host._deviceConfigForm = { ...host._deviceConfigForm, [key]: checked };
      host.requestUpdate();
    },
  });
}
/** Render one side of the physical hardware-button settings. */
function renderHardwareButton(host, cfg, side) {
  const left = side === "left";
  const relayKey = `use_relay_${side}`;
  const entityKey = `button_${side}_entity`;
  const relayId = `dc-${relayKey}`;
  const entityId = `dc-${entityKey}`;
  const relayLabel = left ? t("Left Button - Use Relay") : t("Right Button - Use Relay");
  const relayHint = left
    ? t("When enabled, the left hardware button toggles the built-in physical relay. Disable to assign a Home Assistant entity instead.")
    : t("When enabled, the right hardware button toggles the built-in physical relay. Disable to assign a Home Assistant entity instead.");
  const entityLabel = left ? t("Left Button Entity") : t("Right Button Entity");
  const entityHint = left
    ? t("Toggle this Home Assistant entity (light, switch, scene, etc.) when the left hardware button is pressed. Only available when the left relay is disabled.")
    : t("Toggle this Home Assistant entity (light, switch, scene, etc.) when the right hardware button is pressed. Only available when the right relay is disabled.");

  return html`
    ${checkbox(host, relayId, relayKey, cfg, relayLabel, relayHint)}
    ${!(cfg[relayKey] ?? true) ? renderEntityPicker({
      id: entityId,
      value: host._deviceConfigForm?.[entityKey] ?? cfg[entityKey],
      label: entityLabel,
      hint: entityHint,
      hass: host.hass,
      onInput: (value) => {
        host._deviceConfigForm = { ...host._deviceConfigForm, [entityKey]: value };
      },
      onSelect: (value) => {
        host._deviceConfigForm = { ...host._deviceConfigForm, [entityKey]: value };
      },
    }) : ""}
  `;
}


/**
 * Render an integer field within the device config form, clamped to [min, max]
 * (empty or invalid input counts as min).
 */
function intField(host, id, key, cfg, label, fallback, min, max, hint) {
  return renderField({
    id,
    label,
    control: renderNumberInput(id, cfg[key] ?? fallback, (raw) => {
      const value = parseInt(raw, 10);
      host._deviceConfigForm = {
        ...host._deviceConfigForm,
        [key]: Number.isNaN(value) || value < min ? min : Math.min(value, max),
      };
    }, { min, max }),
    hint,
  });
}

/**
 * Render a brightness field (0-100, empty = the hub leaves the panel's value).
 * The empty field names the brightness the panel itself uses, when known.
 */
function brightnessField(host, key, cfg, label, panelValue, hint) {
  const id = `dc-${key}`;
  return renderField({
    id,
    label,
    control: renderNumberInput(id, cfg[key], (raw) => {
      const value = parseInt(raw, 10);
      host._deviceConfigForm = {
        ...host._deviceConfigForm,
        [key]: Number.isNaN(value) ? null : Math.max(0, Math.min(value, 100)),
      };
    }, {
      min: 0, max: 100,
      placeholder: panelValue == null ? undefined : t("Panel: {value}").replace("{value}", String(panelValue)),
    }),
    hint,
  });
}

/**
 * Render a preset select with an optional free-text strftime field.
 *
 * The select carries the preset options plus a "__custom__" entry; picking it
 * (or having a stored value outside the presets) reveals a text input so
 * advanced users can type any strftime format.  Empty values inherit the
 * hub-level default.
 */
function formatSelectField(host, baseId, key, cfg, label, options, hint) {
  const CUSTOM = "__custom__";
  const current = cfg[key] ?? "";
  const isCustom = current !== "" && !options.some((option) => option.value === current);
  const selectValue = isCustom ? CUSTOM : current;
  const selectOptions = [...options, { value: CUSTOM, label: t("Custom strftime\u2026") }];
  const select = renderSelect(baseId, selectValue, selectOptions, (value) => {
    const next = value === CUSTOM ? (cfg[key] ?? "") : value;
    host._deviceConfigForm = { ...host._deviceConfigForm, [key]: next };
    host.requestUpdate();
  });
  const customInput = isCustom || selectValue === CUSTOM ? html`
    <input
      id=${`${baseId}-custom`}
      class="haui-input"
      .value=${current}
      @input=${(event) => {
        host._deviceConfigForm = { ...host._deviceConfigForm, [key]: event.target.value };
      }}
    />
  ` : nothing;
  return renderField({ id: baseId, label, control: html`${select}${customInput}`, hint });
}

/**
 * Render a select/combobox field within the device config form.
 * Fires `@selected` to update internal state.
 */
function selectField(host, id, key, cfg, label, options, parser = (value) => value, hint = "") {
  return renderField({
    id,
    label,
    control: renderSelect(id, cfg[key] ?? "", options, (value) => {
      host._deviceConfigForm = { ...host._deviceConfigForm, [key]: parser(value) };
      host.requestUpdate();
    }),
    hint,
  });
}

class DeviceSettings extends HauiDialog {
  static get properties() {
    return {
      config: { type: Object },
      saving: { type: Boolean },
      api: { type: Object },
      entryId: { type: String },
      panels: { type: Array },
      /** The hub's panel type descriptors, for the names of untitled panels. */
      panelTypes: { type: Array },
      systemPanels: { type: Array },
      deviceBrightness: { type: Object },
      builtinThemes: { type: Object },
      customThemes: { type: Object },
      /** The group on screen, or null for the landing's tile grid. */
      section: { type: String },
    };
  }

  static styles = [HauiDialog.styles, sidebarFooterStyles, css`
    .haui-device-settings-sidebar {
      display: flex;
      flex-direction: column;
      height: 100%;
      max-height: 100%;
      min-height: 0;
    }
    .haui-device-settings-sidebar > #device-config-form {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      box-sizing: border-box;
      padding: 16px;
      overscroll-behavior: contain;
    }
    .haui-device-settings-snapshot-custom { margin-top: 8px; }
    /* The schedule closes the Screen group: a hairline sets its block off from the fields whose
       values its entries inherit, and its title sits one step above their labels. */
    .haui-settings-schedule {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--divider-color);
    }
    .haui-settings-block-title {
      margin: 0 0 4px;
      font-size: var(--haui-text-body);
      font-weight: 500;
    }
  `];

  constructor() {
    super();
    this.config = null;
    this.saving = false;
    this.api = null;
    this.entryId = "";
    this.panels = [];
    this.panelTypes = [];
    this.systemPanels = [];
    /** The panel's own brightness readings: `{ full, dimmed }`, null when unknown. */
    this.deviceBrightness = null;
    this.builtinThemes = {};
    this.customThemes = {};
    this.section = null;
    /** Which schedule entry and gesture are unfolded: view state, not config. */
    this._expanded = { schedule: null, gestures: null };
    this._deviceConfigForm = null;
  }

  willUpdate(changed) {
    if (!changed.has("config")) return;
    // A save in a sidebar opened from here (theme, updates) brings a new config:
    // the unsaved edits stay on top of it, so saving this form does not undo
    // that save.
    const previous = changed.get("config");
    const edits = previous && this._deviceConfigForm
      ? Object.fromEntries(Object.entries(this._deviceConfigForm).filter(([key, value]) =>
        JSON.stringify(value) !== JSON.stringify(previous[key])))
      : {};
    this._deviceConfigForm = this.config ? { ...this.config, ...edits } : null;
  }

  /** Open one group, replacing the grid (or the group before it). @param {string} key */
  _openSection(key) {
    this._emit("section-change", { section: key });
  }

  /** Fold or unfold one entry: only the open one closes. @param {'schedule'|'gestures'} list */
  _toggleEntry(list, index, isOpen) {
    if (isOpen || this._expanded[list] !== index) return;
    this._expanded = { ...this._expanded, [list]: null };
    this.requestUpdate();
  }

  render() {
    const cfg = this._deviceConfigForm || this.config;
    if (!this.config || !cfg) return "";

    const section = this.section ? settingsSection(this.section) : null;
    // The sidebar frame's strip carries the group's name, the back control and
    // the close control; the footer stays the same on both levels.
    return html`<aside class="haui-device-settings-sidebar" aria-label=${t("Device Settings")}>
      <form id="device-config-form" @submit=${(e) => e.preventDefault()}>
        <div class="haui-dialog-body">
          ${section ? this._renderSection(section.key, cfg) : this._renderLanding(cfg)}
        </div>
      </form>
      ${this._renderFooter(cfg)}
    </aside>`;
  }

  /** The landing: one tile per group, each with what the group holds. @param {any} cfg */
  _renderLanding(cfg) {
    const context = {
      panels: this.panels || [],
      panelTypes: this.panelTypes || [],
      builtinThemes: this.builtinThemes || {},
      customThemes: this.customThemes || {},
    };
    return html`
      <p class="haui-config-section-intro">
        ${t("Pick a group. Every group opens on its own page; Save and Cancel stay in the footer.")}
      </p>
      <div class="haui-settings-grid">
        ${SETTINGS_SECTIONS.map((entry) => settingsTile({
          key: entry.key,
          iconName: entry.iconName,
          label: entry.label(),
          summary: entry.summary(cfg, context),
          onClick: () => this._openSection(entry.key),
        }))}
      </div>`;
  }

  /** One group's page: its intro, its fields and, for two groups, its editor. */
  _renderSection(key, cfg) {
    if (key === 'general') return this._renderGeneral(cfg);
    if (key === 'screen') return this._renderScreen(cfg);
    if (key === 'sounds') return this._renderSounds(cfg);
    if (key === 'home') return this._renderHome(cfg);
    if (key === 'gestures') return this._renderGestures(cfg);
    if (key === 'buttons') return this._renderButtons(cfg);
    if (key === 'hardware') return this._renderHardware(cfg);
    if (key === 'advanced') return this._renderAdvanced(cfg);
    throw new Error(`Unknown device settings section: ${key}`);
  }

  /**
   * The General group's theme choice: the hub's themes, and the stored one while they load.
   * The theme's colors are edited in the Theme sidebar, from the Themes button below the side stack.
   */
  _themeField(cfg) {
    const themes = { ...(this.builtinThemes || {}), ...(this.customThemes || {}) };
    const options = themeOptions(themes);
    const stored = String(cfg.theme_id ?? '');
    // The library loads with the settings; the stored theme stays selectable meanwhile.
    if (stored && !options.some((option) => option.value === stored)) {
      options.push({ value: stored, label: stored });
    }
    return renderField({
      id: 'dc-theme_id',
      label: t('Theme'),
      control: renderSelect('dc-theme_id', stored, options, (value) => {
        this._deviceConfigForm = { ...this._deviceConfigForm, theme_id: value };
        this.requestUpdate();
      }),
      hint: t('The colors this panel draws with. Themes beside Updates edits the colors of the selected theme.'),
    });
  }

  _renderGeneral(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("The display model, the display language and its regional formats, and the theme this panel draws with.")}
      </p>
      ${selectField(this, "dc-display_model", "display_model", cfg, t("Display Model"), displayModelOptions(), (v) => v,
        t("Select the hardware model. EU and US (landscape) use the standard landscape layout; US (portrait) uses the rotated portrait TFT. Saving a changed model asks before the matching TFT is installed."))}
      ${selectField(this, "dc-locale", "locale", cfg, t("Language"), LOCALE_OPTIONS, (v) => v,
        t("The locale determines how dates, times, and numbers are formatted on the display, and which language is used for built-in text labels"))}
      ${formatSelectField(this, "dc-time_format", "time_format", cfg, t("Time format"), timeFormatOptions(),
        t("US 12-hour shows e.g. 2:30 PM. Custom strftime directives: %H = hour (24h), %I = hour (12h), %M = minutes, %p = AM/PM."))}
      ${formatSelectField(this, "dc-date_format", "date_format", cfg, t("Date format"), dateFormatOptions(),
        t("US numeric shows e.g. 03/14/2026. Empty keeps the locale-based layout from the Language setting."))}
      ${selectField(this, "dc-date_format_locale", "date_format_locale", cfg, t("Locale-aware date layout"), [
        { value: "", label: t("Use hub default") },
        { value: "full", label: t("Full") },
        { value: "long", label: t("Long") },
        { value: "medium", label: t("Medium") },
        { value: "short", label: t("Short") },
        { value: "E", label: t("Weekday (short)") },
        { value: "EEEE", label: t("Weekday (full)") },
      ], (v) => v, t("Used when Date format is Default. The selected layout follows the device language."))}
      ${this._themeField(cfg)}
    `;
  }

  _renderScreen(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("Controls the display brightness over time. These settings only dim and turn the screen off - they never switch pages. Turning the display off never requires an idle page.")}
      </p>
      ${brightnessField(this, "brightness", cfg, t("Brightness full (%)"), this.deviceBrightness?.full,
        t("Full display brightness. Leave empty to keep the brightness set on the panel. A schedule needs a value here: it is the brightness outside the schedule's entries."))}
      ${brightnessField(this, "brightness_dim", cfg, t("Brightness dimmed (%)"), this.deviceBrightness?.dimmed,
        t("Brightness the display dims to. Leave empty to keep the value set on the panel. A schedule entry that dims needs a value here: it is the dimmed brightness outside the entry."))}
      ${intField(this, "dc-timeout_dimming", "timeout_dimming", cfg, t("Dimming timeout (s)"), 10, 0, 3600,
        t("Seconds of inactivity before the display dims (0 = disabled, max 3600)."))}
      <div class="haui-field">
        <label for="dc-duration_dimming">${t("Dimming duration (s)")}</label>
        ${renderNumberInput("dc-duration_dimming", cfg.duration_dimming, (raw) => {
          const v = parseFloat(raw);
          this._deviceConfigForm = { ...this._deviceConfigForm, duration_dimming: isNaN(v) ? 0 : Math.max(0, Math.min(v, 5)) };
        }, { min: 0, max: 5, step: "any" })}
        <div class="haui-field-hint">${t("How long the fade between full and dimmed brightness takes (0-5 seconds).")}</div>
      </div>
      ${intField(this, "dc-timeout_display_off", "timeout_display_off", cfg, t("Display-off timeout (s)"), 120, 0, 3600,
        t("Seconds of inactivity before the display turns off (0 = disabled, max 3600)."))}
      ${checkbox(this, "dc-use_auto_dimming", "use_auto_dimming", cfg, t("Auto dimming"),
        t("When enabled, the display dims automatically after the dimming timeout. Disable to keep full brightness. Automations may control this switch; HAUI does not reapply it on reconnects or page changes."))}
      ${checkbox(this, "dc-use_auto_display_off", "use_auto_display_off", cfg, t("Auto display off"),
        t("When enabled, the display turns off (brightness to zero) after the display-off timeout. Disable to prevent automatic off. Automations may control this switch; HAUI does not reapply it on reconnects or page changes. With a schedule, HAUI sets it from the active entry or from this setting."))}
      <section class="haui-settings-schedule">${this._schedulePart(cfg)}</section>
    `;
  }

  _renderSounds(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("Configure audible alerts for startup and incoming notifications. To silence sounds during specific hours, add a Schedule entry with sound off.")}
      </p>
      ${checkbox(this, "dc-sound_on_startup", "sound_on_startup", cfg, t("Sound on startup"),
        t("Play a short audible tone when the display successfully connects to Home Assistant after a restart or power cycle"))}
      ${checkbox(this, "dc-sound_on_notification", "sound_on_notification", cfg, t("Sound on notification"),
        t("Play an audible alert tone whenever a new notification is received from Home Assistant to draw attention to the display"))}
      ${intField(this, "dc-persistent_sound_interval", "persistent_sound_interval", cfg, t("Persistent sound interval (seconds)"), 5, 1, 600,
        t("How often the alert sound repeats while a persistent notification waits to be dismissed (min 1, max 600)."))}
    `;
  }

  _renderHome(cfg) {
    // Snapshot max age: map -1/0/>0 to user-friendly mode labels
    const snapValue = cfg.snapshot_max_age_seconds ?? -1;
    const snapMode = snapValue === -1 ? "-1" : snapValue === 0 ? "0" : "custom";
    const snapCustomVal = snapMode === "custom" && snapValue > 0 ? snapValue : 60;
    // A device without panels has nothing to offer in either picker, so the
    // hints about the first navigation panel and the idle cycle would describe
    // pages that do not exist. Say what is missing instead.
    const noPanels = !(this.panels || []).length;
    return html`
      <p class="haui-config-section-intro">
        ${t("The panel Home opens, the idle panels that open after inactivity, and which panel returns when you wake the device. This only changes the shown panel - use Auto display off to also turn the display off.")}
      </p>
      <div class="haui-field">
        <div class="haui-field-inline">
          <label for="dc-home-panel">${t("Home panel")}</label>
          ${panelPills({
            id: "dc-home-panel", panels: this.panels || [], panelTypes: this.panelTypes || [],
            keys: cfg.home_panel ? [String(cfg.home_panel)] : [], single: true,
            addLabel: t("Set panel"), disabled: this.saving,
            onChange: (keys) => {
              this._deviceConfigForm = { ...this._deviceConfigForm, home_panel: keys[0] || "" };
              this.requestUpdate();
            },
          })}
        </div>
        ${noPanels
          ? html`<div class="haui-field-hint is-persistent">${t("This device has no panels yet. Add a panel, then set the home panel here.")}</div>`
          : html`<div class="haui-field-hint">${t("If no home panel is set, the first panel in navigation is used.")}</div>`}
      </div>
      <div class="haui-field">
        <div class="haui-field-inline">
          <label for="dc-idle-panels">${t("Idle panels")}</label>
          ${panelPills({
            id: "dc-idle-panels", panels: this.panels || [], panelTypes: this.panelTypes || [],
            keys: idlePanelKeys(cfg.idle_panel, cfg.idle_panel_extra),
            numbered: true, reorderable: true, disabled: this.saving,
            onChange: (keys) => {
              this._deviceConfigForm = { ...this._deviceConfigForm, ...idlePanelConfig(keys) };
              this.requestUpdate();
            },
          })}
        </div>
        ${noPanels
          ? html`<div class="haui-field-hint is-persistent">${t("This device has no panels yet. Add a panel, then set the idle panels here.")}</div>`
          : html`
            <div class="haui-field-hint">
              ${t("Panels are shown in order after the page timeout, then cycle. Reorder them by dragging.")}
            </div>
            ${resolveIdleKeys(this.panels || [], cfg).length ? "" : html`
              <div class="haui-field-hint is-persistent">${t("Nothing opens automatically until you add a panel.")}</div>
            `}
          `}
      </div>
      ${checkbox(this, "dc-use_auto_page", "use_auto_page", cfg, t("Auto page"),
        t("When enabled, the hub switches to the configured idle page after the page timeout. The next touch or button press returns to the panel you were on."))}
      ${intField(this, "dc-timeout_page", "timeout_page", cfg, t("Page timeout (seconds)"), 30, 0, 3600,
        t("Seconds of inactivity before the idle page opens (0 = disabled, max 3600)."))}
      <div class="haui-field">
        <label>${t("Snapshot max age")}</label>
        ${renderSelect("dc-snapshot_max_age_mode", snapMode, [
          { value: "-1", label: t("Always restore") },
          { value: "0", label: t("Never restore") },
          { value: "custom", label: t("Custom time limit...") },
        ], (v) => {
          let modeVal;
          if (v === "-1") modeVal = -1;
          else if (v === "0") modeVal = 0;
          else modeVal = (this._deviceConfigForm?.snapshot_max_age_seconds > 0)
            ? this._deviceConfigForm.snapshot_max_age_seconds
            : 60;
          this._deviceConfigForm = { ...this._deviceConfigForm, snapshot_max_age_seconds: modeVal };
          this.requestUpdate();
        })}
        <div class="haui-field-hint">${t("Controls whether the panel you were on before the idle page is restored when waking. With Auto display-off, the display can still turn off and wake without any panel switch.")}</div>
        ${snapMode === "custom" ? html`
          <div class="haui-device-settings-snapshot-custom">
            ${renderNumberInput("dc-snapshot_max_age_custom", snapCustomVal, (raw) => {
              const v = parseInt(raw, 10);
              this._deviceConfigForm = {
                ...this._deviceConfigForm,
                snapshot_max_age_seconds: isNaN(v) || v < 1 ? 60 : v,
              };
              this.requestUpdate();
            })}
            <div class="haui-field-hint">${t("Maximum age in seconds before falling back to the home panel.")}</div>
          </div>
        ` : ""}
      </div>
      ${intField(this, "dc-auto_navigate_home_timeout", "auto_navigate_home_timeout", cfg, t("Return to the home panel after (seconds)"), 0, 0, 86400,
        t("Go back to the home panel after this many seconds without interaction on another panel. Set it shorter than the dimming and display-off timeouts. 0 = off."))}
    `;
  }

  /**
   * The schedule at the end of the Screen group: its entries, all of them in
   * this form's draft. The fields above are the values an entry inherits.
   */
  _schedulePart(cfg) {
    const schedule = cfg.schedule || [];
    const dims = schedule.some((entry) => entry.brightness_dim != null);
    // A schedule needs a full brightness to restore when an entry ends, and a
    // dimmed one while an entry dims: saving this form sets them when it must.
    const addedBrightness = this.config.brightness == null && cfg.brightness != null && schedule.length
      ? cfg.brightness
      : null;
    const addedBrightnessDim = this.config.brightness_dim == null && cfg.brightness_dim != null && dims
      ? cfg.brightness_dim
      : null;
    const change = (entries, fields = {}) => {
      this._deviceConfigForm = { ...this._deviceConfigForm, ...fields, schedule: entries };
      this.requestUpdate();
    };
    return scheduleSection({
      config: cfg,
      schedule,
      deviceBrightness: this.deviceBrightness || {},
      addedBrightness,
      addedBrightnessDim,
      expandedEntryIndex: this._expanded.schedule,
      onEntryToggle: (index, isOpen) => this._toggleEntry('schedule', index, isOpen),
      onChange: change,
      onAdd: (entries, fields) => {
        this._expanded = { ...this._expanded, schedule: entries.length - 1 };
        change(entries, fields);
      },
    });
  }

  /** The gestures: the swipes and the panel each one opens, in this form's draft. */
  _renderGestures(cfg) {
    const change = (gestures) => {
      this._deviceConfigForm = { ...this._deviceConfigForm, gestures };
      this.requestUpdate();
    };
    return gestureSection({
      panels: this.panels || [],
      systemPanels: this.systemPanels || [],
      panelTypes: this.panelTypes || [],
      gestures: cfg.gestures || [],
      expandedEntryIndex: this._expanded.gestures,
      onEntryToggle: (index, isOpen) => this._toggleEntry('gestures', index, isOpen),
      onChange: change,
      onAdd: (gestures) => {
        this._expanded = { ...this._expanded, gestures: gestures.length - 1 };
        change(gestures);
      },
    });
  }

  _renderButtons(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("Toggle visibility of on-screen navigation buttons on panels.")}
      </p>
      ${checkbox(this, "dc-show_home_button", "show_home_button", cfg, t("Show home button"),
        t("Show a home navigation button on panels so users can tap to return to the configured home panel from any page"))}
      ${checkbox(this, "dc-show_idle_button", "show_idle_button", cfg, t("Show idle button"),
        t("Show a button that manually opens the idle page (the configured idle panel)"))}
      ${checkbox(this, "dc-show_notifications_button", "show_notifications_button", cfg, t("Show notifications button"),
        t("Show a notifications button on supported panels that indicates and provides access to any pending notifications"))}
    `;
  }

  _renderHardware(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("Configure the physical left/right hardware buttons on the NSPanel. Each button can toggle its internal relay or a Home Assistant entity.")}
      </p>
      ${renderHardwareButton(this, cfg, "left")}
      ${renderHardwareButton(this, cfg, "right")}
      ${checkbox(this, "dc-reset_interaction_on_button", "reset_interaction_on_button", cfg,
        t("Interact on button press"),
        t("When enabled, pressing a hardware button resets the inactivity timer and prevents the display from dimming or turning off. Disable to allow buttons to work without delaying the display-off."))}
    `;
  }

  _renderAdvanced(cfg) {
    return html`
      <p class="haui-config-section-intro">
        ${t("Diagnostics and fine-tuning: log verbosity, the stale-data indicator and the page settle delay.")}
      </p>
      ${selectField(this, "dc-log_level", "log_level", cfg, t("Log Level"), logLevelOptions(), (v) => v,
        t("Controls the verbosity of this device's app messages in the Home Assistant log: standard logger thresholds. DEBUG adds detailed diagnostics (entity state changes, display commands) on top of the routine INFO lifecycle messages."))}
      ${intField(this, "dc-stale_data_seconds", "stale_data_seconds", cfg, t("Stale data threshold (seconds)"), 0, 0, 86400,
        t("When a sensor value has not updated for this many seconds, the row page shows it dimmed with a … suffix so an old value is not mistaken for current. 0 = off."))}
      <div class="haui-field">
        <label for="dc-page_settle_delay">${t("Page settle delay (seconds)")}</label>
        ${renderNumberInput("dc-page_settle_delay", cfg.page_settle_delay, (raw) => {
          const v = parseFloat(raw);
          this._deviceConfigForm = { ...this._deviceConfigForm, page_settle_delay: isNaN(v) ? 0 : Math.max(0, Math.min(v, 2)) };
        }, { min: 0, max: 2, step: "any" })}
        <div class="haui-field-hint">${t("How long the hub waits after the display confirms a page change before it draws the page. Raise it only if the log shows invalid-variable errors right after a page change.")}</div>
      </div>
    `;
  }

  /** Device Enabled, Cancel and Save: one footer on both levels. @param {any} cfg */
  _renderFooter(cfg) {
    return html`<div slot="footer" class="haui-footer-wrapper">
      <div class="haui-footer-toggle-wrapper">
        <label for="dc-enabled">${t("Device Enabled")}</label>
        ${renderToggle("dc-enabled", Boolean(cfg.enabled), (checked) => {
          this._deviceConfigForm = { ...this._deviceConfigForm, enabled: checked };
          this.requestUpdate();
        })}
      </div>
      <ha-dialog-footer>
        <ha-button slot="secondaryAction" variant="neutral" appearance="plain" @click=${this._dispatchClose}>
          ${t("Cancel")}
        </ha-button>
        <ha-button
          slot="primaryAction"
          variant="brand"
          @click=${this._dispatchSave}
          ?disabled=${this.saving}
        >
          ${this.saving ? t("Saving...") : t("Save")}
        </ha-button>
      </ha-dialog-footer>
    </div>`;
  }

  _dispatchSave() {
    this._emit("dialog-save", { config: this._deviceConfigForm });
  }
}

customElements.define("nspanel-device-settings", DeviceSettings);
