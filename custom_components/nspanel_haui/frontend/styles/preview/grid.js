/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Grid page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewGridStyles = css`
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

  /* Fills full grid area for grid preview */
  .pg-preview-grid-fill {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 3px;
    flex: 1;
    grid-template-rows: 1fr 1fr;
    align-self: stretch;
  }
`;
