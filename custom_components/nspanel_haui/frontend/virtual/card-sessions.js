// @ts-check
/**
 * NSPanel HAUI - the dashboard card's sessions: the browser side of
 * custom_components/nspanel_haui/web/card.py.
 *
 * View-only: a card shows a device's screen to every signed-in user and
 * sends nothing back. Home shows the device's home panel as the hub runs it
 * for the cards (web/preview/home_stream.py); Live shows what the real panel
 * shows, as the editor's live preview does. A subscription the hub ends
 * (`{"type": "ended"}`) calls `onEnded`, and the card subscribes again.
 */
import { LivePanelSession } from './live-panel-session.js';
import { PanelSession } from './panel-session.js';

/** The card's home panel: the hub's own render of it, kept running. */
export class CardHomeSession extends PanelSession {
  static API = 'nspanel_haui/card/home';

  /**
   * @param {object} hass
   * @param {any} opts - see PanelSession, plus `onEnded`
   */
  constructor(hass, opts) {
    super(hass, opts);
    this.onEnded = opts.onEnded || (() => {});
  }

  get live() {
    return false;
  }

  get canInteract() {
    return false;
  }

  /** The home panel is never dimmed: it is not the panel's display. */
  get screenBrightness() {
    return 1;
  }

  get displayOff() {
    return false;
  }

  /** The home panel runs on the hub, whether or not the panel is online. */
  get disconnected() {
    return false;
  }

  /** @param {{ type: string }} message */
  _applyMode(message) {
    if (message.type !== 'ended') return false;
    this.onEnded();
    return true;
  }
}

/** The card's live view: the real panel's screen, without its input. */
export class CardLiveSession extends LivePanelSession {
  static API = 'nspanel_haui/card/live';

  /**
   * @param {object} hass
   * @param {any} opts - see PanelSession, plus `onEnded`
   */
  constructor(hass, opts) {
    super(hass, opts);
    this.onEnded = opts.onEnded || (() => {});
  }

  get canInteract() {
    return false;
  }

  /** Whether the hub reports the panel offline; the card keeps its last screen. */
  get disconnected() {
    return this.physical.connected === false;
  }

  /** @param {{ type: string }} message */
  _applyMode(message) {
    if (message.type !== 'ended') return super._applyMode(message);
    this.onEnded();
    return true;
  }
}
