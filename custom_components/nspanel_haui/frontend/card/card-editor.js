/**
 * NSPanel HAUI - the dashboard card's settings in Home Assistant's card
 * editor: which device, and whether it shows its home panel or its live
 * screen. Loaded when the card editor opens (card.js `getConfigElement`).
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { createApiClient } from '../api/client.js';
import { fetchTranslations, getLanguage, t } from '../localize.js';

export class NSPanelHauiCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _devices: { state: true },
      _error: { state: true },
    };
  }

  constructor() {
    super();
    /** @type {any} */
    this.hass = null;
    /** @type {Object<string, any>|null} */
    this._config = null;
    /** @type {string[]|null} device names, once loaded */
    this._devices = null;
    this._error = '';
    this._loading = false;
  }

  /** @param {Object<string, any>} config */
  setConfig(config) {
    this._config = config;
  }

  updated() {
    if (this.hass && !this._loading) this._load();
  }

  async _load() {
    this._loading = true;
    const api = createApiClient(() => this.hass);
    try {
      const [devices] = await Promise.all([
        api.card.devices(),
        fetchTranslations(api, getLanguage(this.hass)),
      ]);
      this._devices = devices.map((device) => device.name);
    } catch (err) {
      this._error = /** @type {any} */ (err)?.message || String(err);
    }
  }

  _schema() {
    const names = [...(this._devices || [])];
    // A device that is not running now stays selected.
    const current = this._config?.device;
    if (current && !names.includes(current)) names.push(current);
    return [
      {
        name: 'device',
        required: true,
        selector: { select: { mode: 'dropdown', options: names.map((name) => ({ value: name, label: name })) } },
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
            ],
          },
        },
      },
    ];
  }

  /** @param {{ name: string }} field */
  _label(field) {
    return field.name === 'device' ? t('Device') : t('Show');
  }

  /** @param {CustomEvent} event */
  _changed(event) {
    event.stopPropagation();
    const config = { ...this._config, ...event.detail.value };
    this._config = config;
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    if (!this.hass || !this._config || !this._devices && !this._error) return nothing;
    return html`
      ${this._error ? html`<ha-alert alert-type="error">${this._error}</ha-alert>` : nothing}
      ${this._devices && !this._devices.length
        ? html`<ha-alert alert-type="info">${t('No NSPanel HAUI device is running')}</ha-alert>`
        : nothing}
      <ha-form
        .hass=${this.hass}
        .data=${{ mode: 'home', ...this._config }}
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
