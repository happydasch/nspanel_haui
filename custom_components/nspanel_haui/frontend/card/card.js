// @ts-check
/**
 * NSPanel HAUI - the dashboard card: one device's screen on a Home Assistant
 * dashboard, for every signed-in user.
 *
 * The card is the panel, as the hub draws it: the screen in its frame, the
 * hardware buttons' lights, and one row about the panel itself. `mode: home`
 * shows the device's home panel as the hub keeps it running for the cards;
 * `mode: live` shows what the real panel shows; `mode: tile` drops the screen
 * and keeps the row. All three are the hub's own display output replayed in
 * the Nextion simulator, view-only (virtual/card-sessions.js, web/card.py).
 * This module loads on every dashboard page (web/editor.py), so the display
 * code loads only once a card with a screen is shown.
 *
 *   type: custom:nspanel-haui-card
 *   device: Kitchen       # the hub device's name: readable, and what older cards have
 *   device_id: 4f2a…      # the panel's Home Assistant device; the editor stores it
 *   mode: home            # home | live | tile
 *   title: Kitchen        # optional heading above the screen
 *   scale: 100            # the screen's size, in percent of the space it has
 *
 * Everything the card shows is the hub's: its display output, the panel's own
 * state (asleep, offline, the versions it runs), its queued notifications and
 * its hardware buttons.
 */
import { LitElement, html, nothing } from '../lit-import.js';
import { createApiClient } from '../api/client.js';
import { fetchTranslations, getLanguage, t } from '../localize.js';
import { cardStyles } from '../styles/card-styles.js';
import { dashboardComponentStyles } from '../styles/dashboard-component-styles.js';
import { previewStyles } from '../styles/preview-styles.js';
import { dashboardTokens } from '../styles/tokens.js';
import { badge, statusDot } from '../ui/badge.js';
import { emptyState } from '../ui/empty-state.js';
import { displayLabel, versionLabel } from '../ui/format.js';
import { icon } from '../ui/icon.js';

export const CARD_TYPE = 'nspanel-haui-card';
export const CARD_MODES = ['home', 'live', 'tile'];
// The session each mode shows the panel through (virtual/card-sessions.js).
const SESSIONS = { home: 'CardHomeSession', live: 'CardLiveSession', tile: 'CardStatusSession' };
// The hub ended the subscription (a reload, a Home Assistant reconnect).
export const RESUBSCRIBE_DELAY_MS = 5_000;
// The device's hub app may still be starting: try again.
export const RETRY_DELAY_MS = 30_000;
// The screen fills the card's width, but never more than this share of the window's height.
const MAX_HEIGHT_SHARE = 0.8;
const DISCONNECTED_BRIGHTNESS = 0.5;
// The screen's own size, in percent of the space the card gives it.
const FULL_SCALE = 100;
const MIN_SCALE = 20;
// The bezel around the screen and the strip of hardware buttons under it, in px.
const FRAME_PAD = 6;
const HARDWARE_HEIGHT = 16;
// A config change of one of these subscribes the card again; the rest only redraws.
const SUBSCRIPTION_KEYS = ['device', 'device_id', 'mode'];

/**
 * @typedef {Object} CardConfig
 * @property {string} [device] - the hub device name
 * @property {string} [device_id] - the panel's Home Assistant device
 * @property {'home'|'live'|'tile'} mode
 * @property {string} [title]
 * @property {number} [scale] - the screen's size in percent of the space it has
 */

/** @typedef {import('../api/types.js').CardDevice} CardDevice */

/** @type {Promise<any>|null} */
let sessionModules = null;
/** @type {Promise<any>|null} */
let displayModules = null;

/** The card's sessions, loaded with the first card shown. */
function loadSessionModules() {
  sessionModules ??= import('../virtual/card-sessions.js').catch((err) => {
    sessionModules = null;
    throw err;
  });
  return sessionModules;
}

