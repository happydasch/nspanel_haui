/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Styles for simulated preview renderers shown inside grid card bodies.
 * Extracted from panel-grid-styles.js to separate card-layout CSS from
 * preview-visual CSS.
 */
import { css } from '../lit-import.js';

export const panelPreviewStyles = css`
  /* --- Simulated preview primitives --- */

  .pg-preview-time-display {
    font-size: 2.6em;
    font-weight: 600;
    margin-top: -10px;
    color: var(--primary-text-color, #fff);
    line-height: 1.1;
  }
  .pg-preview-date-display {
    font-size: 0.7em;
    color: var(--secondary-text-color, #aaa);
    margin-top: 2px;
  }
  .pg-preview-temp-display {
    font-size: 2.6em;
    font-weight: 600;
    color: var(--primary-text-color, #fff);
  }
  .pg-preview-temp-unit {
    font-size: 0.55em;
    font-weight: 400;
    color: var(--secondary-text-color, #ccc);
    vertical-align: super;
  }

  .pg-preview-tile {
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 4px 2px;
    min-height: 40px;
    overflow: hidden;
    background: rgba(255,255,255,0.08);
  }
  .pg-preview-tile ha-icon {
    --mdc-icon-size: clamp(16px, 5cqi, 28px);
    color: var(--primary-text-color, #ddd);
  }
  .pg-preview-tile-label {
    font-size: 0.55em;
    color: var(--secondary-text-color, #bbb);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    line-height: 1.2;
  }
  .pg-preview-tile-icon-only {
    font-size: 0.65em;
    color: var(--secondary-text-color, #bbb);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .pg-preview-grid {
    display: grid;
    gap: 3px;
    width: 100%;
  }
  .pg-preview-grid-2cols {
    grid-template-columns: 1fr 1fr;
  }
  .pg-preview-grid-3cols {
    grid-template-columns: 1fr 1fr 1fr;
  }
  .pg-preview-grid-4cols {
    grid-template-columns: 1fr 1fr 1fr 1fr;
  }

  .pg-preview-row {
    display: flex;
    gap: 3px;
    width: 100%;
    justify-content: center;
  }
  .pg-preview-row .pg-preview-tile {
    flex: 1;
    max-width: 60px;
    min-height: 48px;
  }

  .pg-preview-slider-track {
    width: 100%;
    height: 8px;
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    position: relative;
  }
  .pg-preview-slider-fill {
    height: 100%;
    background: var(--primary-color, #4fc3f7);
    border-radius: 3px;
    opacity: 0.6;
  }
  .pg-preview-slider-thumb {
    width: 14px;
    height: 14px;
    background: var(--primary-color, #4fc3f7);
    border-radius: 50%;
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
  }

  .pg-preview-slider-vertical {
    height: 100%;
    width: 38px;
    flex: none;
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    position: relative;
  }
  .pg-preview-slider-vertical .pg-preview-slider-fill {
    width: 100%;
    position: absolute;
    bottom: 0;
  }

  .pg-preview-btn-row {
    display: flex;
    gap: 4px;
    justify-content: center;
    width: 100%;
  }
  .pg-preview-btn {
    width: 30px;
    height: 24px;
    border-radius: 3px;
    background: rgba(255,255,255,0.10);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pg-preview-btn ha-icon {
    --mdc-icon-size: 13px;
    color: var(--secondary-text-color, #999);
  }
  .pg-preview-btn.active ha-icon {
    color: var(--primary-color, #4fc3f7);
  }
  .pg-preview-btn-label {
    font-size: 0.4em;
    color: var(--secondary-text-color, #999);
    text-align: center;
    white-space: nowrap;
  }

  .pg-preview-sim-switch {
    width: 22px;
    height: 12px;
    border-radius: 6px;
    background: #555;
    position: relative;
    flex-shrink: 0;
  }
  .pg-preview-sim-switch.on {
    background: var(--primary-color, #4fc3f7);
  }
  .pg-preview-sim-switch::after {
    content: '';
    position: absolute;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #fff;
    top: 1px;
    left: 1px;
    transition: left 0.15s;
  }
  .pg-preview-sim-switch.on::after {
    left: 11px;
  }

  .pg-preview-center-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .pg-preview-center-row {
    display: flex;
    align-items: center;
    gap: 6px;
    justify-content: center;
  }

  .pg-preview-color-circle {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: conic-gradient(
      red, yellow, lime, cyan, blue, magenta, red
    );
    opacity: 0.7;
    flex-shrink: 0;
  }

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

  .pg-preview-list-item {
    height: 14px;
    border-radius: 2px;
    background: rgba(255,255,255,0.08);
  }

  .pg-preview-text-block {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
    padding: 4px 0;
  }
  .pg-preview-text-line {
    height: 8px;
    border-radius: 3px;
    background: rgba(255,255,255,0.08);
  }
  .pg-preview-text-line.wide {
    width: 100%;
  }
  .pg-preview-text-line.medium {
    width: 70%;
  }
  .pg-preview-text-line.narrow {
    width: 50%;
  }

  /* --- Background theme gradients --- */
  .pg-preview-bg-spring {
    background: linear-gradient(135deg, rgba(168,230,207,0.20) 0%, rgba(220,237,193,0.20) 100%);
  }
  .pg-preview-bg-summer {
    background: linear-gradient(135deg, rgba(255,211,182,0.20) 0%, rgba(255,170,165,0.20) 100%);
  }
  .pg-preview-bg-autumn {
    background: linear-gradient(135deg, rgba(212,163,115,0.20) 0%, rgba(204,139,69,0.20) 100%);
  }
  .pg-preview-bg-winter {
    background: linear-gradient(135deg, rgba(168,216,234,0.20) 0%, rgba(170,150,218,0.20) 100%);
  }
  .pg-preview-bg-dog_1 {
    background: linear-gradient(135deg, rgba(212,165,116,0.20) 0%, rgba(196,149,106,0.20) 100%);
  }
  .pg-preview-bg-dog_2 {
    background: linear-gradient(135deg, rgba(141,110,99,0.20) 0%, rgba(109,76,65,0.20) 100%);
  }
  .pg-preview-bg-cat {
    background: linear-gradient(135deg, rgba(158,158,158,0.15) 0%, rgba(255,138,101,0.15) 100%);
  }

  /* --- Compact screen content areas --- */
  .pg-preview-compact {
    gap: 4px;
    padding: 10px 6px;
  }
  .pg-preview-compact .pg-card-preview-icon {
    --mdc-icon-size: 28px;
  }

  /* --- Full-width flex layout --- */
  .pg-preview-full-flex {
    display: flex;
    width: 100%;
    flex: 1;
    align-self: stretch;
    gap: 4px;
  }
  .pg-preview-sidebar {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex-shrink: 0;
    justify-content: center;
  }
  .pg-preview-main-area {
    display: flex;
    flex-direction: column;
    flex: 1;
    align-items: center;
    justify-content: center;
    gap: 4px;
    min-width: 0;
  }

  /* --- Bigger tiles for grid preview --- */
  .pg-preview-grid-tile {
    min-height: 65px;
    font-size: 0.95em;
    padding: 4px 6px;
    gap: 1px;
  }
  .pg-preview-grid-tile ha-icon {
    --mdc-icon-size: clamp(18px, 6cqi, 32px);
  }
  .pg-preview-grid-tile .pg-preview-tile-label {
    font-size: 0.6em;
  }
  .pg-preview-grid-tile.fill {
    box-sizing: border-box;
    min-height: 0;
    height: 100%;
    width: 100%;
  }

  /* --- Stacked row cards for row preview --- */
  .pg-preview-row-stack {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
  }
  .pg-preview-row-card {
    display: flex;
    align-items: center;
    gap: 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 24px;
  }
  .pg-preview-row-card ha-icon {
    --mdc-icon-size: 11px;
    color: var(--secondary-text-color, #bbb);
    flex-shrink: 0;
  }
  .pg-preview-row-card .pg-preview-tile-label {
    flex: 1;
    text-align: left;
    font-size: 0.5em;
  }
  .pg-preview-row-card .pg-preview-btn {
    width: 14px;
    height: 12px;
  }
  .pg-preview-row-card .pg-preview-btn ha-icon {
    --mdc-icon-size: 7px;
  }

  /* --- QR matrix pattern --- */
  .pg-qr-matrix-bg {
    display: inline-flex;
    padding: 4px;
    background: rgba(255,255,255,0.4);
    border-radius: 2px;
    align-items: center;
    justify-content: center;
  }.pg-preview-qr-matrix {
    display: grid;
    grid-template-columns: repeat(15, 6px);
    grid-template-rows: repeat(15, 6px);
    gap: 1px;
    flex-shrink: 0;
  }
  .pg-preview-qr-cell {
    border-radius: 1px;
  }
  .pg-preview-qr-cell.fill {
    background: var(--primary-text-color, #fff);
  }
  .pg-preview-qr-cell.empty {
    background: transparent;
  }
  .pg-preview-qr-side {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    flex: 1;
  }

  /* Each icon+text row in the side info area */
  .pg-preview-qr-info-row {
    display: flex;
    gap: 6px;
    align-items: center;
    width: 100%;
  }
  .pg-preview-qr-info-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex: 1;
    padding: 0;
  }

  /* --- QR card preview --- */
  .pg-card-preview:has(.pg-card-preview-qr-small) .pg-card-preview-screen {
    padding-left: 8px;
  }
  .pg-card-preview-qr-small {
    flex-direction: row;
    gap: 0;
    align-items: center;
    justify-content: flex-start;
    width: 100%;
  }
  .pg-preview-qr-matrix-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-width: 0;
  }
  .pg-qr-icon-big {
    --mdc-icon-size: 56px;
    opacity: 0.85;
  }
  .pg-qr-icon {
    --mdc-icon-size: 20px;
    opacity: 0.7;
    flex-shrink: 0;
  }
  .pg-qr-preview-big-wrap {
    width: 50%;
    max-width: 140px;
    aspect-ratio: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pg-qr-matrix-bg--big {
    width: 100%;
    height: 100%;
    box-sizing: border-box;
  }
  .pg-preview-qr-matrix--big {
    width: 100%;
    height: 100%;
    grid-template-columns: repeat(15, 1fr);
    grid-template-rows: repeat(15, 1fr);
  }
  .pg-card-preview-line {
    width: 40px;
    height: 6px;
    border-radius: 3px;
    background: var(--secondary-text-color, #888);
    opacity: 0.3;
  }

  .pg-preview-bg-system {
    background: linear-gradient(135deg, rgba(30,60,120,0.55), rgba(40,90,180,0.45));
  }

  /* === NEW: Shared utility classes for repeated inline patterns === */

  /* Flex column that fills available space — most common inline pattern */
  .pg-preview-full-col {
    display: flex;
    flex-direction: column;
    width: 100%;
    flex: 1;
  }

  /* 3x4 keypad grid (Alarm, Unlock) */
  .pg-preview-keypad-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(4, 1fr);
    gap: 3px;
    flex: 1;
    min-width: 0;
  }

  /* Action button column (Alarm, Unlock) */
  .pg-preview-action-col {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex-shrink: 0;
    width: 76px;
    justify-content: space-evenly;
  }

  /* Media source selector row */
  .pg-preview-source-row {
    display: flex;
    align-items: center;
    gap: 3px;
    flex: 1;
    min-width: 0;
    background: rgba(255,255,255,0.04);
    border-radius: 4px;
    padding: 2px 4px;
  }

  /* Skeleton bar for media sources */
  .pg-preview-skeleton-bar {
    height: 4px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
  }

  /* Small button label (blank action slots) */
  .pg-preview-btn-label-sm {
    font-size: 0.4em;
    color: var(--secondary-text-color, #666);
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

  /* Fills full grid area for grid preview */
  .pg-preview-grid-fill {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 3px;
    flex: 1;
    grid-template-rows: 1fr 1fr;
    align-self: stretch;
  }

  /* Content area for row/settings previews (flex-start alignment) */
  .pg-preview-content-top {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    width: 100%;
    height: 100%;
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

  /* Clock entity button row */
  .pg-preview-clock-entity-row {
    display: flex;
    gap: 2px;
    justify-content: center;
    width: 100%;
    flex-shrink: 0;
    min-height: 0;
  }
  .pg-preview-clock-entity-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    flex: 1;
    max-width: 48px;
    min-height: 0;
    padding: 1px;
    border-radius: 3px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
  }
  .pg-preview-clock-entity-btn ha-icon {
    --mdc-icon-size: clamp(11px, 3cqi, 20px);
    color: var(--secondary-text-color, #bbb);
  }
  .pg-preview-clock-entity-label {
    font-size: 0.45em;
    color: var(--secondary-text-color, #bbb);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    line-height: 1;
  }
`;