/**
 * Shared content styles for the editor's forms, dialogues and panel widgets.
 *
 * Extracted from `styles.js` so the dashboard shell and the bare dialog bundle
 * compose the same content rules. Dialog-local layout (Fleet, Device, sidebar)
 * belongs in its own module instead.
 */
import { css } from '../lit-import.js';

import { colorDialogStyles } from './color-dialog-styles.js';
import { colorPickerStyles } from './color-picker-styles.js';
import { dropdownStyles } from './dropdown-styles.js';
import { itemListStyles } from './item-list-styles.js';
import { formCommonStyles } from './form-common-styles.js';

export const contentStyles = css`
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

  .notifications-button {
    position: relative;
    flex-shrink: 0;
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
  }

  .notification-count {
    position: absolute;
    inset-block-start: 0;
    inset-inline-end: 0;
    min-width: 16px;
    padding: 1px 4px;
    border-radius: 10px;
    background: var(--error-color);
    color: var(--text-primary-color);
    font-size: 10px;
    line-height: 14px;
    text-align: center;
  }

  .menu-toggle-btn {
    --mdc-icon-button-size: 40px;
    flex-shrink: 0;
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
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

/* ── toast / loading ─────────────── */
  .toast {
    position: fixed;
    inset: auto auto 24px 50%;
    margin: 0;
    border: 0;
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
  .toast.info {
    background: var(--primary-color);
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

  /* ── update install picker ──────── */

  .device-update-picker {
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
  }

  .device-update-picker .native-input {
    display: block;
    width: 100%;
  }

  .device-update-picker {
    margin: 8px 0 0;
    cursor: default;
  }

  .device-update-picker .native-select {
    display: block;
    width: 100%;
  }

  .device-update-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 8px;
  }

  .device-update-error {
    color: var(--error-color, #e53935);
    font-size: 0.85em;
    margin: 4px 0 0;
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
  }

  /* ── editor footer (version + GitHub + Docs links) ── */
  .editor-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 24px;
    padding: 16px;
    border-top: 1px solid var(--divider-color, #e0e0e0);
    margin-top: var(--ha-space-6);
  }
  .footer-version-group { display: inline-flex; align-items: center; gap: 8px; }
  .footer-version { color: var(--secondary-text-color, #666); font-size: 0.88em; }
  .footer-dev-badge {
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--warning-color, #ffc107);
    color: var(--primary-text-color, #212121);
    font-size: 0.72em;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
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
  .footer-link:hover { color: var(--primary-color, #03a9f4); }
  .footer-link ha-icon { --mdc-icon-size: 16px; }
  `;
