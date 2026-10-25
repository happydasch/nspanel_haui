/**
 * NSPanel HAUI - Device Config dialog.
 *
 * Proper Lit custom element replacing the old renderDeviceConfigDialog() function.
 * Uses ha-dialog / ha-dialog-header / ha-dialog-footer with ha-button.
 * Communicates form changes via CustomEvent.
 */
import { html, css } from '../lit-import.js';
import { DATE_FORMAT_OPTIONS, DISPLAY_MODEL_OPTIONS, GESTURE_NAMES, LOCALE_OPTIONS, TIME_FORMAT_OPTIONS } from '../constants.js';
import { renderEntityPicker } from '../haui-entity.js';
import { renderNumberInput, renderSelect, renderToggle } from '../form-fields.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';

/**
 * Render a toggle row used within the device config form.
 * Uses native toggle checkbox via renderToggle.
 */
function checkbox(host, id, key, cfg, label, hint = "") {
  return html`
    <div class="checkbox-wrap">
      <div class="checkbox-row">
        ${renderToggle(id, Boolean(cfg[key]), (checked) => {
          host._deviceConfigForm = { ...host._deviceConfigForm, [key]: checked };
          host.requestUpdate();
        })}
        <label for=${id}>${label}</label>
      </div>
      ${hint ? html`<div class="field-hint">${hint}</div>` : ""}
    </div>
  `;
}

/**
 * Render an integer field within the device config form, clamped to [min, max]
 * (empty or invalid input counts as min).
 */
function intField(host, id, key, cfg, label, fallback, min, max, hint) {
  return html`
    <div class="form-group">
      <label for=${id}>${label}</label>
      ${renderNumberInput(id, cfg[key] ?? fallback, (raw) => {
        const v = parseInt(raw, 10);
        host._deviceConfigForm = { ...host._deviceConfigForm, [key]: isNaN(v) || v < min ? min : Math.min(v, max) };
      }, { min, max })}
      <div class="field-hint">${hint}</div>
    </div>
  `;
}/**
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
  const isCustom = current !== "" && !options.some((o) => o.value === current);
  const selectValue = isCustom ? CUSTOM : current;
  const selectOptions = [...options, { value: CUSTOM, label: t("Custom strftime\u2026") }];
  return html`
    <div class="form-group">
      <label for=${baseId}>${label}</label>
      ${renderSelect(baseId, selectValue, selectOptions, (v) => {
        const next = v === CUSTOM ? (cfg[key] ?? "") : v;
        host._deviceConfigForm = { ...host._deviceConfigForm, [key]: next };
        host.requestUpdate();
      })}
      ${isCustom || selectValue === CUSTOM ? html`
        <input
          id=${`${baseId}-custom`}
          class="native-input"
          .value=${current}
          @input=${(e) => {
            host._deviceConfigForm = { ...host._deviceConfigForm, [key]: e.target.value };
          }}
        />
      ` : ""}
      <div class="field-hint">${hint}</div>
    </div>
  `;
}

/** Debug level options for the debug_level dropdown (labels resolved at render time). */
function debugLevelOptions() {
  return [
    { value: "0", label: t("Off") },
    { value: "1", label: t("Basic") },
    { value: "2", label: t("Verbose") },
  ];
}

/**
 * Render a select/combobox field within the device config form.
 * Fires `@selected` to update internal state.
 */
function selectField(host, id, key, cfg, label, options, parser = (v) => v, hint = "") {
  return html`
    <div class="form-group">
      <label for=${id}>${label}</label>
      ${renderSelect(id, cfg[key] ?? "", options, (v) => {
        host._deviceConfigForm = { ...host._deviceConfigForm, [key]: parser(v) };
        host.requestUpdate();
      })}
      ${hint ? html`<div class="field-hint">${hint}</div>` : ""}
    </div>
  `;
}

class DeviceConfigDialog extends HauiDialog {
  static get properties() {
    return {
      config: { type: Object },
      devicePanels: { type: Array },
      saving: { type: Boolean },
    };
  }

