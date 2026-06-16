/**
 * NSPanel HAUI - Editor - Confirm/delete dialog.
 *
 * Proper Lit custom element following HA's dialog-box pattern.
 * Replaces the old renderConfirmDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';

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
        .preventScrimClose=${true}
      >
        ${dialogHeader(title || t('Confirm'), this._dispatchClose)}
        <div class="dialog-body">
          <p>${message || ""}</p>
        </div>
        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button
              slot="secondaryAction"
              variant="neutral"
              appearance="plain"
              @click=${this._dispatchClose}
            >
              ${cancelText || t('Cancel')}
            </ha-button>
            <ha-button
              slot="primaryAction"
              variant="danger"
              @click=${this._dispatchConfirm}
            >
              ${confirmText || t('Delete')}
            </ha-button>
          </ha-dialog-footer>
        </div>
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