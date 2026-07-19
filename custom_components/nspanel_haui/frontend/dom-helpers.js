/**
 * NSPanel HAUI - DOM helper utilities.
 *
 * Tiny helpers used across the editor to reduce repeated querySelector patterns.
 */

/**
 * Read the value of a form field by its id attribute.
 * @param {HTMLElement} form - the form (or any ancestor) DOM element
 * @param {string} id - the element id (without #)
 * @param {string} [fallback=""] - value to return if element not found
 * @returns {string}
 */
export function formVal(form, id, fallback = "") {
  const el = form.querySelector(`#${id}`);
  return el ? el.value : fallback;
}

/**
 * Walk up the flattened (shadow-aware) tree from a node, one step at a time.
 * Follows assigned slots and crosses shadow roots so the chain matches the
 * layout/containing-block hierarchy, not just the light DOM.
 * @param {Node} node
 * @returns {Element|null}
 */
function flatParent(node) {
  if (!node) return null;
  if (node.assignedSlot) return node.assignedSlot;
  const p = node.parentNode;
  if (!p) return null;
  if (p.nodeType === 11) return p.host || null;   // ShadowRoot -> host
  return p;
}

/**
 * Find the nearest ancestor that establishes a containing block for
 * `position: fixed` (transform / perspective / filter / contain / will-change).
 * Inside ha-dialog this is the animated surface — exactly the box the menu
 * must stay within. Returns null when none exists (true viewport context).
 * @param {Element} el
 * @returns {Element|null}
 */
function fixedContainingBlock(el) {
  let node = flatParent(el);
  while (node && node.nodeType === 1) {
    const cs = getComputedStyle(node);
    if (
      cs.transform !== 'none' ||
      cs.perspective !== 'none' ||
      (cs.filter && cs.filter !== 'none') ||
      /transform|filter|perspective/.test(cs.willChange || '') ||
      /paint|layout|strict|content/.test(cs.contain || '')
    ) {
      return node;
    }
    node = flatParent(node);
  }
  return null;
}

/**
 * Reposition a dropdown to `position: fixed` so it escapes overflow clipping
 * from ancestor scroll containers (e.g., ha-dialog body with overflow: auto).
 *
 * A `position: fixed` element is normally viewport-relative, but inside an
 * ancestor that establishes a containing block — a transform, filter, or
 * `contain` (ha-dialog's animated surface does this) — it becomes relative to
 * that ancestor instead, and is also clipped by it. So we:
 *   1. measure where the containing block's (0,0) lands in viewport coords
 *      (pin the dropdown at top/left 0 and read its rect) for an exact offset;
 *   2. clamp the menu inside the containing block's bounds (the dialog box),
 *      not just the viewport, so it never spills out or gets cut off;
 *   3. cap its height to that box so a long menu scrolls instead of overflowing;
 *   4. convert the clamped viewport coords back to containing-block coords.
 *
 * Must be called AFTER the dropdown is visible so its size is measurable.
 *
 * @param {HTMLElement} dropdown - The dropdown element
 * @param {HTMLElement} trigger - The trigger element (button/input)
 * @param {object} [opts]
 * @param {'left'|'right'} [opts.align='left'] - Horizontal alignment
 * @param {number} [opts.offsetY=4] - Vertical offset from trigger bottom
 * @param {number} [opts.offsetX=0] - Horizontal offset from aligned edge
 */
export function positionFixedDropdown(dropdown, trigger, opts = {}) {
  const { align = 'left', offsetY = 4, offsetX = 0 } = opts;
  const margin = 8;

  // Pin to fixed (0,0) and clear any CSS right/margin so the measured rect
  // reflects the containing-block origin and the natural element size.
  dropdown.style.position = 'fixed';
  dropdown.style.margin = '0';
  dropdown.style.right = 'auto';
  dropdown.style.maxHeight = '';
  dropdown.style.zIndex = '10000';
  dropdown.style.top = '0';
  dropdown.style.left = '0';
  if (align !== 'right') {
    dropdown.style.width = `${trigger.getBoundingClientRect().width}px`;
  } else {
    dropdown.style.width = 'auto';
  }

  const origin = dropdown.getBoundingClientRect();      // viewport coords of (0,0)
  const t = trigger.getBoundingClientRect();

  // Boundary = the dialog box the menu must stay inside, intersected with the
  // viewport. Falls back to the whole viewport outside any dialog.
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const cb = fixedContainingBlock(dropdown);
  const cbRect = cb ? cb.getBoundingClientRect() : { left: 0, top: 0, right: vw, bottom: vh };
  const bound = {
    left: Math.max(margin, cbRect.left + margin),
    top: Math.max(margin, cbRect.top + margin),
    right: Math.min(vw - margin, cbRect.right - margin),
    bottom: Math.min(vh - margin, cbRect.bottom - margin),
  };

  const dw = dropdown.offsetWidth || 160;
  let dh = dropdown.offsetHeight || 0;

  // Cap height to the boundary so a tall menu scrolls instead of overflowing.
  const maxH = bound.bottom - bound.top;
  if (dh > maxH) {
    dropdown.style.maxHeight = `${maxH}px`;
    dropdown.style.overflowY = 'auto';
    dh = maxH;
  }

  // Desired viewport position.
  let top = t.bottom + offsetY;
  let left = align === 'right' ? t.right - dw + offsetX : t.left + offsetX;

  // Flip above the trigger when there isn't room below but there is above.
  if (top + dh > bound.bottom && t.top - offsetY - dh > bound.top) {
    top = t.top - offsetY - dh;
  }

  // Keep inside the boundary.
  left = Math.max(bound.left, Math.min(left, bound.right - dw));
  top = Math.max(bound.top, Math.min(top, bound.bottom - dh));

  // Convert viewport coords -> containing-block coords.
  dropdown.style.top = `${top - origin.top}px`;
  dropdown.style.left = `${left - origin.left}px`;
}

