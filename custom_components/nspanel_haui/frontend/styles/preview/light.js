/**
 * NSPanel HAUI - Preview simulation CSS.
 *
 * Light page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewLightStyles = css`
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
`;
