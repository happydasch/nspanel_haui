// @ts-check
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * A tile that only shows a setting: its label (with an optional icon), its
 * value and an optional detail at the end of the value's row. It looks like an `infoTile` but
 * has no card and no action. Place it in a `<dl class="haui-diag-tiles">`: the
 * label is the term, the value and the detail describe it.
 *
 * @param {{ label: string, value: unknown, detail?: unknown, iconName?: string|null, muted?: boolean }} options
 *   `muted` greys out a value that turns something off.
 */
export function valueTile({ label, value, detail = '', iconName = null, muted = false }) {
  return html`<div class="haui-diag-tile haui-value-tile">
    <dt class="haui-diag-tile-label">${iconName ? icon(iconName) : nothing}${label}</dt>
    <dd class=${`haui-diag-tile-value${muted ? ' is-muted' : ''}`}>${value}</dd>
    ${detail ? html`<dd class="haui-value-tile-detail">${detail}</dd>` : nothing}
  </div>`;
}

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
 *   tone?: string, heading?: unknown, note?: string, aside?: unknown, onClick?: (() => void)|null }} options
 *   `key` is unique within the shadow root (the card's id); each fact is its
 *   label, value and an optional tone; `heading` is the value as the card shows
 *   it, when the tile's own carries more than text; `aside` is a decorative
 *   glyph on the tile's trailing edge, beside both the label and the value.
 */
export function infoTile({
  key, label, value, facts = [], tone = '', heading = value, note = '', aside = nothing, onClick = null,
}) {
  const id = `haui-tile-card-${key}`;
  const body = html`<span class="haui-diag-tile-label">${label}</span>
    <span class=${`haui-diag-tile-value ${tone}`.trim()}>${value}</span>
    ${aside === nothing ? nothing : html`<span class="haui-diag-tile-aside" aria-hidden="true">${aside}</span>`}`;
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
