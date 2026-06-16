/**
 * NSPanel HAUI - Editor - Color dialog CSS.
 *
 * Reusable styles for the color-override dialog: live preview card
 * (.cp-pv-*), grouped swatch grid (.cp-group / .cp-item), and the footer
 * change counter.  Shared by dialogs/colors.js and available to any other
 * component that renders inline color swatches inside a section-based dialog.
 *
 * This module does NOT include the swatch itself (.cp-sw / .cp-sw.round) —
 * those live in color-picker-styles.js so they can be shared with form-fields.js.
 */
import { css } from '../lit-import.js';

export const colorDialogStyles = css`
  /* ── footer change counter ─────────── */
  .footer-changed {
    font-size: 0.85em;
    color: var(--secondary-text-color, #666);
  }

  /* ── live preview card ─────────────── */
  .cp-pv-card {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--divider-color, #e0e0e0);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  }
  .cp-pv-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    font-weight: 600;
    font-size: 0.95em;
  }
  .cp-pv-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cp-pv-hicons {
    display: inline-flex;
    gap: 6px;
    --mdc-icon-size: 18px;
  }
  .cp-pv-body {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .cp-pv-texts {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    font-size: 0.95em;
    font-weight: 500;
  }
  .cp-pv-comps {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  .cp-pv-btn {
    padding: 5px 14px;
    border-radius: 7px;
    font-size: 0.85em;
    font-weight: 600;
    white-space: nowrap;
  }
  .cp-pv-slider {
    width: 48px;
    height: 6px;
    border-radius: 3px;
    position: relative;
    margin: 0 2px;
    flex-shrink: 0;
  }
  .cp-pv-slider-hdl {
    position: absolute;
    top: -5px;
    right: -2px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid;
    box-sizing: border-box;
  }
  .cp-pv-accent {
    --mdc-icon-size: 22px;
    margin-left: 2px;
  }
  .cp-pv-entities {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    font-size: 0.85em;
  }
  .cp-pv-ent {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .cp-pv-ent i {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }

  /* ── grouped swatch grid ───────────── */
  .cp-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 6px;
  }
  .cp-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 8px 5px 6px;
    border-radius: 8px;
    transition: background 0.12s;
  }
  .cp-item:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .cp-item.is-mod .cp-sw {
    box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
  }
  .cp-name {
    flex: 1;
    min-width: 0;
    font-size: 0.86em;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cp-reset {
    flex-shrink: 0;
    --mdc-icon-button-size: 26px;
    --mdc-icon-size: 15px;
    color: var(--secondary-text-color, #888);
  }
`;
