// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';

/** Whether a drag sits over the lower half of a row: the drop lands after it. */
export function dropsAfter(event) {
  const rect = event.currentTarget.getBoundingClientRect?.();
  return Boolean(rect) && event.clientY > rect.top + rect.height / 2;
}

// A row's own controls keep their click; the rest of the row selects the panel.
const OWN_CLICK = 'button, a, input, select, textarea, label, [role="menu"], [role="tooltip"], .haui-panel-handle';

/**
 * One panel row: drag handle, thumbnail, title, key, item count and its own
 * actions. The row is not a button — the title opens the editor and every
 * action stays a separate named control. With `onSelect` the row also selects
 * itself on a click outside those controls (or on Enter and Space), and marks
 * the selection with `aria-current`.
 *
 * @param {{ key?: string, group: string, title: unknown, typeLabel?: string, keyLabel?: string,
 *   itemCount?: number, thumbnail?: unknown, handle?: unknown, actions?: unknown,
 *   lockReason?: string, menu?: unknown, selected?: boolean, onEdit?: (() => void)|null,
 *   onSelect?: (() => void)|null, onDrop?: ((sourceKey: string, after: boolean) => void)|null }} options
 */
export function panelRow({
  key = '', group, title, typeLabel = '', keyLabel = '', itemCount, thumbnail = nothing,
  handle = nothing, actions = nothing, lockReason = '', menu = nothing, selected = false,
  onEdit = null, onSelect = null, onDrop = null,
}) {
  const selectOnClick = onSelect ? (event) => {
    if (/** @type {Element} */ (event.target).closest?.(OWN_CLICK)) return;
    onSelect();
  } : null;
  const selectOnKey = onSelect ? (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    onSelect();
  } : null;
  const countLabel = itemCount === undefined
    ? ''
    : itemCount === 1
      ? t('1 item')
      : t('{count} items').replace('{count}', String(itemCount));
  const clearDrop = (row) => row.classList.remove('is-drop-before', 'is-drop-after');
  const acceptDrop = onDrop ? (event) => {
    event.preventDefault();
    // The row handles its own drop; the group around it appends to its end.
    event.stopPropagation();
    clearDrop(event.currentTarget);
    const sourceKey = event.dataTransfer?.getData('text/plain');
    if (sourceKey) onDrop(sourceKey, dropsAfter(event));
  } : null;
  // Without preventDefault on dragover the browser never fires drop on the row.
  const allowDrop = onDrop ? (event) => {
    event.preventDefault();
    event.stopPropagation();
    const after = dropsAfter(event);
    event.currentTarget.classList.toggle('is-drop-before', !after);
    event.currentTarget.classList.toggle('is-drop-after', after);
  } : null;
  const leaveDrop = onDrop ? (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) clearDrop(event.currentTarget);
  } : null;
  return html`<div class=${`haui-panel-row${selected ? ' is-selected' : ''}`}
    data-panel-key=${key} data-panel-group=${group}
    aria-current=${selected ? 'true' : nothing}
    tabindex=${onSelect ? '0' : nothing}
    @click=${selectOnClick ?? nothing} @keydown=${selectOnKey ?? nothing}
    @dragover=${allowDrop ?? nothing} @dragleave=${leaveDrop ?? nothing} @drop=${acceptDrop ?? nothing}>
    <span class="haui-panel-row-grip">${handle}</span>
    ${thumbnail}
    <div class="haui-panel-row-main">
      <button type="button" class="haui-panel-row-title"
        ?disabled=${!onEdit} @click=${onEdit ?? nothing}>${title}</button>
      ${typeLabel ? html`<span class="haui-panel-row-sub">${typeLabel}</span>` : nothing}
      ${lockReason ? html`<span class="haui-panel-row-lock">${lockReason}</span>` : nothing}
    </div>
    <code class="haui-panel-row-key">${keyLabel || key || t('Auto key')}</code>
    <span class="haui-panel-row-count">${countLabel}</span>
    <div class="haui-panel-row-actions">${actions}</div>
    ${menu}
  </div>`;
}
