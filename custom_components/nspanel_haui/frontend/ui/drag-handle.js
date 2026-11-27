// @ts-check
/**
 * Reordering by touch.
 *
 * A finger never starts an HTML5 drag — mobile Safari and Chrome report no
 * `dragstart` for one — so every grip in the editor was a mouse-only control.
 * A press on a grip therefore runs the drag sequence itself: `dragstart` on the
 * element that is `draggable`, `dragover` on whatever sits under the finger,
 * and `drop` plus `dragend` when it lifts. The reorder code in `crud.js`,
 * `item-renderers.js` and the rows keeps handling plain drag events and does
 * not know the difference.
 */

/** Travel before a press on a grip becomes a drag, so a tap stays a tap. */
const START_DISTANCE = 6;
/** How close to the edge of its scroll box a drag has to come to scroll on its own. */
const EDGE_GAP = 48;
/** Pixels a drag scrolls per frame at the very edge, tapering off towards the gap. */
const EDGE_SPEED = 14;
/** A drag swallows the click a touch ends with; none arrives after this long anyway. */
const CLICK_GUARD_MS = 500;

/** The one finger that is dragging; a second one on another grip would mix the two drags up. */
let activePointerId = null;

/**
 * @typedef {object} Drag
 * @property {Element} origin - the element the browser would have dragged
 * @property {object} data - what `dragstart` fills in and `drop` reads
 * @property {Element} box - the box the drag scrolls by itself near its edges
 * @property {Element|null} hit - the element under the finger right now
 * @property {number} x
 * @property {number} y
 */

/**
 * What `dragstart` fills in and `drop` reads: the reorder handlers only ever set
 * and read plain text, so the stand-in a synthetic event carries is enough.
 */
function dragData() {
  /** @type {Map<string, string>} */
  const data = new Map();
  return {
    effectAllowed: 'move',
    dropEffect: 'move',
    types: /** @type {string[]} */ ([]),
    /** @param {string} type @param {string} value */
    setData(type, value) {
      data.set(String(type), String(value));
      this.types = [...data.keys()];
    },
    /** @param {string} type */
    getData(type) {
      return data.get(String(type)) ?? '';
    },
    /** @param {string} [type] */
    clearData(type) {
      if (type === undefined) data.clear();
      else data.delete(String(type));
      this.types = [...data.keys()];
    },
    setDragImage() {},
  };
}

/**
 * A drag event the reorder handlers recognise. `MouseEvent` carries the
 * position and `relatedTarget`; `dataTransfer` is defined on the instance
 * because only the browser itself can build a real `DragEvent`.
 *
 * @param {string} type
 * @param {object} data
 * @param {{ x: number, y: number, relatedTarget?: EventTarget|null }} position
 */
function dragEvent(type, data, { x, y, relatedTarget = null }) {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    composed: true,
    clientX: x,
    clientY: y,
    relatedTarget,
  });
  Object.defineProperty(event, 'dataTransfer', { value: data, configurable: true });
  return /** @type {DragEvent} */ (/** @type {unknown} */ (event));
}

/**
 * The deepest element at a point: the row, group or card that takes the drop is
 * one of its ancestors, and the events bubble up to it. The editor renders into
 * shadow roots, and the document's own hit test stops at their host, so each
 * open root under the finger is asked again.
 */
function hitAt(x, y) {
  let hit = document.elementFromPoint?.(x, y) || null;
  while (hit?.shadowRoot) {
    const inner = hit.shadowRoot.elementFromPoint?.(x, y);
    if (!inner || inner === hit) break;
    hit = inner;
  }
  return hit || document.body;
}

/**
 * The box a drag in `node` scrolls: the nearest ancestor that scrolls on its
 * own, or the page the editor scrolls as a whole.
 */
function scrollBox(node) {
  for (let parent = node.parentElement; parent; parent = parent.parentElement) {
    if (parent.scrollHeight <= parent.clientHeight + 1) continue;
    const { overflowY } = getComputedStyle(parent);
    if (overflowY === 'auto' || overflowY === 'scroll') return parent;
  }
  return document.scrollingElement || document.documentElement;
}

/** The page scroller's visible band; every other box is its own rectangle. */
function scrollBoxRect(box) {
  const page = document.scrollingElement || document.documentElement;
  return box === page ? { top: 0, bottom: window.innerHeight } : box.getBoundingClientRect();
}

/** Full speed at the very edge, slowing to a stop at the gap. */
function edgeSpeed(distance, gap) {
  return Math.max(1, Math.round(EDGE_SPEED * (1 - Math.max(0, distance) / gap)));
}

/**
 * Scroll the drag's box when the finger comes near its top or bottom edge, so a
 * row can be carried past the screen; says whether it moved.
 */
