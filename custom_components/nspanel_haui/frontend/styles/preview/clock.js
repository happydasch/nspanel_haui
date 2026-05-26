/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Clock / ClockTwo page preview styles.
 */
import { css } from '../../lit-import.js';

export const previewClockStyles = css`
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
