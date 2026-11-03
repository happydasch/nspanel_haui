/**
 * NSPanel HAUI - one live-preview session: the browser side of
 * custom_components/nspanel_haui/websocket_api.py.
 *
 * Subscribes to `nspanel_haui/virtual_panel/subscribe`, feeds the hub's display
 * output into a NextionDisplay and sends touches, swipes, hardware buttons and
 * read responses back as device events, strictly in order.
 */
import { NextionDisplay } from './nextion-display.js';
import { TouchInput } from './touch-input.js';

const MODULE_URL = import.meta.url;

async function fetchLayout(orientation) {
  const response = await fetch(new URL(`layout_${orientation}.json`, MODULE_URL));
  if (!response.ok) throw new Error(`layout_${orientation}.json: HTTP ${response.status}`);
  return response.json();
}

export function pictureUrl(orientation, id) {
  return new URL(`pictures/${orientation}/${id}.webp`, MODULE_URL).href;
}

export class VirtualPanelSession {
  /**
   * @param {object} hass - Home Assistant frontend object (connection, callWS, fetchWithAuth)
   * @param {object} opts
   * @param {string} opts.entryId
   * @param {string} opts.device
   * @param {boolean} [opts.live=false]
   * @param {function(): void} [opts.onUpdate] - the screen or session state changed
   * @param {function(object): void} [opts.onAction] - brightness/sound/display actions
   * @param {function(string): void} [opts.onError]
   * @param {function(string): Promise<object>} [opts.loadLayout] - for tests
   * @param {object} [opts.scheduler] - timer scheduler for the display (tests)
   */
  constructor(hass, opts) {
    this.hass = hass;
    this.entryId = opts.entryId;
    this.device = opts.device;
    this.live = Boolean(opts.live);
    this.onUpdate = opts.onUpdate || (() => {});
    this.onAction = opts.onAction || (() => {});
    this.onError = opts.onError || (msg => console.error(`[virtual panel] ${msg}`));
    this._loadLayout = opts.loadLayout || fetchLayout;
    this._scheduler = opts.scheduler;
    this.sessionId = null;
    this.orientation = null;
    this.display = null;
    this.touch = null;
    this.brightness = 100;
    // Whether the hub shows the idle page (automatic page switching).
    this.idle = false;
    // Widget name -> entity id on the current page, for the hover tooltip.
    this.entityMap = {};
    this.sandboxEntities = [];
    this.iconChars = {};
    this._queue = [];
    this._unsubscribe = null;
    this._sendChain = Promise.resolve();
    this._stopped = false;
  }

  async start() {
    const response = await this.hass.fetchWithAuth('/api/nspanel_haui/icon_chars');
    if (!response.ok) throw new Error(`icon_chars: HTTP ${response.status}`);
    this.iconChars = await response.json();
    this._unsubscribe = await this.hass.connection.subscribeMessage(
      message => this._onMessage(message),
      {
        type: 'nspanel_haui/virtual_panel/subscribe',
        entry_id: this.entryId,
        device: this.device,
        live: this.live,
      },
    );
  }

  async stop() {
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

  iconName(char) {
    return this.iconChars[char] || null;
  }

  pictureUrl(id) {
    return pictureUrl(this.orientation, id);
  }

  // -- hub -> browser -------------------------------------------------------

  _onMessage(message) {
    if (this._stopped) return;
    if (message.type === 'started') {
      this.sessionId = message.session_id;
      this.orientation = message.portrait ? 'portrait' : 'landscape';
      this._loadLayout(this.orientation).then(
        layout => this._attach(layout),
        err => this.onError(err.message),
      );
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

  _attach(layout) {
    if (this._stopped) return;
    this.display = new NextionDisplay(layout, {
      scheduler: this._scheduler,
      onChange: () => this.onUpdate(),
    });
    this.touch = new TouchInput(this.display, (name, value) => this.sendEvent(name, value));
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
      case 'request':
        this._answer(message.kind, message.name);
        break;
      case 'action':
        if (message.name === 'set_brightness') {
          this.brightness = Number(message.value) || 0;
          this.onUpdate();
        }
        this.onAction(message);
        break;
      case 'sandbox':
        this.sandboxEntities = message.entities;
        this.onUpdate();
        break;
      case 'idle':
        this.idle = Boolean(message.active);
        this.onUpdate();
        break;
      case 'entities':
        this.entityMap = message.map;
        break;
      default:
        this.onError(`unknown message type ${message.type}`);
    }
  }

  _answer(kind, name) {
    let payload;
    try {
      payload = this.display.readResponse(kind, name);
    } catch (err) {
      this.onError(err.message);
      return;
    }
    this.sendEvent('esphome.read_response', payload);
  }

  // -- browser -> hub -------------------------------------------------------

  /** Send a device event; events go out one after another, in call order. */
  sendEvent(name, value = '') {
    if (!this.sessionId || this._stopped) return this._sendChain;
    this._sendChain = this._sendChain
      .then(() => this.hass.callWS({
        type: 'nspanel_haui/virtual_panel/event',
        session_id: this.sessionId,
        name,
        value: String(value),
      }))
      .catch(err => this.onError(err?.message || String(err)));
    return this._sendChain;
  }

  /** Press and release a hardware button ("left" or "right"). */
  pressButton(side) {
    this.sendEvent(`esphome.button_${side}`, '1');
    return this.sendEvent(`esphome.button_${side}`, '0');
  }

  /** Act as if the display's inactivity timer switched to the idle page. */
  idleTimeout() {
    return this.sendEvent('esphome.timeout', 'page');
  }

  /** Switch between sandbox and live mode; going live drops the simulated states. */
  async setLive(live) {
    await this.hass.callWS({
      type: 'nspanel_haui/virtual_panel/configure',
      session_id: this.sessionId,
      live,
    });
    this.live = live;
    this.onUpdate();
  }
  /** Clear simulated entity changes without changing preview mode. */
  async resetSandbox() {
    await this.hass.callWS({
      type: 'nspanel_haui/virtual_panel/configure',
      session_id: this.sessionId,
      reset_sandbox: true,
    });
  }
}
