/**
 * NSPanel HAUI - Panel preview: Timer.
 *
 * Device layout: MM:SS display (font:5 light), play/pause/stop buttons at bottom.
 */
import { html } from '../lit-import.js';

export function renderTimerPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:4px;align-items:center;justify-content:center;">
        <div class="pg-preview-temp-display" style="font-size:2.2em;">00:30</div>
        <div class="pg-preview-btn-row" style="gap:6px;">
          <div class="pg-preview-btn active"><ha-icon icon="mdi:play"></ha-icon></div>
          <div class="pg-preview-btn active"><ha-icon icon="mdi:pause"></ha-icon></div>
          <div class="pg-preview-btn active"><ha-icon icon="mdi:cancel"></ha-icon></div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:timer-off-outline', accent: true } },
  };
}
