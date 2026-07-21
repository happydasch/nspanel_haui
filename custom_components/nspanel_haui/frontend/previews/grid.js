/**
 * NSPanel HAUI - Panel preview: Grid.
 *
 * Device layout: 3 columns × 2 rows of tiles.
 * Each tile: icon (font:3 light, 128×48) + name (font:0, 128×30).
 * Power button at top-right of each tile.
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
