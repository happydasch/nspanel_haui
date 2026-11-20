// @ts-check
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * @typedef {object} SearchFieldOptions
 * @property {string} label
 * @property {string} value
 * @property {string} className
 * @property {(value: string) => void} [onInput]
 * @property {(event: KeyboardEvent) => void} [onKeyDown]
 */

/** @param {SearchFieldOptions} options */
export function searchField({ label, value, className, onInput, onKeyDown }) {
  return html`<label class=${`haui-search-field ${className}`}>
    ${icon('search')}
    <input type="search" aria-label=${label} placeholder=${label} .value=${value}
      @input=${(event) => onInput?.(event.currentTarget.value)} @keydown=${onKeyDown ?? nothing}>
  </label>`;
}
