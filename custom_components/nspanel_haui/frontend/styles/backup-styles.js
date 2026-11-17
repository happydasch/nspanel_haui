import { css } from '../lit-import.js';

/** The Backups sidebar's body: one card per direction, each with its button. */
export const backupStyles = css`
  .haui-backup-sidebar { display: grid; gap: 12px; padding: 12px 16px 16px; }
  .haui-backup-sidebar > * { flex: 0 0 auto; }
  /* A card's note and its button sit one under the other, a step apart. */
  .haui-backup-sidebar .haui-surface-body { display: grid; gap: 8px; }
  .haui-backup-note { margin: 0; color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  /* One action fills its card: the label is the card's whole call to action. */
  .haui-backup-sidebar .haui-button { width: 100%; }
`;
