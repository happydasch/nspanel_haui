/**
 * NSPanel HAUI - Logs dialog.
 *
 * Proper Lit custom element replacing the old renderLogsDialog() function.
 */
import { html } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';

class LogsDialog extends HauiDialog {
  static get properties() {
    return {
      logs: { type: Array },
    };
  }

  constructor() {
    super();
    this.logs = [];
  }

  render() {
    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        >
        ${dialogHeader(t("Device Logs"), this._dispatchClose)}

        <div class="dialog-body">
          ${this.logs.length ? html`
            <pre class="logs-content">${this.logs.join("\n")}</pre>
          ` : html`
            <p class="text-secondary">${t("No log entries yet.")}</p>
          `}
        </div>

        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button slot="primaryAction" @click=${this._dispatchClose}>
              ${t("Close")}
            </ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }
}

customElements.define("nspanel-dialog-logs", LogsDialog);
export { LogsDialog };