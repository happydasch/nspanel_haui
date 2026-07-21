/**
 * NSPanel HAUI - Panel preview: Row.
 *
 * Device layout: 5 rows of items. Each row: icon (font:2, 50x50),
 * name (font:1, 220x50), optional slider + up/down/stop buttons.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { getItems, backgroundClass, itemDisplay } from './utils.js';

export function renderRowPreview(host, panel, _pIdx, _pt) {
  const items = getItems(panel);
  const rows = [];
  for (let i = 0; i < 5; i++) {
    const item = items[i];
    if (item) {
      const { icon, name } = itemDisplay(item, host);
      const shortName = name.length > 16 ? name.slice(0, 14) + '\u2026' : name;
      rows.push(html`
            <div class="pg-preview-row-card">
              <ha-icon icon="${icon}"></ha-icon>
              <span class="pg-preview-tile-label">${shortName || t('Item')}</span>
              <div class="pg-preview-btn"><ha-icon icon="mdi:chevron-up"></ha-icon></div>
              <div class="pg-preview-btn"><ha-icon icon="mdi:stop"></ha-icon></div>
              <div class="pg-preview-btn"><ha-icon icon="mdi:chevron-down"></ha-icon></div>
            </div>`);
    } else {
      rows.push(html`<div class="pg-preview-row-card pg-preview-row-empty"></div>`);
    }
  }
  return {
    content: html`
      <div class="pg-preview-row-stack" style="justify-content:flex-start;">
        ${rows}
      </div>`,
    contentClass: 'pg-preview-content-top',
    containerClass: backgroundClass(panel),
  };
}
