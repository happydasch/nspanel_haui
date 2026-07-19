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
  if (items.length === 0) {
    return { content: html``, containerClass: backgroundClass(panel) };
  }
  const shown = items.slice(0, 5);
  return {
    content: html`
      <div class="pg-preview-row-stack" style="justify-content:flex-start;">
        ${shown.map(item => {
          const { icon, name } = itemDisplay(item, host);
          const shortName = name.length > 16 ? name.slice(0, 14) + '\u2026' : name;
          return html`
            <div class="pg-preview-row-card">
              <ha-icon icon="${icon}"></ha-icon>
              <span class="pg-preview-tile-label">${shortName || t('Item')}</span>
              <div class="pg-preview-btn" style="width:18px;height:16px;"><ha-icon icon="mdi:chevron-up" style="--mdc-icon-size:9px;"></ha-icon></div>
              <div class="pg-preview-btn" style="width:18px;height:16px;"><ha-icon icon="mdi:stop" style="--mdc-icon-size:8px;"></ha-icon></div>
              <div class="pg-preview-btn" style="width:18px;height:16px;"><ha-icon icon="mdi:chevron-down" style="--mdc-icon-size:9px;"></ha-icon></div>
            </div>`;
        })}
        ${items.length > 5
          ? html`<div class="pg-preview-btn-row" style="margin-top:2px;">
              ${['\u25CF','\u25CB','\u25CB'].map(d => html`<span style="font-size:11px;color:var(--secondary-text-color,#888);">${d}</span>`)}
            </div>`
          : ''}
      </div>`,
    contentClass: 'pg-preview-content-top',
    containerClass: backgroundClass(panel),
  };
}
