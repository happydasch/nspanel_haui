/**
 * NSPanel HAUI - base class for the editor's dialogs.
 *
 * Holds what every dialog shares: the `hass` and `open` properties, the dialog
 * styles, the closed-dialog render gate and event dispatch. The editor listens
 * on each dialog element directly, so events don't need to bubble.
 */
import { LitElement } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

export class HauiDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
  }

  /**
   * HA replaces `hass` on every state change and the editor passes it to all
   * dialogs, so a closed dialog skips renders caused only by that.
   */
  shouldUpdate(changed) {
    return this.open || !(changed.size === 1 && changed.has('hass'));
  }

  _emit(name, detail) {
    this.dispatchEvent(new CustomEvent(name, { detail }));
  }

  _dispatchClose() {
    this._emit("dialog-closed");
  }
}
