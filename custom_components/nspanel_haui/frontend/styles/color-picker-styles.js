/**
 * NSPanel HAUI - Color picker CSS.
 *
 * Reusable styles for color inputs, swatches, presets, and preview rows.
 * Shared by form-fields.js (inline color pickers) and dialogs/theme.js.
 */
import { css } from '../lit-import.js';

export const colorPickerStyles = css`
  /* ── color picker wrap ───────────── */
  .haui-color-picker-wrap {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .haui-color-picker-wrap > .haui-input {
    flex: 1;
  }
  .haui-color-input-hidden {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  /* ── palette button ──────────────── */
  .haui-color-picker-btn {
    --mdc-icon-button-size: 36px;
    --mdc-icon-size: 20px;
    flex-shrink: 0;
    color: var(--secondary-text-color, #666);
    transition: color 150ms;
  }
  .haui-color-picker-btn:hover {
    color: var(--primary-color, #03a9f4);
  }

  /* ── preview row ─────────────────── */
  .haui-color-preview-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    padding: 4px 8px;
    border-radius: var(--haui-radius-control);
    background: var(--secondary-background-color, #f5f5f5);
  }
  .haui-color-preview-swatch {
    width: 28px;
    height: 28px;
    background-color: var(--vp-color-preview);
    border-radius: var(--haui-radius-control);
    flex-shrink: 0;
    box-shadow: var(--haui-shadow-card);
  }
  .haui-color-preview-label {
    font-size: var(--haui-text-caption);
    font-family: var(--haui-mono);
    color: var(--secondary-text-color, #666);
  }

  /* ── preset swatch row ───────────── */
  .haui-color-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
    padding: 4px 8px;
    border-radius: var(--haui-radius-control);
    background: var(--secondary-background-color, #f5f5f5);
  }
  .haui-color-preset-swatch {
    background: var(--haui-color-preset);
    width: 22px;
    height: 22px;
    border-radius: var(--haui-radius-control);
    cursor: pointer;
    flex-shrink: 0;
    border: 2px solid transparent;
    transition: transform 120ms, border-color 120ms;
    box-shadow: var(--haui-shadow-card);
  }
  .haui-color-preset-swatch:hover {
    transform: scale(1.25);
    border-color: var(--primary-color, #03a9f4);
    z-index: 1;
  }
  .haui-color-presets.is-recent > .haui-color-preset-label { margin-bottom: 4px; }
  .haui-color-preset-label {
    font-size: var(--haui-text-caption);
    color: var(--secondary-text-color, #666);
    margin: 0;
    width: 100%;
    padding-top: 4px;
  }

  .haui-icon-preview-static { pointer-events: none; }

  /* ── color dialog swatches ───────── */
  .haui-color-swatch {
    position: relative;
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    cursor: pointer;
    overflow: hidden;
    border: 2px solid var(--card-background-color, #fff);
    border-radius: var(--haui-radius-control);
    box-shadow: 0 0 0 1px var(--divider-color, #e0e0e0), var(--haui-shadow-card);
    transition: transform 120ms ease, box-shadow 120ms ease;
  }
  .haui-color-editor-swatch {
    pointer-events: auto;
    background-color: var(--haui-color-swatch);
    border-radius: var(--haui-radius-control);
    border: 1px solid var(--divider-color, #e0e0e0);
  }
  .haui-color-swatch:hover {
    transform: translateY(-1px);
  }
  .haui-color-swatch:focus-within {
    box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
  }
  .haui-color-swatch input[type="color"] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    border: none;
    padding: 0;
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
