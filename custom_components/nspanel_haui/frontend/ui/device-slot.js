// @ts-check
import { html } from '../lit-import.js';

/**
 * Decorative empty device cards that complete the visible row; they are intentionally inert.
 * @param {{ count: number, left: number, step: number }} data
 */
export function deviceSlots({ count, left, step }) {
  return html`${Array.from({ length: count }, (_, index) => html`<article
    class="haui-device-card haui-device-slot-card" aria-hidden="true"
    style=${`--haui-device-slot-left: ${left + index * step}px`}></article>`)}`;
}
