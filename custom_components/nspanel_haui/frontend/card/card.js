// @ts-check
/**
 * NSPanel HAUI - the view-only dashboard card of a hub's panels.
 *
 * The card is the panel, as the hub draws it: the screen in its frame, the
 * hardware buttons' lights, and the panel's own state. It has two modes:
 *
 * - `fleet`: every device the hub has.
 * - `device`: one selected device.
 *
 * Both modes use the same display mode: `big` (screen and state), `small`
 * (compact screen beside state), or `status` (state only).
 *
 * A screen is the hub's render of the device's home panel, or with `live`
 * what the real panel shows; both modes take it. Nothing else decides whether
 * a screen is drawn: a disabled device has no live screen, but the hub renders
 * its panels, so its card looks like it while its state says it is disabled.
 *
 * Everything is the hub's own display output replayed in the Nextion simulator
 * (virtual/card-sessions.js, web/card.py), so the card shows what the device
 * shows. It is view-only. This module loads on every dashboard page
 * (web/editor.py), so the display code loads only once a screen is drawn.
 *
 *   type: custom:nspanel-haui-card
 *   mode: fleet            # fleet | device
 *   device_id: 4f2a...     # the panel's Home Assistant device; rename-proof
 *   display_mode: big      # big | small | status; applies to either mode
 *   live: false            # the real screen instead of the home panel
 *   title: Downstairs      # optional heading above the card
 *   scale: 100             # a big preview's size, in percent of the space it has
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
export const CARD_MODES = ['fleet', 'device'];
export const DISPLAY_MODES = ['big', 'small', 'status'];
// The hub ended the subscription (a reload, a Home Assistant reconnect).
export const RESUBSCRIBE_DELAY_MS = 5_000;
// The device's hub app may still be starting: try again.
export const RETRY_DELAY_MS = 30_000;
// The session of each screen kind (virtual/card-sessions.js).
const SESSIONS = { home: 'CardHomeSession', live: 'CardLiveSession', info: 'CardInfoSession' };
// A card saved by the first implementation: its `mode` was the device's screen.
const LEGACY_MODES = {
  overview: { mode: 'fleet', display_mode: 'big' },
  home: { mode: 'device', display_mode: 'big', live: false },
  live: { mode: 'device', display_mode: 'big', live: true },
  tile: { mode: 'device', display_mode: 'status' },
};
const LEGACY_DISPLAY_MODES = { preview: 'big', row: 'small', info: 'status' };
// A preview's screen fills the card's width, but never more than this share of
// the window's height.
const MAX_HEIGHT_SHARE = 0.8;
const DISCONNECTED_BRIGHTNESS = 0.5;
// A preview's size, in percent of the space the card gives it.
const FULL_SCALE = 100;
const MIN_SCALE = 20;
// The screen's bezel in the big and small display modes, in px.
const FRAME_PAD = 8;
const SMALL_FRAME_PAD = 4;
// A config change of one of these subscribes the card again; the rest only redraws.
const SUBSCRIPTION_KEYS = ['mode', 'device', 'device_id', 'live'];

/**
 * @typedef {Object} CardConfig
 * @property {'fleet'|'device'} mode - every device of the hub, or one
 * @property {string} [device] - the device's name in NSPanel HAUI
 * @property {string} [device_id] - the panel's Home Assistant device
 * @property {'big'|'small'|'status'} display_mode - shared by fleet and device
 * @property {boolean} live - the real screen instead of the home panel
 * @property {string} [title]
 * @property {number} [scale] - a preview's size, in percent of the space it has
 */

/** @typedef {import('../api/types.js').CardDevice} CardDevice */

/**
 * One device the card shows: its screen (the hub's own render of it) and its state.
 * @typedef {Object} DeviceEntry
 * @property {CardDevice} device
 * @property {any} session
 * @property {string|null} error
 * @property {'home'|'live'|'info'} kind - the session's kind
 */

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

/**
 * What a hub error code means to the viewer of a session.
 * @param {string} code
 * @param {('home'|'live'|'info')} [kind] - `live` needs the running panel,
 *   `info` only the state it reports
 */
function errorText(code, kind = 'home') {
  if (code === 'no_home_panel') return t('This device has no home panel');
  if (code === 'start_failed') return t('The preview could not be started');
  if (code === 'disabled') {
    return kind === 'live'
      ? t('The device has no live screen')
      : t('The device is disabled in NSPanel HAUI');
  }
  if (code === 'not_found') return t('The device is not running in NSPanel HAUI');
  return t('The preview could not be shown');
}