/** The sessions and the simulator; a card without a screen needs no simulator. */
function loadDisplayModules() {
  displayModules ??= Promise.all([loadSessionModules(), import('../previews/simulator.js')]).then(
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
  if (code === 'disabled') return t('The device is disabled in NSPanel HAUI');
  if (code === 'not_found') return t('The device is not running in NSPanel HAUI');
  return t('The preview could not be shown');
}

/**
 * The card's `scale` option as a percentage, within what a card can draw.
 * @param {number|undefined} scale
 */
function scalePercent(scale) {
  const value = Number(scale);
  if (!Number.isFinite(value)) return FULL_SCALE;
  return Math.max(MIN_SCALE, Math.min(FULL_SCALE, value));
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

  /**
   * A new card starts empty: the picker's preview asks for a device instead of
   * starting the hub's work for one.
   * @param {any} _hass
   */
  static async getStubConfig(_hass) {
    return { mode: 'home' };
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
    // `screen: false` was the pre-release way to ask for the status tile.
    const mode = config.mode ?? (config.screen === false ? 'tile' : 'home');
    if (!CARD_MODES.includes(mode)) {
      throw new Error(t('Unknown mode: {mode}').replace('{mode}', String(mode)));
    }
    const next = { ...config, mode };
    const changed = SUBSCRIPTION_KEYS.some((key) => this._config?.[key] !== next[key]);
    this._config = next;
    if (changed) {
      this._kept = null;
      this._message = null;
      this._restart();
    }
  }

  getCardSize() {
    if (this._config?.mode === 'tile') return 2;
    const full = this._session?.orientation === 'portrait' ? 12 : 6;
    // A smaller screen is a shorter card, so the dashboard keeps its spacing.
    return Math.max(1, Math.round((full * scalePercent(this._config?.scale)) / FULL_SCALE));
  }

  getGridOptions() {
    if (this._config?.mode === 'tile') {
      return { columns: 6, rows: 'auto', min_columns: 3 };
    }
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

  /**
   * @param {string} title
   * @param {boolean} [keepScreen] - false when the device itself is gone: the
   *   last screen would only hide why the card shows nothing.
   */
  _fail(title, keepScreen = true) {
    if (!keepScreen) this._kept = null;
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
    if (!config.device && !config.device_id) {
      this._message = { iconName: 'screen', title: t('Choose a device in the card settings') };
      return;
    }
    const run = {};
    this._run = run;
    const api = createApiClient(() => this._hass);
    try {
      const [devices, view] = await Promise.all([
        api.card.devices(),
        // A tile shows the panel, not a screen: it needs no simulator.
        config.mode === 'tile' ? loadSessionModules() : loadDisplayModules(),
        fetchTranslations(api, getLanguage(hass)),
      ]);
      if (this._run !== run) return;
      this._view = view;
      const found = findDevice(devices, config);
      if (!found) {
        this._fail(
          t('Device not found: {device}').replace('{device}', config.device || String(config.device_id)),
          false,
        );
        return;
      }
      if (!found.enabled) {
        this._fail(t('The device is disabled in NSPanel HAUI'), false);
        return;
      }
      const Session = view[SESSIONS[config.mode]];
      const session = new Session(hass, {
        entryId: found.entry_id,
        device: found.name,
        deviceId: found.device_id,
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
      const code = error?.code;
      if (code === 'disabled') {
        this._fail(t('The device is disabled in NSPanel HAUI'), false);
      } else if (code === 'not_found') {
        this._fail(t('Device not found: {device}').replace('{device}', config.device || ''), false);
      } else {
        this._fail(error?.message || String(error));
      }
    }
  }

  // -- render -----------------------------------------------------------------

  // The vendored Lit's own typings are not exact; a template is what it returns.
  /** @returns {any} */
  render() {
    const config = this._config;
    if (!config) return html`<ha-card class="haui-card"></ha-card>`;
    const tile = config.mode === 'tile';
    // A tile needs no screen: the panel's own state arrives without one.
    const session = tile ? (this._session ?? this._kept) : this._session?.ready ? this._session : this._kept;
    const shown = session && (tile || this._view);
    return html`<ha-card class="haui-card">
      ${config.title ? html`<div class="haui-card-title">${config.title}</div>` : nothing}
      ${shown ? this._shown(session) : this._placeholder()}
    </ha-card>`;
  }

  _placeholder() {
    if (this._message) return emptyState(this._message);
    return html`<div class="haui-preview-sim-loading" role="status" aria-label=${t('Loading')}>
      ${icon('mdi:progress-clock')}
    </div>`;
  }

  /** @param {any} session */
  _shown(session) {
    const screen = this._config?.mode !== 'tile' && session.ready;
    // The row follows the screen's width, so a scaled-down preview is not
    // captioned across the whole card.
    return html`<div class=${screen ? 'haui-card-body is-screen' : 'haui-card-body'}>
      ${screen ? this._screen(session) : nothing}
      ${this._status(session)}
    </div>`;
  }

  /** @param {any} session */
  _screen(session) {
    const layout = session.display.layout;
    const width = layout.visible_width;
    const height = layout.height;
    const maxHeight = (globalThis.innerHeight || height) * MAX_HEIGHT_SHARE;
    // Fit the card first, then the `scale` option: a smaller preview keeps its frame.
    const fit = Math.min(
      ((this._width || width) - 2 * FRAME_PAD) / width,
      (maxHeight - 2 * FRAME_PAD - HARDWARE_HEIGHT) / height,
    );
    const scale = Math.max(0, fit) * (scalePercent(this._config?.scale) / FULL_SCALE);
    const dim = session.disconnected ? DISCONNECTED_BRIGHTNESS : 1;
    const brightness = session.screenBrightness * dim;
    const label = t('Screen of {device}').replace('{device}', session.device);
    const screen = html`<div class="haui-card-screen" style=${[
      `--vp-screen-brightness:${brightness}`,
      `--vp-frame-pad:${FRAME_PAD}px`,
      `--vp-hw-height:${HARDWARE_HEIGHT}px`,
    ].join(';')}>
      ${this._view.renderSimulatorScreen(session.display, {
        iconName: (/** @type {string} */ ch) => session.iconName(ch),
        pictureUrl: (/** @type {number} */ id) => session.pictureUrl(id),
        scale,
      })}
    </div>`;
    return html`<div class="haui-card-stage" role="img" aria-label=${label}>
      ${screen}
      ${this._hardware(session)}
      ${session.disconnected ? badge(t('Disconnected'), 'warning') : nothing}
    </div>`;
  }

  /** The two hardware buttons under the screen; the card cannot press them. */
  _hardware(session) {
    return html`<div class="haui-card-hw">
      ${['left', 'right'].map((side) => {
        const button = session.buttons?.[side];
        return html`<div class="haui-card-hw-button" data-side=${side}>
          ${button?.entity
            ? html`<span class="haui-card-led entity" data-state=${button.state}></span>
                <span class="haui-card-led-dot" data-state=${button.relay_state}></span>`
            : html`<span class="haui-card-led" data-state=${button?.state ?? 'unknown'}></span>`}
        </div>`;
      })}
    </div>`;
  }

  /** The row under the screen: the panel itself, as the hub reports it. */
  _status(session) {
    const connected = session.physical.connected;
    const state = connected === null ? t('Unknown') : session.disconnected ? t('Offline') : t('Connected');
    const queued = session.notifications;
    return html`<div class="haui-card-status">
      <span class="haui-card-status-device">
        ${statusDot(connected === null ? 'unknown' : session.disconnected ? 'offline' : 'online', state)}
        <span class="haui-card-status-name">${session.device}</span>
      </span>
      <span class="haui-card-status-facts">
        <span>${displayLabel(session.physical.display_state)}</span>
        ${queued
          ? html`<span class="haui-card-status-queued"
              title=${t('{count} notifications waiting').replace('{count}', String(queued))}>
              ${icon('bell')}${queued}
            </span>`
          : nothing}
        <span class="haui-text-mono">${versionLabel(session.firmware)}</span>
        <span class="haui-text-mono">${versionLabel(session.tft)}</span>
      </span>
    </div>`;
  }
}

/**
 * The device a card config means: its Home Assistant device first, then its name.
 * @param {CardDevice[]} devices
 * @param {CardConfig} config
 * @returns {CardDevice|undefined}
 */
export function findDevice(devices, config) {
  if (config.device_id) {
    const byId = devices.find((device) => device.device_id === config.device_id);
    if (byId) return byId;
  }
  return devices.find((device) => device.name === config.device);
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

