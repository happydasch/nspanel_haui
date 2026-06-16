/**
 * NSPanel HAUI - Editor - Panel preview: Grid.
 */
import { html } from '../lit-import.js';
import { getItems, backgroundClass } from './utils.js';
import { simItemTile } from './primitives.js';

export function renderGridPreview(host, panel, _pIdx, _pt) {
  const items = getItems(panel);
  if (items.length === 0) {
    return { content: html``, containerClass: backgroundClass(panel) };
  }
  return {
    content: html`
      <div class="pg-preview-grid-fill">
        ${items.slice(0, 6).map(item => simItemTile(item, { tileClass: 'pg-preview-grid-tile fill' }, host))}
      </div>`,
    containerClass: backgroundClass(panel),
  };
}
