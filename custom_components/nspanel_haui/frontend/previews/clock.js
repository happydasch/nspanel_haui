/**
 * NSPanel HAUI - Panel preview: Clock / ClockTwo.
 */
import { html } from '../lit-import.js';
import { backgroundClass, itemDisplay, tileBgColor, tileIconColor } from './utils.js';

export function renderClockPreview(host, panel, _pIdx, _pt) {
  const showWeather = panel?.show_weather !== false;
  const showTemp = panel?.show_temp !== false;
  const showHomeTemp = panel?.show_home_temp === true;
  const hasWeatherEntity = !!(panel?.item);
  const showTimeTime = panel?.show_time_time !== false;
  const showTimeDate = panel?.show_time_date !== false;
  const showTimeOutsideTemp = panel?.show_time_outside_temp !== false;
  const showTimeInsideTemp = panel?.show_time_inside_temp === true;
  const bg = backgroundClass(panel);
  const items = (panel && panel.items) || [];

  const cycleCards = [];
  if (showTimeTime) cycleCards.push('time');
  if (showTimeDate) cycleCards.push('date');
  if (showTimeOutsideTemp) cycleCards.push('outside_temperature');
  if (showTimeInsideTemp) cycleCards.push('inside_temperature');
  if (!cycleCards.length) cycleCards.push('time');
  const card = cycleCards[0];

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
              <div style="font-size:clamp(7px,1.6cqi,11px);color:var(--secondary-text-color,#888);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${hasWeatherEntity ? '1023 hPa' : ''}</div>
            ` : ''}
          </div>
          ${showWeather ? html`
            <div style="display:flex;flex-shrink:0;align-items:center;">
              <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size:clamp(34px,9cqi,58px);color:${panel?.weather_icons === 'monochrome' ? 'var(--primary-text-color,#ddd)' : 'var(--primary-color,#4fc3f7)'};"></ha-icon>
            </div>
          ` : ''}
        </div>

        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;min-height:0;gap:1px;">
          ${card === 'time' ? html`
            <span style="font-size:clamp(50px,14cqi,88px);font-weight:700;color:var(--primary-text-color,#fff);letter-spacing:5px;line-height:1;text-shadow:0 1px 4px rgba(0,0,0,0.3);">12:34</span>
            ${showTimeDate ? html`
              <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">Mon, Jun 16</div>
            ` : ''}
          ` : card === 'date' ? html`
            <span style="font-size:clamp(36px,10cqi,68px);font-weight:600;color:var(--primary-text-color,#fff);line-height:1;">Mon 16</span>
            <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">Mon, Jun 16</div>
          ` : card === 'outside_temperature' ? html`
            <span style="font-size:clamp(36px,10cqi,68px);font-weight:600;color:var(--primary-text-color,#fff);line-height:1;">21&deg;C</span>
            <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">OUTSIDE</div>
          ` : html`
            <span style="font-size:clamp(36px,10cqi,68px);font-weight:600;color:var(--primary-text-color,#fff);line-height:1;">24&deg;C</span>
            <div style="font-size:clamp(9px,2.2cqi,14px);color:var(--secondary-text-color,#aaa);font-weight:400;">INSIDE</div>
          `}

        <div class="pg-preview-clock-entity-row">
          ${entitySlots}
        </div>
      </div>`,
    containerClass: bg,
  };
}

export function renderClockTwoPreview(_host, panel, _pIdx, _pt) {
  // The English word-clock matrix (10 rows x 11 columns = 110 letters),
  // matching the MATRIX layout in clocktwo.py for the 'en' locale.
  const MATRIX_ROWS = [
    'ITLISBFAMPM',
    'ACQUARTERDC',
    'TWENTYFIVEX',
    'HALFBTENFTO',
    'PASTERUNINE',
    'ONESIXTHREE',
    'FOURFIVETWO',
    'EIGHTELEVEN',
    'SEVENTWELVE',
    'TENSEOCLOCK',
  ];
  // Active letter indices — simulate "IT IS FIVE OCLOCK"
  const active = new Set([0,1,3,4, 28,29,30,31, 104,105,106,107,108,109]);
  let idx = 0;
  const rows = MATRIX_ROWS.map((row) => {
    const cells = row.split('').map((ch) => {
      const cur = idx++;
      const isActive = active.has(cur);
      return html`
        <div class="pg-preview-clocktwo-letter${isActive ? ' active' : ''}">
          <span>${ch}</span>
        </div>`;
    });
    return html`<div class="pg-preview-clocktwo-row">${cells}</div>`;
  });

  // Dots near top and bottom of grid (from HMI: s1+s3 left, s2+s4 right, tNotif between right dots)
  const leftDots = [true, true].map((isActive) => html`
    <div class="pg-preview-clocktwo-special${isActive ? ' active' : ''}">
      <span>●</span>
    </div>
  `);
  const rightTop = html`
    <div class="pg-preview-clocktwo-special active">
      <span>●</span>
    </div>`;
  const rightBottom = html`
    <div class="pg-preview-clocktwo-special">
      <span>●</span>
    </div>`;
  const showNotifs = panel?.show_notifications !== false;

  return {
    content: html`
      <div class="pg-preview-clocktwo">
        <div style="display:flex;flex:1;min-height:0;gap:3px;">
          <div class="pg-preview-clocktwo-side-dots">
            ${leftDots}
          </div>
          <div class="pg-preview-clocktwo-grid">
            ${rows}
          </div>
          <div class="pg-preview-clocktwo-side-dots">
            ${rightTop}
            ${showNotifs ? html`
              <div class="pg-preview-clocktwo-notif">
                <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3cqi,24px);color:var(--accent-color,#ffab40);"></ha-icon>
              </div>
            ` : html`<div style="flex:1;"></div>`}
            ${rightBottom}
          </div>
        </div>
      </div>`,
    containerClass: backgroundClass(panel),
  };
}
