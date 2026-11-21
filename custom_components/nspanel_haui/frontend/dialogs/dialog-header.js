import { html } from '../lit-import.js';
import { t } from '../localize.js';

/** The shared header slot for HA dialogs. */
export function dialogHeader(title, onClose) {
  return html`
    <div slot="header" class="haui-dialog-header">
      <span class="haui-dialog-header-title">${title}</span>
      <ha-icon-button
        class="haui-dialog-header-close"
        title=${t('Close')}
        @click=${onClose}
      >
        <ha-icon icon="mdi:close"></ha-icon>
      </ha-icon-button>
    </div>
  `;
}
