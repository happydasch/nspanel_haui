/**
 * NSPanel HAUI - Editor - toast helpers.
 * Extracted from panel-editor.js _showToast and _renderToast methods.
 */

import { html } from './lit-import.js';

export function showToast(host, message, type = "success") {
  host._toast = { message, type };
  setTimeout(() => {
    if (
      host._toast &&
      host._toast.message === message &&
      host._toast.type === type
    ) {
      host._toast = null;
    }
  }, 3000);
}

export function renderToast(host) {
  if (!host._toast) return "";
  const { message, type } = host._toast;
  return html`<div class="toast ${type}">${message}</div>`;
}
