/**
 * NSPanel HAUI - Editor - Device Config dialog.
 *
 * Proper Lit custom element replacing the old renderDeviceConfigDialog() function.
 * Uses ha-dialog / ha-dialog-header / ha-dialog-footer with ha-button.
 * Communicates form changes via CustomEvent.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { LOCALE_OPTIONS, DEBUG_LEVELS } from '../constants.js';
import { renderEntityPicker } from '../haui-entity.js';

/**
 * Render a checkbox row used within the device config form.
 * Fires `@change` to update internal state.
 */
function checkbox(host, id, key, cfg, label, hint = "") {
  return html`
    <div class="checkbox-row">
      <input
        type="checkbox"
        id=${id}
        .checked=${Boolean(cfg[key])}
        @change=${(e) => {
          host._deviceConfigForm = { ...host._deviceConfigForm, [key]: e.target.checked };
          host.requestUpdate();
        }}
      />
      <label for=${id}>${label}${hint ? html` <span class="hint">${hint}</span>` : ""}</label>
    </div>
  `;
}

/**
 * Render a select/combobox field within the device config form.
 * Fires `@selected` to update internal state.
 */
function selectField(host, id, key, cfg, label, options, parser = (v) => v) {
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

  static styles = [haStyle, haStyleDialog, editorStyles];

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

    const panelOptions = [
      { value: "", label: "- None -" },
      ...this.devicePanels.filter(p => p.key).map(p => ({ value: p.key, label: p.key })),
    ];

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title="Device Settings"
        .preventScrimClose=${this.saving}
      >

        <form id="device-config-form" @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">
            <div class="form-group">
              <label for="dc-friendly_name">
                Friendly Name
                <span class="hint">(optional, defaults to device name)</span>
              </label>
              <ha-input
                id="dc-friendly_name"
                style="width: 100%"
                .value=${cfg.friendly_name || ""}
                @input=${(e) => {
                  this._deviceConfigForm = {
                    ...this._deviceConfigForm,
                    friendly_name: e.target.value,
                  };
                  this.requestUpdate();
                }}
              ></ha-input>
            </div>

            <details class="config-section">
              <summary>Panel Assignments</summary>
              <div class="config-section-body">
                ${selectField(this, "dc-home_panel", "home_panel", cfg, "Home Panel", panelOptions)}
                ${selectField(this, "dc-sleep_panel", "sleep_panel", cfg, "Sleep Panel", panelOptions)}
                ${selectField(this, "dc-wakeup_panel", "wakeup_panel", cfg, "Wakeup Panel", panelOptions)}
              </div>
            </details>

            <details class="config-section">
              <summary>Sleep and Wakeup</summary>
              <div class="config-section-body">
                ${checkbox(this, "dc-home_on_wakeup", "home_on_wakeup", cfg, "Home on wakeup")}
                ${checkbox(this, "dc-home_on_first_touch", "home_on_first_touch", cfg, "Home on first touch")}
                ${checkbox(this, "dc-home_only_when_on", "home_only_when_on", cfg, "Home only when on")}
                ${checkbox(this, "dc-home_on_button_toggle", "home_on_button_toggle", cfg, "Home on button toggle")}
                ${checkbox(this, "dc-always_return_to_home", "always_return_to_home", cfg, "Always return to home")}
                <div class="form-group">
                  <label for="dc-return_to_home_after_seconds">
                    Return to home after (seconds)
                    <span class="hint">(0 = disabled)</span>
                  </label>
                  <ha-input
                    id="dc-return_to_home_after_seconds"
                    type="number"
                    .inputMode="numeric"
                    .value=${String(cfg.return_to_home_after_seconds || 0)}
                    @input=${(e) => {
                      const v = parseInt(e.target.value, 10);
                      this._deviceConfigForm = {
                        ...this._deviceConfigForm,
                        return_to_home_after_seconds: isNaN(v) ? 0 : v,
                      };
                      this.requestUpdate();
                    }}
                  ></ha-input>
                </div>
              </div>
            </details>

            <details class="config-section">
              <summary>Navigation Buttons</summary>
              <div class="config-section-body">
                ${checkbox(this, "dc-show_home_button", "show_home_button", cfg, "Show home button")}
                ${checkbox(this, "dc-show_sleep_button", "show_sleep_button", cfg, "Show sleep button")}
                ${checkbox(this, "dc-show_notifications_button", "show_notifications_button", cfg, "Show notifications button")}
              </div>
            </details>

            <details class="config-section">
              <summary>Hardware Buttons</summary>
              <div class="config-section-body">
                ${renderEntityPicker(this, {
                  id: "dc-button_left_entity",
                  value: cfg.button_left_entity,
                  label: "Left Button Entity",
                  hint: "(optional)",
                  hass: this.hass,
                })}
                ${renderEntityPicker(this, {
                  id: "dc-button_right_entity",
                  value: cfg.button_right_entity,
                  label: "Right Button Entity",
                  hint: "(optional)",
                  hass: this.hass,
                })}
                ${checkbox(this, "dc-use_relay_left", "use_relay_left", cfg, "Use Relay Left", "(physical relay follows left button press)")}
                ${checkbox(this, "dc-use_relay_right", "use_relay_right", cfg, "Use Relay Right", "(physical relay follows right button press)")}
              </div>
            </details>

            <details class="config-section">
              <summary>Sounds</summary>
              <div class="config-section-body">
                ${checkbox(this, "dc-sound_on_startup", "sound_on_startup", cfg, "Sound on startup")}
                ${checkbox(this, "dc-sound_on_notification", "sound_on_notification", cfg, "Sound on notification")}
              </div>
            </details>

            <details class="config-section">
              <summary>Language</summary>
              <div class="config-section-body">
                ${selectField(this, "dc-locale", "locale", cfg, "Language", LOCALE_OPTIONS)}
              </div>
            </details>

            <details class="config-section">
              <summary>Debug</summary>
              <div class="config-section-body">
                ${selectField(this, "dc-debug_level", "debug_level", cfg, "Debug Level", DEBUG_LEVELS, (v) => parseInt(v, 10))}
              </div>
            </details>

            <hr style="border: none; border-top: 1px solid var(--divider-color, #e0e0e0); margin: 12px 0 16px 0;">

            <div class="form-group" style="margin-bottom: 16px;">
            <div class="checkbox-row">
              <ha-switch
                id="dc-enabled"
                ?checked=${Boolean(cfg.enabled)}
                @change=${(e) => {
                  this._deviceConfigForm = { ...this._deviceConfigForm, enabled: e.target.checked };
                  this.requestUpdate();
                }}
              ></ha-switch>
              <label for="dc-enabled">Device Enabled</label>
            </div>
            <span class="field-hint">Disabled devices are skipped by HAUI at runtime</span>
          </div>


          </div>
        </form>

        <ha-dialog-footer slot="footer">
          <ha-button slot="secondaryAction" appearance="plain" @click=${this._dispatchClose}>
            Cancel
          </ha-button>
          <ha-button
            slot="primaryAction"
            variant="brand"
            @click=${this._dispatchSave}
            ?disabled=${this.saving}
          >
            ${this.saving ? "Saving…" : "Save"}
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchSave() {
    // Attach current form state so the editor can read it
    this.dispatchEvent(new CustomEvent("dialog-save", {
      detail: { config: this._deviceConfigForm },
    }));
  }
}

customElements.define("ha-dialog-device-config", DeviceConfigDialog);
export { DeviceConfigDialog };
