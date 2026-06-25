/**
 * NSPanel HAUI - Editor - Shared panel card chrome.
 *
 * Renders the visual chrome of a panel grid card: top row (icon, title, key,
 * badges, actions), simulated panel preview (with optional header bar), and
 * bottom row (description). Used by both user panel grid cards and system
 * panel grid cards.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';

/**
 * @param {Object} opts
 * @param {string} opts.icon                 - MDI icon name for the type icon (left of title)
 * @param {string} opts.title                - Primary title shown in top row & preview header
 * @param {string} [opts.titleFallback]      - Fallback markup when title is empty (e.g. type label)
 * @param {string} opts.key                  - Panel key shown in top row
 * @param {Array}  [opts.badges]             - Array of TemplateResult badges
 * @param {boolean} opts.hasHeader           - Whether the preview shows the simulated header bar
 * @param {Object} opts.preview              - { content, contentClass?, containerClass? }
 * @param {string} [opts.description]        - Subtitle text under the preview
 * @param {Function} [opts.onClick]          - Click handler for top-row and preview (omit for read-only)
 * @param {*} opts.actions                   - TemplateResult rendered in top-right action area
 */
export function renderCardChrome(opts) {
  const {
    icon,
    title,
    titleFallback,
    key,
    badges = [],
    hasHeader,
    headerButtons,
    preview,
    description,
    onClick,
    actions,
  } = opts;

  const containerExtra = preview?.containerClass ? ' ' + preview.containerClass : '';
  const contentExtra = preview?.contentClass ? ' ' + preview.contentClass : '';
  const previewClass = `pg-card-preview${hasHeader ? ' pg-card-preview--with-header' : ''}${containerExtra}`;
  const titleAttr = title || titleFallback || '';

  const titleContent = title
    ? title
    : (titleFallback
        ? html`<span class="pg-unnamed">${titleFallback}</span>`
        : '');

  // When a panel provides its own background CSS class (containerClass — a
  // gradient, system, or blank background), it uses its OWN visual identity.
  // We still apply both a fixed background (lighter than the real device
  // screen for preview readability) AND the device theme CSS variables so
  // text/icons render with light-on-dark colours regardless of HA's light/
  // dark mode.  Panels WITHOUT a containerClass get device theme colors
  // applied inline with no background override.
  const ownBg = !!preview?.containerClass;
  const dc = preview?.deviceColors || {};
  const containerStyle = ownBg
    ? 'background:#4a4a65;' + (preview?.deviceStyle || '')
    : (preview?.deviceStyle || '');
  const screenBg = ownBg
    ? ''
    : 'background:' + (dc.background || 'rgba(0,0,0,0.12)') + ';';

  return html`
    <div class="pg-card-top-row" @click=${onClick}>
      ${icon ? html`<ha-icon class="pg-card-type-icon" icon="${icon}"></ha-icon>` : ''}
      ${badges.length ? html`<div class="pg-card-badges">${badges}</div>` : ''}
      <span class="pg-card-title" title=${titleAttr}>${titleContent}</span>
      <span class="pg-card-key">${key || '-'}</span>
      ${actions ? html`<div class="pg-card-actions">${actions}</div>` : ''}
    </div>
    <div class=${previewClass} style="${containerStyle}" @click=${onClick}>
      ${hasHeader ? (() => {
        const btns = headerButtons || { left: ['', ''], right: ['', ''] };
        const lBtns = btns.left || ['', ''];
        const rBtns = btns.right || ['', ''];

        // Render a simulated header button icon.
        // Each value can be a plain icon string or an object { icon, accent? }.
        const _simBtn = (v) => {
          if (!v) return '';
          const icon = typeof v === 'string' ? v : v.icon;
          const isAccent = typeof v === 'object' && v.accent;
          return html`<ha-icon icon="${icon}" class="${isAccent ? 'icon-accent' : ''}"></ha-icon>`;
        };

        const dc = preview?.deviceColors || {};
        const headerBg = ownBg ? 'rgba(0,0,0,0.45)' : (dc.header_background || 'rgba(0,0,0,0.45)');
        const headerTextColor = ownBg ? '#fff' : (dc.header_text || '#fff');
        return html`
        <div class="pg-card-preview-header" style="background:${headerBg}">
          <div class="pg-sim-btn-group pg-sim-btn-group-left">
            <div class="pg-sim-btn">${_simBtn(lBtns[0])}</div>
            <div class="pg-sim-btn">${_simBtn(lBtns[1])}</div>
          </div>
          <span class="pg-sim-title" style="color:${headerTextColor}">${title || titleFallback || t('Panel')}</span>
          <div class="pg-sim-btn-group pg-sim-btn-group-right">
            <div class="pg-sim-btn">${_simBtn(rBtns[0])}</div>
            <div class="pg-sim-btn">${_simBtn(rBtns[1])}</div>
          </div>
        </div>`;
      })() : ''}
      <div class="pg-card-preview-screen" style="${screenBg}">
        <div class="pg-card-preview-content${contentExtra}">
          ${preview?.content}
        </div>
      </div>
    </div>
    <div class="pg-card-bottom-row">
      ${description
        ? html`<span class="pg-card-preview-desc">${description}</span>`
        : html`<span></span>`}
    </div>
  `;
}

/**
 * Keyboard handler that triggers a callback on Enter or Space.
 * Use as: @keydown=${onKeyActivate(() => doSomething())}
 */
export function onKeyActivate(cb) {
  return (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      cb(e);
    }
  };
}

/**
 * Render the more-actions trigger + dropdown panel used by both user and system
 * panel cards. Centralizes menu state on host._cardMenuKey so the outside-click
 * handler can close any open card menu uniformly.
 *
 * @param {LitElement} host       - editor component
 * @param {string}     menuKey    - unique string identifying this card's menu
 * @param {Function}   renderDropdown - called when open; receives onClose, returns TemplateResult
 * @returns {TemplateResult|''}   - empty when menuKey is falsy (no menu for this card)
 */
export function renderCardActions(host, menuKey, renderDropdown) {
  if (!menuKey) return '';
  const isOpen = host._cardMenuKey === menuKey;
  const toggle = () => {
    host._cardMenuKey = isOpen ? null : menuKey;
    host.requestUpdate();
  };
  const close = () => { host._cardMenuKey = null; host.requestUpdate(); };
  return html`
    <span
      title=${host._t('More')}
      class="pg-card-more ${isOpen ? 'active' : ''}"
      role="button"
      tabindex="0"
      @click=${(e) => { e.stopPropagation(); toggle(); }}
      @keydown=${onKeyActivate(toggle)}
    >
      <ha-icon icon="mdi:dots-vertical"></ha-icon>
    </span>
    ${isOpen
      ? html`<div class="pg-card-dropdown-wrap" @click=${(e) => e.stopPropagation()}>
          ${renderDropdown(close)}
        </div>`
      : ''}
  `;
}
