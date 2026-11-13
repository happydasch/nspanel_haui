/**
 * NSPanel HAUI - Theme color editor CSS.
 *
 * Reusable styles for the theme sidebar: live preview card
 * (.haui-theme-preview-*), grouped swatch grid (.haui-theme-color-group / .haui-color-item), the name editor and
 * the footer change counter.  Shared by dialogs/theme.js and available to any
 * other component that renders inline color swatches inside a section-based
 * dialog.
 *
 * This module does NOT include the swatch itself (.haui-color-swatch / .haui-color-swatch.round) —
 * those live in haui-color-picker-styles.js so they can be shared with form-fields.js.
 */
import { css } from '../lit-import.js';

export const colorDialogStyles = css`
  /* ── footer change counter ─────────── */
  .haui-footer-changed {
    font-size: var(--haui-text-caption);
    color: var(--secondary-text-color, #666);
  }

  /* ── live preview card ─────────────── */
  .haui-theme-preview-card {
    background: var(--vp-theme-background);
    border-radius: var(--haui-radius-control);
    overflow: hidden;
    border: 1px solid var(--divider-color, #e0e0e0);
    box-shadow: var(--haui-shadow-card);
  }
  .haui-theme-preview-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--vp-theme-header-background);
    color: var(--vp-theme-header-text);
    font-weight: 600;
    font-size: var(--haui-text-label);
  }
  .haui-theme-preview-hicons ha-icon { color: var(--vp-theme-icon-color); }
  .haui-theme-preview-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-theme-preview-hicons {
    display: inline-flex;
    gap: 4px;
    --mdc-icon-size: 18px;
  }
  .haui-theme-preview-body {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .haui-theme-preview-texts {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: var(--haui-text-label);
    font-weight: 500;
  }
  .haui-theme-preview-texts > span { color: var(--vp-theme-text-color); }
  .haui-theme-preview-comps {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  .haui-theme-preview-btn {
    padding: 4px 12px;
    border-radius: var(--haui-radius-control);
    background: var(--vp-theme-component-background);
    color: var(--vp-theme-component-text);
    font-size: var(--haui-text-caption);
    font-weight: 600;
    white-space: nowrap;
  }
  .haui-theme-preview-slider {
    width: 48px;
    height: 6px;
    border-radius: var(--haui-radius-control);
    position: relative;
    margin: 0 4px;
    flex-shrink: 0;
    background: var(--vp-theme-slider-background);
  }
  .haui-theme-preview-slider-hdl {
    position: absolute;
    top: -5px;
    right: -2px;
    width: 14px;
    height: 14px;
    border-radius: var(--haui-radius-round);
    border: 2px solid var(--vp-theme-slider-handle);
    background: var(--vp-theme-slider-handle);
    box-sizing: border-box;
  }
  .haui-theme-preview-accent {
    --mdc-icon-size: 22px;
    margin-left: 4px;
    color: var(--vp-theme-accent);
  }
  .haui-theme-preview-entities {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: var(--haui-text-caption);
    color: var(--vp-theme-entity-text);
  }
  .haui-theme-preview-ent {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .haui-theme-preview-ent i {
    width: 11px;
    height: 11px;
    border-radius: var(--haui-radius-round);
    display: inline-block;
    flex-shrink: 0;
    background: var(--vp-theme-entity-color);
  }

  /* ── grouped swatch grid ───────────── */
  .haui-color-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 4px;
  }
  .haui-color-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px 4px 4px;
    border-radius: var(--haui-radius-control);
    transition: background 120ms;
  }
  .haui-color-item:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .haui-color-item .haui-color-swatch { background-color: var(--vp-color-swatch); }
  .haui-color-item.is-mod .haui-color-swatch {
    box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
  }
  .haui-color-name {
    flex: 1;
    min-width: 0;
    font-size: var(--haui-text-caption);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-color-reset {
    flex-shrink: 0;
    --mdc-icon-button-size: 26px;
    --mdc-icon-size: 15px;
    color: var(--secondary-text-color, #666);
  }

  .haui-theme-name {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0;
  }

  .haui-theme-name input {
    min-width: 180px;
    flex: 1;
    padding: 8px;
  }

  .haui-theme-error {
    color: var(--error-color, #db4437);
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
