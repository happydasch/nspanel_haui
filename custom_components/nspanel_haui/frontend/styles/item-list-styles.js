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
    transition: border-color 150ms, background-color 150ms, box-shadow 150ms;
  }
  .haui-item-list-row:hover {
    border-color: var(--primary-color, #03a9f4);
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, var(--card-background-color, #fff));
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
  .haui-item-row-main:hover { background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent); }
  .haui-item-row-edit {
    flex-shrink: 0;
    --mdc-icon-size: 16px;
    color: var(--secondary-text-color, #666);
    opacity: 0.7;
  }
  .haui-item-row-main:hover .haui-item-row-edit { opacity: 1; }

  .haui-item-service-data {
    min-height: 80px;
    font-family: var(--haui-mono);
    font-size: var(--haui-text-label);
  }

  .haui-item-row-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: var(--haui-radius-control);
    background: var(--haui-item-row-icon-background, var(--secondary-background-color, #f5f5f5));
    color: var(--haui-item-row-icon-color, var(--primary-color, #03a9f4));
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
    font-size: var(--haui-text-label);
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
    letter-spacing: .05em;
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
  .haui-item-row-remove:hover { color: var(--haui-bad-icon); }

  /* ── advanced fold (details/summary) ── */
  .haui-collapsible-title {
    list-style: none;
    cursor: pointer;
    font-size: var(--haui-text-caption);
    font-weight: 500;
    color: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    gap: 4px;
    user-select: none;
    padding: 4px 0;
    border-radius: var(--haui-radius-control);
  }
  .haui-collapsible-title::-webkit-details-marker { display: none; }
  .haui-collapsible-title:focus-visible {
    outline: var(--haui-focus-ring);
    outline-offset: var(--haui-focus-offset);
  }
  .haui-collapsible-title .haui-collapsible-icon {
    transition: transform 150ms;
    --mdc-icon-size: 18px;
    flex-shrink: 0;
  }
  .haui-item-advanced[open] > .haui-collapsible-title .haui-collapsible-icon {
    transform: rotate(90deg);
  }
  .haui-item-advanced-section {
    padding-left: 12px;
    border-left: 2px solid var(--divider-color, #e0e0e0);
    margin-top: 8px;
    margin-bottom: 8px;
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

  /* ── one value or a value per state ── */
  /* The label keeps its row; the switch between one value and a value per
     state sits at its right edge, compact like a label. */
  .haui-field-label-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 4px 8px;
    margin-bottom: 4px;
  }
  .haui-item-edit-inline .haui-field-label-row > label { margin-bottom: 0; }
  .haui-state-mode { margin-left: auto; }
  .haui-state-mode .haui-segmented { padding: 0; gap: 0; }
  .haui-state-mode .haui-segmented-option {
    min-height: 24px;
    padding: 0 8px;
    font-size: var(--haui-text-caption);
  }
  .haui-state-value-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  /* State, its value and the remove button on one line; the value's template
     result, presets and the row's warning go under the state and the value. */
  .haui-state-value {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr) auto;
    align-items: start;
    gap: 4px 8px;
  }
  .haui-state-value > .haui-icon-button { width: 32px; height: 32px; --mdc-icon-size: 18px; }
  .haui-state-value-control { min-width: 0; }
  .haui-state-value-warning { grid-column: 1 / -1; margin-top: 0; }

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