  static styles = [HauiDialog.styles, css`
    .footer-toggle-wrapper label {
      margin: 0;
      font-weight: 500;
      font-size: 0.92em;
    }
    .time-range-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .time-range-sep {
      flex-shrink: 0;
      color: var(--secondary-text-color, #666);
      font-weight: 500;
    }
    .gesture-row {
      display: grid;
      grid-template-columns: minmax(0, 2fr) 72px minmax(0, 1.4fr) auto;
      gap: 8px;
      align-items: center;
      margin-bottom: 6px;
    }
    .gesture-row-labels {
      font-size: 0.8em;
      color: var(--secondary-text-color, #666);
      margin-bottom: 2px;
    }
    .gesture-remove {
      --mdc-icon-button-size: 32px;
      color: var(--secondary-text-color, #666);
    }
  `];

  constructor() {
    super();
    this.config = null;
    this.devicePanels = [];
    this.saving = false;
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

    const panelOptions = [
      { value: "", label: t("- None -") },
      ...this.devicePanels.filter(p => p.key).map(p => ({ value: p.key, label: p.key })),
    ];

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        .preventScrimClose=${true}
      >
        ${dialogHeader(t("Device Settings"), this._dispatchClose)}

        <form id="device-config-form" @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">

          <p class="config-section-intro">
            ${t("Configure how this device behaves: language and diagnostics, audible alerts, hardware buttons, navigation, display dimming and display-off, automatic page switching, and which panels play which role.")}
          </p>

          <details class="config-section">
            <summary>${t("General Settings")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("General device behavior: display language, diagnostic logging verbosity, and audible alerts for startup and notifications.")}
              </p>
              ${selectField(this, "dc-locale", "locale", cfg, t("Language"), LOCALE_OPTIONS, (v) => v,
                t("The locale determines how dates, times, and numbers are formatted on the display, and which language is used for built-in text labels"))}

                ${selectField(this, "dc-display_model", "display_model", cfg, t("Display Model"), DISPLAY_MODEL_OPTIONS, (v) => v,
                  t("Select the hardware model. EU and US (landscape) use the standard landscape layout; US (portrait) uses the rotated portrait TFT. The update controller downloads the matching TFT for the selected model."))}

              ${selectField(this, "dc-debug_level", "debug_level", cfg, t("Debug Level"), debugLevelOptions(), (v) => parseInt(v, 10),
                t("Controls the verbosity of diagnostic logging sent to the Home Assistant logs: Off = no debug output, Basic = key lifecycle events, Verbose = all commands and data exchanged with the display"))}
              ${checkbox(this, "dc-log_items", "log_items", cfg, t("Log item updates"),
                t("Write every item update of this device to the Home Assistant log. For troubleshooting; leave it off otherwise."))}
              ${intField(this, "dc-stale_data_seconds", "stale_data_seconds", cfg, t("Stale data threshold (seconds)"), 0, 0, 86400,
                t("When a sensor value has not updated for this many seconds, the row page shows it dimmed with a … suffix so an old value is not mistaken for current. 0 = off."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Display dimming & off")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Controls the display brightness over time. These settings only dim and turn the screen off - they never switch pages. Turning the display off never requires an idle page.")}
              </p>
                ${checkbox(this, "dc-use_auto_dimming", "use_auto_dimming", cfg, t("Auto dimming"),
                  t("When enabled, the display dims automatically after the dimming timeout. Disable to keep the display at full brightness at all times."))}
                ${intField(this, "dc-timeout_dimming", "timeout_dimming", cfg, t("Dimming timeout (seconds)"), 10, 0, 3600,
                  t("Seconds of inactivity before the display dims (0 = disabled, max 3600)."))}

                ${checkbox(this, "dc-use_auto_display_off", "use_auto_display_off", cfg, t("Auto display off"),
                  t("When enabled, the display turns off (brightness to zero) after the display-off timeout. A touch or button press wakes it again. Disable to keep the display on."))}
                ${intField(this, "dc-timeout_display_off", "timeout_display_off", cfg, t("Display-off timeout (seconds)"), 120, 0, 3600,
                  t("Seconds of inactivity before the display turns off (0 = disabled, max 3600)."))}

                ${checkbox(this, "dc-use_sleep_schedule", "use_sleep_schedule", cfg, t("Sleep schedule"),
                  t("Only allow the display to turn off inside the time window below. Outside it the screen stays on (and only dims after the dimming timeout) while the idle page is shown. While enabled, the window overrides the Auto display-off toggle."))}
                ${cfg.use_sleep_schedule ? html`
                  <div class="form-group">
                    <label>${t("Sleep schedule window")}</label>
                    <div class="time-range-row">
                      <input
                        id="dc-sleep_schedule_start"
                        type="time"
                        class="native-input"
                        .value=${String(cfg.sleep_schedule_start ?? "")}
                        @input=${(e) => {
                          this._deviceConfigForm = { ...this._deviceConfigForm, sleep_schedule_start: e.target.value };
                          this.requestUpdate();
                        }}
                      />
                      <span class="time-range-sep">&ndash;</span>
                      <input
                        id="dc-sleep_schedule_end"
                        type="time"
                        class="native-input"
                        .value=${String(cfg.sleep_schedule_end ?? "")}
                        @input=${(e) => {
                          this._deviceConfigForm = { ...this._deviceConfigForm, sleep_schedule_end: e.target.value };
                          this.requestUpdate();
                        }}
                      />
                    </div>
                    <div class="field-hint">${t("The display turns off only within this time window. Overnight ranges such as 22:00–07:00 are supported. Leave both fields empty to keep the Auto display-off setting.")}</div>
                  </div>
                ` : ""}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Automatic page switching")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Switches to the idle page after inactivity. This only changes the shown page - use Auto display-off to also turn the display off.")}
              </p>
                ${checkbox(this, "dc-use_auto_page", "use_auto_page", cfg, t("Auto page"),
                  t("When enabled, the hub switches to the configured idle page after the page timeout. The next touch or button press returns to the panel you were on."))}
                ${intField(this, "dc-timeout_page", "timeout_page", cfg, t("Page timeout (seconds)"), 30, 0, 3600,
                  t("Seconds of inactivity before the idle page opens (0 = disabled, max 3600)."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Hardware Buttons")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Configure the physical left/right hardware buttons on the NSPanel. Each button can toggle its internal relay or a Home Assistant entity.")}
              </p>
              ${checkbox(this, "dc-use_relay_left", "use_relay_left", cfg, t("Left Button - Use Relay"),
                t("When enabled, the left hardware button toggles the built-in physical relay. Disable to assign a Home Assistant entity instead."))}

              ${!(cfg.use_relay_left ?? true) ? renderEntityPicker({
                id: "dc-button_left_entity",
                value: this._deviceConfigForm?.button_left_entity ?? cfg.button_left_entity,
                label: t("Left Button Entity"),
                hint: t("Toggle this Home Assistant entity (light, switch, scene, etc.) when the left hardware button is pressed. Only available when the left relay is disabled."),
                hass: this.hass,
                onInput: (val) => {
                  this._deviceConfigForm = { ...this._deviceConfigForm, button_left_entity: val };
                },
                onSelect: (v) => {
                  this._deviceConfigForm = { ...this._deviceConfigForm, button_left_entity: v };
                },
              }) : ""}

              <div class="section-divider"></div>

              ${checkbox(this, "dc-use_relay_right", "use_relay_right", cfg, t("Right Button - Use Relay"),
                t("When enabled, the right hardware button toggles the built-in physical relay. Disable to assign a Home Assistant entity instead."))}

              ${!(cfg.use_relay_right ?? true) ? renderEntityPicker({
                id: "dc-button_right_entity",
                value: this._deviceConfigForm?.button_right_entity ?? cfg.button_right_entity,
                label: t("Right Button Entity"),
                hint: t("Toggle this Home Assistant entity (light, switch, scene, etc.) when the right hardware button is pressed. Only available when the right relay is disabled."),
                hass: this.hass,
                onInput: (val) => {
                  this._deviceConfigForm = { ...this._deviceConfigForm, button_right_entity: val };
                },
                onSelect: (v) => {
                  this._deviceConfigForm = { ...this._deviceConfigForm, button_right_entity: v };
                },
              }) : ""}
            <div class="section-divider"></div>
              ${checkbox(this, "dc-reset_interaction_on_button", "reset_interaction_on_button", cfg,
                t("Interact on button press"),
                t("When enabled, pressing a hardware button resets the inactivity timer and prevents the display from dimming or turning off. Disable to allow buttons to work without delaying the display-off."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Display Buttons")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
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

          <details class="config-section">
            <summary>${t("Gestures")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("A single swipe navigates: left/right step through the navigation panels, up opens About, down opens Settings. A gesture sequence opens a panel of your choice when its swipes arrive in this order within the time limit.")}
              </p>
              ${(cfg.gesture_sequences || []).length ? html`
                <div class="gesture-row gesture-row-labels">
                  <span>${t("Swipes, in order")}</span>
                  <span>${t("Within (s)")}</span>
                  <span>${t("Open panel")}</span>
                  <span></span>
                </div>
              ` : ""}
              ${(cfg.gesture_sequences || []).map((seq, i) => this._renderGestureSequence(seq, i, panelOptions))}
              <ha-button appearance="plain" @click=${() => this._updateGestureSequences((list) => [
                ...list, { sequence: ["swipe_left", "swipe_right"], timeframe: 3, open: "" },
              ])}>
                ${t("Add sequence")}
              </ha-button>
              <div class="field-hint">${t("Swipes: {names}, separated by commas. The panel opens when the last swipe arrives within the time limit after the first.").replace("{names}", GESTURE_NAMES.join(", "))}</div>
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Notifications")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Configure audible alerts for startup and incoming notifications, and set a do-not-disturb window to silence sounds during specific hours.")}
              </p>
              ${checkbox(this, "dc-sound_on_startup", "sound_on_startup", cfg, t("Sound on startup"),
                t("Play a short audible tone when the display successfully connects to Home Assistant after a restart or power cycle"))}
              ${checkbox(this, "dc-sound_on_notification", "sound_on_notification", cfg, t("Sound on notification"),
                t("Play an audible alert tone whenever a new notification is received from Home Assistant to draw attention to the display"))}
              ${intField(this, "dc-persistent_sound_interval", "persistent_sound_interval", cfg, t("Persistent sound interval (seconds)"), 5, 1, 600,
                t("How often the alert sound repeats while a persistent notification waits to be dismissed (min 1, max 600)."))}
              ${checkbox(this, "dc-use_do_not_disturb", "use_do_not_disturb", cfg, t("Use do not disturb"),
                t("Silence all sounds during the quiet hours below. Notifications are still shown on the display."))}
              ${cfg.use_do_not_disturb ? html`
                <div class="form-group">
                  <label>${t("Quiet hours")}</label>
                  <div class="time-range-row">
                    <input
                      id="dc-quiet_hours_start"
                      type="time"
                      class="native-input"
                      .value=${String(cfg.quiet_hours_start ?? "")}
                      @input=${(e) => {
                        this._deviceConfigForm = { ...this._deviceConfigForm, quiet_hours_start: e.target.value };
                        this.requestUpdate();
                      }}
                    />
                    <span class="time-range-sep">&ndash;</span>
                    <input
                      id="dc-quiet_hours_end"
                      type="time"
                      class="native-input"
                      .value=${String(cfg.quiet_hours_end ?? "")}
                      @input=${(e) => {
                        this._deviceConfigForm = { ...this._deviceConfigForm, quiet_hours_end: e.target.value };
                        this.requestUpdate();
                      }}
                    />
                  </div>
                  <div class="field-hint">${t("No sounds are played within this time window. Overnight ranges such as 22:00–07:00 are supported. Leave both fields empty to never silence sounds.")}</div>
                </div>
              ` : ""}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Idle & Wake Behavior")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Controls what happens when the idle page is shown and what is restored when the user wakes the device again.")}
              </p>
              <div class="form-group">
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
                <div class="field-hint">${t("Controls whether the panel you were on before the idle page is restored when waking. With Auto display-off, the display can still turn off and wake without any panel switch.")}</div>
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
                    <div class="field-hint">${t("Maximum age in seconds before falling back to the home panel.")}</div>
                  </div>
                ` : ""}
              </div>
              ${intField(this, "dc-auto_navigate_home_timeout", "auto_navigate_home_timeout", cfg, t("Return to the home panel after (seconds)"), 0, 0, 86400,
                t("Go back to the home panel after this many seconds without interaction on another panel. Set it shorter than the dimming and display-off timeouts. 0 = off."))}
              ${intField(this, "dc-hub_idle_timeout", "hub_idle_timeout", cfg, t("Idle page fallback (seconds)"), 0, 0, 86400,
                t("Open the idle page after this many seconds without interaction, also when the device doesn't report its own page timeout (for example with auto page off). 0 = off."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Time & Date")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Choose how time and date are shown on the clock, clock-two and weather pages. Leave at Default to use the integration-wide setting.")}
              </p>
              ${formatSelectField(this, "dc-time_format", "time_format", cfg, t("Time format"), TIME_FORMAT_OPTIONS,
                t("US 12-hour shows e.g. 2:30 PM. Custom strftime directives: %H = hour (24h), %I = hour (12h), %M = minutes, %p = AM/PM."))}
              ${formatSelectField(this, "dc-date_format", "date_format", cfg, t("Date format"), DATE_FORMAT_OPTIONS,
                t("US numeric shows e.g. 03/14/2026. Empty keeps the locale-based layout from the Language setting."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Panel Assignments")}</summary>
            <div class="config-section-body"><summary>${t("Panel Assignments")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Choose which panels play the home and idle roles. Leave unset to keep the current panel.")}
              </p>
              ${selectField(this, "dc-home_panel", "home_panel", cfg, t("Home panel"), panelOptions, (v) => v,
                t("The panel shown when the user navigates home or when the idle page is exited without a snapshot to restore"))}
              ${selectField(this, "dc-idle_panel", "idle_panel", cfg, t("Idle Panel"), panelOptions, (v) => v,
                t("The idle page opened by Automatic page switching after the page timeout"))}
              <div class="form-group">
                <label for="dc-idle_panel_extra">${t("Extra idle panels (carousel)")}</label>
                <input
                  id="dc-idle_panel_extra"
                  class="native-input"
                  .value=${cfg.idle_panel_extra ?? ""}
                  @input=${(e) => {
                    this._deviceConfigForm = { ...this._deviceConfigForm, idle_panel_extra: e.target.value };
                  }}
                />
                <div class="field-hint">${t("Comma-separated panel keys. Each automatic page switch advances to the next panel in this list, cycling through them (screensaver carousel).")}</div>
              </div>
            </div>
          </details>


          </div>
        </form>

        <div slot="footer" class="footer-wrapper">
          <div class="footer-toggle-wrapper">
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
      </ha-dialog>
    `;
  }

  /** Replace the gesture sequence list with `update(list)` (a copy is passed in). */
  _updateGestureSequences(update) {
    const list = [...(this._deviceConfigForm?.gesture_sequences || [])];
    this._deviceConfigForm = { ...this._deviceConfigForm, gesture_sequences: update(list) };
    this.requestUpdate();
  }

  _renderGestureSequence(seq, index, panelOptions) {
    const setField = (key, value) => this._updateGestureSequences((list) => {
      list[index] = { ...list[index], [key]: value };
      return list;
    });
    return html`
      <div class="gesture-row">
        <input
          id="dc-gesture_sequence_${index}"
          class="native-input"
          .value=${(seq.sequence || []).join(", ")}
          placeholder=${GESTURE_NAMES.slice(0, 2).join(", ")}
          @change=${(e) => setField("sequence", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
        />
        ${renderNumberInput(`dc-gesture_timeframe_${index}`, seq.timeframe ?? 3, (raw) => {
          const v = parseInt(raw, 10);
          setField("timeframe", isNaN(v) ? 3 : v);
        }, { min: 1, max: 60 })}
        ${renderSelect(`dc-gesture_open_${index}`, seq.open ?? "", panelOptions, (v) => setField("open", v))}
        <ha-icon-button
          class="gesture-remove"
          .label=${t("Remove sequence")}
          title=${t("Remove sequence")}
          @click=${() => this._updateGestureSequences((list) => list.filter((_, i) => i !== index))}
        ><ha-icon icon="mdi:delete-outline"></ha-icon></ha-icon-button>
      </div>
    `;
  }

  _dispatchSave() {
    this._emit("dialog-save", { config: this._deviceConfigForm });
  }
}

customElements.define("nspanel-dialog-device-config", DeviceConfigDialog);
export { DeviceConfigDialog };
