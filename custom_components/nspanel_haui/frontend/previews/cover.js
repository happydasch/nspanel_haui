/**
 * NSPanel HAUI - Panel preview: Cover.
 */
import { html } from '../lit-import.js';
import { simSliderVertical } from './primitives.js';

export function renderCoverPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;">
        <div style="flex:1;display:flex;justify-content:flex-end;align-items:center;">
          <div class="pg-preview-sidebar" style="gap:5px;justify-content:center;">
            <div class="pg-preview-btn active"><ha-icon icon="mdi:arrow-up-bold"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:stop"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:arrow-down-bold"></ha-icon></div>
          </div>
        </div>
        <div style="flex:none;display:flex;align-items:center;">
          ${simSliderVertical({ value: 60 })}
        </div>
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:0.65em;font-weight:500;color:var(--secondary-text-color,#aaa);">60%</span>
        </div>
      </div>`,
  };
}
