/**
 * NSPanel HAUI - Preview simulation CSS.
 *
 * Alarm / Unlock page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewAlarmStyles = css`
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

  /* Portrait TFT: keypad on top, the action buttons as a 2x2 block below */
  .pg-card-preview--portrait .pg-preview-alarm {
    flex-direction: column;
  }
  .pg-card-preview--portrait .pg-preview-alarm .pg-preview-action-col {
    flex-direction: row;
    flex-wrap: wrap;
    width: 100%;
  }
  .pg-card-preview--portrait .pg-preview-alarm .pg-preview-action-col .pg-preview-btn {
    flex: 1 1 45%;
    min-height: 18px;
  }
`;
