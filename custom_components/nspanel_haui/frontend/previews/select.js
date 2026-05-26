/**
 * NSPanel HAUI - Editor - Panel preview: Select.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';

export function renderSelectPreview(_host, panel, _pIdx, _pt) {
  const isFull = panel && panel.select_mode === 'full';
  const labels = isFull
    ? [t('Option A'), t('Option B'), t('Option C'), t('Option D')]
    : ['1','2','3','4','5','6','7','8','9','10','11','12'];
  return {
    content: html`
      <div style="display:${isFull ? 'flex' : 'grid'};flex-direction:column;${isFull ? '' : 'grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(4,1fr)'};gap:3px;width:100%;flex:1;min-height:0;">
        ${isFull
          ? labels.map(l => html`
              <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label" style="font-size:0.5em;color:var(--secondary-text-color,#999);">${l}</span></div>
            `)
          : labels.map(l => html`
              <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.5em;color:var(--secondary-text-color,#999);">${l}</span></div>
            `)}
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:chevron-double-down', accent: true } },
  };
}
