/**
 * NSPanel HAUI - Panel preview: Climate.
 *
 * Device layout: side buttons (fan, preset, swing) on left,
 * temperature display center, up/down buttons right,
 * mode buttons at bottom.
 */
import { html } from '../lit-import.js';

export function renderClimatePreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-flex" style="flex-direction:column;padding:2px 0;gap:0;">
        <div style="display:flex;flex:1;align-items:center;gap:4px;min-height:0;">
          <div class="pg-preview-sidebar" style="gap:4px;justify-content:center;padding:0 2px;">
            <div class="pg-preview-btn active"><ha-icon icon="mdi:fan"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:thermostat"></ha-icon></div>
            <div class="pg-preview-btn active"><ha-icon icon="mdi:swap-vertical"></ha-icon></div>
          </div>
          <div style="display:flex;align-items:center;justify-content:center;flex:1;gap:1px;min-width:0;">
            <div class="pg-preview-temp-display" style="font-size:2.2em;line-height:1;">22<span class="pg-preview-temp-unit">&deg;C</span></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:3px;flex-shrink:0;padding-right:2px;">
              <div class="pg-preview-btn active" style="width:20px;height:18px;"><ha-icon icon="mdi:chevron-up" style="--mdc-icon-size:11px;"></ha-icon></div>
              <div class="pg-preview-btn active" style="width:20px;height:18px;"><ha-icon icon="mdi:chevron-down" style="--mdc-icon-size:11px;"></ha-icon></div>
            </div>
          </div>
        </div>
        <div class="pg-preview-btn-row" style="gap:2px;flex-shrink:0;width:100%;justify-content:space-evenly;padding:0 4px;">
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:snowflake" style="--mdc-icon-size:12px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:fire" style="--mdc-icon-size:12px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:autorenew" style="--mdc-icon-size:12px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:water" style="--mdc-icon-size:12px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:fan-off" style="--mdc-icon-size:12px;"></ha-icon></div>
          <div class="pg-preview-btn" style="flex:1;max-width:48px;height:20px;"><ha-icon icon="mdi:fan" style="--mdc-icon-size:12px;"></ha-icon></div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:power', accent: true } },
  };
}
