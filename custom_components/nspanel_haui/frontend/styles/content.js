/**
 * Shared content styles for the editor's forms, dialogues and panel widgets.
 *
 * Extracted from `styles.js` so the dashboard shell and the bare dialog bundle
 * compose the same content rules. Dialog-local layout (Fleet, Device, sidebar)
 * belongs in its own module instead.
 */
import { css } from '../lit-import.js';

export const contentStyles = css`
  /* ── main content area (flex-grows to push footer down) ── */
  .haui-main-content {
    /* The titlebar and the footer stay full-bleed; the column between them stops at the reading
       width and centres. */
    width: 100%;
    max-width: var(--haui-content-max-width);
    margin-inline: auto;
    flex: 1 0 auto;
  }

  /* ── title header ──────────────── */
  .haui-toolbar-header {
    /* The page scrolls as a whole (the footer stays after the screen content), so the
       header pins to the viewport instead of scrolling away. Its z-index sits above
       card content and below the popovers (30) and modal sidebars (40/41). */
    position: sticky;
    top: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    /* The Home Assistant app draws under the status bar: the header takes the
       top inset, so the strip above the title shows the header colour. */
    height: var(--haui-header-height);
    padding: var(--safe-area-inset-top, 0px) 12px 0;
    box-sizing: border-box;
    background: var(--app-header-background-color, var(--sidebar-background-color, #f0f0f0));
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }

  .haui-toolbar-title {
    line-height: var(--haui-line-height);
    flex-grow: 1;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
    min-width: 0;
    font-size: var(--haui-text-headline);
    font-weight: 400;
    margin-inline-start: var(--ha-space-6);
  }

  .haui-toolbar-notifications-button {
    position: relative;
    flex-shrink: 0;
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
  }

  .haui-toolbar-notification-count {
    position: absolute;
    inset-block-start: 0;
    inset-inline-end: 0;
    box-sizing: border-box;
    min-width: 20px;
    height: 20px;
    padding: 0 4px;
    border-radius: var(--haui-radius-control);
    background: var(--error-color);
    color: var(--text-primary-color);
    font-size: var(--haui-text-caption);
    font-weight: 400;
    line-height: 20px;
    text-align: center;
  }

  .haui-toolbar-menu-toggle {
    --mdc-icon-button-size: 40px;
    flex-shrink: 0;
    color: var(--app-header-text-color, var(--sidebar-text-color, #333));
  }
  /* ── content card ────────────────── */

  .haui-content-card {
    margin: var(--ha-space-6);
  }

  .haui-content-card .haui-card-content {
    padding: 0;
  }

  /* ── dialog body (inside ha-dialog) ── */
  .haui-dialog-body {
    position: relative;
  }

/* ── toast / loading actions ─────────────── */
  .haui-toast {
    position: fixed;
    inset: auto auto 24px 50%;
    margin: 0;
    border: 0;
    transform: translateX(-50%);
    padding: 12px 24px;
    border-radius: var(--haui-radius-control);
    color: var(--text-primary-color, #fff);
    font-weight: 500;
    z-index: 10000;
    animation: toast-in 150ms ease;
  }
  .haui-toast.success {
    background: var(--success-color, #43a047);
  }
  .haui-toast.info {
    background: var(--primary-color);
  }
  .haui-toast.error {
    background: var(--error-color, #db4437);
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
  .haui-empty-state-loading { font-size: var(--haui-text-body); }
  .haui-loading-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }

  /* ── update install picker ──────── */

  .haui-update-picker {
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: var(--haui-radius-control);
    padding: 12px;
    margin: 8px 0 16px;
    cursor: default;
  }

  .haui-update-picker .haui-input {
    display: block;
    width: 100%;
  }

  .haui-update-picker .haui-select {
    display: block;
    width: 100%;
  }

  .haui-update-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 8px;
  }

  .haui-update-error {
    color: var(--haui-bad-text);
    font-size: var(--haui-text-caption);
    margin: 4px 0 0;
  }

  /* ── dialog header (title left, close button on the right) ─────── */
  .haui-dialog-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--card-background-color, #fff);
  }
  .haui-dialog-header-title {
    flex: 1;
    min-width: 0;
    font-size: var(--haui-text-headline);
    font-weight: 400;
    color: var(--primary-text-color, #212121);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-dialog-header-close {
    flex-shrink: 0;
    --mdc-icon-button-size: 40px;
    color: var(--secondary-text-color, #666);
    margin-inline-end: -8px;
  }

  /* ── dialog footer (primary actions grouped on the right) ──────── */
  .haui-footer-wrapper {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    width: 100%;
  }
  .haui-footer-toggle-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
  }
  .haui-footer-toggle-wrapper label {
    margin: 0;
    font-weight: 500;
    font-size: var(--haui-text-label);
  }

  /* ── RSSI signal bars ──────────────── */
  .haui-rssi-bars {
    display: inline-flex;
    align-items: end;
    gap: 4px;
    height: 14px;
  }
  .haui-rssi-bar {
    width: 4px;
    border-radius: var(--haui-radius-control);
    background: var(--disabled-text-color, #d0d0d0);
    transition: background 150ms ease;
  }
  /* Fractions of the row's height, so a larger row (a tile's aside) scales the bars with it. */
  .haui-rssi-bar:nth-child(1) { height: 28%; }
  .haui-rssi-bar:nth-child(2) { height: 50%; }
  .haui-rssi-bar:nth-child(3) { height: 72%; }
  .haui-rssi-bar:nth-child(4) { height: 100%; }
  .haui-rssi-bar.haui-wifi-excellent { background: var(--haui-good); }
  .haui-rssi-bar.haui-wifi-good      { background: var(--haui-good); }
  .haui-rssi-bar.haui-wifi-fair      { background: var(--haui-warn); }
  .haui-rssi-bar.haui-wifi-weak      { background: var(--haui-bad); }

  /* ── responsive: tablet (container) ─── */
  @container haui-editor (max-width: 870px) {
    .haui-toolbar-title {
      margin-inline-start: var(--ha-space-2);
    }
  }

  /* ── responsive: narrow container ─── */
  @container haui-editor (max-width: 600px) {
    .haui-toolbar-header {
      padding-inline: 4px;
    }
    .haui-content-card {
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
  .footer-version { color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); }
  .footer-dev-badge {
    padding: 4px 8px;
    border-radius: var(--haui-radius-pill);
    background: var(--warning-color, #ffa600);
    color: var(--primary-text-color, #212121);
    font-size: var(--haui-text-caption);
    font-weight: 400;
  }
  .footer-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--secondary-text-color, #666);
    text-decoration: none;
    font-size: var(--haui-text-caption);
    transition: color 150ms;
  }
  .footer-link:hover { color: var(--primary-color, #03a9f4); }
  .footer-link ha-icon { --mdc-icon-size: 16px; }

  /* ── reorder grips ──────────────── */
  /* A grip turns a touch into a drag (ui/drag-handle.js): the gesture must not
     scroll the page under it, and a long press must not select or call out the icon.
     The rule lives here because every shadow root that renders a grip composes this
     sheet, while Fleet's own rules never reach the dialog that edits a panel. */
  [data-drag-handle] {
    touch-action: none;
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
