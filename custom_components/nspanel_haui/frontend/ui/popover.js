// @ts-check
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

const VIEWPORT_MARGIN = 12;
const ANCHOR_GAP = 6;

/**
 * The key a trigger and its popover share through `data-overlay-anchor` /
 * `data-popover-anchor`.
 *
 * @param {string} kind
 * @param {string|null} [subject]
 */
export function overlayAnchor(kind, subject = null) {
  return subject ? `${kind}:${subject}` : kind;
}

/** @param {string} anchorKey */
function anchorSelector(anchorKey) {
  return `[data-overlay-anchor="${String(anchorKey).replace(/"/g, '\\"')}"]`;
}

/**
 * Find the trigger that owns an anchored popover.
 *
 * @param {ParentNode|null|undefined} root
 * @param {string|null} anchorKey
 * @returns {any}
 */
export function anchorElement(root, anchorKey) {
  if (!anchorKey || !root?.querySelector) return null;
  return root.querySelector(anchorSelector(anchorKey));
}

/**
 * The element an anchored popover renders into, for outside-click checks.
 *
 * @param {ParentNode|null|undefined} root
 * @returns {any}
 */
export function popoverSurface(root) {
  if (!root?.querySelector) return null;
  return root.querySelector('[data-popover-anchor]');
}

/**
 * Return focus to the trigger of a closed popover.
 *
 * @param {ParentNode|null|undefined} root
 * @param {string|null} anchorKey
 */
export function focusAnchor(root, anchorKey) {
  const anchor = anchorElement(root, anchorKey);
  if (anchor?.focus) anchor.focus();
}

/**
 * A menu row; the accessible name always comes from the label.
 * @param {{ label: string, iconName?: string, onSelect?: (() => void)|null, danger?: boolean, disabled?: boolean, checked?: boolean }} options
 */
export function menuItem({ label, iconName, onSelect, danger = false, disabled = false, checked }) {
  return html`<button type="button" class=${'haui-menu-item' + (danger ? ' danger' : '')}
    role=${checked === undefined ? 'menuitem' : 'menuitemcheckbox'} ?disabled=${disabled}
    aria-checked=${checked === undefined ? nothing : String(checked)}
    @click=${onSelect}>${iconName ? icon(iconName) : nothing}<span>${label}</span></button>`;
}

/**
 * An expandable menu entry with its own nested menu.
 * @param {{ id: string, label: string, iconName?: string, items: unknown, open: boolean, onToggle: () => void }} options
 */
export function menuSubmenu({ id, label, iconName, items, open, onToggle }) {
  return html`<div class="haui-menu-submenu" role="none">
    <button type="button" class="haui-menu-item haui-menu-submenu-trigger" role="menuitem"
      aria-haspopup="menu" aria-expanded=${String(open)} aria-controls=${id}
      @click=${onToggle}>${iconName ? icon(iconName) : nothing}<span>${label}</span>
      ${icon('chevronRight', 'haui-menu-submenu-chevron')}</button>
    <div id=${id} class="haui-menu-submenu-items" role="menu" aria-label=${label}
      ?hidden=${!open} @keydown=${menuKeydown}>${items}</div>
  </div>`;
}

/**
 * Arrow, Home and End keys move between the items of a menu popover.
 * @param {KeyboardEvent} event - a keydown on the menu (its `currentTarget`)
 */
export function menuKeydown(event) {
  const menu = /** @type {any} */ (event.currentTarget);
  if (event.key === 'ArrowLeft' && menu.classList.contains('haui-menu-submenu-items')) {
    event.preventDefault();
    event.stopPropagation();
    const trigger = menu.parentElement?.querySelector('.haui-menu-submenu-trigger');
    trigger?.focus();
    trigger?.click();
    return;
  }
  if (event.key === 'ArrowRight') {
    const trigger = /** @type {any} */ (event.target).closest?.('[aria-haspopup="menu"]');
    if (trigger && menu.contains(trigger)) {
      event.preventDefault();
      event.stopPropagation();
      if (trigger.getAttribute('aria-expanded') === 'true') {
        const submenuId = trigger.getAttribute('aria-controls');
        menu.querySelector(`#${submenuId} [role="menuitem"]`)?.focus();
      } else {
        trigger.click();
      }
    }
    return;
  }
  const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
  if (step === undefined && event.key !== 'Home' && event.key !== 'End') return;
  const items = [...menu.querySelectorAll('[role^="menuitem"]:not([disabled])')]
    .filter((item) => item.closest('[role="menu"]') === menu);
  if (!items.length) return;
  event.preventDefault();
  event.stopPropagation();
  const root = menu.getRootNode?.();
  const current = items.indexOf(root?.activeElement);
  const next = event.key === 'Home' ? 0
    : event.key === 'End' ? items.length - 1
      : (current + step + items.length) % items.length;
  items[current < 0 && step === -1 ? items.length - 1 : next].focus();
}

