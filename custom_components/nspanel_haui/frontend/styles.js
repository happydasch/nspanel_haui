/**
 * NSPanel HAUI - Editor - styles.
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


/**
 * Base HA-style typography and layout utilities.
 * Subset of HA's `haStyle` — only what this editor needs.
 */
export const haStyle = css`
  :host {
    display: block;
    container-type: inline-size;
    container-name: haui-editor;
  }
  .container {
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
  .container {
    padding-bottom: var(--ha-space-6);
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

  /* ── form ────────────────────────── */
  ha-input,
  textarea {
    display: block;
    width: 100%;
  }
  textarea {
    min-height: 96px;
    box-sizing: border-box;
    padding: 8px 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 4px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    resize: vertical;
  }
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
    border-radius: 6px;
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
  /* number-type ha-input renders ~8px taller bottom-padding than text-type
     in mwc-textfield; crop with negative margin so layout matches other inputs */
  ha-input {
    margin-bottom: -8px;
  }

  .form-group {
    margin-bottom: 20px;
  }
  .form-group label {
    display: block;
    font-weight: 500;
    font-size: 0.92em;
    margin-bottom: 4px;
  }
  .entity-picker-wrap ha-input {
    width: 100%;
  }
  .form-row {
    display: flex;
    gap: 16px;
  }
  .form-row > * {
    flex: 1;
  }

  /* ── unified config section (used inside dialogs) ──────────────────── */
  .config-section {
    border-radius: 8px;
    margin-top: 12px;
    background: var(--card-background-color, #fff);
    overflow: hidden;
  }
  .config-section > summary {
    list-style: none;
    cursor: pointer;
    padding: 12px 16px 12px 8px;
    font-weight: 500;
    font-size: 1.1em;
    color: var(--primary-text-color, #212121);
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
    border-radius: 8px;
  }
  .config-section > summary::-webkit-details-marker { display: none; }
  .config-section > summary::after {
    content: "";
    margin-left: auto;
    width: 5px;
    height: 5px;
    border-right: 2px solid var(--secondary-text-color, #666);
    border-bottom: 2px solid var(--secondary-text-color, #666);
    transform: rotate(-45deg);
    transition: transform 0.15s;
  }
  .config-section[open] > summary::after {
    transform: rotate(45deg);
  }
  .config-section[open] > summary {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .config-section > summary:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .config-section-body {
    padding: 12px;
  }
  .config-section-intro {
    margin: 0 0 16px;
    font-size: 1.05em;
    color: var(--secondary-text-color, #666);
  }
  .config-section-body .form-group:last-child,
  .config-section-body .checkbox-row:last-child {
    margin-bottom: 0;
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .checkbox-row label {
    margin-bottom: 0;
    font-weight: 500;
    font-size: 0.92em;
  }
  /* Wrapper for toggles with help text below — used in device config dialog */
  .checkbox-wrap {
    margin-bottom: 12px;
  }
  .checkbox-wrap .checkbox-row {
    margin-bottom: 2px;
  }
  .config-section-body .checkbox-wrap:last-child {
    margin-bottom: 0;
  }
  .field-hint {
    display: block;
    font-size: 0.85em;
    color: var(--secondary-text-color, #666);
    margin-top: 4px;
    margin-bottom: 0;
  }
  .field-full {
    display: block;
    width: 100%;
  }
  .field-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .field-row > .field-row-grow {
    flex: 1;
  }

  /* ── color picker ───────────────────── */
  .color-picker-wrap {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .color-picker-wrap > ha-input {
    flex: 1;
  }
  .color-input-hidden {
    position: absolute;
    opacity: 0;
    /* Removed pointer-events: none — Safari blocks .click() on pointer-events:none elements */
    width: 0;
    height: 0;
  }
  .color-preview-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
  }
  .color-preview-swatch {
    width: 24px;
    height: 24px;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    flex-shrink: 0;
  }
  .color-preview-label {
    font-size: 0.85em;
    color: var(--secondary-text-color, #999);
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

  /* ── template preview ──────────────── */
  .template-preview {
    margin-top: 4px;
    font-size: 0.85em;
    padding: 2px 8px;
    border-left: 3px solid var(--primary-color, #03a9f4);
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 0 4px 4px 0;
  }
  .template-preview > span { word-break: break-word; }
  .template-preview[hidden] { display: none; }

  /* ── icon picker ───────────────────── */
  .icon-picker-wrap {
    position: relative;
    margin-bottom: 16px;
  }
  .icon-picker-input {
    width: 100%;
  }
  .icon-preview-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
  }
  .icon-preview {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }
  .icon-preview-label {
    font-size: 0.85em;
    color: var(--secondary-text-color, #999);
  }
  .icon-dropdown {
    position: absolute;
    z-index: 10;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid var(--divider-color, #ddd);
    border-radius: 4px;
    background: var(--card-background-color, #fff);
    margin-top: 2px;
  }
  .icon-dropdown[hidden] { display: none; }
  .icon-dropdown-item {
    cursor: pointer;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }
  .icon-dropdown-item span {
    font-size: 0.85em;
  }

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
  .item-list-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    transition: background 0.15s, border-color 0.15s;
  }
  .item-list-row:hover {
    border-color: var(--primary-color, #03a9f4);
  }
  .item-row-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background: var(--secondary-background-color, #f0f0f0);
    color: var(--primary-color, #03a9f4);
    --mdc-icon-size: 20px;
    position: relative;
  }
  .item-row-color-dot {
    position: absolute;
    bottom: -2px;
    right: -2px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid var(--card-background-color, #fff);
    box-shadow: 0 1px 2px rgba(0,0,0,0.25);
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
    padding: 2px 6px;
    border-radius: 10px;
    background: var(--secondary-background-color, #eee);
    color: var(--secondary-text-color, #666);
  }
  .item-row-secondary {
    font-size: 0.8em;
    color: var(--secondary-text-color, #666);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--code-font-family, monospace);
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
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9em;
    font-weight: 500;
    width: 100%;
    margin-top: 8px;
    transition: background 0.15s, border-color 0.15s;
  }
  .add-item-btn:hover {
    background: rgba(3, 169, 244, 0.08);
    border-color: var(--primary-color, #03a9f4);
    border-style: solid;
  }

  /* ── item advanced section ───────── */
  .item-advanced-toggle {
    cursor: pointer;
    font-size: 0.85em;
    color: var(--primary-color, #03a9f4);
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 8px;
    user-select: none;
  }
  .item-advanced-toggle .toggle-arrow {
    transition: transform 0.2s;
    --mdc-icon-size: 18px;
  }
  .item-advanced-toggle .toggle-arrow.open {
    transform: rotate(90deg);
  }
  .item-advanced-section {
    display: none;
    padding-left: 12px;
    border-left: 2px solid var(--divider-color, #e0e0e0);
    margin-top: 8px;
  }
  .item-advanced-section.open {
    display: block;
  }

  /* ── item inline edit ────────────── */
  .item-edit-inline {
    padding: 12px;
    border: 1px solid var(--primary-color, #03a9f4);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    margin: 8px 0;
  }
  .item-edit-inline .item-edit-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
  }

  /* ── entity picker dropdown ────────── */
  .entity-dropdown-item:hover,
  .entity-dropdown-item.active {
    background: var(--primary-color, #03a9f4);
    color: #fff;
  }
  .entity-dropdown-item.active .entity-friendly-name,
  .entity-dropdown-item.active .entity-id {
    color: #fff;
  }
  .entity-dropdown-item .entity-id {
    font-size: 0.75em;
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
    z-index: 1000;
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

  /* ── active listeners table ──────── */
  .active-listeners-section {
    margin-top: 20px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
    padding-top: 12px;
  }

  .active-listeners-section h4 {
    margin: 0 0 8px;
    font-size: 0.85em;
    font-weight: 500;
    color: var(--primary-text-color, #333);
  }

  .listeners-table {
    display: table;
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8em;
  }

  .listeners-header,
  .listeners-row {
    display: table-row;
  }

  .listeners-col {
    display: table-cell;
    padding: 4px 8px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    vertical-align: top;
  }

  .listeners-header .listeners-col {
    font-weight: 600;
    color: var(--secondary-text-color, #666);
    border-bottom: 2px solid var(--divider-color, #e0e0e0);
    white-space: nowrap;
  }

  .listeners-col-entity {
    width: 40%;
    max-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .listeners-col-attr {
    width: 25%;
  }

  .listeners-col-cb {
    width: 35%;
    font-family: monospace;
    font-size: 0.9em;
  }

  /* ── active timers table ─────────── */

  .active-timers-section {
    margin-top: 16px;
    padding-top: 12px;
  }

  .active-timers-section h4 {
    margin: 0 0 8px;
    font-size: 0.85em;
    font-weight: 500;
    color: var(--primary-text-color, #333);
  }

  .timers-table {
    display: table;
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8em;
  }

  .timers-header,
  .timers-row {
    display: table-row;
  }

  .timers-col {
    display: table-cell;
    padding: 4px 8px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    vertical-align: top;
  }

  .timers-header .timers-col {
    font-weight: 600;
    color: var(--secondary-text-color, #666);
    border-bottom: 2px solid var(--divider-color, #e0e0e0);
    white-space: nowrap;
  }

  .timers-col-cb {
    width: 40%;
    font-family: monospace;
    font-size: 0.9em;
  }

  .timers-col-type {
    width: 25%;
  }

  .timers-col-int {
    width: 35%;
  }

  /* ── logs dialog content ─────────── */

  .logs-content {
    max-height: 400px;
    overflow: auto;
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

  .device-mgr-add-form ha-input {
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
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .device-mgr-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 12px;
    border-radius: 8px;
    margin-bottom: 6px;
    transition: background 0.1s;
    cursor: pointer;
  }

  .device-mgr-row:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }

  .device-mgr-row.selected {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--primary-color, #03a9f4) 20%, transparent);
  }

  .device-mgr-row-status {
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .device-mgr-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .device-mgr-dot.dot-connected {
    background: var(--success-color, #43a047);
  }

  .device-mgr-dot.dot-disconnected {
    background: var(--disabled-text-color, #9e9e9e);
  }

  .device-mgr-row-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .device-mgr-name {
    font-weight: 500;
    font-size: 0.95em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .device-mgr-meta {
    font-size: 0.8em;
    color: var(--secondary-text-color, #666);
  }

  .device-mgr-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 0.82em;
    font-family: var(--font-family-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace);
    color: var(--primary-text-color, #212121);
    background: var(--secondary-background-color, #e0e0e0);
  }

  .device-mgr-row-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .device-mgr-remove-btn ha-icon {
    color: var(--error-color, #e53935);
  }

  .discovered-row {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 4%, transparent);
    border-radius: 8px;
  }
  .discovered-row:hover {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent);
  }

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
  `;
