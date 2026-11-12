// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';

// How much larger than the thumbnail the enlarged preview is, and how far it
// stays from the thumbnail and from the viewport's edges.
const ZOOM = 4;
const ZOOM_GAP = 12;
const ZOOM_MARGIN = 8;

/** @param {number} value @param {number} size @param {number} limit */
const insideViewport = (value, size, limit) => (
  Math.max(ZOOM_MARGIN, Math.min(value, limit - size - ZOOM_MARGIN))
);

/**
 * Where the enlarged preview goes: beside the thumbnail, centred on it, moved
 * back inside the viewport where it would leave it.
 * @param {{ top: number, right: number, width: number, height: number }} box
 * @param {{ width: number, height: number }} viewport
 */
export function zoomPlacement(box, viewport) {
  const width = Math.min(box.width * ZOOM, viewport.width - 2 * ZOOM_MARGIN);
  const height = width * box.height / box.width;
  return {
    left: insideViewport(box.right + ZOOM_GAP, width, viewport.width),
    top: insideViewport(box.top + box.height / 2 - height / 2, height, viewport.height),
    width,
    height,
  };
}

/** @param {any} thumb */
function closeZoom(thumb) {
  if (!thumb.classList.contains('is-zoomed')) return;
  thumb.classList.remove('is-zoomed');
  thumb.setAttribute('aria-expanded', 'false');
  thumb.querySelector('.haui-panel-thumb-view')?.removeAttribute('style');
  thumb.__stopZoomWatch?.();
  thumb.__stopZoomWatch = null;
}

/**
 * Enlarge the thumbnail's own render: the simulator frame follows its box, so
 * no second render is needed.
 * @param {any} thumb
 */
function openZoom(thumb) {
  if (thumb.classList.contains('is-zoomed')) return;
  const view = thumb.querySelector('.haui-panel-thumb-view');
  if (!view) return;
  const place = zoomPlacement(thumb.getBoundingClientRect(), {
    width: window.innerWidth, height: window.innerHeight,
  });
  thumb.classList.add('is-zoomed');
  thumb.setAttribute('aria-expanded', 'true');
  view.style.cssText = `left:0;top:0;width:${place.width}px;height:${place.height}px;`;
  // An ancestor may be the containing block of fixed boxes (containment, a
  // transform), so place the view by where "0, 0" really is.
  const origin = view.getBoundingClientRect();
  view.style.left = `${place.left - origin.left}px`;
  view.style.top = `${place.top - origin.top}px`;

  // A tap leaves no hover to end and may not move the focus; scrolling moves
  // the thumbnail away from its fixed preview.
  const dismiss = (event) => {
    if (event.type === 'scroll' || !event.composedPath().includes(thumb)) closeZoom(thumb);
  };
  document.addEventListener('pointerdown', dismiss, true);
  window.addEventListener('scroll', dismiss, true);
  thumb.__stopZoomWatch = () => {
    document.removeEventListener('pointerdown', dismiss, true);
    window.removeEventListener('scroll', dismiss, true);
  };
}

/**
 * Wrap a hub-rendered page in the panel-list thumbnail, with its role markers.
 * Hovering it with a mouse, or tapping or pressing it, shows the page enlarged.
 *
 * @param {{content?: unknown, portrait?: boolean, label: string, roles?: unknown[]}} options
 */
export function panelThumb({ content = nothing, portrait = false, label, roles = [] }) {
  const hover = (event, open) => {
    if (event.pointerType !== 'mouse') return;
    (open ? openZoom : closeZoom)(event.currentTarget);
  };
  return html`<button type="button" class=${'haui-panel-thumb' + (portrait ? ' portrait' : '')}
    aria-label=${t('Preview of {name}').replace('{name}', label)} aria-expanded="false"
    @pointerenter=${(event) => hover(event, true)}
    @pointerleave=${(event) => hover(event, false)}
    @click=${(event) => {
      const thumb = event.currentTarget;
      // A mouse click arrives on a preview its hover already opened.
      if (event.pointerType === 'mouse' || !thumb.classList.contains('is-zoomed')) openZoom(thumb);
      else closeZoom(thumb);
    }}
    @blur=${(event) => closeZoom(event.currentTarget)}
    @keydown=${(event) => {
      if (event.key !== 'Escape' || !event.currentTarget.classList.contains('is-zoomed')) return;
      event.stopPropagation();
      closeZoom(event.currentTarget);
    }}>
    <span class="haui-panel-thumb-view">${content}</span>
    ${roles.length ? html`<span class="haui-panel-thumb-roles">${roles}</span>` : nothing}
  </button>`;
}
