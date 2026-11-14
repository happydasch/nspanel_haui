import { html, nothing } from '../lit-import.js';

const TONES = new Set(['neutral', 'primary', 'success', 'warning', 'danger']);

export function badge(text, tone = 'neutral', className = '') {
  const safeTone = TONES.has(tone) ? tone : 'neutral';
  return html`<span class=${`haui-badge haui-badge-${safeTone} ${className}`.trim()}>${text}</span>`;
}

/**
 * The number beside a label: a section heading, a folded section, a segment or
 * a filter. `title` says what is counted when the label alone does not.
 *
 * @param {number} count
 * @param {{ tone?: string, title?: string }} [options]
 */
export function countBadge(count, { tone = 'neutral', title = '' } = {}) {
  const safeTone = TONES.has(tone) ? tone : 'neutral';
  return html`<span class=${`haui-badge haui-badge-${safeTone} haui-badge-count`}
    title=${title || nothing}>${count}</span>`;
}

export function statusDot(state, label) {
  const tone = state === 'online' || state === true ? 'online'
    : state === 'stale' ? 'stale' : state === 'unknown' ? 'unknown' : 'offline';
  return html`<span class=${`haui-status-dot haui-status-dot-${tone}`} role="img" aria-label=${label}></span>`;
}
