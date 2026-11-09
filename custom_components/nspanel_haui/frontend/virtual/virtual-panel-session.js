/**
 * NSPanel HAUI - a sandbox preview session: the browser side of
 * custom_components/nspanel_haui/websocket_api.py.
 *
 * Shows the device's virtual app (panel-session.js does the display): touches
 * change only simulated states. It answers the hub's widget reads and follows
 * the idle page, the brightness, sounds and the entity of each widget.
 */
import { PanelSession } from './panel-session.js';

export class VirtualPanelSession extends PanelSession {
  static API = 'nspanel_haui/virtual_panel';

  /**
   * @param {object} hass - Home Assistant frontend object (connection, callWS)
   * @param {object} opts - see PanelSession, plus:
   * @param {function(object): void} [opts.onAction] - brightness/sound/display actions
   */
  constructor(hass, opts) {
    super(hass, opts);
    this.onAction = opts.onAction || (() => {});
    this.sandboxChanged = false;
    this.brightness = 100;
    this.displayOff = false;
    // Widget name -> entity id on the current page, for the hover tooltip.
    this.entityMap = {};
    this._openHome = Boolean(opts.openHome);
  }

  get live() {
    return false;
  }

  /** CSS brightness of the screen; a dimmed panel stays readable. */
  get screenBrightness() {
    return Math.max(this.brightness, 15) / 100;
  }

  _attach(layout, iconChars) {
    super._attach(layout, iconChars);
    if (this._openHome) {
      this._openHome = false;
      this.openHome();
    }
  }

  _applyMode(message) {
    switch (message.type) {
      case 'request':
        this._answer(message.kind, message.name);
        return true;
      case 'action':
        if (message.name === 'set_brightness') {
          this.brightness = Number(message.value) || 0;
        } else if (message.name === 'display_off') {
          this.displayOff = true;
        } else if (message.name === 'display_on') {
          this.displayOff = false;
        }
        this.onAction(message);
        this.onUpdate();
        return true;
      case 'idle':
        this.idle = Boolean(message.active);
        this.onUpdate();
        return true;
      case 'sandbox':
        this.sandboxChanged = Boolean(message.changed);
        this.onUpdate();
        return true;
      case 'entities':
        this.entityMap = message.map;
        return true;
      default:
        return false;
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

  /** Act as if inactivity opened the virtual app's idle page. */
  idleTimeout() {
    return this._send('idle');
  }

  /**
   * Start the sandbox over on its home panel: no simulated states, no idle
   * page and a fresh inactivity clock.
   */
  openHome() {
    return this._send('home');
  }

  /** Drop all simulated states so entities show their real Home Assistant state. */
  async resetSandbox() {
    await this.hass.callWS({
      type: `${VirtualPanelSession.API}/reset_sandbox`,
      session_id: this.sessionId,
    });
    this.onUpdate();
  }
}
