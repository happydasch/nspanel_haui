/**
 * NSPanel HAUI - Editor - shared dialog header.
 *
 * Renders a custom `slot="header"` for ha-dialog with the title on the left and
 * the close button on the right. Accepts optional extra content (e.g. a live
 * preview) rendered below the title bar — when present, the header gets the
 * `.dialog-header--extended` class with sticky positioning and bottom border.
 *
 * Styles (.dialog-header / .dialog-header-title / .dialog-header-close /
 * .dialog-header-bar / .dialog-header--extended) live in editorStyles, which
 * every dialog already imports.
 */
import { html, nothing } from '../lit-import.js';

export function dialogHeader(title, onClose, extra) {
  const cls = extra
    ? "dialog-header dialog-header--extended"
    : "dialog-header";
  return html`
    <div slot="header" class="${cls}">
      <div class="dialog-header-bar">
        <span class="dialog-header-title">${title}</span>
        <ha-icon-button
          class="dialog-header-close"
          title="Close"
          @click=${onClose}
        >
          <ha-icon icon="mdi:close"></ha-icon>
        </ha-icon-button>
      </div>
      ${extra ?? nothing}
    </div>
  `;
}
