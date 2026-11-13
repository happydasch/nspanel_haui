/**
 * NSPanel HAUI - Item list CSS.
 *
 * Reusable styles for item list rows, editing panels, and action buttons.
 * Extracted from editorStyles in styles.js.
 */
import { css } from '../lit-import.js';

export const itemListStyles = css`
  /* ── item list ───────────────────── */
  .haui-item-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  /* ── item list row ───────────────── */
  .haui-item-list-row {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 4px 4px 4px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    transition: border-color 150ms, box-shadow 150ms;
  }
  .haui-item-list-row:hover {
    border-color: var(--primary-color, #03a9f4);
    box-shadow: 0 1px 4px color-mix(in srgb, var(--primary-color) 10%, transparent);
  }
  .haui-item-row-main {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px 4px 4px;
    border: 0;
    border-radius: var(--haui-radius-control);
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
  }
  .haui-item-row-main:hover { background: var(--secondary-background-color, #f5f5f5); }
  .haui-item-row-edit {
    flex-shrink: 0;
    --mdc-icon-size: 16px;
    color: var(--secondary-text-color, #666);
    opacity: 0.7;
  }
  .haui-item-row-main:hover .haui-item-row-edit { opacity: 1; }

  .haui-item-row-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: var(--haui-radius-control);
    background: var(--secondary-background-color, #f5f5f5);
    color: var(--primary-color, #03a9f4);
    --mdc-icon-size: 20px;
    position: relative;
  }

  .haui-item-row-text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .haui-item-row-primary {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--haui-text-body);
    font-weight: 500;
  }
  .haui-item-row-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-item-row-chip {
    flex-shrink: 0;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-radius: var(--haui-radius-control);
    color: var(--secondary-text-color, #666);
  }
  .haui-item-row-secondary {
    font-size: var(--haui-text-caption);
    color: var(--secondary-text-color, #666);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--haui-mono);
    opacity: 0.9;
  }
  .haui-item-list-row[draggable="true"] { cursor: grab; }
  .haui-item-list-row.is-dragging { opacity: .5; }
  .haui-item-list-row.is-drop-before { box-shadow: inset 0 2px 0 var(--primary-color, #03a9f4); }
  .haui-item-list-row.is-drop-after { box-shadow: inset 0 -2px 0 var(--primary-color, #03a9f4); }
  .haui-item-row-grip {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    color: var(--secondary-text-color, #666);
    opacity: 0.7;
    --mdc-icon-size: 18px;
  }
  .haui-item-list-row:hover .haui-item-row-grip { opacity: 1; }
  .haui-item-row-remove {
    flex-shrink: 0;
    --mdc-icon-button-size: 34px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color, #666);
  }
  .haui-item-row-remove:hover { color: var(--error-color, #db4437); }

  /* ── collapsible toggle ──────────── */
  .haui-collapsible-title {
    cursor: pointer;
    font-size: var(--haui-text-caption);
    color: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    gap: 4px;
    user-select: none;
    text-transform: uppercase;
    padding: 4px 0;
  }
  .haui-collapsible-title .haui-collapsible-icon {
    transition: transform 150ms;
    --mdc-icon-size: 18px;
    flex-shrink: 0;
  }
  .haui-collapsible-title .haui-collapsible-icon.is-open {
    transform: rotate(90deg);
  }
  .haui-item-advanced-section {
    display: none;
    padding-left: 12px;
    border-left: 2px solid var(--divider-color, #e0e0e0);
    margin-top: 8px;
    margin-bottom: 8px;
  }
  .haui-item-advanced-section.is-open {
    display: block;
  }

  /* ── color popover ────────────────── */
  .haui-color-popover {
    display: none;
    position: absolute;
    z-index: 100;
    margin-top: 4px;
    padding: 8px;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    box-shadow: var(--haui-shadow-overlay);
  }
  .haui-color-popover.open {
    display: block;
  }
  .haui-item-edit-inline .haui-field {
    position: relative;
  }

  /* ── inline item edit form ───────── */
  .haui-item-edit-inline {
    padding: 12px;
    border: 1px solid var(--primary-color, #03a9f4);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    margin: 8px 0;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary-color, #03a9f4) 10%, transparent);
  }
  .haui-item-edit-inline .haui-item-edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
  }

  /* ── list items editor ───────────── */
  .haui-item-list-items {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .haui-item-list-limit {
    font-size: var(--haui-text-caption);
    color: var(--secondary-text-color, #666);
    text-align: center;
    padding: 4px;
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;