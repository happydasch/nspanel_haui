// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { countBadge } from '../ui/badge.js';
import { segmented } from '../ui/segmented.js';
import { emptyState } from '../ui/empty-state.js';
import { icon } from '../ui/icon.js';

// One object per type: a preview frame replays its render again whenever it is
// handed a different panel object.
/** @type {Map<string, { type: string, key: string }>} */
const newPanels = new Map();
const newPanel = (type) => newPanels.get(type) || newPanels.set(type, { type, key: '' }).get(type);
// The same for each starter template's keyless panel.
/** @type {Map<string, any>} */
const starterPanels = new Map();
/** @param {{ key: string, panel: any }} starter */
const starterPanel = (starter) => {
  const cached = starterPanels.get(starter.key);
  if (cached?.source === starter.panel) return cached.panel;
  const panel = { ...starter.panel, key: '' };
  starterPanels.set(starter.key, { source: starter.panel, panel });
  return panel;
};

/**
 * The panels to copy, one group per device in the order they come.
 * @param {Array<{ device?: string, deviceLabel?: string }>} copies
 * @returns {Array<{ device: string, label: string, entries: any[] }>}
 */
function byDevice(copies) {
  /** @type {Map<string, { device: string, label: string, entries: any[] }>} */
  const groups = new Map();
  for (const entry of copies) {
    const device = entry.device || '';
    if (!groups.has(device)) groups.set(device, { device, label: entry.deviceLabel || device, entries: [] });
    groups.get(device).entries.push(entry);
  }
  return [...groups.values()];
}

/**
 * The matching panel types, one group per category, with grouping first and
 * the remaining groups in the order the hub lists them.
 * @param {any[]} matches
 * @returns {Array<{ key: string, label: string, icon: string, entries: any[] }>}
 */
function byCategory(matches) {
  /** @type {Map<string, { key: string, label: string, icon: string, entries: any[] }>} */
  const groups = new Map();
  for (const panelType of matches) {
    const { key, label, icon } = panelType.category;
    if (!groups.has(key)) groups.set(key, { key, label, icon, entries: [] });
    groups.get(key).entries.push(panelType);
  }
  const categories = [...groups.values()];
  const groupingIndex = categories.findIndex(({ key }) => key === 'grouping');
  if (groupingIndex > 0) categories.unshift(categories.splice(groupingIndex, 1)[0]);
  return categories;
}

/**
 * What a new panel can start from: a panel type with its defaults, a starter
 * template, a built-in popup the device does not extend yet, or a copy of a
 * panel the hub already has. All of them lead into the panel editor.
 *
 * The catalog keeps search and preview-size controls together above its
 * collapsible sections: one per panel category (grouping first, then the
 * remaining categories), then *Start from a template*, *Extend a popup* and
 * *Copy an existing panel*.
 * The search is a bare Home Assistant style field (no visible label, the
 * placeholder carries the name), and one line of intro text under it says
 * what the sections offer. Grouping starts open; the other headings alone fit
 * the sidebar. A search opens every section it looks into. The copies are
 * grouped by device inside their section.
 *
 * A panel type shows the hub's render of a new, still empty panel of that type
 * on the device (`preview`), so the list tells the page layouts apart; a popup
 * shows the device's built-in one (`preview(entry, true)`, rendered by key). A
 * starter template shows the hub's render of its panel, its empty slots filled
 * with example entities.
 *
 * @param {{ panelTypes: any[], query?: string, onQuery: (query: string) => void,
 *   onSelect: (typeKey: string) => void, compactPreviews?: boolean,
 *   onPreviewSize?: (compact: boolean) => void,
 *   preview?: ((panel: { type: string, key: string }, byKey?: boolean) => unknown)|null,
 *   portrait?: boolean,
 *   popups?: Array<{ key: string, type: string, label?: string }>,
 *   onSelectPopup?: (entry: any) => void,
 *   copies?: Array<{ id: string, device?: string, deviceLabel?: string, label: string,
 *     detail: string, icon?: string, panel: any }>,
 *   onSelectCopy?: (panel: any) => void,
 *   starters?: Array<{ key: string, label: string, description: string, icon: string, panel: any }>,
 *   onSelectStarter?: (panel: any) => void }} options
 */
