/**
 * NSPanel HAUI - Logs dialog.
 *
 * Proper Lit custom element replacing the old renderLogsDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';

class LogsDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      logs: { type: Array },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
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

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }
}

customElements.define("ha-dialog-logs", LogsDialog);
export { LogsDialog };