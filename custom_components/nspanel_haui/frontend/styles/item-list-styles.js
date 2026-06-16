/**
 * NSPanel HAUI - Editor - Item list CSS.
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
    gap: 10px;
    padding: 8px 12px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .item-list-row:hover {
    border-color: var(--primary-color, #03a9f4);
    box-shadow: 0 1px 4px rgba(3, 169, 244, 0.1);
  }

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
  .item-row-color-dot {
    position: absolute;
    bottom: -2px;
    right: -2px;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    border: 2px solid var(--card-background-color, #fff);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    pointer-events: none;
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
  .item-list-override-badge {
    flex-shrink: 0;
    font-size: 0.85em;
    color: var(--secondary-text-color, #666);
  }

  .item-row-actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0;
  }
  .item-row-actions ha-icon-button {
    --mdc-icon-button-size: 32px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color, #666);
    transition: color 0.12s;
  }
  .item-row-actions ha-icon-button:hover {
    color: var(--primary-text-color, #212121);
  }
  .item-row-actions ha-icon-button[disabled] {
    opacity: 0.3;
    pointer-events: none;
  }

  .add-item-btn {
    background: transparent;
    color: var(--primary-color, #03a9f4);
    border: 1px dashed var(--divider-color, #e0e0e0);
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9em;
    font-weight: 500;
    width: 100%;
    margin-top: 8px;
    transition: background 0.15s, border-color 0.15s;
    font-family: inherit;
  }
  .add-item-btn:hover {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent);
    border-color: var(--primary-color, #03a9f4);
    border-style: solid;
  }

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
  .list-items-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    transition: border-color 0.15s;
  }
  .list-items-row:hover {
    border-color: var(--primary-color, #03a9f4);
  }
  .list-items-input {
    flex: 1;
    min-width: 0;
  }
  .list-items-input ha-input,
  .list-items-input ha-select,
  .list-items-input .entity-picker-wrap {
    width: 100%;
  }
  .list-items-remove {
    flex-shrink: 0;
    --mdc-icon-button-size: 32px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color, #666);
  }
  .item-list-limit {
    font-size: 0.82em;
    color: var(--secondary-text-color, #999);
    text-align: center;
    padding: 4px;
  }
`;