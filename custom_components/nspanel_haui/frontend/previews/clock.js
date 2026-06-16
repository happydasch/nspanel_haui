/**
 * NSPanel HAUI - Editor - Panel preview: Clock / ClockTwo.
 */
import { html } from '../lit-import.js';
import { backgroundClass, itemDisplay, tileBgColor, tileIconColor } from './utils.js';

export function renderClockPreview(host, panel, _pIdx, _pt) {
  const showWeather = panel?.show_weather !== false;
  const showTemp = panel?.show_temp !== false;
  const showNotifs = panel?.show_notifications !== false;
  const showHomeTemp = panel?.show_home_temp === true;
  const bg = backgroundClass(panel);
  const items = (panel && panel.items) || [];

  const entitySlots = [0, 1, 2, 3, 4, 5].map(i => {
    const item = items[i];
    if (item) {
      const { icon, name } = itemDisplay(item, host);
      const shortName = name.length > 6 ? name.slice(0, 5) + '\u2026' : name;
      const tileBg = tileBgColor(item);
      const tileIc = tileIconColor(item);
      return html`
        <div class="pg-preview-clock-entity-btn" style="${tileBg ? `background:${tileBg};` : ''}">
          <ha-icon icon="${icon}" style="${tileIc ? `color:${tileIc};` : ''}"></ha-icon>
          ${name ? html`<span class="pg-preview-clock-entity-label">${shortName}</span>` : ''}
        </div>
      `;
    }
    return html`
      <div class="pg-preview-clock-entity-btn" style="background:rgba(255,255,255,0.04);">
        <ha-icon icon="mdi:plus" style="--mdc-icon-size:clamp(10px,2.2cqi,15px);color:rgba(255,255,255,0.12);"></ha-icon>
      </div>
    `;
  });

  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:1px;">
        <div style="display:flex;flex-shrink:0;align-items:center;width:100%;gap:4px;min-height:0;">
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:1px;">
            ${showTemp ? html`
              <div style="font-size:clamp(9px,2.5cqi,15px);color:var(--primary-text-color,#ddd);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                ${showHomeTemp ? html`
                  <ha-icon icon="mdi:home-thermometer" style="--mdc-icon-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
                  21<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
                  <span style="margin:0 3px;"></span>
                ` : ''}
                <ha-icon icon="mdi:thermometer" style="--mdc-icon-size:clamp(9px,2cqi,13px);color:var(--secondary-text-color,#aaa);vertical-align:middle;"></ha-icon>
                21<small style="font-size:0.7em;color:var(--secondary-text-color,#ccc);">&deg;</small>
              </div>
              <div style="font-size:clamp(7px,1.6cqi,11px);color:var(--secondary-text-color,#888);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">1023 hPa</div>
            ` : ''}
          </div>
          ${showNotifs ? html`
            <div style="display:flex;flex:1;min-width:0;">
              <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3cqi,26px);color:var(--accent-color,#ffab40);"></ha-icon>
            </div>
          ` : ''}
          ${showWeather ? html`
            <div style="display:flex;flex-shrink:0;align-items:center;">
              <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size:clamp(28px,8cqi,52px);color:var(--primary-color,#4fc3f7);"></ha-icon>
            </div>
          ` : ''}
        </div>

        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;min-height:0;gap:1px;">
          <span class="pg-preview-weather-clock">12:34</span>
          <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">Mon, Jun 16</div>
        </div>

        <div class="pg-preview-clock-entity-row">
          ${entitySlots}
        </div>
      </div>`,
    containerClass: bg,
  };
}

export function renderClockTwoPreview(_host, panel, _pIdx, _pt) {
  const letters = 'ITLISASAMPMACKWADTENFIFTYFOURHALFBTWOTHR'.split('');
  const rows = [];
  for (let r = 0; r < 5; r++) {
    const cells = [];
    for (let c = 0; c < 7; c++) {
      const idx = r * 7 + c;
      if (idx < letters.length) {
        cells.push(html`<div style="height:100%;background:rgba(255,255,255,0.10);border-radius:3px;display:flex;align-items:center;justify-content:center;"><span style="font-size:0.55em;color:var(--secondary-text-color,#888);font-weight:500;">${letters[idx]}</span></div>`);
      }
    }
    rows.push(html`<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;height:100%;">${cells}</div>`);
  }
  return {
    content: html`
      <div style="display:grid;grid-template-rows:repeat(5,1fr);gap:3px;width:100%;flex:1;">
        ${rows}
      </div>`,
    containerClass: backgroundClass(panel),
  };
}
