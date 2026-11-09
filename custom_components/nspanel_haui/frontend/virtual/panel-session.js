/**
 * NSPanel HAUI - a preview's connection to the hub, shared by both modes.
 *
 * Subscribes for one device, builds the simulated Nextion display from the
 * layout of its orientation and applies the hub's display output to it;
 * touches go back as device events, in order. The sandbox session
 * (virtual-panel-session.js) and the live session (live-panel-session.js)
 * name their WebSocket commands (`static API`) and handle their own messages
 * (`_applyMode`).
 */
import { loadIconMap, loadLayout, pictureUrlFor } from './assets.js';
import { NextionDisplay } from './nextion-display.js';
import { TouchInput } from './touch-input.js';

export class PanelSession {
  /**
   * @param {object} hass - Home Assistant frontend object (connection, callWS)
   * @param {object} opts
   * @param {string} opts.entryId
   * @param {string} opts.device
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
    this.relays = { left: 'unknown', right: 'unknown' };
    // State of the entity a button switches instead of its relay; null in relay mode.
    this.buttonEntityStates = { left: null, right: null };
    this.iconChars = {};
    this._queue = [];
    this._unsubscribe = null;
    this._sendChain = Promise.resolve();
    this._stopped = false;
  }

  async start() {
    const unsubscribe = await this.hass.connection.subscribeMessage(
      message => this._onMessage(message),
      {
        type: `${this.constructor.API}/subscribe`,
        entry_id: this.entryId,
        device: this.device,
      },
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
    Promise.all([this._loadLayout(this.orientation), this._loadIconMap()]).then(
      ([layout, iconChars]) => this._attach(layout, iconChars),
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
      case 'relays':
        this.relays = { left: message.left, right: message.right };
        this.buttonEntityStates = message.entities;
        this.onUpdate();
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
