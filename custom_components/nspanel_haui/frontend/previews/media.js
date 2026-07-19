/**
 * NSPanel HAUI - Panel preview: Media Player.
 *
 * Device layout: media icon + title/artist at top,
 * transport controls (shuffle, prev, play, next, repeat),
 * volume slider, source buttons at bottom.
 */
import { html } from '../lit-import.js';
import { simSlider } from './primitives.js';

export function renderMediaPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col">
        <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;padding:4px 2px;">
          <ha-icon icon="mdi:music-note" style="--mdc-icon-size:clamp(20px,5cqi,32px);color:var(--primary-color,#4fc3f7);flex-shrink:0;"></ha-icon>
          <div style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0;">
            <div style="height:6px;width:100%;background:rgba(255,255,255,0.12);border-radius:2px;"></div>
            <div style="height:5px;width:70%;background:rgba(255,255,255,0.07);border-radius:2px;"></div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:2px;flex:1;justify-content:center;padding:0 4px;">
          <div class="pg-preview-btn-row" style="justify-content:space-evenly">
            <div class="pg-preview-btn active" style="flex:1;max-width:32px;min-width:16px;"><ha-icon icon="mdi:shuffle"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:32px;min-width:16px;"><ha-icon icon="mdi:skip-previous"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:32px;min-width:16px;"><ha-icon icon="mdi:play"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:32px;min-width:16px;"><ha-icon icon="mdi:skip-next"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:32px;min-width:16px;"><ha-icon icon="mdi:repeat"></ha-icon></div>
          </div>
          <div style="padding:2px 0;">
            ${simSlider({ value: 45 })}
          </div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0;padding:2px 4px;justify-content:space-around;">
          <div class="pg-preview-btn" style="flex:1;max-width:40px;height:18px;"><ha-icon icon="mdi:music-box" style="--mdc-icon-size:10px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:40px;height:18px;"><ha-icon icon="mdi:music-box" style="--mdc-icon-size:10px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:40px;height:18px;"><ha-icon icon="mdi:music-box" style="--mdc-icon-size:10px;"></ha-icon></div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:stop', accent: true } },
  };
}
