/**
 * NSPanel HAUI - Editor - Panel preview: System About.
 */
import { html } from '../lit-import.js';

export function renderAboutPreview(_host, _panel, _pIdx, _pt) {
  return {
    containerClass: 'pg-preview-bg-system',
    content: html`
      <div class="pg-preview-full-col" style="gap:3px;padding:6px;">
        <div class="pg-preview-text-line" style="height:clamp(6px,2cqi,12px);width:85%;align-self:center;"></div>
        <div class="pg-preview-text-line" style="height:clamp(6px,2cqi,12px);width:75%;align-self:center;"></div>
        <div style="flex:1;min-height:6px;"></div>
        <div style="display:flex;flex-direction:column;gap:2px;width:60%;align-self:flex-end;">
          <div class="pg-preview-text-line" style="height:clamp(7px,2cqi,13px);width:85%;align-self:flex-end;background:rgba(255,255,255,0.14);"></div>
          <div class="pg-preview-text-line" style="height:clamp(5px,1.5cqi,10px);width:65%;align-self:flex-end;"></div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;margin-top:3px;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
          <div style="display:flex;gap:clamp(10px,3cqi,20px);width:100%;">
            <div class="pg-preview-text-line" style="flex:1;"></div>
            <div class="pg-preview-text-line" style="width:28%;"></div>
          </div>
        </div>
      </div>`,
  };
}