/** Focus the first item of an open menu popover, once per opening. */
export function focusMenu(root) {
  const menu = root?.querySelector?.('.haui-popover[role="menu"]');
  if (!menu || menu.dataset.menuFocused) return;
  menu.dataset.menuFocused = 'true';
  menu.querySelector('[role^="menuitem"]:not([disabled])')?.focus();
}

export function menuSeparator() {
  return html`<div class="haui-menu-separator" role="separator"></div>`;
}

/**
 * Render an anchored popover. Placement happens after render through
 * `placeOpenPopovers`; `staticPlacement` keeps a surface that positions
 * itself with CSS (the notifications popover).
 *
 * @param {{ open: boolean, id: string, label: string, content: unknown, role?: string, className?: string, anchorKey?: string|null, align?: 'start'|'end', staticPlacement?: boolean }} options
 */
export function popover({
  open, id, label, content, role = 'dialog', className = '', anchorKey = null,
  align = 'end', staticPlacement = false,
}) {
  if (!open) return nothing;
  return html`<section id=${id} class=${`haui-popover ${className}`.trim()} role=${role}
    aria-label=${label} tabindex="-1"
    data-popover-anchor=${anchorKey ?? nothing}
    data-popover-align=${align}
    data-popover-static=${staticPlacement ? 'true' : nothing}
    @keydown=${role === 'menu' ? menuKeydown : nothing}>${content}</section>`;
}

/**
 * Place an anchored popover next to its trigger, clamped to the viewport and
 * flipped above the trigger when there is no room below it.
 *
 * @param {any} panel
 * @param {any} anchor
 * @param {{ align?: 'start'|'end', win?: any, margin?: number }} [options]
 */
export function placePopover(panel, anchor, { align = 'end', win = globalThis, margin = VIEWPORT_MARGIN } = {}) {
  const trigger = anchor.getBoundingClientRect();
  const width = panel.offsetWidth || 240;
  const height = panel.offsetHeight || 0;
  const viewportWidth = win.innerWidth || trigger.right + margin;
  const viewportHeight = win.innerHeight || trigger.bottom + margin;
  let left = align === 'end' ? trigger.right - width : trigger.left;
  left = Math.max(margin, Math.min(left, viewportWidth - width - margin));
  let top = trigger.bottom + ANCHOR_GAP;
  if (height && top + height > viewportHeight - margin && trigger.top - height - ANCHOR_GAP > margin) {
    top = trigger.top - height - ANCHOR_GAP;
  }
  top = Math.max(margin, Math.min(top, viewportHeight - height - margin));
  panel.style.top = `${Math.round(top)}px`;
  panel.style.left = `${Math.round(left)}px`;
  panel.style.right = 'auto';
  panel.style.bottom = 'auto';
}

/**
 * Place every open anchored popover next to its trigger, clamped to the viewport.
 * Static surfaces keep the placement declared by their own styles.
 *
 * @param {ParentNode|null|undefined} root
 * @param {any} [win]
 */
export function placeOpenPopovers(root, win = globalThis) {
  const panels = /** @type {any} */ (root?.querySelectorAll?.('[data-popover-anchor]'));
  if (!panels) return;
  panels.forEach((panel) => {
    if (panel.dataset.popoverStatic === 'true') return;
    const anchor = anchorElement(root, panel.dataset.popoverAnchor);
    if (!anchor) return;
    placePopover(panel, anchor, {
      align: panel.dataset.popoverAlign === 'start' ? 'start' : 'end',
      win,
    });
  });
}

