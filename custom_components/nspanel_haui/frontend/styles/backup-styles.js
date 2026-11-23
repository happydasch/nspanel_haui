import { css } from '../lit-import.js';

/** The Backups sidebar's body: the file's two directions, then the copy's picks. */
export const backupStyles = css`
  /* The body scrolls inside the sidebar's strip, like the Updates and Theme
     bodies. A column of cards, not a grid: grid rows would shrink to the space
     they get, and a card must keep the height its own content needs. */
  .haui-backup-sidebar {
    display: flex;
    box-sizing: border-box;
    /* The scroll area, not the page around it: the host is the flex column the
       editor sheet gives the sidebar, so a flex share and a definite height both
       keep this box inside the strip - a body that only knows its content size
       would grow and be clipped by the host instead of scrolling. */
    flex: 1 1 auto;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 12px 16px 16px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .haui-backup-sidebar > * { flex: 0 0 auto; }
  /* A card's blocks sit one under the other, a step apart. */
  .haui-backup-sidebar .haui-surface-body { display: grid; gap: 12px; }
  .haui-backup-note { margin: 0; color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  /* What an import or a copy replaces is a banner, not a note: the HA alert
     brings its own icon, tone and frame, so this file styles nothing of it. */
  /* Export and Import work on the same file, so they are one pair: one row of
     the same width, and the sentence that explains the file is the card's
     subtitle while the warning that belongs to Import runs below both. */
  .haui-backup-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .haui-backup-actions .haui-button, .haui-backup-sidebar .haui-surface-body > .haui-button { width: 100%; }
  .haui-backup-error { margin: 0; color: var(--haui-bad-text); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
`;