/**
 * Why a device shows nothing, from the error the hub or the client raised.
 * @param {any} err
 * @param {('home'|'live'|'info')} [kind]
 */
function raisedText(err, kind = 'home') {
  const code = err?.code;
  if (code) return errorText(code, kind);
  return err?.message || String(err);
}

/**
 * The card's config, folding older mode/layout keys into `mode` and
 * `display_mode`.
 * @param {any} config
 * @returns {CardConfig}
 */
export function normalizeConfig(config) {
  if (!config || typeof config !== 'object') throw new Error(t('Invalid configuration'));
  const saved = config.mode;
  if (saved !== undefined && !CARD_MODES.includes(saved) && !(saved in LEGACY_MODES)) {
    throw new Error(t('Unknown mode: {mode}').replace('{mode}', String(saved)));
  }
  const next = { ...config, ...(LEGACY_MODES[saved] ?? {}) };
  if (!(saved in LEGACY_MODES)) next.mode = saved ?? (config.screen === false ? 'device' : 'fleet');
  const oldDisplayMode = LEGACY_DISPLAY_MODES[next.layout];
  next.display_mode ??= oldDisplayMode ?? (config.screen === false ? 'status' : 'big');
  if (!DISPLAY_MODES.includes(next.display_mode)) {
    throw new Error(t('Unknown display mode: {mode}').replace('{mode}', String(next.display_mode)));
  }
  next.live = Boolean(next.live);
  if (next.mode === 'fleet') {
    // A fleet is every device of the hub; a single-device selection is irrelevant.
    delete next.device;
    delete next.device_id;
  }
  // A card of the first implementation: its mode now says what it shows.
  delete next.devices;
  delete next.focus_mode;
  delete next.screen;
  delete next.layout;
  return next;
}

/** @param {boolean|null} connected */
function connectionLabel(connected) {
  if (connected === null || connected === undefined) return t('Unknown');
  return connected ? t('Connected') : t('Offline');
}

/** @param {boolean|null} connected */
function connectionTone(connected) {
  if (connected === null || connected === undefined) return 'unknown';
  return connected ? 'online' : 'offline';
}