/**
 * Position a context menu dropdown (right-aligned) at trigger location.
 * @param {HTMLElement} dropdown
 * @param {HTMLElement} trigger
 */
export function positionContextMenu(dropdown, trigger) {
  positionFixedDropdown(dropdown, trigger, { align: 'right', offsetY: 4 });
}

/**
 * Position an autocomplete picker dropdown (left-aligned, fills input width).
 * @param {HTMLElement} dropdown
 * @param {HTMLElement} input
 */
export function positionPickerDropdown(dropdown, input) {
  positionFixedDropdown(dropdown, input, { align: 'left', offsetY: 4 });
}

/* ── dropdown keyboard navigation ─────────────────────────────────────── */

/**
 * Create a keydown handler for filtered dropdown keyboard navigation.
 *
 * Handles ArrowDown, ArrowUp, Enter (select), and Escape (dismiss).
 * Items are filtered by checking `el.style.display !== "none"` or `!el.hidden`.
 *
 * @param {object} opts
 * @param {function} opts.getWrap   - (e) => the wrapping element containing the dropdown
 * @param {string}  [opts.dropdownSelector=".entity-dropdown"] - CSS selector for the dropdown
 * @param {string}  [opts.itemSelector=".entity-dropdown-item"] - CSS selector for items
 * @param {string}  [opts.indexField="_activeIndex"] - property name for the active index on wrap
 * @param {function} opts.onSelect  - (visibleItems, idx, e) => called on Enter with the event
 * @param {function} opts.onDismiss - (e) => called on Escape with the event
 * @returns {function} keydown event handler
 */
export function createDropdownKeyboardController(opts) {
  const {
    getWrap,
    dropdownSelector = '.entity-dropdown',
    itemSelector = '.entity-dropdown-item',
    indexField = '_activeIndex',
    onSelect,
    onDismiss,
  } = opts;
  return (e) => {
    const wrap = typeof getWrap === 'function' ? getWrap(e) : getWrap;
    if (!wrap) return;
    const dropdown = wrap.querySelector(dropdownSelector);
    if (!dropdown || dropdown.style.display === 'none' || dropdown.hidden) return;

    const visibleItems = [...dropdown.querySelectorAll(itemSelector)]
      .filter((el) => el.style.display !== 'none' && !el.hidden);
    if (!visibleItems.length) return;

    let idx = wrap[indexField] != null ? wrap[indexField] : -1;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      idx = Math.min(idx + 1, visibleItems.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      idx = Math.max(idx - 1, 0);
    } else if (e.key === 'Enter') {
      if (idx >= 0) {
        e.preventDefault();
        onSelect(visibleItems, idx, e);
      }
      return;
    } else if (e.key === 'Escape') {
      e.preventDefault();
      if (onDismiss) onDismiss(e);
      return;
    } else {
      return;
    }

    wrap[indexField] = idx;
    dropdown.querySelectorAll(itemSelector).forEach((item, i) => {
      item.classList.toggle('active', i === idx);
    });
    if (visibleItems[idx]) {
      visibleItems[idx].scrollIntoView({ block: 'nearest' });
    }
  };
}

/* ── outside-click dismiss ─────────────────────────────────────────────── */

/**
 * Register a document-level mousedown (capture phase) listener that calls
 * `close` when the click target is outside all elements matching `check`.
 *
 * Caller must call `offOutsideClick(host)` in disconnectedCallback.
 *
 * @param {object}   host    - LitElement instance (stores handler on it)
 * @param {function} check   - (e) => true if click is inside a guard element
 * @param {function} close   - (e) => called when click is outside
 */
export function onOutsideClick(host, check, close) {
  const handler = (e) => {
    if (!check(e)) close(e);
  };
  host.__outsideClickHandler = handler;
  document.addEventListener('mousedown', handler, true);
}

/**
 * Unregister the document-level mousedown listener previously installed by
 * `onOutsideClick`.
 *
 * @param {object} host - LitElement instance
 */
export function offOutsideClick(host) {
  if (host.__outsideClickHandler) {
    document.removeEventListener('mousedown', host.__outsideClickHandler, true);
    host.__outsideClickHandler = null;
  }
}


