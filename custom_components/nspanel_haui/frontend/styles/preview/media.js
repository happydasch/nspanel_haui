/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Media page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewMediaStyles = css`
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
`;