function scrollAtEdge(drag) {
  const rect = scrollBoxRect(drag.box);
  const gap = Math.min(EDGE_GAP, rect.height / 2);
  const fromTop = drag.y - rect.top;
  const fromBottom = rect.bottom - drag.y;
  const delta = fromTop < gap
    ? -edgeSpeed(fromTop, gap)
    : fromBottom < gap
      ? edgeSpeed(fromBottom, gap)
      : 0;
  if (!delta) return false;
  const before = drag.box.scrollTop;
  drag.box.scrollBy?.({ top: delta });
  if (drag.box.scrollTop === before) drag.box.scrollTop = before + delta;
  return drag.box.scrollTop !== before;
}

/**
 * Swallow the click a touch ends with, so a drop does not also open or select
 * the row it landed on; a tap that never became a drag keeps its click.
 */
function suppressNextClick() {
  const off = () => {
    document.removeEventListener('click', swallow, true);
    document.removeEventListener('pointerdown', off, true);
    clearTimeout(timer);
  };
  /** @param {Event} click */
  const swallow = (click) => {
    click.preventDefault();
    click.stopPropagation();
    off();
  };
  const timer = setTimeout(off, CLICK_GUARD_MS);
  document.addEventListener('click', swallow, true);
  // A press of its own means the click this drag would have ended with never came.
  document.addEventListener('pointerdown', off, true);
}

/**
 * Drag a reorder grip with a finger or a pen. Attach it to the grip's
 * `pointerdown`; anything inside the `draggable` element works, and a mouse is
 * left to the browser's own drag.
 *
 * @param {PointerEvent} event
 */
export function startHandleDrag(event) {
  const grip = /** @type {HTMLElement|null} */ (event.currentTarget);
  const origin = grip?.closest?.('[draggable="true"]');
  // A mouse drags the HTML5 way; only a touch or a pen needs this bridge.
  if (!grip || !origin || event.button !== 0 || event.pointerType === 'mouse') return;
  if (activePointerId !== null) return;
  activePointerId = event.pointerId;

  const from = { x: event.clientX, y: event.clientY };
  /** @type {Drag|null} */
  let drag = null;
  let frame = 0;

  /** Point the drop markers at whatever the finger is over now. */
  const mark = () => {
    if (!drag) return;
    const hit = hitAt(drag.x, drag.y);
    if (hit !== drag.hit) {
      // The element being left says so, and each row and group above it decides
      // by `relatedTarget` whether the finger left it too.
      drag.hit?.dispatchEvent(dragEvent('dragleave', drag.data, { x: drag.x, y: drag.y, relatedTarget: hit }));
      drag.hit = hit;
    }
    hit.dispatchEvent(dragEvent('dragover', drag.data, { x: drag.x, y: drag.y }));
  };

  /** Keep scrolling while the finger rests near an edge, following the rows under it. */
  const pump = () => {
    frame = 0;
    if (!drag || !scrollAtEdge(drag)) return;
    mark();
    frame = requestAnimationFrame(pump);
  };

  /** End the gesture, dropping on whatever is under the finger only when `dropped` is set. */
  const finish = (dropped = false) => {
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup', release);
    document.removeEventListener('pointercancel', cancel);
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    activePointerId = null;
    const current = drag;
    drag = null;
    if (!current) return;
    const hit = dropped ? hitAt(current.x, current.y) : null;
    if (hit && hit !== current.hit) {
      current.hit?.dispatchEvent(
        dragEvent('dragleave', current.data, { x: current.x, y: current.y, relatedTarget: hit }),
      );
    }
    if (hit) {
      hit.dispatchEvent(dragEvent('drop', current.data, { x: current.x, y: current.y }));
    } else if (current.hit) {
      current.hit.dispatchEvent(dragEvent('dragleave', current.data, { x: current.x, y: current.y }));
    }
    current.origin.dispatchEvent(dragEvent('dragend', current.data, { x: current.x, y: current.y }));
    suppressNextClick();
  };

  /** @param {PointerEvent} moved */
  const move = (moved) => {
    if (moved.pointerId !== event.pointerId) return;
    if (!drag) {
      if (Math.hypot(moved.clientX - from.x, moved.clientY - from.y) < START_DISTANCE) return;
      const data = dragData();
      const started = dragEvent('dragstart', data, { x: moved.clientX, y: moved.clientY });
      origin.dispatchEvent(started);
      // A handler may refuse a drag, as it may refuse the browser's own one.
      if (started.defaultPrevented) {
        finish();
        return;
      }
      drag = { origin, data, box: scrollBox(origin), hit: null, x: moved.clientX, y: moved.clientY };
      // The grip is neither text to select nor an icon to call out.
      moved.preventDefault();
    }
    drag.x = moved.clientX;
    drag.y = moved.clientY;
    mark();
    if (!frame) frame = requestAnimationFrame(pump);
  };

  /** @param {PointerEvent} up */
  const release = (up) => {
    if (up.pointerId !== event.pointerId) return;
    // The lift is the drop: it happens where the finger left, not where it last moved.
    if (drag) {
      drag.x = up.clientX;
      drag.y = up.clientY;
      mark();
    }
    finish(true);
  };
  /** @param {PointerEvent} cancelled */
  const cancel = (cancelled) => {
    if (cancelled.pointerId === event.pointerId) finish();
  };

  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', release);
  document.addEventListener('pointercancel', cancel);
}
