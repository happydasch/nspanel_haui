// @ts-check
/**
 * NSPanel HAUI - the dashboard card's settings in Home Assistant's card
 * editor: which device, what it shows, and how big.
 * Loaded when the card editor opens (card.js `getConfigElement`).
 *
 * Four fields, and nothing that hides part of the card: a card is the panel
 * (its screen, its frame, the row under it) or, in `tile` mode, the row alone.
 *
 * The device selector stores the panel's Home Assistant `device_id` together
 * with its hub name, so a device renamed in the editor keeps every dashboard
 * working (web/card.py resolves the id). A disabled device stays selectable:
 * its card says it is disabled and starts working when it is enabled again.
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { createApiClient } from '../api/client.js';
import { fetchTranslations, getLanguage, t } from '../localize.js';
import { dashboardComponentStyles } from '../styles/dashboard-component-styles.js';
import { dashboardTokens } from '../styles/tokens.js';
import { button } from '../ui/button.js';

/** @typedef {import('../api/types.js').CardDevice} CardDevice */

export class NSPanelHauiCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _devices: { state: true },
      _error: { state: true },
    };
  }

  static styles = [dashboardTokens, dashboardComponentStyles];

  constructor() {
    super();
    /** @type {any} */
    this.hass = null;
    /** @type {Object<string, any>|null} */
    this._config = null;
    /** @type {CardDevice[]|null} the hub's devices, once loaded */
    this._devices = null;
    this._error = '';
    this._loading = false;
  }

  /** @param {Object<string, any>} config */
  setConfig(config) {
    this._config = config;
  }

  updated() {
    if (this.hass && !this._loading && !this._devices && !this._error) this._load();
  }

  async _load() {
    if (!this.hass) return;
    this._loading = true;
    this._error = '';
    const api = createApiClient(() => this.hass);
    try {
      const [devices] = await Promise.all([
        api.card.devices(),
        fetchTranslations(api, getLanguage(this.hass)),
      ]);
      this._devices = devices;
    } catch (err) {
      this._error = /** @type {any} */ (err)?.message || String(err);
    } finally {
      // A failed load can be tried again from the error's Retry button.
      this._loading = false;
      this.requestUpdate();
    }
  }

  _schema() {
    const devices = [...(this._devices || [])];
    // A device that no longer exists stays selected, so the card can say why.
    const current = this._config?.device;
    if (current && !devices.some((device) => device.name === current)) {
      devices.push({ entry_id: '', name: current, device_id: null, enabled: false });
    }
    return [
      {
        name: 'device',
        required: true,
        selector: {
          select: {
            mode: 'dropdown',
            options: devices.map((device) => ({
              value: device.name,
              label: device.enabled
                ? device.name
                : t('{name} (disabled)').replace('{name}', device.name),
            })),
          },
        },
      },
      {
        name: 'mode',
        required: true,
        selector: {
          select: {
            mode: 'list',
            options: [
              { value: 'home', label: t('Home panel') },
              { value: 'live', label: t('Live screen') },
              { value: 'tile', label: t('Status tile') },
            ],
          },
        },
      },
      { name: 'title', selector: { text: {} } },
      {
        name: 'scale',
        selector: {
          number: { min: 20, max: 100, step: 5, mode: 'slider', unit_of_measurement: '%' },
        },
      },
    ];
  }

  /** @param {{ name: string }} field */
  _label(field) {
    if (field.name === 'device') return t('Device');
    if (field.name === 'mode') return t('Show');
    if (field.name === 'title') return t('Title');
    return t('Screen size');
  }

  /** @param {CustomEvent} event */
  _changed(event) {
    event.stopPropagation();
    const value = /** @type {Object<string, any>} */ (event.detail.value);
    const config = { ...this._config, ...value };
    // The device's id travels with its name, so a rename keeps this card working.
    if (value.device !== undefined) {
      const device = (this._devices || []).find((entry) => entry.name === value.device);
      if (device?.device_id) config.device_id = device.device_id;
      else delete config.device_id;
    }
    this._config = config;
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  /** The form's data. */
  _data() {
    return { mode: 'home', scale: 100, ...this._config };
  }

  // The vendored Lit's own typings are not exact; a template is what it returns.
  /** @returns {any} */
  render() {
    if (!this.hass || !this._config || (!this._devices && !this._error)) return nothing;
    return html`
      ${this._error
        ? html`<ha-alert alert-type="error">
            ${this._error}
            ${button({ label: t('Retry'), onClick: () => this._load() })}
          </ha-alert>`
        : nothing}
      ${this._devices && !this._devices.length
        ? html`<ha-alert alert-type="info">${t('No NSPanel HAUI device is set up')}</ha-alert>`
        : nothing}
      <ha-form
        .hass=${this.hass}
        .data=${this._data()}
        .schema=${this._schema()}
        .computeLabel=${(/** @type {{ name: string }} */ field) => this._label(field)}
        @value-changed=${this._changed}
      ></ha-form>
    `;
  }
}

if (!customElements.get('nspanel-haui-card-editor')) {
  customElements.define('nspanel-haui-card-editor', NSPanelHauiCardEditor);
}

