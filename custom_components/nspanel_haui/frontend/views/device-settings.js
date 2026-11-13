/**
 * NSPanel HAUI - Device settings view.
 *
 * Renders the complete device-config form in the Device sidebar while keeping
 * the existing field model and save event contract.
 */
import { html, css, nothing } from '../lit-import.js';
import { DATE_FORMAT_OPTIONS, DISPLAY_MODEL_OPTIONS, LOCALE_OPTIONS, LOG_LEVEL_OPTIONS, TIME_FORMAT_OPTIONS } from '../constants.js';
import { renderEntityPicker } from '../haui-entity.js';
import { renderField, renderNumberInput, renderSelect, renderToggle, renderToggleField } from '../form-fields.js';
import { dialogHeader } from '../dialogs/dialog-header.js';
import { HauiDialog } from '../dialogs/haui-dialog.js';
import { t } from '../localize.js';
import { sidebarFooterStyles } from '../styles/sidebar-footer.js';
import { idlePanelConfig, idlePanelKeys, panelPills } from '../ui/panel-pills.js';

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
      inline: { type: Boolean },
      saving: { type: Boolean },
      api: { type: Object },
      entryId: { type: String },
      panels: { type: Array },
    };
  }

  static styles = [HauiDialog.styles, sidebarFooterStyles, css`
    .haui-footer-toggle-wrapper label {
      margin: 0;
      font-weight: 500;
      font-size: var(--haui-text-label);
    }
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
  `];

  constructor() {
    super();
    this.inline = false;
    this.config = null;
    this.saving = false;
    this.api = null;
    this.entryId = "";
    this.panels = [];
    this._deviceConfigForm = null;
  }

  willUpdate(changed) {
    if (changed.has("config")) {
      this._deviceConfigForm = this.config ? { ...this.config } : null;
    }
  }

  render() {
    const cfg = this._deviceConfigForm || this.config;
    if (!this.config || !cfg) return "";

    // Snapshot max age: map -1/0/>0 to user-friendly mode labels
    const snapValue = cfg.snapshot_max_age_seconds ?? -1;
    const snapMode = snapValue === -1 ? "-1" : snapValue === 0 ? "0" : "custom";
    const snapCustomVal = snapMode === "custom" && snapValue > 0 ? snapValue : 60;

    const content = html`
        ${this._renderHeader(t("Device Settings"))}

        <form id="device-config-form" @submit=${(e) => e.preventDefault()}>
          <div class="haui-dialog-body">

          <p class="haui-config-section-intro">
            ${t("Configure how this device behaves: language and regional formats, diagnostics, audible alerts, hardware buttons, navigation, display dimming and display-off, and automatic page switching.")}
          </p>

          <details class="haui-config-section">
            <summary>${t("Language & region")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("The display language and its regional formats. Time and date formats apply to the clock, clock-two and weather pages; leave them at Default to follow the language.")}
              </p>
              ${selectField(this, "dc-locale", "locale", cfg, t("Language"), LOCALE_OPTIONS, (v) => v,
                t("The locale determines how dates, times, and numbers are formatted on the display, and which language is used for built-in text labels"))}
              ${formatSelectField(this, "dc-time_format", "time_format", cfg, t("Time format"), TIME_FORMAT_OPTIONS,
                t("US 12-hour shows e.g. 2:30 PM. Custom strftime directives: %H = hour (24h), %I = hour (12h), %M = minutes, %p = AM/PM."))}
              ${formatSelectField(this, "dc-date_format", "date_format", cfg, t("Date format"), DATE_FORMAT_OPTIONS,
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
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("General Settings")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("General device behavior: display model, diagnostic logging verbosity and the stale-data indicator.")}
              </p>
                ${selectField(this, "dc-display_model", "display_model", cfg, t("Display Model"), DISPLAY_MODEL_OPTIONS, (v) => v,
                  t("Select the hardware model. EU and US (landscape) use the standard landscape layout; US (portrait) uses the rotated portrait TFT. Saving a changed model asks before the matching TFT is installed."))}

              ${selectField(this, "dc-log_level", "log_level", cfg, t("Log Level"), LOG_LEVEL_OPTIONS, (v) => v,
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
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Display dimming & off")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Controls the display brightness over time. These settings only dim and turn the screen off - they never switch pages. Turning the display off never requires an idle page.")}
              </p>
                <div class="haui-field">
                  <label for="dc-brightness">${t("Brightness full (%)")}</label>
                  ${renderNumberInput("dc-brightness", cfg.brightness, (raw) => {
                    const v = parseInt(raw, 10);
                    this._deviceConfigForm = { ...this._deviceConfigForm, brightness: isNaN(v) ? null : Math.max(0, Math.min(v, 100)) };
                  }, { min: 0, max: 100 })}
                  <div class="haui-field-hint">${t("Full display brightness. Leave empty to keep the brightness set on the panel. A schedule needs a value here: it is the brightness outside the schedule's entries.")}</div>
                </div>
                <div class="haui-field">
                  <label for="dc-brightness_dim">${t("Brightness dimmed (%)")}</label>
                  ${renderNumberInput("dc-brightness_dim", cfg.brightness_dim, (raw) => {
                    const v = parseInt(raw, 10);
                    this._deviceConfigForm = { ...this._deviceConfigForm, brightness_dim: isNaN(v) ? null : Math.max(0, Math.min(v, 100)) };
                  }, { min: 0, max: 100 })}
                  <div class="haui-field-hint">${t("Brightness the display dims to. Leave empty to keep the value set on the panel.")}</div>
                </div>
                ${checkbox(this, "dc-use_auto_dimming", "use_auto_dimming", cfg, t("Auto dimming"),
                  t("When enabled, the display dims automatically after the dimming timeout. Disable to keep full brightness. Automations may control this switch; HAUI does not reapply it on reconnects or page changes."))}
                ${intField(this, "dc-timeout_dimming", "timeout_dimming", cfg, t("Dimming timeout (seconds)"), 10, 0, 3600,
                  t("Seconds of inactivity before the display dims (0 = disabled, max 3600)."))}
                <div class="haui-field">
                  <label for="dc-duration_dimming">${t("Dimming duration (seconds)")}</label>
                  ${renderNumberInput("dc-duration_dimming", cfg.duration_dimming, (raw) => {
                    const v = parseFloat(raw);
                    this._deviceConfigForm = { ...this._deviceConfigForm, duration_dimming: isNaN(v) ? 0 : Math.max(0, Math.min(v, 5)) };
                  }, { min: 0, max: 5, step: "any" })}
                  <div class="haui-field-hint">${t("How long the fade between full and dimmed brightness takes (0-5 seconds).")}</div>
                </div>

                ${checkbox(this, "dc-use_auto_display_off", "use_auto_display_off", cfg, t("Auto display off"),
                  t("When enabled, the display turns off (brightness to zero) after the display-off timeout. Disable to prevent automatic off. Automations may control this switch; HAUI does not reapply it on reconnects or page changes. With a schedule, HAUI sets it from the active entry or from this setting."))}
                ${intField(this, "dc-timeout_display_off", "timeout_display_off", cfg, t("Display-off timeout (seconds)"), 120, 0, 3600,
                  t("Seconds of inactivity before the display turns off (0 = disabled, max 3600)."))}

            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Automatic page switching")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Switches to the idle page after inactivity. This only changes the shown page - use Auto display-off to also turn the display off.")}
              </p>
                ${checkbox(this, "dc-use_auto_page", "use_auto_page", cfg, t("Auto page"),
                  t("When enabled, the hub switches to the configured idle page after the page timeout. The next touch or button press returns to the panel you were on."))}
                ${intField(this, "dc-timeout_page", "timeout_page", cfg, t("Page timeout (seconds)"), 30, 0, 3600,
                  t("Seconds of inactivity before the idle page opens (0 = disabled, max 3600)."))}
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Special pages")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Choose the page opened by Home and the ordered pages shown while the device is idle.")}
              </p>
              <div class="haui-field">
                <label for="dc-home-panel">${t("Home panel")}</label>
                ${panelPills({
                  id: "dc-home-panel", panels: this.panels || [],
                  keys: cfg.home_panel ? [String(cfg.home_panel)] : [], single: true,
                  addLabel: t("Set panel"), disabled: this.saving,
                  onChange: (keys) => {
                    this._deviceConfigForm = { ...this._deviceConfigForm, home_panel: keys[0] || "" };
                    this.requestUpdate();
                  },
                })}
                <div class="haui-field-hint">${t("If no home panel is set, the first panel in navigation is used.")}</div>
              </div>
              <div class="haui-field">
                <label for="dc-idle-panels">${t("Idle panels")}</label>
                ${panelPills({
                  id: "dc-idle-panels", panels: this.panels || [],
                  keys: idlePanelKeys(cfg.idle_panel, cfg.idle_panel_extra),
                  numbered: true, reorderable: true, disabled: this.saving,
                  onChange: (keys) => {
                    this._deviceConfigForm = { ...this._deviceConfigForm, ...idlePanelConfig(keys) };
                    this.requestUpdate();
                  },
                })}
                <div class="haui-field-hint">
                  ${t("Panels are shown in order after the page timeout, then cycle. Reorder them by dragging.")}
                </div>
                ${idlePanelKeys(cfg.idle_panel, cfg.idle_panel_extra).length ? "" : html`
                  <div class="haui-field-hint">${t("Nothing opens automatically until you add a panel.")}</div>
                `}
              </div>
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Hardware Buttons")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Configure the physical left/right hardware buttons on the NSPanel. Each button can toggle its internal relay or a Home Assistant entity.")}
              </p>
              ${renderHardwareButton(this, cfg, "left")}

              <div class="haui-section-divider"></div>

              ${renderHardwareButton(this, cfg, "right")}
              <div class="haui-section-divider"></div>
            <div class="haui-section-divider"></div>
              ${checkbox(this, "dc-reset_interaction_on_button", "reset_interaction_on_button", cfg,
                t("Interact on button press"),
                t("When enabled, pressing a hardware button resets the inactivity timer and prevents the display from dimming or turning off. Disable to allow buttons to work without delaying the display-off."))}
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Display Buttons")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Toggle visibility of on-screen navigation buttons on panels.")}
              </p>
              ${checkbox(this, "dc-show_home_button", "show_home_button", cfg, t("Show home button"),
                t("Show a home navigation button on panels so users can tap to return to the configured home panel from any page"))}
              ${checkbox(this, "dc-show_idle_button", "show_idle_button", cfg, t("Show idle button"),
                t("Show a button that manually opens the idle page (the configured idle panel)"))}
              ${checkbox(this, "dc-show_notifications_button", "show_notifications_button", cfg, t("Show notifications button"),
                t("Show a notifications button on supported panels that indicates and provides access to any pending notifications"))}
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Notifications")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Configure audible alerts for startup and incoming notifications. To silence sounds during specific hours, add a Schedule entry with sound off.")}
              </p>
              ${checkbox(this, "dc-sound_on_startup", "sound_on_startup", cfg, t("Sound on startup"),
                t("Play a short audible tone when the display successfully connects to Home Assistant after a restart or power cycle"))}
              ${checkbox(this, "dc-sound_on_notification", "sound_on_notification", cfg, t("Sound on notification"),
                t("Play an audible alert tone whenever a new notification is received from Home Assistant to draw attention to the display"))}
              ${intField(this, "dc-persistent_sound_interval", "persistent_sound_interval", cfg, t("Persistent sound interval (seconds)"), 5, 1, 600,
                t("How often the alert sound repeats while a persistent notification waits to be dismissed (min 1, max 600)."))}
            </div>
          </details>

          <details class="haui-config-section">
            <summary>${t("Idle & Wake Behavior")}</summary>
            <div class="haui-config-section-body">
              <p class="haui-config-section-intro">
                ${t("Controls what happens when the idle page is shown and what is restored when the user wakes the device again.")}
              </p>
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
                  <div style="margin-top: 8px;">
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
            </div>
          </details>

          </div>
        </form>

        <div slot="footer" class="haui-footer-wrapper">
          <div class="haui-footer-toggle-wrapper">
            ${renderToggle("dc-enabled", Boolean(cfg.enabled), (checked) => {
              this._deviceConfigForm = { ...this._deviceConfigForm, enabled: checked };
              this.requestUpdate();
            })}
            <label for="dc-enabled" style="margin-inline-start:8px;">${t("Device Enabled")}</label>
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
        </div>
    `;
    if (this.inline) {
      return html`<aside class="haui-device-settings-sidebar" aria-label=${t("Device Settings")}>${content}</aside>`;
    }
    return html`<ha-dialog .open=${this.open} @closed=${this._dispatchClose}>${content}</ha-dialog>`;
  }

  /** The dialog's header; in the sidebar the frame's strip carries the title and the close control. */
  _renderHeader(title) {
    return this.inline ? nothing : dialogHeader(title, this._dispatchClose);
  }

  _dispatchSave() {
    this._emit("dialog-save", { config: this._deviceConfigForm });
  }
}

customElements.define("nspanel-device-settings", DeviceSettings);
