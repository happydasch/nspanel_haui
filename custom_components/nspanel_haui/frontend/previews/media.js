/**
 * NSPanel HAUI - Editor - Panel preview: Media Player.
 */
import { html } from '../lit-import.js';
import { simSlider } from './primitives.js';

export function renderMediaPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col">
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;padding:4px 0;">
          <ha-icon icon="mdi:music-note" style="--mdc-icon-size:34px;color:var(--primary-color,#4fc3f7);flex-shrink:0;padding:2px;"></ha-icon>
          <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:0;">
            <div style="height:7px;width:100%;background:rgba(255,255,255,0.12);border-radius:3px;"></div>
            <div style="height:6px;width:100%;background:rgba(255,255,255,0.07);border-radius:3px;"></div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:2px;flex:1;justify-content:center;">
          <div class="pg-preview-btn-row" style="justify-content:space-evenly">
            <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:shuffle"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:skip-previous"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:play"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:skip-next"></ha-icon></div>
            <div class="pg-preview-btn active" style="flex:1;max-width:38px;min-width:18px;"><ha-icon icon="mdi:repeat"></ha-icon></div>
          </div>
          ${simSlider({ value: 45 })}
        </div>
        <div style="display:flex;gap:8px;flex-shrink:0;">
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
          <div class="pg-preview-source-row">
            <ha-icon icon="mdi:music-box" style="--mdc-icon-size:14px;color:var(--secondary-text-color,#888);flex-shrink:0;"></ha-icon>
            <div class="pg-preview-skeleton-bar" style="width:100%;"></div>
          </div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:stop', accent: true } },
  };
}
