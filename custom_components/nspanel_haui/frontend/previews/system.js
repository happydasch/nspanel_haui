/**
 * NSPanel HAUI - Panel preview: System.
 *
 * Device layout: QR code in center (140x140) with spinner,
 * error message text below.
 */
import { html } from '../lit-import.js';

export function renderSystemPreview(_host, _panel, _pIdx, _pt) {
  return {
    containerClass: 'pg-preview-bg-system',
    content: html`
      <div style="display:flex;width:100%;flex:1;align-items:center;justify-content:center;">
        <ha-icon icon="mdi:connection" style="--mdc-icon-size:48px;color:var(--primary-color,#4fc3f7);"></ha-icon>
      </div>`,
  };
}
