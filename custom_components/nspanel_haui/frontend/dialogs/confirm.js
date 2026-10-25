/**
 * NSPanel HAUI - Confirm/delete dialog.
 *
 * Proper Lit custom element following HA's dialog-box pattern.
 * Replaces the old renderConfirmDialog() function.
 */
import { html } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';

class ConfirmDialog extends HauiDialog {
  static get properties() {
    return {
      params: { type: Object },
    };
  }

  constructor() {
    super();
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

  _dispatchConfirm() {
    this._emit("dialog-confirmed");
  }
}

customElements.define("nspanel-dialog-confirm", ConfirmDialog);
export { ConfirmDialog };