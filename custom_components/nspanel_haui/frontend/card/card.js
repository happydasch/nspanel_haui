/**
 * NSPanel HAUI - the dashboard card: one device's screen on a Home Assistant
 * dashboard, for every signed-in user.
 *
 * `mode: home` shows the device's home panel as the hub keeps it running for
 * the cards; `mode: live` shows what the real panel shows. Both are the hub's
 * own display output replayed in the Nextion simulator, view-only
 * (virtual/card-sessions.js, web/card.py). This module loads on every
 * dashboard page (web/editor.py), so the display code loads only once a card
 * is shown.
 *
 *   type: custom:nspanel-haui-card
 *   device: Kitchen
 *   mode: home   # or live
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { createApiClient } from '../api/client.js';
import { fetchTranslations, getLanguage, t } from '../localize.js';
import { cardStyles } from '../styles/card-styles.js';
import { dashboardComponentStyles } from '../styles/dashboard-component-styles.js';
import { previewStyles } from '../styles/preview-styles.js';
import { dashboardTokens } from '../styles/tokens.js';
import { badge } from '../ui/badge.js';
import { emptyState } from '../ui/empty-state.js';
import { icon } from '../ui/icon.js';

export const CARD_TYPE = 'nspanel-haui-card';
export const CARD_MODES = ['home', 'live'];
// The hub ended the subscription (a reload, a Home Assistant reconnect).
export const RESUBSCRIBE_DELAY_MS = 5_000;
// The device's hub app may still be starting: try again.
export const RETRY_DELAY_MS = 30_000;
// The screen fills the card's width, but never more than this share of the window's height.
const MAX_HEIGHT_SHARE = 0.8;
const DISCONNECTED_BRIGHTNESS = 0.5;

/**
 * @typedef {Object} CardConfig
 * @property {string} [device]
 * @property {'home'|'live'} mode
 */

/** @type {Promise<any>|null} */
let displayModules = null;

/** The sessions and the simulator, loaded with the first card shown. */
function loadDisplayModules() {
  displayModules ??= Promise.all([
    import('../virtual/card-sessions.js'),
    import('../previews/simulator.js'),
  ]).then(
    ([sessions, simulator]) => ({ ...sessions, ...simulator }),
    (err) => {
      displayModules = null;
      throw err;
    },
  );
  return displayModules;
}

/** @param {string} code - an error the hub sent the session */
function errorText(code) {
  if (code === 'no_home_panel') return t('This device has no home panel');
  if (code === 'start_failed') return t('The preview could not be started');
  return code;
}

export class NSPanelHauiCard extends LitElement {
  static get properties() {
    return {
      _config: { state: true },
      _message: { state: true },
    };
  }

  static styles = [dashboardTokens, dashboardComponentStyles, previewStyles, cardStyles];

  static async getConfigElement() {
    await import('./card-editor.js');
    return document.createElement('nspanel-haui-card-editor');
  }

  /** @param {any} hass */
  static async getStubConfig(hass) {
    const devices = await createApiClient(() => hass).card.devices();
    return { device: devices.length ? devices[0].name : '', mode: 'home' };
  }

  constructor() {
    super();
    /** @type {any} */
    this._hass = null;
    /** @type {CardConfig|null} */
    this._config = null;
    /** @type {any} */
    this._session = null;
    // The last screen, shown while the card subscribes again.
    /** @type {any} */
    this._kept = null;
    /** @type {any} */
    this._view = null;
    /** @type {{ iconName: string, title: string }|null} */
    this._message = null;
    /** @type {object|null} */
    this._run = null;
    /** @type {ReturnType<typeof setTimeout>|undefined} */
    this._retry = undefined;
    this._width = 0;
    /** @type {ResizeObserver|null} */
    this._resizeObserver = null;
    // Home Assistant reconnected (it restarted): the hub may have restarted too.
    this._onReconnect = () => this._schedule(RESUBSCRIBE_DELAY_MS);
  }

