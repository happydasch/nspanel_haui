/**
 * NSPanel HAUI - Editor - Panel preview: Timer.
 */
import { html } from '../lit-import.js';

export function renderTimerPreview(_host, _panel, _pIdx, _pt) {
  return {
    content: html`
      <div class="pg-preview-full-col" style="gap:6px;align-items:center;justify-content:center;">
        <div class="pg-preview-temp-display">00:30</div>
        <div class="pg-preview-btn-row">
          <div class="pg-preview-btn"><ha-icon icon="mdi:play"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:pause"></ha-icon></div>
          <div class="pg-preview-btn"><ha-icon icon="mdi:cancel"></ha-icon></div>
        </div>
      </div>`,
    headerButtonOverrides: { rightSec: { icon: 'mdi:timer-off-outline', accent: true } },
  };
}
