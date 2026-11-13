/**
 * NSPanel HAUI - shared dialog header.
 *
 * Renders a custom `slot="header"` for ha-dialog with the title on the left and
 * the close button on the right. Accepts optional extra content (e.g. a live
 * preview) rendered below the title bar — when present, the header gets the
 * `.haui-dialog-header.is-extended` class with sticky positioning and bottom border.
 *
 * Styles (`.haui-dialog-header` / `.haui-dialog-header-title` / `.haui-dialog-header-close` /
 * `.haui-dialog-header-bar` / `.haui-dialog-header.is-extended`) live in the shared dialog styles,
 * every dialog already imports.
 */
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';


export function dialogHeader(title, onClose, extra) {
  const cls = extra
    ? 'haui-dialog-header is-extended'
    : 'haui-dialog-header';
  return html`
    <div slot="header" class="${cls}">
      <div class="haui-dialog-header-bar">
        <span class="haui-dialog-header-title">${title}</span>
        <ha-icon-button
          class="haui-dialog-header-close"
          title=${t('Close')}
          @click=${onClose}
        >
          <ha-icon icon="mdi:close"></ha-icon>
        </ha-icon-button>
      </div>
      ${extra ?? nothing}
    </div>
  `;
}
