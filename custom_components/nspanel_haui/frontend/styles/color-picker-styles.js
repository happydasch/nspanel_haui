/**
 * NSPanel HAUI - Editor - Color picker CSS.
 *
 * Reusable styles for color inputs, swatches, presets, and preview rows.
 * Shared by form-fields.js (inline color pickers) and dialogs/colors.js.
 */
import { css } from '../lit-import.js';

export const colorPickerStyles = css`
  /* ── color picker wrap ───────────── */
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
    width: 0;
    height: 0;
  }

  /* ── palette button ──────────────── */
  .color-picker-btn {
    --mdc-icon-button-size: 36px;
    --mdc-icon-size: 20px;
    flex-shrink: 0;
    color: var(--secondary-text-color, #666);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    transition: border-color 0.15s, background 0.15s;
  }
  .color-picker-btn:hover {
    border-color: var(--primary-color, #03a9f4);
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 6%, transparent);
  }

  /* ── preview row ─────────────────── */
  .color-preview-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 6px;
    padding: 6px 10px;
    border-radius: 8px;
    background: var(--secondary-background-color, #f5f5f5);
  }
  .color-preview-swatch {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    flex-shrink: 0;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.12),
                0 1px 3px rgba(0, 0, 0, 0.15);
  }
  .color-preview-label {
    font-size: 0.85em;
    font-family: var(--code-font-family, monospace);
    color: var(--secondary-text-color, #888);
  }

  /* ── preset swatch row ───────────── */
  .color-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 6px;
    padding: 6px 8px;
    border-radius: 8px;
    background: var(--secondary-background-color, #f5f5f5);
  }
  .color-preset-swatch {
    width: 22px;
    height: 22px;
    border-radius: 4px;
    cursor: pointer;
    flex-shrink: 0;
    border: 2px solid transparent;
    transition: transform 0.1s, border-color 0.1s;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
  }
  .color-preset-swatch:hover {
    transform: scale(1.25);
    border-color: var(--primary-color, #03a9f4);
    z-index: 1;
  }
  .color-preset-label {
    font-size: 0.75em;
    color: var(--secondary-text-color, #999);
    margin: 0;
    width: 100%;
    padding-top: 4px;
  }

  /* ── color dialog swatches ───────── */
  .cp-sw {
    position: relative;
    width: 30px;
    height: 30px;
    border-radius: 7px;
    border: 1px solid rgba(0, 0, 0, 0.18);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
    flex-shrink: 0;
    cursor: pointer;
    overflow: hidden;
  }
  .cp-sw input[type="color"] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    border: none;
    padding: 0;
  }
`;
