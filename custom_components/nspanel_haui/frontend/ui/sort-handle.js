import { html } from '../lit-import.js';
import { icon } from './icon.js';

/** Drag grip of a reorderable card or row. */
export function sortHandle({ label, onDragStart, onDragEnd }) {
  return html`<span class="haui-sort-handle" role="img" aria-label=${label} title=${label} draggable="true"
      @dragstart=${onDragStart} @dragend=${onDragEnd}>
    ${icon('grip')}
  </span>`;
}
