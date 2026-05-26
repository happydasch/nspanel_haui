/**
 * NSPanel HAUI - Editor - Panel preview: Climate.
 */
import { html } from '../lit-import.js';

export function renderClimatePreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex">
        <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;">
          <div class="pg-preview-btn"><ha-icon icon="mdi:fan"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:thermostat"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:swap-vertical"></ha-icon></div>
        </div>
        <div class="pg-preview-main-area" style="gap:2px;">
          <div class="pg-preview-temp-display">22<span class="pg-preview-temp-unit">&deg;C</span></div>
          <div class="pg-preview-btn-row" style="gap:3px;">
            ${['mdi:snowflake','mdi:fire','mdi:autorenew','mdi:water'].map(
              icon => html`<div class="pg-preview-btn active"><ha-icon icon="${icon}"></ha-icon></div>`
            )}
          </div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:power', accent: true } },
  };
}
