/**
 * NSPanel HAUI - Common form field CSS.
 *
 * Reusable styles for form groups, labels, hints, checkboxes, textareas,
 * and field layouts. Extracted from editorStyles in styles.js.
 */
import { css } from '../lit-import.js';

export const formCommonStyles = css`
  /* ── form group ──────────────────── */
  .haui-field {
    margin-bottom: 20px;
  }
  .haui-field label {
    display: block;
    font-weight: 500;
    font-size: var(--haui-text-label);
    margin-bottom: 4px;
  }

  /* ── inputs ──────────────────────── */
  textarea {
    display: block;
    width: 100%;
  }
  textarea {
    min-height: 96px;
    box-sizing: border-box;
    padding: 8px 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    resize: vertical;
    transition: border-color 150ms;
  }
  textarea:focus {
    border-color: var(--primary-color, #03a9f4);
    outline: none;
  }

  /* ── native input (replaces ha-input) ── */
  .haui-input {
    display: block;
    width: 100%;
    padding: 8px 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: var(--haui-text-label);
    outline: none;
    transition: border-color 150ms;
    box-sizing: border-box;
  }
  .haui-input:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .haui-input[aria-invalid="true"] {
    border-color: var(--error-color, #db4437);
  }
  .haui-input::placeholder {
    color: var(--secondary-text-color, #666);
  }
  /* ── native select (replaces ha-select) ── */
  .haui-select {
    display: block;
    width: 100%;
    padding: 8px 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: var(--haui-text-label);
    outline: none;
    cursor: pointer;
    box-sizing: border-box;
    -webkit-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='%23999'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    padding-right: 32px;
    transition: border-color 150ms;
  }
  .haui-select:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .haui-select:hover {
    border-color: var(--primary-color, #03a9f4);
  }
  .haui-select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── field hint ──────────────────── */
  .haui-field-hint {
    display: block;
    font-size: var(--haui-text-caption);
    color: var(--secondary-text-color, #666);
    margin-top: 4px;
    margin-bottom: 0;
    line-height: 1.4;
  }

  /* ── native toggle (replaces ha-switch) ── */
  .haui-switch {
    position: relative;
    width: 36px;
    height: 20px;
    flex-shrink: 0;
    appearance: none;
    -webkit-appearance: none;
    background: var(--secondary-text-color, #666);
    border-radius: var(--haui-radius-pill);
    cursor: pointer;
    outline: none;
    transition: background 150ms;
    margin: 0;
  }
  .haui-switch::after {
    content: "";
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: var(--haui-radius-round);
    background: #fff;
    transition: transform 150ms;
    box-shadow: var(--haui-shadow-card);
  }
  .haui-switch:checked {
    background: var(--primary-color, #03a9f4);
  }
  .haui-switch:checked::after {
    transform: translateX(16px);
  }

  /* ── checkbox / switch row ───────── */
  .haui-checkbox-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .haui-checkbox-row label {
    margin-bottom: 0;
    font-weight: 500;
    font-size: var(--haui-text-label);
    cursor: pointer;
  }
  .haui-checkbox-wrap {
    margin-bottom: 12px;
  }
  .haui-checkbox-wrap .haui-checkbox-row {
    margin-bottom: 4px;
  }
  .haui-config-section-body .haui-checkbox-wrap:last-child {
    margin-bottom: 0;
  }

  /* ── config section (details/summary) ── */
  .haui-config-section {
    border-radius: var(--haui-radius-control);
    margin-top: 12px;
    background: var(--card-background-color, #fff);
  }
  .haui-config-section > summary {
    list-style: none;
    cursor: pointer;
    padding: 12px 16px 12px 8px;
    font-weight: 500;
    font-size: var(--haui-text-title);
    color: var(--primary-text-color, #212121);
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
    border-radius: var(--haui-radius-control);
  }
  .haui-config-section > summary::-webkit-details-marker { display: none; }
  .haui-config-section > summary::after {
    content: "";
    margin-left: auto;
    width: 5px;
    height: 5px;
    border-right: 2px solid var(--secondary-text-color, #666);
    border-bottom: 2px solid var(--secondary-text-color, #666);
    transform: rotate(-45deg);
    transition: transform 150ms;
  }
  .haui-config-section[open] > summary::after {
    transform: rotate(45deg);
  }
  .haui-config-section[open] > summary {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .haui-config-section > summary:hover {
    background: var(--secondary-background-color, #f5f5f5);
  }
  .haui-config-section-body {
    padding: 12px;
  }
  .haui-config-section-intro {
    margin: 0 0 16px;
    font-size: var(--haui-text-title);
    color: var(--secondary-text-color, #666);
  }
  .haui-config-section-body .haui-field:last-child,
  .haui-config-section-body .haui-checkbox-row:last-child {
    margin-bottom: 0;
  }

  /* ── field row (inline icon + input) ─── */
  .haui-field-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .haui-field-row ha-icon {
    align-self: center;
  }

  /* ── input with preview inside ────── */
  .haui-input-preview-wrap {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1;
  }
  .haui-input-preview-wrap > .haui-input-preview {
    position: absolute;
    left: 6px;
    z-index: 1;
    pointer-events: auto;
    flex-shrink: 0;
  }
  .haui-input-preview-wrap > .haui-input {
    width: 100%;
    padding: 8px 8px 8px 32px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: var(--haui-text-label);
    outline: none;
    transition: border-color 150ms;
    box-sizing: border-box;
  }
  .haui-input-preview-wrap > .haui-input:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .haui-input-preview-wrap > .haui-input::placeholder {
    color: var(--secondary-text-color, #666);
  }

  /* ── dialog body ─────────────────── */
  .haui-dialog-body > .haui-field:not(:last-child) {
    margin-bottom: 16px;
  }

  /* ── template preview ────────────── */
  .haui-template-preview {
    margin-top: 4px;
    font-size: var(--haui-text-caption);
    padding: 4px 8px;
    border-left: 3px solid var(--primary-color, #03a9f4);
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 0 var(--haui-radius-control) var(--haui-radius-control) 0;
  }
  .haui-template-preview > span {
    word-break: break-word;
  }
  .haui-template-preview[hidden] {
    display: none;
  }

  /* ── state-keyed preview ──────────── */
  .haui-state-keyed-preview {
    margin-top: 4px;
    font-size: var(--haui-text-caption);
    padding: 4px 8px;
    border-left: 3px solid var(--accent-color, #ff9800);
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 0 var(--haui-radius-control) var(--haui-radius-control) 0;
    word-break: break-word;
  }
  .haui-state-keyed-preview[hidden] {
    display: none;
  }

  /* ── icon preview row ────────────── */
  .haui-icon-preview {
    width: 16px;
    height: 16px;
    --mdc-icon-size: 16px;
    flex-shrink: 0;
  }

  /* ── add row button ──────────────────
     The one "+ Add …" row of every list editor (items, schedule entries,
     gestures): dashed until hovered, then a solid primary outline. */
  .haui-item-add-button {
    background: transparent;
    color: var(--primary-color, #03a9f4);
    border: 1px dashed var(--divider-color, #e0e0e0);
    padding: 8px 16px;
    border-radius: var(--haui-radius-control);
    cursor: pointer;
    font-size: var(--haui-text-label);
    font-weight: 500;
    width: 100%;
    margin-top: 8px;
    transition: background 150ms, border-color 150ms;
    font-family: inherit;
  }
  .haui-item-add-button:hover:not(:disabled) {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 8%, transparent);
    border-color: var(--primary-color, #03a9f4);
    border-style: solid;
  }
  .haui-item-add-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
