/**
 * NSPanel HAUI - Panel preview: Light.
 */
import { html } from '../lit-import.js';
import { simSliderVertical } from './primitives.js';

export function renderLightPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;">
        <div style="flex:1;display:flex;justify-content:flex-start;align-items:center;">
          <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;">
            <div class="pg-preview-btn active"><ha-icon icon="mdi:brightness-6"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:palette"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:thermometer"></ha-icon></div>
            <div class="pg-preview-btn"><ha-icon icon="mdi:fire"></ha-icon></div>
          </div>
        </div>
        <div style="flex:none;display:flex;align-items:center;">
          ${simSliderVertical({ value: 70 })}
        </div>
        <div style="flex:1;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:0.6em;color:var(--secondary-text-color,#888);font-weight:500;">70%</span>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:power', accent: true } },
  };
}
