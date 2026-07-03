/**
 * NSPanel HAUI - Preview simulation CSS.
 *
 * Row page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewRowStyles = css`
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
`;
