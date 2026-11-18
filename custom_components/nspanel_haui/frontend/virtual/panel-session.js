/**
 * NSPanel HAUI - a preview's connection to the hub, shared by both modes.
 *
 * Subscribes for one device, builds the simulated Nextion display from the
 * layout of its orientation and applies the hub's display output to it;
 * touches go back as device events, in order. The sandbox session
 * (virtual-panel-session.js) and the live session (live-panel-session.js)
 * name their WebSocket commands (`static API`) and handle their own messages
 * (`_applyMode`).
 *
 * The device may be named by its hub device name (`entryId`/`device`) or by
 * its Home Assistant device id (`deviceId`), which a rename does not change.
 *
 * The panel's own state (`physical`) and its queued notifications
 * (`notifications`) are the base's: every mode reports them, and they arrive
 * whether or not the display has drawn. So are the hardware buttons
 * (`buttons`): the entity each one switches and what its light shows.
 */
import { loadIconMap, loadLayout, pictureUrlFor } from './assets.js';
import { NextionDisplay } from './nextion-display.js';
import { TouchInput } from './touch-input.js';

/**
 * One hardware button, as the hub's `buttons` message reports it: the entity
 * it switches (`entity`, null in relay mode) and the panel's own relay
 * (`relay`), with what each light shows (`state`, and the relay's own
 * `relay_state` for the dot beside it).
 * @typedef {Object} ButtonView
 * @property {string|null} entity
 * @property {string|null} relay
 * @property {string} state
 * @property {string} relay_state
 */

/** A button the hub has not reported yet: nothing known, nothing lit. */
const NO_BUTTON = Object.freeze(
  /** @type {ButtonView} */ ({ entity: null, relay: null, state: 'unknown', relay_state: 'unknown' }),
);

/**
 * One side of the hub's `buttons` message, with every field present.
 * @param {any} view
 * @returns {ButtonView}
 */
function buttonView(view) {
  return view ? { ...NO_BUTTON, ...view } : NO_BUTTON;
}

export class PanelSession {
  /**
   * @param {object} hass - Home Assistant frontend object (connection, callWS)
   * @param {object} opts
   * @param {string} [opts.entryId]
   * @param {string} [opts.device]
   * @param {string} [opts.deviceId] - the panel's Home Assistant device; preferred
   * @param {function(): void} [opts.onUpdate] - the screen or session state changed
   * @param {function(string): void} [opts.onError]
   * @param {function(string): Promise<object>} [opts.loadLayout] - for tests
   * @param {function(): Promise<object>} [opts.loadIconMap] - for tests
   * @param {object} [opts.scheduler] - timer scheduler for the display (tests)
   */
  constructor(hass, opts) {
    this.hass = hass;
    this.entryId = opts.entryId;
    this.device = opts.device;
    this.deviceId = opts.deviceId || null;
    this.onUpdate = opts.onUpdate || (() => {});
    this.onError = opts.onError || (msg => console.error(`[virtual panel] ${msg}`));
    this._loadLayout = opts.loadLayout || loadLayout;
    this._loadIconMap = opts.loadIconMap || loadIconMap;
    this._scheduler = opts.scheduler;
    this.sessionId = null;
    this.orientation = null;
    this.display = null;
    this.touch = null;
    // Whether the hub shows the idle page (automatic page switching).
    this.idle = false;
    // The panel itself: its display and whether the hub reaches it. Unknown
    // until the hub reports it (`display_state === null`).
    this.physical = { display_state: null, connected: null };
    // The panel's reported versions; null until the hub reports them.
    this.firmware = null;
    this.tft = null;
    // The panel's queued notifications; null until the hub reports them.
    this.notifications = null;
    /**
     * The panel's two hardware buttons as the hub reports them: the entity
     * each one switches (its relay, or an entity in place of the relay), and
     * what their lights show.
     * @type {{ left: ButtonView, right: ButtonView }}
     */
    this.buttons = { left: NO_BUTTON, right: NO_BUTTON };
    // Widget name -> entity id on the current page, for the hover tooltip.
    this.entityMap = {};
    this.iconChars = {};
    this._queue = [];
    this._unsubscribe = null;
    this._sendChain = Promise.resolve();
    this._stopped = false;
  }

  async start() {
    /** @type {Object<string, unknown>} */
    const target = this.deviceId
      ? { device_id: this.deviceId }
      : { entry_id: this.entryId, device: this.device };
    const unsubscribe = await this.hass.connection.subscribeMessage(
      message => this._onMessage(message),
      { type: `${this.constructor.API}/subscribe`, ...target },
    );
    if (this._stopped) {
      // Stopped while subscribing: nothing else would ever close it.
      await unsubscribe();
      return;
    }
    this._unsubscribe = unsubscribe;
  }

