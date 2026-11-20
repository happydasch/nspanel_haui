// @ts-check
/**
 * NSPanel HAUI - the dashboard card's settings in Home Assistant's card
 * editor: every panel of the hub or one of them, the display size, and whether
 * to mirror the real panel. Loaded when the card editor opens (card.js `getConfigElement`).
 *
 * The card's config is read through `normalizeConfig`, so a card saved by the
 * first implementation (`mode: overview`, `home`, `live` or `tile`) is edited
 * as the fleet or device card it now is.
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { createApiClient } from '../api/client.js';
import { fetchTranslations, getLanguage, t } from '../localize.js';
import { dashboardComponentStyles } from '../styles/dashboard-component-styles.js';
import { dashboardTokens } from '../styles/tokens.js';
import { button } from '../ui/button.js';
import { normalizeConfig } from './card.js';

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
    const config = normalizeConfig(this._config || {});
    const devices = [...(this._devices || [])];
    // A device that no longer exists stays selected, so the card can say why.
    const current = this._config?.device;
    if (current && !devices.some((device) => device.name === current)) {
      devices.push({ entry_id: '', name: current, device_id: null, enabled: false });
    }
    const schema = /** @type {any[]} */ ([
      {
        name: 'mode',
        required: true,
        selector: {
          select: {
            mode: 'list',
            options: [
              { value: 'fleet', label: t('All panels of the hub') },
              { value: 'device', label: t('One panel') },
            ],
          },
        },
      },
    ]);
    if (config.mode === 'device') {
      schema.push({
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
      });
    }
    schema.push(
      {
        name: 'display_mode',
        required: true,
        selector: {
          select: {
            mode: 'list',
            options: [
              { value: 'big', label: t('Big preview') },
              { value: 'small', label: t('Small preview') },
              { value: 'status', label: t('Status only') },
            ],
          },
        },
      },
      {
        name: 'live',
        selector: { boolean: {} },
        description: t('Show what the real panel shows instead of its home panel'),
      },
      { name: 'title', selector: { text: {} } },
    );
    if (config.display_mode === 'big') {
      schema.push({
        name: 'scale',
        selector: {
          number: { min: 20, max: 100, step: 5, mode: 'slider', unit_of_measurement: '%' },
        },
      });
    }
    return schema;
  }

  /** @param {{ name: string }} field */
  _label(field) {
    if (field.name === 'mode') return t('Show');
    if (field.name === 'device') return t('Panel');
    if (field.name === 'display_mode') return t('Display mode');
    if (field.name === 'live') return t('Live screen');
    if (field.name === 'title') return t('Title');
    return t('Screen size');
  }

  /** @param {CustomEvent} event */
  _changed(event) {
    event.stopPropagation();
    const value = /** @type {Object<string, any>} */ (event.detail.value);
    const merged = { ...this._config, ...value };
    // The device's id travels with its name, so a rename keeps this card working.
    if (value.device !== undefined) {
      const device = (this._devices || []).find((entry) => entry.name === value.device);
      if (device?.device_id) merged.device_id = device.device_id;
      else delete merged.device_id;
    }
    const config = normalizeConfig(merged);
    this._config = config;
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  /** The form's data. */
  _data() {
    return { live: false, scale: 100, ...normalizeConfig(this._config || {}) };
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
