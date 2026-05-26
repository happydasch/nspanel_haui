/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Weather page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewWeatherStyles = css`
  .pg-preview-forecast {
    display: flex;
    gap: 3px;
    justify-content: center;
    width: 100%;
    flex-shrink: 0;
  }
  .pg-preview-forecast-day {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    flex: 1;
    padding: 4px 2px;
    background: rgba(255,255,255,0.04);
    border-radius: 3px;
    min-height: 0;
  }
  .pg-preview-forecast-day .pg-preview-forecast-dayname {
    font-size: clamp(7.5px, 1.7cqi, 11px);
    color: var(--secondary-text-color, #aaa);
    white-space: nowrap;
    line-height: 1.2;
  }
  .pg-preview-forecast-day ha-icon {
    --mdc-icon-size: clamp(14px, 3cqi, 22px);
    color: var(--primary-text-color, #ddd);
  }
  .pg-preview-forecast-day .pg-preview-forecast-hightemp {
    font-size: clamp(10px, 2.2cqi, 14px);
    font-weight: 500;
    color: var(--primary-text-color, #ddd);
    line-height: 1.2;
  }
  .pg-preview-forecast-day .pg-preview-forecast-lowtemp {
    font-size: clamp(7.5px, 1.6cqi, 10px);
    color: var(--secondary-text-color, #888);
    line-height: 1.2;
  }

  /* Weather forecast day cell */
  .pg-preview-forecast-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    flex: 1;
    padding: 1px 0;
    background: rgba(255,255,255,0.04);
    border-radius: 3px;
  }

  /* === Weather preview classes === */

  /* Info row: icon + label for d1/d2 panels */
  .pg-preview-weather-info-row {
    display: flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
  }

  /* Giant clock (tTime replacement) */
  .pg-preview-weather-clock {
    font-size: clamp(42px, 12cqi, 82px);
    font-weight: 600;
    color: var(--primary-text-color, #fff);
    letter-spacing: 5px;
    line-height: 1;
  }

  /* Entity button cell */
  .pg-preview-weather-entity-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 4px;
    background: rgba(255,255,255,0.06);
    flex-shrink: 0;
  }
`;
