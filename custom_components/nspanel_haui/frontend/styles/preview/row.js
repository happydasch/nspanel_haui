/**
 * NSPanel HAUI - Preview simulation CSS.
 *
 * Row page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewRowStyles = css`
  /* --- Stacked row cards for row preview (each row = 20% height via flex) --- */
  .pg-preview-row-stack {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex: 1;
    align-self: stretch;
    min-height: 0;
  }
  .pg-preview-row-card {
    display: flex;
    align-items: center;
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
    gap: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 6px;
    padding: 0 6px;
  }
  .pg-preview-row-card ha-icon {
    --mdc-icon-size: clamp(14px, 3cqi, 24px);
    color: var(--secondary-text-color, #bbb);
    flex-shrink: 0;
    display: flex;
  }
  .pg-preview-row-card .pg-preview-tile-label {
    flex: 1;
    text-align: left;
    font-size: clamp(0.55em, 1.5cqi, 0.85em);
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pg-preview-row-card .pg-preview-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: clamp(16px, 3.5cqi, 26px);
    height: clamp(16px, 3.5cqi, 26px);
    flex-shrink: 0;
  }
  .pg-preview-row-card .pg-preview-btn ha-icon {
    --mdc-icon-size: clamp(12px, 2.5cqi, 20px);
  }
  .pg-preview-row-empty {
    background: rgba(255,255,255,0.03);
  }
`;
