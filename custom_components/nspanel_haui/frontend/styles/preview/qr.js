/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * QR page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewQRStyles = css`
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
`;
