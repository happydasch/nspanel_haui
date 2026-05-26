/**
 * NSPanel HAUI - Editor - Panel preview: Weather.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { backgroundClass } from './utils.js';

export function renderWeatherPreview(_host, panel, _pIdx, _pt) {
  const showNotifs = panel?.show_notifications !== false;
  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:1px;">
        <div style="display:flex;gap:4px;flex-shrink:0;align-items:center;min-height:20px;">
          <div style="font-size:clamp(9px,2.4cqi,16px);color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500;flex:1;min-width:0;">
            <ha-icon icon="mdi:home-thermometer" style="--mdc-icon-size:clamp(9px,2cqi,14px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
            22<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
            &nbsp;
            <ha-icon icon="mdi:thermometer" style="--mdc-icon-size:clamp(9px,2cqi,14px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
            21<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
          </div>
          ${showNotifs ? html`
            <div style="flex:1;display:flex;align-items:center;justify-content:center;">
              <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3cqi,26px);color:var(--accent-color,#ffab40);"></ha-icon>
            </div>
          ` : ''}
          <div style="font-size:clamp(9px,2.4cqi,16px);color:var(--primary-text-color,#ddd);font-weight:500;flex:1;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">Monday, 21 May</div>
        </div>
        <div style="display:flex;flex-shrink:0;min-height:14px;">
          <div style="font-size:clamp(8px,1.8cqi,12px);color:var(--secondary-text-color,#888);">1023 hPa</div>
        </div>
        <div class="pg-preview-full-flex" style="gap:4px;flex:1;min-height:0;">
          <div style="display:flex;gap:4px;flex:1;min-width:0;align-items:flex-start;">
            <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size:clamp(38px,11cqi,70px);color:var(--primary-color,#4fc3f7);flex-shrink:0;"></ha-icon>
            <div style="display:flex;flex-direction:column;gap:3px;min-width:0;">
              <div class="pg-preview-weather-info-row">
                <ha-icon icon="mdi:water-percent" style="--mdc-icon-size:clamp(12px,2.8cqi,20px);color:var(--secondary-text-color,#aaa);flex-shrink:0;"></ha-icon>
                <span style="font-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#999);">65%</span>
              </div>
              <div class="pg-preview-weather-info-row">
                <ha-icon icon="mdi:weather-windy" style="--mdc-icon-size:clamp(12px,2.8cqi,20px);color:var(--secondary-text-color,#aaa);flex-shrink:0;"></ha-icon>
                <span style="font-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#999);">15 km/h</span>
              </div>
            </div>
          </div>
          <div style="display:flex;align-items:flex-start;justify-content:flex-end;flex:1.6;min-width:0;margin-top:-4px;">
            <span class="pg-preview-weather-clock">12:34</span>
          </div>
        </div>
        <div class="pg-preview-forecast">
          ${[t('Mon'),t('Tue'),t('Wed'),t('Thu'),t('Fri')].map((day, i) => html`
            <div class="pg-preview-forecast-day">
              <span class="pg-preview-forecast-dayname">${day}</span>
              <ha-icon icon="${['mdi:weather-sunny','mdi:weather-cloudy','mdi:weather-rainy','mdi:weather-partly-cloudy','mdi:weather-sunny'][i]}"></ha-icon>
              <span class="pg-preview-forecast-hightemp">${['22','18','15','20','25'][i]}&deg;</span>
              <span class="pg-preview-forecast-lowtemp">${['12','10','8','11','14'][i]}&deg;</span>
            </div>
          `)}
        </div>
      </div>`,
    containerClass: backgroundClass(panel),
  };
}