  // Home Assistant sets hass on every state change; the screen comes from the
  // session, which reports its own changes.
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._restart();
  }

  get hass() {
    return this._hass;
  }

  /** @param {any} config */
  setConfig(config) {
    if (!config || typeof config !== 'object') throw new Error(t('Invalid configuration'));
    const mode = config.mode ?? 'home';
    if (!CARD_MODES.includes(mode)) {
      throw new Error(t('Unknown mode: {mode}').replace('{mode}', String(mode)));
    }
    const changed = this._config?.device !== config.device || this._config?.mode !== mode;
    this._config = { ...config, mode };
    if (changed) {
      this._kept = null;
      this._message = null;
      this._restart();
    }
  }

  getCardSize() {
    return this._session?.orientation === 'portrait' ? 12 : 6;
  }

  getGridOptions() {
    return { columns: 'full', rows: 'auto', min_columns: 6 };
  }

  connectedCallback() {
    super.connectedCallback();
    if (typeof ResizeObserver === 'function') {
      this._resizeObserver = new ResizeObserver((entries) => {
        this._width = entries[0].contentRect.width;
        this.requestUpdate();
      });
      this._resizeObserver.observe(this);
    }
    this._restart();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._stop();
  }

  // -- session ----------------------------------------------------------------

  _stop() {
    clearTimeout(this._retry);
    this._run = null;
    this._hass?.connection?.removeEventListener?.('ready', this._onReconnect);
    const session = this._session;
    this._session = null;
    // The hub may have dropped the subscription already (it ended it).
    if (session) session.stop().catch(() => {});
  }

  /** Subscribe again after `delay` ms, keeping the screen until the new one draws. */
  _schedule(delay) {
    clearTimeout(this._retry);
    this._retry = setTimeout(() => this._restart(true), delay);
  }

  /** @param {string} title */
  _fail(title) {
    this._message = { iconName: 'alert', title };
    this._schedule(RETRY_DELAY_MS);
  }

  /** @param {boolean} [again] - the same device and mode: keep the last screen */
  async _restart(again = false) {
    const kept = again ? (this._session?.ready ? this._session : this._kept) : null;
    this._stop();
    this._kept = kept;
    const config = this._config;
    const hass = this._hass;
    if (!this.isConnected || !hass || !config) return;
    if (!config.device) {
      this._message = { iconName: 'screen', title: t('Choose a device in the card settings') };
      return;
    }
    const device = config.device;
    const run = {};
    this._run = run;
    const api = createApiClient(() => this._hass);
    try {
      const [devices, view] = await Promise.all([
        api.card.devices(),
        loadDisplayModules(),
        fetchTranslations(api, getLanguage(hass)),
      ]);
      if (this._run !== run) return;
      this._view = view;
      const found = devices.find((d) => d.name === device);
      if (!found) {
        this._fail(t('Device not found: {device}').replace('{device}', device));
        return;
      }
      const Session = config.mode === 'live' ? view.CardLiveSession : view.CardHomeSession;
      const session = new Session(hass, {
        entryId: found.entry_id,
        device,
        onUpdate: () => {
          if (this._session !== session) return;
          if (session.ready) {
            this._kept = null;
            this._message = null;
          }
          this.requestUpdate();
        },
        onError: (/** @type {string} */ code) => {
          if (this._session === session) this._fail(errorText(code));
        },
        onEnded: () => {
          if (this._session === session) this._schedule(RESUBSCRIBE_DELAY_MS);
        },
      });
      this._session = session;
      hass.connection.addEventListener?.('ready', this._onReconnect);
      await session.start();
    } catch (err) {
      if (this._run !== run) return;
      const error = /** @type {any} */ (err);
      this._fail(error?.code === 'not_found'
        ? t('Device not found: {device}').replace('{device}', device)
        : error?.message || String(error));
    }
  }

  // -- render -----------------------------------------------------------------

  render() {
    return html`<ha-card class="haui-card">${this._content()}</ha-card>`;
  }

  _content() {
    const session = this._session?.ready ? this._session : this._kept;
    if (session && this._view) return this._screen(session);
    if (this._message) return emptyState(this._message);
    return html`<div class="haui-preview-sim-loading" role="status" aria-label=${t('Loading')}>
      ${icon('mdi:progress-clock')}
    </div>`;
  }

  /** @param {any} session */
  _screen(session) {
    const layout = session.display.layout;
    const width = layout.visible_width;
    const height = layout.height;
    const maxHeight = (globalThis.innerHeight || height) * MAX_HEIGHT_SHARE;
    const scale = Math.min((this._width || width) / width, maxHeight / height);
    const brightness = session.displayOff
      ? 0
      : session.disconnected ? DISCONNECTED_BRIGHTNESS : 1;
    const label = t('Screen of {device}').replace('{device}', session.device);
    return html`<div class="haui-card-stage" role="img" aria-label=${label}>
      <div class="haui-card-screen" style=${`--vp-screen-brightness:${brightness};`}>
        ${this._view.renderSimulatorScreen(session.display, {
          iconName: (/** @type {string} */ ch) => session.iconName(ch),
          pictureUrl: (/** @type {number} */ id) => session.pictureUrl(id),
          scale,
        })}
      </div>
      ${session.disconnected ? badge(t('Disconnected'), 'warning') : nothing}
    </div>`;
  }
}

if (!customElements.get(CARD_TYPE)) customElements.define(CARD_TYPE, NSPanelHauiCard);

const cardsWindow = /** @type {any} */ (window);
cardsWindow.customCards = cardsWindow.customCards || [];
if (!cardsWindow.customCards.some((/** @type {any} */ card) => card.type === CARD_TYPE)) {
  cardsWindow.customCards.push({
    type: CARD_TYPE,
    name: 'NSPanel HAUI',
    description: t('Shows a device\'s home panel or what its screen shows right now'),
    preview: true,
  });
}
