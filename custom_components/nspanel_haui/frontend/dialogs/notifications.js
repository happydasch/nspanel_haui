import { css, html } from '../lit-import.js';
import { t } from '../localize.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';

class NotificationsDialog extends HauiDialog {
  static styles = [
    ...HauiDialog.styles,
    css`
      .notification-list { display: grid; gap: 12px; }
      .notification-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
      }
      .notification-icon { color: var(--primary-color); padding-top: 2px; }
      .notification-content { flex: 1; min-width: 0; }
      .notification-heading { display: flex; justify-content: space-between; gap: 12px; }
      .notification-heading strong { overflow-wrap: anywhere; }
      .notification-severity, .notification-meta { color: var(--secondary-text-color); }
      .notification-item p { margin: 8px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
      .notification-meta { display: flex; gap: 12px; font-size: 0.9em; }
    `,
  ];

  static get properties() {
    return {
      notifications: { type: Array },
    };
  }

  constructor() {
    super();
    this.notifications = [];
  }

  _dismiss(notification) {
    this.dispatchEvent(new CustomEvent('notification-dismiss', {
      detail: { notification },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    const severity = {
      info: t('Info'),
      warning: t('Warning'),
      critical: t('Critical'),
    };
    return html`
      <ha-dialog .open=${this.open} @closed=${this._dispatchClose}>
        ${dialogHeader(t('Notifications'), this._dispatchClose)}
        <div class="dialog-body">
          ${this.notifications.length ? html`
            <div class="notification-list">
              ${this.notifications.map((notification) => html`
                <section class="notification-item">
                  <div class="notification-icon">
                    <ha-icon icon=${notification.icon || 'mdi:bell-outline'}></ha-icon>
                  </div>
                  <div class="notification-content">
                    <div class="notification-heading">
                      <strong>${notification.title}</strong>
                      <span class="notification-severity">
                        ${severity[notification.notif_type] || notification.notif_type}
                      </span>
                    </div>
                    ${notification.message ? html`<p>${notification.message}</p>` : ''}
                    <div class="notification-meta">
                      <span>${notification.device}</span>
                      ${notification.persistent ? html`<span>${t('Persistent')}</span>` : ''}
                    </div>
                  </div>
                  <ha-icon-button
                    label=${t('Dismiss')}
                    title=${t('Dismiss')}
                    @click=${() => this._dismiss(notification)}
                  >
                    <ha-icon icon="mdi:close"></ha-icon>
                  </ha-icon-button>
                </section>
              `)}
            </div>
          ` : html`<p class="text-secondary">${t('No notifications queued.')}</p>`}
        </div>
        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button slot="primaryAction" @click=${this._dispatchClose}>${t('Close')}</ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }
}

customElements.define('nspanel-dialog-notifications', NotificationsDialog);
export { NotificationsDialog };
