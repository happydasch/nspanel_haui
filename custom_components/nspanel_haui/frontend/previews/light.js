/**
 * NSPanel HAUI - Panel preview: Light.
 *
 * Device layout: sidebar buttons (light functions) on left,
 */
import { html } from '../lit-import.js';
import { simSliderVertical } from './primitives.js';

export function renderLightPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="justify-content:center;align-items:center;">
        <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;padding:0 2px;">
          <div class="pg-preview-btn active"><ha-icon icon="mdi:lightbulb-on-outline"></ha-icon></div>
          <div class="pg-preview-btn active"><ha-icon icon="mdi:theme-light-dark"></ha-icon></div>
          <div class="pg-preview-btn active"><ha-icon icon="mdi:brightness-auto"></ha-icon></div>
          <div class="pg-preview-btn active"><ha-icon icon="mdi:flash"></ha-icon></div>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:6px;flex:1;padding:0 8px 0 2px;">
          <div style="flex:0 0 auto;height:clamp(60px, 50cqi, 180px);display:flex;align-items:stretch;width:40px;">
            ${simSliderVertical({ value: 70 })}
          </div>
        </div>
        <div style="flex-shrink:0;padding-right:8px;">
          <span style="font-size:0.55em;font-weight:400;color:var(--primary-text-color,#ddd);">70%</span>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:power', accent: true } },
  };
}
