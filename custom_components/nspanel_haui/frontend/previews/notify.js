/**
 * NSPanel HAUI - Editor - Panel preview: Notify.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';

export function renderNotifyPreview(_host, panel, _pIdx, _pt) {
  // notifs type shows prev/next notification arrows on left_sec and right_sec
  const isNotifs = panel && panel.type === 'notifs';
  const overrides = isNotifs
    ? { leftSec: { icon: 'mdi:chevron-double-left', accent: true }, rightSec: { icon: 'mdi:chevron-double-right', accent: true } }
    : undefined;
  return {
    content: html`
      <div class="pg-preview-full-col" style="min-height:0;">
        <div style="display:flex;flex:1;gap:4px;min-height:0;align-items:stretch;">
          <div style="display:flex;align-items:center;justify-content:center;flex-shrink:0;width:28%;background:rgba(255,255,255,0.04);border-radius:3px;">
            <ha-icon icon="mdi:bell-ring-outline" style="--mdc-icon-size:clamp(14px,3cqi,26px);color:var(--primary-text-color,#ddd);opacity:0.6;"></ha-icon>
          </div>
          <div style="display:flex;flex-direction:column;justify-content:center;flex:1;gap:3px;min-width:0;padding:2px 0;">
            <div class="pg-preview-text-line wide" style="height:clamp(4px,1cqi,9px);"></div>
            <div class="pg-preview-text-line wide" style="height:clamp(4px,1cqi,9px);"></div>
            <div class="pg-preview-text-line medium" style="height:clamp(4px,1cqi,9px);width:60%;"></div>
          </div>
        </div>
        <div class="pg-preview-btn-row" style="gap:2px;margin-top:2px;">
          <div class="pg-preview-btn active" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label">${t('DISMISS')}</span></div>
          <div class="pg-preview-btn active" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label">${t('ACTION')}</span></div>
        </div>
      </div>`,
    headerButtonOverrides: overrides,
  };
}
