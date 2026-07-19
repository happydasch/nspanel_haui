/**
 * NSPanel HAUI - Panel preview: Alarm / Unlock / PopupAlarm.
 *
 * Device layout: 3x4 keypad on left (bKey1-bKey9, bKeyClr, bKey0, bKeyDel),
 * 4 function buttons on right (b1Fnc-b4Fnc).
 * Each key: 70x55, font:1. Each fnc button: 180x55, font:1.
 */
import { html } from '../lit-import.js';
import { t } from '../localize.js';

export function renderAlarmPreview(_host, _panel, _pIdx, _pt) {
  const fnBtns = [t('AWAY'), t('HOME'), t('DISARM'), t('PANIC')];
  const keys = ['1','2','3','4','5','6','7','8','9',t('CLR'),'0',t('DEL')];
  return {
    content: html`
      <div class="pg-preview-full-flex" style="gap:6px;align-items:stretch;padding:2px 0;">
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.5em;font-weight:400;color:var(--secondary-text-color,#999);">${k}</span></div>
          `)}
        </div>
        <div class="pg-preview-action-col" style="gap:4px;">
          ${fnBtns.map(label => html`
            <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label" style="font-size:0.45em;">${label}</span></div>
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
      <div class="pg-preview-full-flex" style="gap:6px;align-items:stretch;padding:2px 0;">
        <div class="pg-preview-keypad-grid">
          ${keys.map(k => html`
            <div class="pg-preview-btn" style="width:100%;height:100%;"><span style="font-size:0.5em;font-weight:400;color:rgba(255,255,255,0.25);">${k}</span></div>
          `)}
        </div>
        <div class="pg-preview-action-col" style="gap:4px;">
          <div class="pg-preview-btn active" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label" style="font-size:0.45em;color:var(--primary-color,#4fc3f7);">${t('UNLOCK')}</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
          <div class="pg-preview-btn" style="width:100%;flex:1;min-height:0;"><span class="pg-preview-btn-label-sm">&nbsp;</span></div>
        </div>
      </div>`,
  };
}
