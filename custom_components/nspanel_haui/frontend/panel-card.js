/**
 * NSPanel HAUI - Shared panel card chrome.
 *
 * Renders the visual chrome of a panel grid card: top row (icon, title, key,
 * badges, actions), the panel preview (the hub's render in the Nextion
 * simulator, which draws the page's own title bar), and bottom row
 * (description). Used by both user panel grid cards and system panel grid
 * cards.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';

/**
 * @param {Object} opts
 * @param {string} opts.icon                 - MDI icon name for the type icon (left of title)
 * @param {string} opts.title                - Primary title shown in the top row
 * @param {string} [opts.titleFallback]      - Fallback markup when title is empty (e.g. type label)
 * @param {string} opts.key                  - Panel key shown in top row
 * @param {Array}  [opts.badges]             - Array of TemplateResult badges
 * @param {*} opts.preview                   - TemplateResult of the preview (`renderPanelPreview`)
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
    preview,
    description,
    onClick,
    actions,
  } = opts;

  const titleAttr = title || titleFallback || '';

  const titleContent = title
    ? title
    : (titleFallback
        ? html`<span class="pg-unnamed">${titleFallback}</span>`
        : '');

  return html`
    <div class="pg-card-top-row" @click=${onClick}>
      ${icon ? html`<ha-icon class="pg-card-type-icon" icon="${icon}"></ha-icon>` : ''}
      ${badges.length ? html`<div class="pg-card-badges">${badges}</div>` : ''}
      <span class="pg-card-title" title=${titleAttr}>${titleContent}</span>
      <span class="pg-card-key" title=${key || ''}>${key || '-'}</span>
      ${actions ? html`<div class="pg-card-actions">${actions}</div>` : ''}
    </div>
    <div class="pg-card-preview" @click=${onClick}>${preview}</div>
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
function onKeyActivate(cb) {
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
      title=${t('More')}
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