export function panelCatalog({
  panelTypes, query = '', onQuery, onSelect, copies = [], onSelectCopy = () => {},
  starters = [], onSelectStarter = () => {},
  popups = [], onSelectPopup = () => {}, preview = null, portrait = false,
  compactPreviews = false, onPreviewSize,
}) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const found = (text) => text.toLocaleLowerCase().includes(normalizedQuery);
  const matches = panelTypes.filter((panelType) => found(
    `${panelType.label} ${panelType.description || ''} ${panelType.category.label}`,
  ));
  const copyMatches = copies.filter((copy) => found(
    `${copy.label} ${copy.detail} ${copy.deviceLabel || ''}`,
  ));
  const starterMatches = starters.filter((starter) => found(`${starter.label} ${starter.description}`));
  const defaults = popups.filter((entry) => found(`${entry.label || ''} ${entry.key}`));
  const thumb = (panel, byKey = false) => (preview
    ? html`<span class=${`haui-panel-catalog-preview ${portrait ? 'is-portrait' : ''}`.trim()}
      aria-hidden="true">${preview(panel, byKey)}</span>`
    : nothing);
  /** @param {string} key @param {string} iconName @param {string} label @param {string} detail
   *  @param {() => void} onClick @param {unknown} [thumb] */
  const option = (key, iconName, label, detail, onClick, thumb = nothing) => html`<button type="button"
    class="haui-panel-catalog-option" role="listitem" data-option=${key}
    ?data-preview=${thumb !== nothing} @click=${onClick}>
    ${thumb === nothing ? (iconName ? icon(iconName) : html`<span></span>`) : thumb}
    <span><strong>${label}</strong>${detail ? html`<span>${detail}</span>` : nothing}</span>
    ${icon('chevronRight')}
  </button>`;
  /**
   * One collapsible catalog section: its heading row first, the content folded
   * below. A search looks into every section, so it opens them.
   * @param {string} key @param {string} iconName @param {string} label
   * @param {number} count @param {unknown} body
   */
  const section = (key, iconName, label, count, body) => html`<details class="haui-panel-catalog-section"
    data-section=${key} ?open=${normalizedQuery !== '' || key === 'grouping'}>
    <summary>
      ${icon(iconName)}
      <span>${label}</span>
      ${countBadge(count)}
      ${icon('chevronRight', 'haui-panel-catalog-chevron')}
    </summary>
    <div class="haui-panel-catalog-content">${body}</div>
  </details>`;
  const list = (entries, render) => html`<div class="haui-panel-catalog-list" role="list">
    ${entries.map(render)}
  </div>`;
  return html`<section class=${`haui-panel-catalog ${compactPreviews ? 'is-compact-previews' : ''}`.trim()}
    aria-label=${t('Add panel')}>
    <div class="haui-panel-catalog-controls">
      <div class="haui-panel-catalog-controls-row">
        <div class="haui-panel-catalog-search">
          <span class="haui-panel-catalog-search-field">
            ${icon('search')}
            <input type="search" aria-label=${t('Search panels')} placeholder=${t('Search panels')}
              .value=${query} @input=${(event) => onQuery(event.currentTarget.value)}>
          </span>
        </div>
        ${preview ? html`<div class="haui-panel-catalog-layout">
          ${segmented({
            label: t('Preview layout'),
            value: compactPreviews ? 'compact' : 'large',
            options: [
              { value: 'large', label: t('Large'), icon: 'view-dashboard-outline' },
              { value: 'compact', label: t('Compact'), icon: 'view-agenda-outline' },
            ],
            onSelect: (value) => onPreviewSize?.(value === 'compact'),
          })}
        </div>` : nothing}
      </div>
    </div>
    <p class="haui-config-section-intro">${t('Start from a panel type below, extend a built-in popup, or copy a panel this hub already has.')}</p>
    ${matches.length ? byCategory(matches).map((group) => section(
      group.key, group.icon, group.label, group.entries.length,
      list(group.entries, (panelType) => option(
        panelType.type_key, panelType.icon, panelType.label, panelType.description,
        () => onSelect(panelType.type_key),
        thumb(newPanel(panelType.type_key)),
      )),
    )) : copyMatches.length || defaults.length || starterMatches.length ? nothing
      : emptyState({ message: t('No panels match this search.'), iconName: null, className: 'haui-empty-state-compact' })}
    ${starterMatches.length ? section('starters', 'template', t('Start from a template'), starterMatches.length, html`
      <p class="haui-panel-catalog-hint">${t('A ready-made panel; choose the entities it marks, then save.')}</p>
      ${list(starterMatches, (starter) => option(
        starter.key, starter.icon, starter.label, starter.description,
        () => onSelectStarter(starter.panel), thumb(starterPanel(starter)),
      ))}`) : nothing}
    ${defaults.length ? section('popups', 'card-outline', t('Extend a popup'), defaults.length, html`
      <p class="haui-panel-catalog-hint">${t('Start from a built-in popup; your changes are saved on top of it for this device.')}</p>
      ${list(defaults, (entry) => option(
        entry.key, 'card-outline', entry.label || entry.key, entry.key,
        () => onSelectPopup(entry), thumb(entry, true),
      ))}`) : nothing}
    ${copyMatches.length ? section('copies', 'content-copy', t('Copy an existing panel'), copyMatches.length, html`
      <p class="haui-panel-catalog-hint">${t('Start from a panel this hub already has; its options and items are copied.')}</p>
      ${byDevice(copyMatches).map((group) => html`<details class="haui-panel-catalog-group"
        data-device=${group.device} ?open=${normalizedQuery !== ''}>
        <summary>
          ${icon('tablet-dashboard')}
          <span>${group.label}</span>
          ${countBadge(group.entries.length)}
          ${icon('chevronRight', 'haui-panel-catalog-chevron')}
        </summary>
        <div class="haui-panel-catalog-content">${list(group.entries, (copy) => option(
          copy.id, copy.icon || 'content-copy', copy.label, copy.detail,
          () => onSelectCopy(copy.panel),
        ))}</div>
      </details>`)}`) : nothing}
  </section>`;
}
