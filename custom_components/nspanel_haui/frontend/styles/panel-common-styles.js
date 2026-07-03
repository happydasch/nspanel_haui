/**
 * NSPanel HAUI - Shared common CSS.
 *
 * Styles shared between grid view (panel-grid.js) and list view (panel-table.js):
 * panel groups, headers, device selector, dropdown menus.
 */
import { css } from '../lit-import.js';

export const panelCommonStyles = css`
  /* ── device selector bar (no-device state) ── */
  .device-selector-bar {
    padding: 16px;
  }

  /* ── panel toolbar (two rows) ─────── */
  .panel-toolbar {
    display: flex;
    flex-direction: column;
  }
  .panel-toolbar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
  }
  .panel-toolbar-row-selector {
    padding: 10px;
  }
  .panel-toolbar-row-selector .toolbar-select-wrap {
    flex: 1;
    min-width: 0;
  }
  .panel-toolbar-row-selector .toolbar-select-wrap .toolbar-select {
    width: 100%;
  }
  .panel-toolbar-row-actions {
    padding-bottom: 10px;
  }
  /* ── toolbar device info strip (inside toolbar card) ── */
  .card-toolbar-device-info {
    padding: 0 16px 10px;
  }

  /* ── panel groups ────────────────── */

  .panel-group[open] {
    padding-bottom: 4px;
  }

  .panel-group {
    margin-bottom: 0;
  }

  .group-title {
    left: 0;
    z-index: 1;
    padding: 12px 0;
    font-weight: 600;
    font-size: 1em;
  }
  .info-grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  details.panel-group .group-title {
    user-select: none;
    padding: 12px;
    cursor: pointer;
  }
  details.panel-group .collapse-indicator {
    margin-left: 6px;
    font-size: 0.85em;
  }

  /* ── empty-state placeholders ── */
  .no-device-selected {
    padding: 16px;
  }

  /* ── dropdown menu ───────────────── */
  .pl-more {
    position: relative;
    display: inline-block;
  }
  .pl-more ha-icon-button.active {
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 50%;
  }
  .pl-dropdown {
    position: absolute;
    right: 0;
    top: 100%;
    z-index: 300;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    min-width: 160px;
    overflow: hidden;
  }
  .pl-dropdown-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 16px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 0.9em;
    color: var(--primary-text-color, #212121);
  }
  .pl-dropdown-item:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .pl-dropdown-item:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .pl-dropdown-divider {
    height: 1px;
    background: var(--divider-color, #e0e0e0);
    margin: 4px 0;
  }
  .pl-dropdown-item.danger {
    color: var(--error-color, #db4437);
  }
  .pl-dropdown-item.danger:hover {
    background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent);
  }

  /* ── system panel "Edited" badge (icon-only, pl-badge family) ─── */
  .pl-badge-edited {
    background: var(--warning-color, #ffa726);
  }

  /* ── spacer (pushes items to opposite edges) ── */
  .pl-spacer {
    flex: 1;
  }
  /* ── toolbar actions strip (below toolbar card) ── */
  .toolbar-actions-strip {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: var(--ha-space-6);
  }

  /* ── view toggle segmented group ─── */
  .view-toggle-group {
    display: flex;
    border: 1px solid var(--primary-color, #03a9f4);
    border-radius: 8px;
    overflow: hidden;
  }
  .view-toggle-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border: none;
    background: transparent;
    color: var(--secondary-text-color, #666);
    cursor: pointer;
    font-size: 0.85em;
    font-family: inherit;
    transition: background 0.15s, color 0.15s;
  }
  .view-toggle-btn:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .view-toggle-btn.active {
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
  }
  .view-toggle-btn.active:hover {
    background: var(--primary-color, #03a9f4);
  }
  .view-toggle-btn ha-icon {
    --mdc-icon-size: 16px;
  }
`;