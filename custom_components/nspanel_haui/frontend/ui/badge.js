import { html } from '../lit-import.js';

const TONES = new Set(['neutral', 'primary', 'success', 'warning', 'danger']);

export function badge(text, tone = 'neutral', className = '') {
  const safeTone = TONES.has(tone) ? tone : 'neutral';
  return html`<span class=${`haui-badge haui-badge-${safeTone} ${className}`.trim()}>${text}</span>`;
}

export function chip(text, { tone = 'neutral', iconName } = {}) {
  return html`<span class=${`haui-chip haui-chip-${TONES.has(tone) ? tone : 'neutral'}`}>
    ${iconName ? html`<ha-icon icon=${`mdi:${iconName}`} aria-hidden="true"></ha-icon>` : ''}${text}
  </span>`;
}

export function statusDot(state, label) {
  const tone = state === 'online' || state === true ? 'online'
    : state === 'stale' ? 'stale' : state === 'unknown' ? 'unknown' : 'offline';
  return html`<span class=${`haui-status-dot haui-status-dot-${tone}`} role="img" aria-label=${label}></span>`;
}
