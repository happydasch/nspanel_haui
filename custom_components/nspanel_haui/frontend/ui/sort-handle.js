import { html } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * Drag grip of a reorderable card or row. Dragging needs a pointer, so the
 * grip is hidden from screen readers instead of announcing what they cannot do.
 */
export function sortHandle({ label, onDragStart, onDragEnd }) {
  return html`<span class="haui-sort-handle" aria-hidden="true" title=${label} draggable="true"
      @dragstart=${onDragStart} @dragend=${onDragEnd}>
    ${icon('grip')}
  </span>`;
}
