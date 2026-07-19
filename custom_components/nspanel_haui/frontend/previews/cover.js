/**
 * NSPanel HAUI - Panel preview: Cover.
 *
 * Device layout: Up/Stop/Down buttons left, vertical slider center,
 * position info right.
 */
import { html } from '../lit-import.js';
import { simSliderVertical } from './primitives.js';

export function renderCoverPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;align-items:center;">
        <div style="display:flex;align-items:center;justify-content:center;gap:8px;flex:1;padding:0 4px;">
          <div style="display:flex;flex-direction:column;justify-content:center;gap:3px;flex-shrink:0;">
            <div class="pg-preview-btn active" style="width:24px;height:24px;"><ha-icon icon="mdi:chevron-up" style="--mdc-icon-size:14px;"></ha-icon></div>
            <div class="pg-preview-btn active" style="width:24px;height:24px;"><ha-icon icon="mdi:stop" style="--mdc-icon-size:12px;"></ha-icon></div>
            <div class="pg-preview-btn active" style="width:24px;height:24px;"><ha-icon icon="mdi:chevron-down" style="--mdc-icon-size:14px;"></ha-icon></div>
          </div>
          <div style="flex:0 0 auto;height:clamp(60px, 50cqi, 180px);display:flex;align-items:stretch;width:40px;">
            ${simSliderVertical({ value: 60 })}
          </div>
        </div>
        <div style="flex-shrink:0;padding-right:8px;">
          <span style="font-size:0.55em;font-weight:400;color:var(--primary-text-color,#ddd);">60%</span>
        </div>
      </div>`,
  };
}
