/**
 * NSPanel HAUI - a live preview session: the browser side of
 * custom_components/nspanel_haui/live_panel.py.
 *
 * Mirrors the device's own hub app (panel-session.js does the display): the
 * screen shows what that app sends to the panel, and touches, swipes,
 * hardware buttons and the idle control act on the real panel and its
 * entities, while the panel is connected.
 */
import { PanelSession } from './panel-session.js';

export class LivePanelSession extends PanelSession {
  static API = 'nspanel_haui/live_panel';

  constructor(hass, opts) {
    super(hass, opts);
    this.physical = { display_state: null, connected: null };
  }

  get live() {
    return true;
  }

  get canInteract() {
    return this.ready && this.physical.connected === true;
  }

  get displayOff() {
    return this.physical.display_state === 'off';
  }

  /** CSS brightness of the screen. */
  get screenBrightness() {
    return this.displayOff ? 0 : 1;
  }

  _onMessage(message) {
    if (!this.display && message.type === 'physical') this._applyMode(message);
    super._onMessage(message);
  }

  _applyMode(message) {
    if (message.type !== 'physical') return false;
    this.physical = {
      display_state: message.display_state ?? null,
      connected: message.connected ?? null,
    };
    this.idle = Boolean(message.idle);
    this.onUpdate();
    return true;
  }

  /** Send a slider value from a browser drag to the app's current page. */
  sendSlider(pageId, componentId, value) {
    return this._send('slider', { page_id: pageId, component_id: componentId, value });
  }

  /** Toggle the panel's idle page: open it, or wake back to the panel. */
  idleTimeout() {
    return this._action('idle');
  }

  /** Reset the panel's inactivity timer without changing its page. */
  resetInteractionTimer() {
    return this._action('reset_interaction_timer');
  }

  _action(action) {
    if (!this.canInteract) return this._sendChain;
    return this._send('action', { action });
  }
}
