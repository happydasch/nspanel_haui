/**
 * NSPanel HAUI - Item list CSS.
 *
 * Reusable styles for item list rows, editing panels, and action buttons.
 * Extracted from editorStyles in styles.js.
 */
import { css } from '../lit-import.js';

export const itemListStyles = css`
  /* ── item list ───────────────────── */
  .item-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .item-list-empty {
    padding: 12px;
    text-align: center;
    font-size: 0.85em;
    color: var(--secondary-text-color, #666);
    border: 1px dashed var(--divider-color, #e0e0e0);
    border-radius: 6px;
  }

  /* ── item list row ───────────────── */
  .item-list-row {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 3px 2px 3px 3px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .item-list-row:hover {
    border-color: var(--primary-color, #03a9f4);
    box-shadow: 0 1px 4px rgba(3, 169, 244, 0.1);
  }
  .item-row-main {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 8px 4px 4px;
    border: 0;
    border-radius: 6px;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
  }
  .item-row-main:hover { background: var(--secondary-background-color, #f5f5f5); }
  .item-row-main:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -2px; }
  .item-row-edit {
    flex-shrink: 0;
    --mdc-icon-size: 16px;
    color: var(--secondary-text-color, #666);
    opacity: 0.7;
  }
  .item-row-main:hover .item-row-edit { opacity: 1; }

  .item-row-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--secondary-background-color, #f0f0f0);
    color: var(--primary-color, #03a9f4);
    --mdc-icon-size: 20px;
    position: relative;
  }

  .item-row-text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .item-row-primary {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 1em;
    font-weight: 500;
  }
  .item-row-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item-row-chip {
    flex-shrink: 0;
    font-size: 0.7em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 7px;
    border-radius: 10px;
    background: var(--secondary-background-color, #eee);
    color: var(--secondary-text-color, #666);
  }
  .item-row-secondary {
    font-size: 0.82em;
    color: var(--secondary-text-color, #666);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--code-font-family, monospace);
    opacity: 0.9;
  }
  .item-list-row[draggable="true"] { cursor: grab; }
  .item-list-row.is-dragging { opacity: .5; }
  .item-list-row.is-drop-before { box-shadow: inset 0 2px 0 var(--primary-color, #03a9f4); }
  .item-list-row.is-drop-after { box-shadow: inset 0 -2px 0 var(--primary-color, #03a9f4); }
  .item-row-grip {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    color: var(--secondary-text-color, #666);
    opacity: 0.7;
    --mdc-icon-size: 18px;
  }
  .item-list-row:hover .item-row-grip { opacity: 1; }
  .item-row-remove {
    flex-shrink: 0;
    --mdc-icon-button-size: 34px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color, #666);
  }
  .item-row-remove:hover { color: var(--error-color, #db4437); }

  /* ── collapsible toggle ──────────── */
  .collapsible-title {
    cursor: pointer;
    font-size: 0.85em;
    color: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    gap: 4px;
    user-select: none;
    text-transform: uppercase;
    padding: 4px 0;
  }
  .collapsible-title .collapsible-icon {
    transition: transform 0.2s;
    --mdc-icon-size: 18px;
    flex-shrink: 0;
  }
  .collapsible-title .collapsible-icon.is-open {
    transform: rotate(90deg);
  }
  .item-advanced-section {
    display: none;
    padding-left: 12px;
    border-left: 2px solid var(--divider-color, #e0e0e0);
    margin-top: 8px;
    margin-bottom: 8px;
  }
  .item-advanced-section.open {
    display: block;
  }

  /* ── color popover ────────────────── */
  .color-popover {
    display: none;
    position: absolute;
    z-index: 100;
    margin-top: 4px;
    padding: 8px;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  }
  .color-popover.open {
    display: block;
  }
  .item-edit-inline .form-group {
    position: relative;
  }

  /* ── inline item edit form ───────── */
  .item-edit-inline {
    padding: 14px;
    border: 1px solid var(--primary-color, #03a9f4);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    margin: 8px 0;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary-color, #03a9f4) 10%, transparent);
  }
  .item-edit-inline .item-edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
  }

  /* ── list items editor ───────────── */
  .list-items {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .item-list-limit {
    font-size: 0.82em;
    color: var(--secondary-text-color, #999);
    text-align: center;
    padding: 4px;
  }
`;