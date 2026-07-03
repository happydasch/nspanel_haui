/**
 * NSPanel HAUI - Panel preview: System Settings.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { simSlider } from './primitives.js';

export function renderSettingsPreview(_host, _panel, _pIdx, _pt) {
  return {
    contentClass: 'pg-preview-content-top',
    content: html`
      <div class="pg-preview-full-col" style="gap:4px;padding:3px 0;justify-content:flex-start;min-height:0;">
        <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
          <ha-icon icon="mdi:brightness-6" style="--mdc-icon-size:12px;color:var(--secondary-text-color,#999);flex-shrink:0;"></ha-icon>
          <span style="flex:1;min-width:0;font-size:0.55em;color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${t('Brightness')}</span>
          <span style="font-size:0.55em;color:var(--secondary-text-color,#999);flex-shrink:0;">85%</span>
        </div>
        ${simSlider({ value: 85 })}
        <div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">
          <ha-icon icon="mdi:brightness-4" style="--mdc-icon-size:12px;color:var(--secondary-text-color,#999);flex-shrink:0;"></ha-icon>
          <span style="flex:1;min-width:0;font-size:0.55em;color:var(--primary-text-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${t('Dimmed')}</span>
          <span style="font-size:0.55em;color:var(--secondary-text-color,#999);flex-shrink:0;">30%</span>
        </div>
        ${simSlider({ value: 30 })}
      </div>`,
  };
}
