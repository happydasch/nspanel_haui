/**
 * NSPanel HAUI - Editor - Device Config dialog.
 *
 * Proper Lit custom element replacing the old renderDeviceConfigDialog() function.
 * Uses ha-dialog / ha-dialog-header / ha-dialog-footer with ha-button.
 * Communicates form changes via CustomEvent.
 */
import { LitElement, html, css } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { LOCALE_OPTIONS, DEBUG_LEVELS } from '../constants.js';
import { renderEntityPicker } from '../haui-entity.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';

/**
 * Render a toggle (ha-switch) row used within the device config form.
 * Fires `@change` to update internal state.
 */
function checkbox(host, id, key, cfg, label, hint = "") {
  return html`
    <div class="checkbox-wrap">
      <div class="checkbox-row">
        <ha-switch
          id=${id}
          ?checked=${Boolean(cfg[key])}
          @change=${(e) => {
            host._deviceConfigForm = { ...host._deviceConfigForm, [key]: e.target.checked };
            host.requestUpdate();
          }}
        ></ha-switch>
        <label for=${id}>${label}</label>
      </div>
      ${hint ? html`<div class="field-hint">${hint}</div>` : ""}
    </div>
  `;
}

/**
 * Render a select/combobox field within the device config form.
 * Fires `@selected` to update internal state.
 */
function selectField(host, id, key, cfg, label, options, parser = (v) => v, hint = "") {
  return html`
    <div class="form-group">
      <label for=${id}>${label}</label>
      <ha-select
        id=${id}
        .value=${String(cfg[key] ?? "")}
        .options=${options}
        @selected=${(e) => {
          host._deviceConfigForm = { ...host._deviceConfigForm, [key]: parser(e.detail.value) };
          host.requestUpdate();
        }}
      ></ha-select>
      ${hint ? html`<div class="field-hint">${hint}</div>` : ""}
    </div>
  `;
}

class DeviceConfigDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      config: { type: Object },
      devicePanels: { type: Array },
      saving: { type: Boolean },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles, css`
    .footer-toggle-wrapper label {
      margin: 0;
      font-weight: 500;
      font-size: 0.92em;
    }
  `];

  constructor() {
    super();
    this.open = false;
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
            ${t("Configure how this device behaves: language and diagnostics, audible alerts, hardware buttons, navigation, sleep/wakeup, and which panels appear in each display state.")}
          </p>

          <details class="config-section">
            <summary>${t("General Settings")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("General device behavior: display language, diagnostic logging verbosity, and audible alerts for startup and notifications.")}
              </p>
              ${selectField(this, "dc-locale", "locale", cfg, t("Language"), LOCALE_OPTIONS, (v) => v,
                t("The locale determines how dates, times, and numbers are formatted on the display, and which language is used for built-in text labels"))}
              ${selectField(this, "dc-debug_level", "debug_level", cfg, t("Debug Level"), DEBUG_LEVELS, (v) => parseInt(v, 10),
                t("Controls the verbosity of diagnostic logging sent to the Home Assistant logs: Off = no debug output, Basic = key lifecycle events, Verbose = all commands and data exchanged with the display"))}
              ${checkbox(this, "dc-sound_on_startup", "sound_on_startup", cfg, t("Sound on startup"),
                t("Play a short audible tone when the display successfully connects to Home Assistant after a restart or power cycle"))}
              ${checkbox(this, "dc-sound_on_notification", "sound_on_notification", cfg, t("Sound on notification"),
                t("Play an audible alert tone whenever a new notification is received from Home Assistant to draw attention to the display"))}
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
              ${checkbox(this, "dc-show_sleep_button", "show_sleep_button", cfg, t("Show sleep button"),
                t("Show a sleep button on the home panel that lets users manually put the display into sleep mode"))}
              ${checkbox(this, "dc-show_notifications_button", "show_notifications_button", cfg, t("Show notifications button"),
                t("Show a notifications button on supported panels that indicates and provides access to any pending notifications"))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Panel Assignments")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Choose which panels appear in specific display states. Leave unset to keep the current panel.")}
              </p>
              ${selectField(this, "dc-home_panel", "home_panel", cfg, t("Home panel"), panelOptions, (v) => v,
                t("The panel shown when the user navigates home or after dim/sleep returns"))}
              ${selectField(this, "dc-sleep_panel", "sleep_panel", cfg, t("Sleep Panel"), panelOptions, (v) => v,
                t("The panel shown when the display enters sleep mode"))}
              ${selectField(this, "dc-wakeup_panel", "wakeup_panel", cfg, t("Wakeup Panel"), panelOptions, (v) => v,
                t("The panel shown briefly when the display wakes from sleep"))}
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

              ${!(cfg.use_relay_left ?? true) ? renderEntityPicker(this, {
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

              ${!(cfg.use_relay_right ?? true) ? renderEntityPicker(this, {
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
                t("When enabled, pressing a hardware button resets the inactivity timer and prevents the display from dimming or sleeping. Disable to allow buttons to work without delaying display sleep."))}
            </div>
          </details>

          <details class="config-section">
            <summary>${t("Sleep and Wakeup")}</summary>
            <div class="config-section-body">
              <p class="config-section-intro">
                ${t("Controls how the display behaves when waking from dimmed or sleep state.")}
              </p>
              <div class="form-group">
                <label>${t("Snapshot max age")}</label>
                <ha-select
                  id="dc-snapshot_max_age_mode"
                  .value=${snapMode}
                  .options=${[
                    { value: "-1", label: t("Always restore") },
                    { value: "0", label: t("Never restore") },
                    { value: "custom", label: t("Custom time limit...") },
                  ]}
                  @selected=${(e) => {
                    const mode = e.detail.value;
                    let v;
                    if (mode === "-1") v = -1;
                    else if (mode === "0") v = 0;
                    else v = (this._deviceConfigForm?.snapshot_max_age_seconds > 0)
                      ? this._deviceConfigForm.snapshot_max_age_seconds
                      : 60;
                    this._deviceConfigForm = { ...this._deviceConfigForm, snapshot_max_age_seconds: v };
                    this.requestUpdate();
                  }}
                ></ha-select>
                <div class="field-hint">${t("Controls whether the last viewed panel is restored when waking from sleep or dimmed state.")}</div>
                ${snapMode === "custom" ? html`
                  <div style="margin-top: 8px;">
                    <ha-input
                      id="dc-snapshot_max_age_custom"
                      type="number"
                      .inputMode="numeric"
                      .value=${String(snapCustomVal)}
                      @input=${(e) => {
                        const v = parseInt(e.target.value, 10);
                        this._deviceConfigForm = {
                          ...this._deviceConfigForm,
                          snapshot_max_age_seconds: isNaN(v) || v < 1 ? 60 : v,
                        };
                        this.requestUpdate();
                      }}
                    ></ha-input>
                    <div class="field-hint">${t("Maximum age in seconds before falling back to the home panel.")}</div>
                  </div>
                ` : ""}
              </div>
            </div>
          </details>

          </div>
        </form>

        <div slot="footer" class="footer-wrapper">
          <div class="footer-toggle-wrapper">
            <ha-switch
              id="dc-enabled"
              ?checked=${Boolean(cfg.enabled)}
              @change=${(e) => {
                this._deviceConfigForm = { ...this._deviceConfigForm, enabled: e.target.checked };
                this.requestUpdate();
              }}
            ></ha-switch>
            <label for="dc-enabled" style="margin-inline-start:8px;">${t("Device Enabled")}</label>
          </div>
          ${this._validationError ? html`
            <div class="config-validation-error" role="alert" style="color:var(--error-color,#db4437);margin:8px 0;">
              ${this._validationError}
            </div>
          ` : ""}
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

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchSave() {
    const cfg = this._deviceConfigForm || {};

    // check validity of values to store if needed here, on error
    // this.requestUpdate() to show error message in the dialog
    // and return early without dispatching save event

    this._validationError = "";
    this.dispatchEvent(new CustomEvent("dialog-save", {
      detail: { config: this._deviceConfigForm },
    }));
  }
}

customElements.define("ha-dialog-device-config", DeviceConfigDialog);
export { DeviceConfigDialog };
