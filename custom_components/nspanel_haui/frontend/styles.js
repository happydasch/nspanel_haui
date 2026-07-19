/**
 * NSPanel HAUI - styles.
 *
 * Split into modular exports:
 *   haStyle         — typography, layout utilities, link styles
 *   haStyleDialog   — responsive dialog sizing rules (adopted from HA's haStyleDialog)
 *   editorStyles    — everything else (panel list, config sections, form elements, device info strip, etc.)
 *
 * Follows HA's resources/styles.ts pattern to avoid duplicate overlay/button/dialog
 * styles that ha-dialog and ha-button already provide.
 */

import { css } from './lit-import.js';

import { panelGridStyles } from './styles/panel-grid-styles.js';
import { panelTableStyles } from './styles/panel-table-styles.js';
import { panelCommonStyles } from './styles/panel-common-styles.js';
import { panelPreviewStyles } from './styles/panel-preview-styles.js';
import { colorPickerStyles } from './styles/color-picker-styles.js';
import { dropdownStyles } from './styles/dropdown-styles.js';
import { itemListStyles } from './styles/item-list-styles.js';
import { colorDialogStyles } from './styles/color-dialog-styles.js';
import { formCommonStyles } from './styles/form-common-styles.js';


/**
 * Base HA-style typography and layout utilities.
 * Subset of HA's `haStyle` — only what this editor needs.
 *
 * NOTE: container-type is intentionally NOT on :host here.
 * It's on editorContainerStyles, which is only applied to NSPanelEditor
 * (not dialog components), so dialogs don't get layout containment and
 * position: fixed works relative to the viewport inside them.
 */
export const haStyle = css`
  :host {
    display: block;
  }
  .container {
    display: flex;
    flex-direction: column;
    flex: 1;
    padding-bottom: var(--ha-space-6);
  }
  ha-icon-button {
    color: var(--secondary-text-color, #666);
  }

  /* ── layout utility classes ───────── */
  .w-full {
    width: 100%;
  }
  .text-secondary {
    color: var(--secondary-text-color, #666);
  }
  .empty-state-text {
    color: var(--secondary-text-color, #666);
    font-style: italic;
  }
  .panel-table-empty {
    text-align: center;
    padding: 2rem;
  }
`;

/**
 * Container-type styles for the NSPanelEditor host only.
 * Kept separate from haStyle so that dialog components (device-manager,
 * edit-panel, etc.) do NOT get layout containment, allowing position: fixed
 * dropdowns inside them to be viewport-relative.
 */
export const editorContainerStyles = css`
  :host {
    container-type: inline-size;
    container-name: haui-editor;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }
`;

/**
 * Responsive dialog sizing rules, adopted from HA's haStyleDialog.
 * ha-dialog handles animations, overlay/scrim, focus management, and close
 * buttons; we only set min/max widths and a fullscreen breakpoint.
 */
export const haStyleDialog = css`
  ha-dialog {
    --ha-dialog-max-width: min(600px, 95vw);
    max-height: calc(100vh - 96px);
  }
  @media all and (max-width: 450px), all and (max-height: 500px) {
    ha-dialog {
      --ha-dialog-max-width: 100vw;
      max-height: 100vh;
      width: 100vw;
    }
  }
`;

/**
 * Editor-specific styles: toolbar, action bar, panel list, form groups,
 * config sections, item lists, device info strip, dropdowns, etc.
 * Dialog overlay / footer / button styles are NOT included — ha-dialog
 * and ha-button provide those.
 */
