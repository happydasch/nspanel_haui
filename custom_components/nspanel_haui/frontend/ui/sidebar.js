// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { readStorage, writeStorage } from '../dom-helpers.js';
import { iconButton } from './button.js';
import { trapTab } from './focus-trap.js';

// Every sidebar shares the width the user dragged it to, kept per browser.
const WIDTH_KEY = 'haui_sidebarWidth';
const DEFAULT_WIDTH = 380;
const MIN_WIDTH = 320;
const KEY_STEP = 24;
let sidebarWidth = Number(readStorage(WIDTH_KEY, '')) || DEFAULT_WIDTH;

/** The widest a sidebar may grow: a strip of the page stays visible to click away. */
function maxWidth() {
  return Math.max(MIN_WIDTH, (globalThis.innerWidth || DEFAULT_WIDTH * 3) - 120);
}

/** @param {HTMLElement} handle @param {number} width @param {boolean} [save] */
function applyWidth(handle, width, save = false) {
  sidebarWidth = Math.round(Math.min(maxWidth(), Math.max(MIN_WIDTH, width)));
  /** @type {HTMLElement|null} */ (handle.closest('.haui-modal-sidebar'))
    ?.style.setProperty('--haui-sidebar-width', `${sidebarWidth}px`);
  handle.setAttribute('aria-valuenow', String(sidebarWidth));
  if (save) writeStorage(WIDTH_KEY, String(sidebarWidth));
}

/** Drag the sidebar's inner edge; the sidebar keeps its right edge. @param {PointerEvent} event */
function startResize(event) {
  if (event.button !== 0) return;
  const handle = /** @type {HTMLElement} */ (event.currentTarget);
  const sidebar = handle.closest('.haui-modal-sidebar');
  if (!sidebar) return;
  event.preventDefault();
  const right = sidebar.getBoundingClientRect().right;
  handle.setPointerCapture?.(event.pointerId);
  sidebar.classList.add('is-resizing');
  const move = (/** @type {PointerEvent} */ moved) => applyWidth(handle, right - moved.clientX);
  const end = () => {
    handle.removeEventListener('pointermove', move);
    handle.removeEventListener('pointerup', end);
    handle.removeEventListener('pointercancel', end);
    sidebar.classList.remove('is-resizing');
    applyWidth(handle, sidebarWidth, true);
  };
  handle.addEventListener('pointermove', move);
  handle.addEventListener('pointerup', end);
  handle.addEventListener('pointercancel', end);
}

/** Arrow keys move the edge as a drag would; Home and End go to the limits. @param {KeyboardEvent} event */
function keyResize(event) {
  const handle = /** @type {HTMLElement} */ (event.currentTarget);
  const widths = {
    ArrowLeft: sidebarWidth + KEY_STEP,
    ArrowRight: sidebarWidth - KEY_STEP,
    Home: MIN_WIDTH,
    End: maxWidth(),
  };
  if (!(event.key in widths)) return;
  event.preventDefault();
  applyWidth(handle, widths[event.key], true);
}

/** The sidebar's inner edge, a separator that resizes it; a double click restores the default. */
function resizeHandle() {
  return html`<div class="haui-sidebar-resize" role="separator" aria-orientation="vertical"
    aria-label=${t('Resize sidebar')} title=${t('Drag to resize, double-click to reset')} tabindex="0"
    aria-valuemin=${MIN_WIDTH} aria-valuemax=${maxWidth()} aria-valuenow=${sidebarWidth}
    @pointerdown=${startResize} @keydown=${keyResize}
    @dblclick=${(event) => applyWidth(event.currentTarget, DEFAULT_WIDTH, true)}></div>`;
}

/**
 * The Device side stack's modal frame: a labelled strip with the close control
 * above a body that fills the panel. The body is the migrated form element,
 * which owns its own scrolling content and sticky footer.
 *
 * @param {{ label: string, body: unknown, onClose: () => void, closeLabel?: string }} options
 */
export function sidebarFrame({ label, body, onClose, closeLabel = t('Close sidebar') }) {
  return html`<div class="haui-sidebar" role="group" aria-label=${label}>
    <header class="haui-sidebar-strip">
      <span class="haui-sidebar-title">${label}</span>
      ${iconButton({ label: closeLabel, iconName: 'close', onClick: onClose, className: 'haui-sidebar-close' })}
    </header>
    <div class="haui-sidebar-body">${body}</div>
  </div>`;
}

/**
 * Keep a wheel turn inside the modal sidebar: unless a scrollable part of it is
 * under the pointer, the turn would scroll the page behind it.
 *
 * @param {WheelEvent} event - a wheel event on the sidebar (its `currentTarget`)
 */
export function keepWheelInside(event) {
  for (const node of event.composedPath()) {
    if (node === event.currentTarget) break;
    const element = /** @type {any} */ (node);
    if (!(element.scrollHeight > element.clientHeight + 1)) continue;
    const overflow = globalThis.getComputedStyle?.(element).overflowY;
    if (overflow === 'auto' || overflow === 'scroll') return;
  }
  event.preventDefault();
}

/**
 * The modal sidebar over a screen: a scrim that closes it and the framed panel,
 * which keeps Tab and the wheel inside. The Device screen and Fleet (Logs) share it.
 *
 * @param {{ label: string, body: unknown, onClose: () => void, ariaLabel?: string }} options
 */
export function modalSidebar({ label, body, onClose, ariaLabel = label }) {
  return html`<div class="haui-sidebar-scrim" @click=${onClose}
      @wheel=${(event) => event.preventDefault()}></div>
    <aside class="haui-modal-sidebar" aria-label=${ariaLabel}
      role="dialog" aria-modal="true" tabindex="-1"
      style=${`--haui-sidebar-width: ${sidebarWidth}px`}
      @wheel=${keepWheelInside}
      @keydown=${(event) => trapTab(event, event.currentTarget)}>
      ${resizeHandle()}
      ${sidebarFrame({ label, body, onClose })}
    </aside>`;
}
