// @ts-check
import { html, nothing } from '../lit-import.js';

/** Toggle a hover card on tap; it closes again when its button loses focus. */
export function toggleHoverCard(/** @type {Event} */ event) {
  const trigger = /** @type {HTMLElement} */ (event.currentTarget);
  const open = trigger.getAttribute('aria-expanded') !== 'true';
  trigger.setAttribute('aria-expanded', String(open));
  // Safari does not focus a tapped button, and focus is what closes the card again.
  if (open) trigger.focus();
}

export function closeHoverCard(/** @type {Event} */ event) {
  const trigger = /** @type {HTMLElement} */ (event.currentTarget);
  if (event.type === 'keydown' && /** @type {KeyboardEvent} */ (event).key !== 'Escape') return;
  trigger.setAttribute('aria-expanded', 'false');
}

/**
 * A status tile with its label and value only; hover, focus or a tap opens a
 * card under it with the full value (the tile cuts a long one off) and the
 * tile's other facts. A tile with `onClick` runs that on a tap instead, so its
 * card opens on hover and focus only.
 *
 * @param {{ key: string, label: string, value: unknown, facts?: unknown[][],
 *   tone?: string, heading?: unknown, note?: string, onClick?: (() => void)|null }} options
 *   `key` is unique within the shadow root (the card's id); each fact is its
 *   label, value and an optional tone; `heading` is the value as the card shows
 *   it, when the tile's own carries more than text.
 */
export function infoTile({ key, label, value, facts = [], tone = '', heading = value, note = '', onClick = null }) {
  const id = `haui-tile-card-${key}`;
  const body = html`<span class="haui-diag-tile-label">${label}</span>
    <span class=${`haui-diag-tile-value ${tone}`.trim()}>${value}</span>`;
  // The aria-expanded attribute is static so a status poll never closes an open card.
  const trigger = onClick
    ? html`<button type="button" class="haui-diag-tile" aria-describedby=${id} @click=${onClick}>${body}</button>`
    : html`<button type="button" class="haui-diag-tile" aria-describedby=${id} aria-expanded="false"
        @click=${toggleHoverCard} @blur=${closeHoverCard} @keydown=${closeHoverCard}>${body}</button>`;
  return html`<div class="haui-tile-info">
    ${trigger}
    <div class="haui-tile-card" id=${id} role="tooltip">
      <strong>${heading}</strong>
      ${facts.length ? html`<dl>${facts.map(([name, fact, factTone = '']) => html`<div>
        <dt>${name}</dt><dd class=${String(factTone)}>${fact}</dd>
      </div>`)}</dl>` : nothing}
      ${note ? html`<p>${note}</p>` : nothing}
    </div>
  </div>`;
}
