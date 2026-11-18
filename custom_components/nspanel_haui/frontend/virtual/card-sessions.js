// @ts-check
/**
 * NSPanel HAUI - the dashboard card's sessions: the browser side of
 * custom_components/nspanel_haui/web/card.py.
 *
 * View-only: a card shows a device's screen to every signed-in user and
 * sends nothing back. Home shows the device's home panel as the hub runs it
 * for the cards (web/preview/home_stream.py); Live shows what the real panel
 * shows, as the editor's live preview does; Tile keeps only the panel's own
 * state. All three also report the panel itself (asleep, offline, queued
 * notifications) and its hardware buttons, which panel-session.js applies.
 *
 * A subscription the hub ends (`{"type": "ended"}`) calls `onEnded`, and the
 * card subscribes again.
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

  /**
   * The home panel is the hub's render, not the panel's screen, so it stays
   * readable while the panel is dark: only its dimmed offline look applies.
   */
  get screenBrightness() {
    return 1;
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

  /** @param {{ type: string }} message */
  _applyMode(message) {
    if (message.type !== 'ended') return super._applyMode(message);
    this.onEnded();
    return true;
  }
}

/** What the hub sends for a screen, which a status tile has none of. */
const DISPLAY_OUTPUT = new Set(['page', 'commands', 'entities']);

/**
 * The card's status tile (`mode: tile`): the panel itself, with no screen.
 *
 * It reads the live subscription, because the panel's own state is all it
 * shows and the hub renders nothing for it; it never builds a display, so a
 * dashboard of tiles downloads no layout.
 */
export class CardStatusSession extends CardLiveSession {
  static API = 'nspanel_haui/card/live';

  /** @param {any} message */
  _onMessage(message) {
    if (this._stopped) return;
    if (message.type === 'started') {
      this.sessionId = message.session_id;
      this.onUpdate();
      return;
    }
    if (message.type === 'error') {
      this.onError(message.message);
      return;
    }
    this._apply(message);
  }

  /** @param {{ type: string }} message */
  _apply(message) {
    if (!DISPLAY_OUTPUT.has(message.type)) super._apply(message);
  }
}
