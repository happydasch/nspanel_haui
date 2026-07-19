/**
 * NSPanel HAUI - Common form field CSS.
 *
 * Reusable styles for form groups, labels, hints, checkboxes, textareas,
 * and field layouts. Extracted from editorStyles in styles.js.
 */
import { css } from '../lit-import.js';

export const formCommonStyles = css`
  /* ── form group ──────────────────── */
  .form-group {
    margin-bottom: 20px;
  }
  .form-group label {
    display: block;
    font-weight: 500;
    font-size: 0.92em;
    margin-bottom: 4px;
  }
  .form-row {
    display: flex;
    gap: 16px;
  }
  .form-row > * {
    flex: 1;
  }

  /* ── inputs ──────────────────────── */
  textarea {
    display: block;
    width: 100%;
  }
  textarea {
    min-height: 96px;
    box-sizing: border-box;
    padding: 8px 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    resize: vertical;
    transition: border-color 0.15s;
  }
  textarea:focus {
    border-color: var(--primary-color, #03a9f4);
    outline: none;
  }

  /* ── native input (replaces ha-input) ── */
  .native-input {
    display: block;
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: 0.92em;
    outline: none;
    transition: border-color 0.15s;
    box-sizing: border-box;
  }
  .native-input:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .native-input::placeholder {
    color: var(--secondary-text-color, #999);
  }
  .w-full {
    width: 100%;
  }

  /* ── native select (replaces ha-select) ── */
  .native-select {
    display: block;
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: 0.92em;
    outline: none;
    cursor: pointer;
    box-sizing: border-box;
    -webkit-appearance: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='%23999'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    padding-right: 32px;
    transition: border-color 0.15s;
  }
  .native-select:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .native-select:hover {
    border-color: var(--primary-color, #03a9f4);
  }
  .native-select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── field hint ──────────────────── */
  .field-hint {
    display: block;
    font-size: 0.85em;
    color: var(--secondary-text-color, #666);
    margin-top: 4px;
    margin-bottom: 0;
    line-height: 1.4;
  }

  /* ── native toggle (replaces ha-switch) ── */
  .native-toggle {
    position: relative;
    width: 36px;
    height: 20px;
    flex-shrink: 0;
    appearance: none;
    -webkit-appearance: none;
    background: var(--secondary-text-color, #999);
    border-radius: 10px;
    cursor: pointer;
    outline: none;
    transition: background 0.2s;
    margin: 0;
  }
  .native-toggle::after {
    content: "";
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.2s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  }
  .native-toggle:checked {
    background: var(--primary-color, #03a9f4);
  }
  .native-toggle:checked::after {
    transform: translateX(16px);
  }
  .native-toggle:focus-visible {
    box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
  }

  /* ── checkbox / switch row ───────── */
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
    cursor: pointer;
  }
  .checkbox-wrap {
    margin-bottom: 12px;
  }
  .checkbox-wrap .checkbox-row {
    margin-bottom: 2px;
  }
  .config-section-body .checkbox-wrap:last-child {
    margin-bottom: 0;
  }

  /* ── config section (details/summary) ── */
  .config-section {
    border-radius: 8px;
    margin-top: 12px;
    background: var(--card-background-color, #fff);
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

  /* ── field row (inline icon + input) ─── */
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
  .field-row ha-icon {
    align-self: center;
  }

  /* ── input with preview inside ────── */
  .input-preview-wrap {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1;
  }
  .input-preview-wrap > .input-preview {
    position: absolute;
    left: 6px;
    z-index: 1;
    pointer-events: auto;
    flex-shrink: 0;
  }
  .input-preview-wrap > .native-input {
    width: 100%;
    padding: 7px 10px 7px 32px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 6px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font: inherit;
    font-size: 0.92em;
    outline: none;
    transition: border-color 0.15s;
    box-sizing: border-box;
  }
  .input-preview-wrap > .native-input:focus {
    border-color: var(--primary-color, #03a9f4);
  }
  .input-preview-wrap > .native-input::placeholder {
    color: var(--secondary-text-color, #999);
  }

  /* ── dialog body ─────────────────── */
  .dialog-body > .form-group:not(:last-child) {
    margin-bottom: 18px;
  }

  /* ── template preview ────────────── */
  .template-preview {
    margin-top: 4px;
    font-size: 0.85em;
    padding: 3px 10px;
    border-left: 3px solid var(--primary-color, #03a9f4);
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 0 6px 6px 0;
  }
  .template-preview > span {
    word-break: break-word;
  }
  .template-preview[hidden] {
    display: none;
  }

  /* ── state-keyed preview ──────────── */
  .state-keyed-preview {
    margin-top: 4px;
    font-size: 0.85em;
    padding: 3px 10px;
    border-left: 3px solid var(--accent-color, #ff9800);
    background: var(--secondary-background-color, #f5f5f5);
    border-radius: 0 6px 6px 0;
    word-break: break-word;
  }
  .state-keyed-preview[hidden] {
    display: none;
  }

  /* ── icon preview row ────────────── */
  .icon-preview {
    width: 16px;
    height: 16px;
    --mdc-icon-size: 16px;
    flex-shrink: 0;
  }
  `;
