/**
 * NSPanel HAUI - Preview simulation CSS.
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

  /* === ClockTwo word-clock matrix === */
  .pg-preview-clocktwo {
    display: flex;
    flex-direction: column;
    width: 100%;
    flex: 1;
    gap: 3px;
  }
  .pg-preview-clocktwo-grid {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-height: 0;
  }
  .pg-preview-clocktwo-row {
    display: grid;
    grid-template-columns: repeat(11, 1fr);
    gap: 1px;
    flex: 1;
  }
  .pg-preview-clocktwo-letter {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 2px;
    background: rgba(255,255,255,0.04);
    min-height: 0;
  }
  .pg-preview-clocktwo-letter span {
    font-size: clamp(6px, 1.3cqi, 9px);
    color: var(--secondary-text-color, #555);
    font-weight: 500;
    line-height: 1;
  }
  .pg-preview-clocktwo-letter.active {
    background: rgba(79, 195, 247, 0.2);
  }
  .pg-preview-clocktwo-letter.active span {
    color: var(--primary-color, #4fc3f7);
    font-weight: 700;
  }
  .pg-preview-clocktwo-side-dots {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
    min-width: 12px;
    padding: 4px 0;
  }
  .pg-preview-clocktwo-special {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 6px;
    color: rgba(255,255,255,0.12);
    flex-shrink: 0;
  }
  .pg-preview-clocktwo-special.active {
    color: var(--accent-color, #ffab40);
  }
  .pg-preview-clocktwo-notif {
    display: flex;
    align-items: center;
    justify-content: center;
  }
`;
