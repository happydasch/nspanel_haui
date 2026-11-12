// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { addButton, iconButton } from './button.js';

/** "{n} entries" — the count badge of a folded card of entries (schedule, gestures). */
export function entryCount(/** @type {number} */ count) {
  return count === 1 ? t('1 entry') : t('{count} entries').replace('{count}', String(count));
}

/**
 * The list editor of the schedule and the gestures: the add row, then one
 * folding card per entry. A card's head is its fold control and reads
 * "Entry N", the summary (what starts the entry: its window, its swipes) and
 * the note (what it does), then the remove button. Only `expandedIndex` (the
 * entry just added) opens by state; the others keep the fold the user gave them.
 *
 * @template T
 * @param {{ entries: T[], className: string, addId: string, addLabel: string, removeLabel: string,
 *   expandedIndex?: number|null, onAdd: () => void, onRemove: (index: number) => void,
 *   onToggle?: (index: number, open: boolean) => void, summary: (entry: T) => unknown,
 *   note?: (entry: T) => unknown, body: (entry: T, index: number) => unknown }} options
 */
export function entryList({
  entries, className, addId, addLabel, removeLabel, expandedIndex = null,
  onAdd, onRemove, onToggle, summary, note, body,
}) {
  const card = (/** @type {T} */ entry, /** @type {number} */ index) => html`<details class="haui-entry"
    ?open=${index === expandedIndex} @toggle=${(event) => onToggle?.(index, event.target.open)}>
    <summary class="haui-entry-head">
      <span class="haui-entry-title">${t('Entry {number}').replace('{number}', String(index + 1))}</span>
      <span class="haui-entry-summary">${summary(entry)}</span>
      <span class="haui-entry-note">${note ? note(entry) : nothing}</span>
      ${iconButton({
        label: removeLabel, iconName: 'delete-outline',
        onClick: (event) => {
          // The row is the fold control: a click on its delete button must not toggle it.
          event.preventDefault();
          // Lit reuses the rows by position, so each later row hands its fold state up one
          // first; otherwise an open row would close and its neighbour open in its place.
          const list = /** @type {Element|null} */ (event.currentTarget)?.closest('.haui-entry-list');
          const rows = /** @type {HTMLDetailsElement[]} */ (
            [...(list?.querySelectorAll(':scope > details.haui-entry') ?? [])]);
          for (let i = index; i < rows.length - 1; i++) rows[i].open = rows[i + 1].open;
          onRemove(index);
        },
      })}
      <span class="haui-entry-chevron" aria-hidden="true"></span>
    </summary>
    <div class="haui-entry-body">${body(entry, index)}</div>
  </details>`;
  return html`<div class=${`haui-entry-list ${className}`}>
    ${addButton({ label: addLabel, id: addId, onClick: onAdd })}
    ${entries.map(card)}
  </div>`;
}