export const editorStyles = css`
  ${panelGridStyles}${panelTableStyles}${panelCommonStyles}${panelPreviewStyles}
  ${colorDialogStyles}${colorPickerStyles}${dropdownStyles}${itemListStyles}${formCommonStyles}
  .container {
    display: flex;
    flex-direction: column;
    flex: 1;
    padding-bottom: var(--ha-space-6);
  }

  /* ── main content area (flex-grows to push footer down) ── */
  .main-content {
    flex: 1 0 auto;
  }

  /* ── title header ──────────────── */
  .toolbar-header {
    display: flex;
    align-items: center;
    height: var(--header-height, 56px);
    padding: 0 12px;
    box-sizing: border-box;
    background: var(--app-header-background-color, var(--sidebar-background-color, #f0f0f0));
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }

  .toolbar-title {
    line-height: var(--ha-line-height-normal);
    flex-grow: 1;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
    min-width: 0;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: 400;
    margin-inline-start: var(--ha-space-6);
  }

  .menu-toggle-btn {
    --mdc-icon-button-size: 40px;
    flex-shrink: 0;
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
  }

  /* ── device manager button ────────── */
  .device-manager-btn {
    --mdc-icon-button-size: 36px;
  }
  .device-manager-btn ha-icon {
    color: var(--primary-color, #03a9f4);
  }
  .toolbar-select {
    flex: 1;
    min-width: 0;
    --mdc-menu-min-width: 200px;
  }
  .device-name-static {
    flex: 1 1 auto;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0 4px;
  }
  .device-name-static .device-name-count {
    color: var(--secondary-text-color, #666);
    font-weight: 400;
    margin-left: 6px;
    font-size: 0.85em;
  }

  /* ── content card ────────────────── */

  .content-card {
    margin: var(--ha-space-6);
  }

  .content-card .card-content {
    padding: 0;
  }

  /* ── dialog body (inside ha-dialog) ── */
  .dialog-body {
    position: relative;
  }
  .dialog-body > .form-group:not(:last-child) {
    margin-bottom: 18px;
  }

  /* ── palette preview ───────────────── */
  .palette-preview-row {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    padding: 4px 0;
  }
  .palette-swatch {
    flex: 1;
    height: 32px;
    border-radius: 4px;
    border: 1px solid var(--divider-color, #ccc);
  }
  .palette-caption {
    font-size: 0.8em;
    color: var(--secondary-text-color, #999);
  }

/* ── toast / loading ─────────────── */
  .toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 24px;
    border-radius: 8px;
    color: #fff;
    font-weight: 500;
    z-index: 10000;
    animation: toast-in 0.3s ease;
  }
  .toast.success {
    background: var(--success-color, #4caf50);
  }
  .toast.error {
    background: var(--error-color, #f44336);
  }
  @keyframes toast-in {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
  .loading {
    text-align: center;
    padding: 32px;
    color: var(--secondary-text-color, #666);
  }

  /* ── device info strip (inline in toolbar) ── */
  .device-info-strip {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--secondary-text-color, #666);
    white-space: nowrap;
  }
  .info-strip-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.9em;
  }

  .connection-indicator-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .connection-indicator-dot.dot-connected {
    background: var(--success-color, #43a047);
  }

  .connection-indicator-dot.dot-handshaking {
    background: var(--warning-color, #fb8c00);
  }

  .connection-indicator-dot.dot-disconnected {
    background: var(--error-color, #e53935);
  }

  .connection-indicator-dot.dot-unknown {
    background: var(--disabled-text-color, #9e9e9e);
  }

  /* ── device info strip: richer icons, labels, inline RSSI ── */
  .strip-icon {
    --mdc-icon-size: 14px;
    flex-shrink: 0;
  }
  .strip-label {
    font-size: 0.9em;
  }
  .strip-mono {
    font-family: var(--font-family-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace);
    font-size: 0.82em;
  }
  .strip-error {
    color: var(--error-color, #f44336);
  }
  .strip-rssi-bars {
    display: inline-flex;
    align-items: end;
    gap: 1.5px;
    height: 11px;
  }
  .strip-rssi-bar {
    width: 3px;
    border-radius: 1px;
    background: var(--disabled-text-color, #d0d0d0);
    transition: background 0.3s ease;
  }
  .strip-rssi-bar:nth-child(1) { height: 3px; }
  .strip-rssi-bar:nth-child(2) { height: 6px; }
  .strip-rssi-bar:nth-child(3) { height: 9px; }
  .strip-rssi-bar:nth-child(4) { height: 12px; }
  .strip-rssi-bar.wifi-excellent { background: var(--success-color, #43a047); }
  .strip-rssi-bar.wifi-good      { background: #7cb342; }
  .strip-rssi-bar.wifi-fair      { background: var(--warning-color, #fb8c00); }
  .strip-rssi-bar.wifi-weak      { background: var(--error-color, #e53935); }

  /* ── device info dialog: status card (top) ── */
  .di-status-card {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    border: 1px solid var(--divider-color, #e0e0e0);
    background: var(--secondary-background-color, #f5f5f5);
    transition: background 0.2s;
  }
  .di-status-card.connected {
    border-color: var(--success-color, #43a047);
    background: color-mix(in srgb, var(--success-color, #43a047) 8%, transparent);
  }
  .di-status-card.disconnected {
    border-color: var(--error-color, #e53935);
    background: color-mix(in srgb, var(--error-color, #e53935) 6%, transparent);
  }
  .di-status-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }
  .di-status-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .di-status-icon {
    --mdc-icon-size: 28px;
  }
  .di-status-card.connected .di-status-icon {
    color: var(--success-color, #43a047);
  }
  .di-status-card.disconnected .di-status-icon {
    color: var(--error-color, #e53935);
  }
  .di-status-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .di-status-label {
    font-size: 1.05em;
    font-weight: 600;
    color: var(--primary-text-color, #212121);
  }
  .di-status-detail {
    font-size: 0.78em;
    color: var(--secondary-text-color, #888);
    text-transform: capitalize;
  }
  .di-status-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-inline-start: auto;
  }
  .di-status-meta-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.82em;
    color: var(--secondary-text-color, #888);
    white-space: nowrap;
  }
  .di-meta-icon {
    --mdc-icon-size: 14px;
    color: var(--secondary-text-color, #aaa);
  }

  /* ── device info dialog: section icon ── */
  .di-section-icon {
    --mdc-icon-size: 16px;
    color: var(--secondary-text-color, #999);
  }
  .di-info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .di-info-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 4px 0;
  }
  .di-info-label {
    font-size: 0.72em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: var(--secondary-text-color, #999);
  }
  .di-info-value {
    font-size: 0.88em;
    color: var(--primary-text-color, #333);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .di-mono {
    font-family: var(--font-family-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace);
    font-size: 0.85em;
  }
  .di-rssi-text {
    font-size: 0.82em;
    color: var(--secondary-text-color, #888);
    margin-left: 4px;
  }

  /* ── device info dialog: tables (listeners / timers) ── */
  .di-table {
    display: table;
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8em;
  }
  .di-table-row {
    display: table-row;
  }
  .di-table-cell {
    display: table-cell;
    padding: 4px 8px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    vertical-align: top;
  }
  .di-table-header .di-table-cell {
    font-weight: 600;
    color: var(--secondary-text-color, #666);
    border-bottom: 2px solid var(--divider-color, #e0e0e0);
    white-space: nowrap;
  }
  .di-table-cell-entity {
    width: 40%;
    max-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .di-table-cell-attr {
    width: 25%;
  }
  .di-table-cell-cb {
    width: 35%;
  }
  .di-table-cell-type {
    width: 25%;
  }
  .di-table-cell-int {
    width: 35%;
  }

  /* ── logs dialog content ─────────── */

  .logs-content {
    background: var(--secondary-background-color, #f5f5f5);
    padding: 12px;
    border-radius: 6px;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.5;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* ── device manager dialog ──────── */

  .device-mgr-add-form {
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
  }

  .device-mgr-add-form .native-input {
    display: block;
    width: 100%;
  }

  .device-mgr-add-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 8px;
  }

  .device-mgr-error {
    color: var(--error-color, #e53935);
    font-size: 0.85em;
    margin: 4px 0 0;
  }

  .device-mgr-section {
    margin-top: 12px;
  }

  .device-mgr-section-title {
    margin: 0 0 8px;
    font-size: 0.95em;
    font-weight: 600;
    color: var(--primary-text-color, #333);
  }

  .device-mgr-empty {
    color: var(--secondary-text-color, #666);
    font-size: 0.9em;
    font-style: italic;
  }

  .device-mgr-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
  }

  /* ── dialog header (title left, close button on the right) ─────── */
  .dialog-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--card-background-color, #fff);
  }
  .dialog-header.dialog-header--extended {
    flex-direction: column;
    gap: 0;
    position: sticky;
    top: 0;
    z-index: 2;
    padding-bottom: 12px;
  }
  .dialog-header.dialog-header--extended .dialog-header-bar {
    margin-bottom: 8px;
  }
  .dialog-header-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
  }
  .dialog-header-title {
    flex: 1;
    min-width: 0;
    font-size: 1.25em;
    font-weight: 400;
    color: var(--primary-text-color, #212121);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .dialog-header-close {
    flex-shrink: 0;
    --mdc-icon-button-size: 40px;
    color: var(--secondary-text-color, #666);
    margin-inline-end: -8px;
  }

  /* ── dialog footer (primary actions grouped on the right) ──────── */
  .footer-wrapper {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    width: 100%;
  }
  .footer-toggle-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }

  .device-mgr-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 6px;
    transition: background 0.1s;
    cursor: pointer;
  }
  .device-mgr-row.row-disabled .device-mgr-row-body,
  .device-mgr-row.row-disabled .device-mgr-row-actions ha-icon-button {
    opacity: 0.55;
  }

  .device-mgr-row-body {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .device-mgr-row-head {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .device-mgr-state-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .device-mgr-state-indicator.state-on { background: var(--success-color, #43a047); }
  .device-mgr-state-indicator.state-off { background: var(--disabled-text-color, #bbb); }

  .device-mgr-name {
    font-weight: 600;
    font-size: 1em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .device-mgr-panel-count {
    font-size: 0.83em;
    color: var(--secondary-text-color, #888);
    white-space: nowrap;
    margin-inline-start: auto;
  }

  .device-mgr-row-details {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    padding-inline-start: 16px; /* align with text after status dot */
  }

  .device-mgr-row-actions {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .device-mgr-row:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }

  .device-mgr-row.selected {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--primary-color, #03a9f4) 20%, transparent);
  }

  .device-mgr-more {
    position: relative;
    display: inline-block;
  }
  .device-mgr-more ha-icon-button.active {
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 50%;
  }

  .device-mgr-dropdown {
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
  .device-mgr-dropdown-item {
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
  .device-mgr-dropdown-item:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .device-mgr-dropdown-item:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .device-mgr-dropdown-divider {
    height: 1px;
    background: var(--divider-color, #e0e0e0);
    margin: 4px 0;
  }
  .device-mgr-dropdown-item.danger {
    color: var(--error-color, #db4437);
  }
  .device-mgr-dropdown-item.danger:hover {
    background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent);
  }

  /* ── info chips (versions, IP) ────────── */
  .info-chip {
    display: inline-flex;
    align-items: center;
    font-size: 0.82em;
    font-family: var(--font-family-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace);
    background: var(--secondary-background-color, #e0e0e0);
    color: var(--secondary-text-color, #888);
    padding: 1px 7px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .info-chip-ip {
    background: transparent;
    padding: 1px 0;
  }

  /* ── WiFi icon in title row ──────────── */
  .wifi-icon-head {
    --mdc-icon-size: 16px;
    flex-shrink: 0;
    transition: color 0.3s ease;
    cursor: default;
  }
  .wifi-icon-head.wifi-excellent { color: var(--success-color, #43a047); }
  .wifi-icon-head.wifi-good      { color: #7cb342; }
  .wifi-icon-head.wifi-fair      { color: var(--warning-color, #fb8c00); }
  .wifi-icon-head.wifi-weak      { color: var(--error-color, #e53935); }
  .wifi-icon-head.wifi-off       { color: var(--disabled-text-color, #bbb); }

  /* ── RSSI signal bars ──────────────── */
  .rssi-bars {
    display: inline-flex;
    align-items: end;
    gap: 2px;
    height: 14px;
  }
  .rssi-bar {
    width: 4px;
    border-radius: 1px;
    background: var(--disabled-text-color, #d0d0d0);
    transition: background 0.3s ease;
  }
  .rssi-bar:nth-child(1) { height: 4px; }
  .rssi-bar:nth-child(2) { height: 7px; }
  .rssi-bar:nth-child(3) { height: 10px; }
  .rssi-bar:nth-child(4) { height: 14px; }
  .rssi-bar.wifi-excellent { background: var(--success-color, #43a047); }
  .rssi-bar.wifi-good      { background: #7cb342; }
  .rssi-bar.wifi-fair      { background: var(--warning-color, #fb8c00); }
  .rssi-bar.wifi-weak      { background: var(--error-color, #e53935); }
  .section-divider {
    height: 1px;
    background: var(--divider-color, rgba(0,0,0,0.12));
    margin: 12px 0;
  }

  /* ── responsive: tablet (container) ─── */
  @container haui-editor (max-width: 870px) {
    .toolbar-title {
      margin-inline-start: var(--ha-space-2);
    }
  }

  /* ── responsive: narrow container ─── */
  @container haui-editor (max-width: 600px) {
    .toolbar-header {
      padding: 0 4px;
    }
    .content-card {
      margin: var(--ha-space-4);
    }
    .panel-toolbar-row {
      padding: 12px;
      gap: 6px;
    }
  }
  @container haui-editor (max-width: 500px) {
    .pl-key { max-width: 80px; overflow: hidden; text-overflow: ellipsis; }
    .pl-card-type-icon { max-width: 30px; }
  }

  /* ── editor footer (GitHub + Docs links) ── */
  .editor-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
    padding: 16px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
    margin-top: var(--ha-space-6);
  }
  .footer-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--secondary-text-color, #666);
    text-decoration: none;
    font-size: 0.88em;
    transition: color 0.15s;
  }
  .footer-link:hover {
    color: var(--primary-color, #03a9f4);
  }
  .footer-link ha-icon {
    --mdc-icon-size: 16px;
  }
  `;
