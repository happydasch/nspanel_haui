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
  .w-full {
    width: 100%;
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

  /* ── icon preview row ────────────── */
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
`;
