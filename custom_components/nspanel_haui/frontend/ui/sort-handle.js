import { html } from '../lit-import.js';
import { startHandleDrag } from './drag-handle.js';
import { icon } from './icon.js';

/**
 * Drag grip of a reorderable card or row. Dragging needs a pointer, so the
 * grip is hidden from screen readers instead of announcing what they cannot do;
 * a finger drags it through `ui/drag-handle.js`, because a touch starts no HTML5
 * drag of its own.
 */
export function sortHandle({ label, onDragStart, onDragEnd }) {
  return html`<span class="haui-sort-handle" aria-hidden="true" title=${label} draggable="true"
      data-drag-handle @dragstart=${onDragStart} @dragend=${onDragEnd} @pointerdown=${startHandleDrag}>
    ${icon('grip')}
  </span>`;
}
