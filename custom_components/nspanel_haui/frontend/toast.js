/**
 * NSPanel HAUI - toast helpers.
 * Show and render the editor toast message.
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
  host.updateComplete.then(() => {
    const toast = host.renderRoot.querySelector(".toast[popover]");
    if (toast && !toast.matches(":popover-open")) toast.showPopover();
  });
  return html`<div class="toast ${type}" popover="manual">${message}</div>`;
}