/** @param {number|null|undefined} count */
function queuedLabel(count) {
  if (count === null || count === undefined) return t('Unknown');
  return t('{count} notifications waiting').replace('{count}', String(count));
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

/** @param {CardDevice} device */
function deviceKey(device) {
  return device.device_id || device.name;
}

/** Whether a session has drawn: its screen, or the state it reports. */
function hasDrawn(entry) {
  const session = entry.session;
  if (!session) return false;
  return Boolean(
    session.ready
    || session.notifications !== null
    || session.physical.connected !== null,
  );
}

export class NSPanelHauiCard extends LitElement {
  static get properties() {
    return {
      _config: { state: true },
      _message: { state: true },
      _entries: { state: true },
      _loading: { state: true },
    };
  }

  static styles = [dashboardTokens, dashboardComponentStyles, previewStyles, cardStyles];

  static async getConfigElement() {
    await import('./card-editor.js');
    return document.createElement('nspanel-haui-card-editor');
  }

  /**
   * A new card shows every panel of the hub; one panel remains optional.
   * @param {any} _hass
   */
  static async getStubConfig(_hass) {
    return { mode: 'fleet', display_mode: 'big', live: false };
  }

  constructor() {
    super();
    /** @type {any} */
    this._hass = null;
    /** @type {CardConfig|null} */
    this._config = null;
    /** @type {DeviceEntry[]} */
    this._entries = [];
    this._loading = false;
    /** @type {{ iconName: string, title: string }|null} */
    this._message = null;
    /** @type {any} */
    this._view = null;
    // The last cards, shown while the device subscribes again.
    /** @type {DeviceEntry[]|null} */
    this._kept = null;
    /** @type {object|null} */
    this._run = null;
    /** @type {ReturnType<typeof setTimeout>|undefined} */
    this._retry = undefined;
    /** @type {Map<string, { element: HTMLElement, width?: number }>} */
    this._previewSlots = new Map();
    /** @type {ResizeObserver|null} */
    this._resizeObserver = null;
    // Home Assistant reconnected (it restarted): the hub may have restarted too.
    this._onReconnect = () => this._schedule(RESUBSCRIBE_DELAY_MS);
  }

  // Home Assistant sets hass on every state change; the card comes from the
  // sessions, which report their own changes.
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
    const next = normalizeConfig(config);
    const sessionChanged = this._config
      && (this._config.display_mode === 'status') !== (next.display_mode === 'status');
    const changed = sessionChanged || SUBSCRIPTION_KEYS.some((key) => this._config?.[key] !== next[key]);
    this._config = next;
    if (changed) {
      this._kept = null;
      this._message = null;
      this._restart();
    }
  }

  getCardSize() {
    const config = this._config;
    if (!config) return 2;
    const mode = this._displayMode();
    if (mode === 'status') return config.mode === 'fleet' ? 3 : 2;
    if (mode === 'small') return config.mode === 'fleet' ? 4 : 3;
    const entry = this._entries[0];
    const full = entry?.session?.orientation === 'portrait' ? 12 : 6;
    return Math.max(1, Math.round((full * scalePercent(config.scale)) / FULL_SCALE));
  }

  getGridOptions() {
    if (this._displayMode() === 'big') {
      return { columns: 'full', rows: 'auto', min_columns: 6 };
    }
    return { columns: 6, rows: 'auto', min_columns: 3 };
  }

  connectedCallback() {
    super.connectedCallback();
    if (typeof ResizeObserver === 'function') {
      this._resizeObserver = new ResizeObserver((entries) => {
        let changed = false;
        for (const { target, contentRect } of entries) {
          const key = target.getAttribute('data-preview');
          const slot = key === null ? undefined : this._previewSlots.get(key);
          if (slot?.element === target && slot.width !== contentRect.width) {
            slot.width = contentRect.width;
            changed = true;
          }
        }
        if (changed) this.requestUpdate();
      });
    }
    this._restart();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._previewSlots.clear();
    this._stop();
  }

  updated() {
    const root = this.shadowRoot;
    if (!this._resizeObserver || !root) return;
    for (const [key, slot] of this._previewSlots) {
      if (!root.contains(slot.element) || slot.element.dataset.preview !== key) {
        this._resizeObserver.unobserve(slot.element);
        this._previewSlots.delete(key);
      }
    }
    // Measure the preview's content box, not the dashboard card: a fleet can
    // have several columns and the bezel must fit even when a track shrinks.
    for (const element of root.querySelectorAll('[data-preview]')) {
      if (!(element instanceof HTMLElement)) continue;
      const key = element.dataset.preview;
      if (key === undefined || this._previewSlots.has(key)) continue;
      this._previewSlots.set(key, { element });
      this._resizeObserver.observe(element);
    }
  }

  _displayMode() {
    return this._config?.display_mode ?? 'big';
  }

  /** A status-only card has no display output; the other modes need a screen. */
  _screenKind() {
    if (this._displayMode() === 'status') return 'info';
    return this._config?.live ? 'live' : 'home';
  }

  // -- sessions ---------------------------------------------------------------

  _stop() {
    clearTimeout(this._retry);
    this._run = null;
    this._hass?.connection?.removeEventListener?.('ready', this._onReconnect);
    const sessions = this._entries.map((entry) => entry.session).filter(Boolean);
    this._entries = [];
    this._loading = false;
    this._message = null;
    // The hub may have dropped the subscriptions already (it ended them).
    sessions.forEach((session) => session.stop().catch(() => {}));
  }

  /** Subscribe again after `delay` ms, keeping the card until the new one draws. */
  _schedule(delay) {
    clearTimeout(this._retry);
    this._retry = setTimeout(() => this._restart(true), delay);
  }

  /**
   * @param {string} title
   * @param {boolean} [keepCard] - false when the device itself is gone: the
   *   last card would only hide why the card shows nothing.
   */
  _fail(title, keepCard = true) {
    if (!keepCard) this._kept = null;
    this._message = { iconName: 'alert', title };
    this._schedule(RETRY_DELAY_MS);
  }

  /** @param {boolean} [again] - the same device and mode: keep the last card */
  async _restart(again = false) {
    const kept = again && this._entries.some(hasDrawn) ? this._entries : null;
    this._stop();
    this._kept = kept;
    const config = this._config;
    const hass = this._hass;
    if (!this.isConnected || !hass || !config) return;
    if (config.mode === 'device' && !config.device && !config.device_id) {
      this._message = { iconName: 'screen', title: t('Choose a device in the card settings') };
      return;
    }
    const run = {};
    this._run = run;
    this._loading = true;
    const api = createApiClient(() => this._hass);
    const kind = this._screenKind();
    try {
      const [devices, view] = await Promise.all([
        api.card.devices(),
        kind === 'info' ? loadSessionModules() : loadDisplayModules(),
        fetchTranslations(api, getLanguage(hass)),
      ]);
      if (this._run !== run) return;
      this._view = view;
      if (config.mode === 'fleet') {
        await this._startEntries(devices, hass, run);
        return;
      }
      const found = findDevice(devices, config);
      if (!found) {
        this._fail(t('Device not found: {device}')
          .replace('{device}', config.device || String(config.device_id ?? '')), false);
        return;
      }
      await this._startEntries([found], hass, run);
    } catch (err) {
      if (this._run !== run) return;
      this._loading = false;
      this._fail(raisedText(err, kind), false);
    }
  }

  /**
   * One card per device the hub has, each showing its own panels. A disabled
   * device keeps its place (and its settings): the hub renders its panels, so
   * it shows a screen; only the state it would report is missing.
   * @param {CardDevice[]} devices
   * @param {any} hass
   * @param {object} run
   */
  async _startEntries(devices, hass, run) {
    const kind = this._screenKind();
    this._entries = devices.map((device) => ({ device, session: null, error: null, kind }));
    this._loading = false;
    this.requestUpdate();
    hass.connection.addEventListener?.('ready', this._onReconnect);
    await Promise.all(this._entries.map((entry) => this._startEntry(entry, hass, run)));
  }

  /**
   * Subscribe one device: its screen, or only its state.
   * @param {DeviceEntry} entry @param {any} hass @param {object} run
   */
  async _startEntry(entry, hass, run) {
    const Session = this._view[SESSIONS[entry.kind]];
    const session = new Session(hass, {
      entryId: entry.device.entry_id,
      device: entry.device.name,
      deviceId: entry.device.device_id,
      onUpdate: () => {
        if (this._run !== run || entry.session !== session) return;
        if (session.ready) this._kept = null;
        this.requestUpdate();
      },
      onError: (/** @type {string} */ code) => {
        if (this._run !== run || entry.session !== session) return;
        entry.error = errorText(code, entry.kind);
        this.requestUpdate();
      },
      onEnded: () => {
        if (this._run === run && entry.session === session) this._schedule(RESUBSCRIBE_DELAY_MS);
      },
    });
    entry.session = session;
    entry.error = null;
    try {
      await session.start();
    } catch (err) {
      if (this._run !== run || entry.session !== session) return;
      entry.error = raisedText(err, entry.kind);
      this.requestUpdate();
    }
  }

  // -- render -----------------------------------------------------------------

  // The vendored Lit's own typings are not exact; a template is what it returns.
  /** @returns {any} */
  render() {
    const config = this._config;
    if (!config) return html`<ha-card class="haui-card"></ha-card>`;
    return html`<ha-card class="haui-card">
      ${config.title ? html`<div class="haui-card-title">${config.title}</div>` : nothing}
      ${config.mode === 'fleet' ? this._fleetView() : this._deviceView()}
    </ha-card>`;
  }

  /** The cards to draw: this subscription's, or the last ones while it starts. */
  _shownEntries() {
    if (!this._kept || this._entries.some(hasDrawn)) return this._entries;
    return this._kept;
  }

  /** A fleet contains one consistently arranged panel card for every device. */
  _fleetView() {
    const entries = this._shownEntries();
    if (this._message) return emptyState(this._message);
    if (!entries.length) {
      return this._loading
        ? this._placeholder()
        : emptyState({ iconName: 'screen', title: t('The hub has no panel') });
    }
    return html`<div class=${`haui-card-fleet is-${this._displayMode()}`} role="list">
      ${entries.map((entry) => this._deviceCard(entry, true))}
    </div>`;
  }

  /** A device view and a fleet item share the same preview/status arrangement. */
  _deviceView() {
    const entries = this._shownEntries();
    if (this._message) return emptyState(this._message);
    if (!entries.length) {
      return this._loading
        ? this._placeholder()
        : emptyState({ iconName: 'screen', title: t('The hub has no panel') });
    }
    return this._deviceCard(entries[0], false);
  }

  /** @param {DeviceEntry} entry @param {boolean} fleet */
  _deviceCard(entry, fleet) {
    const mode = this._displayMode();
    const key = deviceKey(entry.device);
    const ready = entry.session?.ready;
    const slotWidth = this._previewSlots.get(key)?.width;
    const showPreview = mode !== 'status' && (ready || !entry.error);
    return html`<article
      class=${`haui-card-panel is-${mode}${fleet ? ' is-fleet-item' : ''}${showPreview ? ' has-preview' : ''}`}
      data-device-id=${key}
      aria-label=${entry.device.name}
      role=${fleet ? 'listitem' : nothing}
    >
      ${showPreview ? html`<div class="haui-card-panel-screen" data-preview=${key}>
        ${ready && (slotWidth !== undefined || !this._resizeObserver)
          ? this._screen(entry, mode === 'small', slotWidth)
          : this._placeholder()}
      </div>` : nothing}
      ${this._status(entry)}
      ${entry.error ? html`<div class="haui-card-note" role="status">${entry.error}</div>` : nothing}
    </article>`;
  }

  _placeholder() {
    return html`<div class="haui-preview-sim-loading" role="status" aria-label=${t('Loading')}>
      ${icon('mdi:progress-clock')}
    </div>`;
  }

  /** @param {DeviceEntry} entry @param {boolean} compact @param {number} [slotWidth] */
  _screen(entry, compact, slotWidth) {
    const session = entry.session;
    const { visible_width: width, height } = session.display.layout;
    const pad = compact ? SMALL_FRAME_PAD : FRAME_PAD;
    const space = slotWidth ?? (compact ? width / 3 : width);
    const maxHeight = (globalThis.innerHeight || height) * MAX_HEIGHT_SHARE;
    const size = compact ? 1 : scalePercent(this._config?.scale) / FULL_SCALE;
    const scale = Math.max(
      0,
      Math.min((space - 2 * pad) / width, (maxHeight - 2 * pad) / height),
    ) * size;
    const dim = entry.device.enabled && session.disconnected ? DISCONNECTED_BRIGHTNESS : 1;
    const label = t('Screen of {device}').replace('{device}', session.device);
    return html`<div class="haui-card-stage" role="img" aria-label=${label}
        style=${`--vp-frame-pad:${pad}px`}>
      <div class="haui-card-screen" style=${`--vp-screen-brightness:${session.screenBrightness * dim}`}>
        ${this._view.renderSimulatorScreen(session.display, {
          iconName: (/** @type {string} */ ch) => session.iconName(ch),
          pictureUrl: (/** @type {number} */ id) => session.pictureUrl(id),
          scale,
        })}
      </div>
      ${entry.device.enabled && session.disconnected
        ? badge(t('Disconnected'), 'warning')
        : nothing}
    </div>`;
  }

  /** Hardware-button lights: compact indicators alongside the device status. */
  _hardware(session) {
    return html`<span class="haui-card-hardware" aria-label=${t('Button lights')}>
      ${['left', 'right'].map((side) => {
        const button = session?.buttons?.[side];
        const label = side === 'left' ? t('Left') : t('Right');
        const state = button?.state ?? 'unknown';
        const stateLabel = displayLabel(button?.state ?? null);
        const accessibleLabel = t('{side} button: {state}')
          .replace('{side}', label).replace('{state}', stateLabel);
        return html`<span class="haui-card-hardware-side" aria-label=${accessibleLabel} title=${accessibleLabel}>
          <span class="haui-card-hardware-label" aria-hidden="true">${label}</span>
          <span class=${button?.entity ? 'haui-card-led is-entity' : 'haui-card-led'} data-state=${state}></span>
          ${button?.entity
            ? html`<span class="haui-card-led-dot" data-state=${button.relay_state}></span>`
            : nothing}
        </span>`;
      })}
    </span>`;
  }

  /** The device's connection, display, notification and version state. @param {DeviceEntry} entry */
  _status(entry) {
    const { device, session } = entry;
    const connected = session?.physical.connected ?? null;
    const label = device.enabled ? connectionLabel(connected) : t('Disabled');
    const tone = device.enabled ? connectionTone(connected) : 'unknown';
    return html`<div class="haui-card-status">
      <div class="haui-card-status-heading">
        <span class="haui-card-status-name">${device.name}</span>
        <span class="haui-card-status-connection">${statusDot(tone, label)}${label}</span>
      </div>
      ${device.enabled ? html`<div class="haui-card-status-facts">
        <span class="haui-card-status-display">${icon('screen')}${displayLabel(session?.physical.display_state ?? null)}</span>
        ${this._queued(entry)}
        <span>${t('Firmware')} <span class="haui-text-mono">${versionLabel(session?.firmware)}</span></span>
        <span>${t('TFT')} <span class="haui-text-mono">${versionLabel(session?.tft)}</span></span>
        ${this._hardware(session)}
      </div>` : nothing}
    </div>`;
  }

  /** @param {DeviceEntry} entry */
  _queued(entry) {
    const count = entry.session?.notifications;
    if (!count) return nothing;
    return html`<span class="haui-card-queued" title=${queuedLabel(count)}>
      ${icon('bell')}${count}
    </span>`;
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
    // Read when the card picker draws the card, after the card loaded its
    // translations: a string taken here would keep the import-time English.
    get description() {
      return t("Shows every NSPanel of a hub, or one panel's screen");
    },
    preview: true,
  });
}
