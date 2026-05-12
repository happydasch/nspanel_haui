/**
 * NSPanel HAUI - Editor - Logs dialog.
 *
 * Proper Lit custom element replacing the old renderLogsDialog() function.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';

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
        header-title="Logs"
      >

        <div class="dialog-body">
          ${this.logs.length ? html`
            <pre class="logs-content">${this.logs.join("\n")}</pre>
          ` : html`
            <p style="color:var(--secondary-text-color,#666);">No log entries yet.</p>
          `}
        </div>

        <ha-dialog-footer slot="footer">
          <ha-button slot="primaryAction" appearance="plain" @click=${this._dispatchClose}>
            Close
          </ha-button>
        </ha-dialog-footer>
      </ha-dialog>
    `;
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }
}

customElements.define("ha-dialog-logs", LogsDialog);
export { LogsDialog };