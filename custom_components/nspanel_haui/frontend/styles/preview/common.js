/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Common preview styles shared across all panel types.
 * Extracted from panel-preview-styles.js.
 */
import { css } from '../../lit-import.js';

export const previewCommonStyles = css`
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
    gap: 2px;
    padding: 4px 2px;
    min-height: 40px;
    overflow: hidden;
    background: rgba(255,255,255,0.08);
  }
  .pg-preview-tile-icon-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 0;
  }
  .pg-preview-tile-icon-wrap ha-icon {
    --mdc-icon-size: clamp(16px, 5cqi, 28px);
    color: var(--primary-text-color, #ddd);
  }
  .pg-preview-tile-label {
    flex-shrink: 0;
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

  .pg-preview-btn-label-sm {
    font-size: 0.4em;
    color: var(--secondary-text-color, #666);
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

  /* Content area for row/settings previews (flex-start alignment) */
  .pg-preview-content-top {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    width: 100%;
    height: 100%;
  }
`;