  async stop() {
    this.touch?.cancel();
    this._stopped = true;
    this.display?.dispose();
    if (this._unsubscribe) {
      const unsubscribe = this._unsubscribe;
      this._unsubscribe = null;
      await unsubscribe();
    }
  }

  get ready() {
    return this.display !== null;
  }

  /** Whether touches and buttons reach the hub. */
  get canInteract() {
    return this.ready;
  }

  /** The panel is dark. */
  get displayOff() {
    return this.physical.display_state === 'off';
  }

  /** Whether the hub reports the panel offline. */
  get disconnected() {
    return this.physical.connected === false;
  }

  iconName(char) {
    return this.iconChars[char] || null;
  }

  pictureUrl(id) {
    return pictureUrlFor(this.orientation, id);
  }

  // -- hub -> browser -------------------------------------------------------

  _onMessage(message) {
    if (this._stopped) return;
    if (message.type === 'started') {
      this._started(message);
      return;
    }
    if (message.type === 'error') {
      this.onError(message.message);
      return;
    }
    // The panel itself, not its screen: known before the layout has drawn.
    if (message.type === 'physical' || message.type === 'notifications') {
      this._apply(message);
      return;
    }
    if (!this.display) {
      // Output that arrives while the layout is still loading.
      this._queue.push(message);
      return;
    }
    this._apply(message);
  }

  _started(message) {
    this.sessionId = message.session_id;
    this.orientation = message.portrait ? 'portrait' : 'landscape';
    // A start again (a reconnect, a card's home panel after a save) draws on a
    // fresh display: what follows waits for it instead of drawing on the old one.
    const start = this._start = {};
    this.touch?.cancel();
    this.display?.dispose();
    this.display = null;
    Promise.all([this._loadLayout(this.orientation), this._loadIconMap()]).then(
      ([layout, iconChars]) => { if (this._start === start) this._attach(layout, iconChars); },
      err => this.onError(err.message),
    );
  }

  _attach(layout, iconChars) {
    if (this._stopped) return;
    // A reconnect starts the session again on a fresh display.
    this.display?.dispose();
    this.iconChars = iconChars;
    this.display = new NextionDisplay(layout, {
      scheduler: this._scheduler,
      onChange: () => this.onUpdate(),
    });
    this.touch = new TouchInput(
      this.display,
      (name, value) => this.sendEvent(name, value),
      // Live: the panel's app draws every touch effect itself.
      () => !this.live,
      this.live
        ? (pageId, componentId, value) => this.sendSlider(pageId, componentId, value)
        : null,
    );
    const queued = this._queue;
    this._queue = [];
    this.display.batch(() => queued.forEach(m => this._apply(m)));
    this.onUpdate();
  }

  _apply(message) {
    switch (message.type) {
      case 'page':
        this.display.gotoPage(message.page);
        break;
      case 'commands':
        this.display.exec(message.commands);
        break;
      case 'buttons':
        this.buttons = { left: buttonView(message.left), right: buttonView(message.right) };
        this.onUpdate();
        break;
      case 'entities':
        this.entityMap = message.map;
        break;
      case 'physical': {
        const physical = {
          display_state: message.display_state ?? null,
          connected: message.connected ?? null,
        };
        const changed = physical.display_state !== this.physical.display_state
          || physical.connected !== this.physical.connected
          || (message.firmware ?? null) !== this.firmware
          || (message.tft ?? null) !== this.tft;
        this.physical = physical;
        this.firmware = message.firmware ?? null;
        this.tft = message.tft ?? null;
        this.idle = Boolean(message.idle);
        if (changed) this.onUpdate();
        break;
      }
      case 'notifications':
        if (message.count !== this.notifications) {
          this.notifications = message.count;
          this.onUpdate();
        }
        break;
      default:
        if (!this._applyMode(message)) this.onError(`unknown message type ${message.type}`);
    }
  }

  /** Handle a message of this mode; returns whether it was one. */
  _applyMode(_message) {
    return false;
  }

  // -- browser -> hub -------------------------------------------------------

  /** Send a command of this session's API after the ones before it. */
  _send(command, data = {}) {
    if (!this.sessionId || this._stopped) return this._sendChain;
    this._sendChain = this._sendChain
      .then(() => this.hass.callWS({
        type: `${this.constructor.API}/${command}`,
        session_id: this.sessionId,
        ...data,
      }))
      .catch(err => this.onError(err?.message || String(err)));
    return this._sendChain;
  }

  /** Send a device event (touch, swipe, hardware button). */
  sendEvent(name, value = '') {
    if (!this.canInteract) return this._sendChain;
    return this._send('event', { name, value: String(value) });
  }

  /** Press and release a hardware button ("left" or "right"). */
  pressButton(side) {
    this.sendEvent(`esphome.button_${side}`, '1');
    return this.sendEvent(`esphome.button_${side}`, '0');
  }
}
