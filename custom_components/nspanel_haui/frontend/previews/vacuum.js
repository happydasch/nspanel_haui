/**
 * NSPanel HAUI - Panel preview: Vacuum.
 *
 * Device layout: fan speed, action buttons (play, home, locate),
 * battery status, 6 entity buttons at bottom.
 */
import { html } from '../lit-import.js';
import { itemDisplay } from './utils.js';

export function renderVacuumPreview(host, _panel, _pIdx, _pt) {
  const items = (_panel && _panel.items) || [];
  const entityBtns = [];
  for (let i = 0; i < 6; i++) {
    if (i < items.length) {
      const { icon } = itemDisplay(items[i], host);
      entityBtns.push(html`
        <div class="pg-preview-btn" style="width:20px;height:100%;flex:1 1 0;min-width:12px;"><ha-icon icon="${icon}"></ha-icon></div>
      `);
    } else {
      entityBtns.push(html`
        <div class="pg-preview-btn" style="width:20px;height:100%;flex:1 1 0;min-width:12px;background:rgba(255,255,255,0.04);"><ha-icon icon="mdi:plus" style="--mdc-icon-size:10px;color:rgba(255,255,255,0.12);"></ha-icon></div>
      `);
    }
  }
  return {
    content: html`
      <div class="pg-preview-full-col" style="align-self:stretch;min-height:0;">
        <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:0;">
          <div class="pg-preview-btn-row" style="gap:4px;">
            <div class="pg-preview-btn active"><ha-icon icon="mdi:fan"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:play"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:home-map-marker"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:map-marker"></ha-icon></div>
          </div>
          <div style="display:flex;align-items:center;gap:4px;">
            <ha-icon icon="mdi:battery-charging" style="--mdc-icon-size:12px;color:var(--primary-color,#4fc3f7);"></ha-icon>
            <span class="pg-preview-tile-label" style="font-size:0.5em;">85%</span>
          </div>
        </div>
        <div class="pg-preview-btn-row" style="flex-shrink:0;gap:2px;max-width:100%;overflow:hidden;">
          ${entityBtns}
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:battery', accent: true } },
  };
}
