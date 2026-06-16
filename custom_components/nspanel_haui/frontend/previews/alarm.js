/**
 * NSPanel HAUI - Editor - Panel preview: Alarm / Unlock.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';

export function renderAlarmPreview(_host, _panel, _pIdx, _pt) {
  const fnBtns = [t('AWAY'), t('HOME'), t('DISARM'), t('PANIC')];
  const keys = ['1','2','3','4','5','6','7','8','9',t('CLR'),'0',t('DEL')];
  return {
    content: html`
      <div class="pg-preview-full-flex" style="gap:8px;align-items:stretch;">
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.55em;color:var(--secondary-text-color,#999);">${k}</span></div>
          `)}
        </div>
        <div class="pg-preview-action-col">
          ${fnBtns.map(label => html`
            <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label">${label}</span></div>
          `)}
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:shield-lock-outline', accent: true } },
  };
}

export function renderUnlockPreview(_host, _panel, _pIdx, _pt) {
  const keys = ['1','2','3','4','5','6','7','8','9',t('CLR'),'0',t('DEL')];
  return {
    content: html`
      <div class="pg-preview-full-flex" style="gap:8px;align-items:stretch;">
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.55em;color:rgba(255,255,255,0.25);">${k}</span></div>
          `)}
        </div>
        <div class="pg-preview-action-col">
          <div class="pg-preview-btn active" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label" style="color:var(--accent-color,#f69d31);">${t('UNLOCK')}</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
        </div>
      </div>`,
  };
}
