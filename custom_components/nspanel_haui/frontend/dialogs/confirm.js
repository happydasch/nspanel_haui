/**
 * NSPanel HAUI - Editor - Confirm/delete dialog.
 *
 * Proper Lit custom element following HA's dialog-box pattern.
 * Replaces the old renderConfirmDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

class ConfirmDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      params: { type: Object },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
    this.params = null;
  }

  render() {
    if (!this.params) return "";
    const { title, message, confirmText, cancelText } = this.params;

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        type="alert"
        prevent-scrim-close
        header-title=${title || "Confirm"}
      >
        <div class="dialog-body">
          <p style="margin:0;">${message || ""}</p>
        </div>
        <ha-dialog-footer slot="footer">
          <ha-button
            slot="secondaryAction"
            appearance="plain"
            @click=${this._dispatchClose}
          >
            ${cancelText || "Cancel"}
          </ha-button>
          <ha-button
            slot="primaryAction"
            variant="danger"
            @click=${this._dispatchConfirm}
          >
            ${confirmText || "Delete"}
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchConfirm() {
    this.dispatchEvent(new CustomEvent("dialog-confirmed"));
  }
}

customElements.define("ha-dialog-confirm", ConfirmDialog);
export { ConfirmDialog };