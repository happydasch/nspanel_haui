/**
 * NSPanel HAUI - Panel list (table) CSS.
 *
 * Styles for `.pl-*` classes used by panel-table.js.
 */
import { css } from '../lit-import.js';

export const panelTableStyles = css`
  /* ── panel list (flexbox) ──────────── */

  .pl-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    min-height: 36px;
    overflow: visible;
  }
  .pl-row + .pl-row {
    border-top: 1px solid var(--divider-color, #e0e0e0);
  }

  .pl-card-type-icon {
    flex-shrink: 0;
    color: var(--secondary-text-color, #666);
    opacity: 0.55;
    min-width: 0;
    max-width: 40px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pl-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--primary-text-color, #000);
  }
  .pl-title .pl-unnamed {
    color: var(--secondary-text-color, #999);
    font-style: italic;
  }

  .pl-meta {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    flex-shrink: 0;
  }

  .pl-key {
    flex-shrink: 0;
    font-size: 0.72em;
    color: var(--secondary-text-color, #666);
    background: var(--secondary-background-color, #eee);
    padding: 1px 6px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .pl-badges {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
  }
  .pl-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: auto;
    min-width: 20px;
    height: 18px;
    border-radius: 3px;
    background: var(--secondary-background-color, #e0e0e0);
    color: var(--primary-background-color, #fff);
  }
  .pl-badge ha-icon {
    --mdc-icon-size: 13px;
  }
  .pl-badge-home {
    background: var(--primary-color, #03a9f4);
  }
  .pl-badge-sleep {
    background: var(--warning-color, #ffa726);
  }
  .pl-badge-wakeup {
    background: var(--success-color, #43a047);
  }
  .pl-actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .pl-move-btn {
    --mdc-icon-button-size: 32px;
  }
  .pl-move-btn ha-icon {
    --mdc-icon-size: 18px;
  }

  /* Hide inline move & edit buttons on small screens (they're in the dropdown) */
  @media all and (max-width: 500px) {
    .pl-move-btn {
      display: none;
    }
    .pl-edit-btn {
      display: none;
    }
  }
`;