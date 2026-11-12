// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';

// One object per type: a preview frame replays its render again whenever it is
// handed a different panel object.
/** @type {Map<string, { type: string, key: string }>} */
const newPanels = new Map();
const newPanel = (type) => newPanels.get(type) || newPanels.set(type, { type, key: '' }).get(type);

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
 * What a new panel can start from: a panel type with its defaults, a built-in
 * popup the device does not extend yet, or a copy of a panel the hub already
 * has. All of them lead into the panel editor.
 *
 * The catalog is a stack of collapsible sections, each led by its heading row:
 * one per panel category (grouping first, then the remaining categories), then
 * *Extend a popup* and *Copy an existing panel*. Grouping starts open; the
 * other headings alone fit the sidebar. A search opens every section it looks
 * into. The copies are grouped by device inside their section.
 *
 * A panel type shows the hub's render of a new, still empty panel of that type
 * on the device (`preview`), so the list tells the page layouts apart; a popup
 * shows the device's built-in one (`preview(entry, true)`, rendered by key).
 *
 * @param {{ panelTypes: any[], query?: string, onQuery: (query: string) => void,
 *   onSelect: (typeKey: string) => void,
 *   preview?: ((panel: { type: string, key: string }, byKey?: boolean) => unknown)|null,
 *   portrait?: boolean,
 *   popups?: Array<{ key: string, type: string, label?: string }>,
 *   onSelectPopup?: (entry: any) => void,
 *   templates?: Array<{ id: string, device?: string, deviceLabel?: string, label: string,
 *     detail: string, icon?: string, panel: any }>,
 *   onSelectTemplate?: (panel: any) => void }} options
 */
export function panelCatalog({
  panelTypes, query = '', onQuery, onSelect, templates = [], onSelectTemplate = () => {},
  popups = [], onSelectPopup = () => {}, preview = null, portrait = false,
}) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const found = (text) => text.toLocaleLowerCase().includes(normalizedQuery);
  const matches = panelTypes.filter((panelType) => found(
    `${panelType.label} ${panelType.description || ''} ${panelType.category.label}`,
  ));
  const copies = templates.filter((template) => found(
    `${template.label} ${template.detail} ${template.deviceLabel || ''}`,
  ));
  const defaults = popups.filter((entry) => found(`${entry.label || ''} ${entry.key}`));
  const thumb = (panel, byKey = false) => (preview
    ? html`<span class=${`haui-panel-catalog-preview ${portrait ? 'portrait' : ''}`.trim()}
      aria-hidden="true">${preview(panel, byKey)}</span>`
    : nothing);
  /** @param {string} key @param {string} icon @param {string} label @param {string} detail
   *  @param {() => void} onClick @param {unknown} [thumb] */
  const option = (key, icon, label, detail, onClick, thumb = nothing) => html`<button type="button"
    class="haui-panel-catalog-option" role="listitem" data-option=${key}
    ?data-preview=${thumb !== nothing} @click=${onClick}>
    ${thumb === nothing ? (icon ? html`<ha-icon icon=${icon}></ha-icon>` : html`<span></span>`) : thumb}
    <span><strong>${label}</strong>${detail ? html`<span>${detail}</span>` : nothing}</span>
    <ha-icon icon="mdi:chevron-right"></ha-icon>
  </button>`;
  /**
   * One collapsible catalog section: its heading row first, the content folded
   * below. A search looks into every section, so it opens them.
   * @param {string} key @param {string} icon @param {string} label
   * @param {number} count @param {unknown} body
   */
  const section = (key, icon, label, count, body) => html`<details class="haui-panel-catalog-section"
    data-section=${key} ?open=${normalizedQuery !== '' || key === 'grouping'}>
    <summary>
      <ha-icon icon=${icon}></ha-icon>
      <span>${label}</span>
      <span class="haui-panel-catalog-count">${count}</span>
      <ha-icon class="haui-panel-catalog-chevron" icon="mdi:chevron-right"></ha-icon>
    </summary>
    <div class="haui-panel-catalog-content">${body}</div>
  </details>`;
  const list = (entries, render) => html`<div class="haui-panel-catalog-list" role="list">
    ${entries.map(render)}
  </div>`;
  return html`<section class="haui-panel-catalog" aria-label=${t('Add panel')}>
    <p class="haui-panel-catalog-hint">${t('Choose a panel type to configure.')}</p>
    <label class="haui-panel-catalog-search">
      <span>${t('Search panel types')}</span>
      <input type="search" .value=${query} @input=${(event) => onQuery(event.currentTarget.value)}>
    </label>
    ${matches.length ? byCategory(matches).map((group) => section(
      group.key, group.icon, group.label, group.entries.length,
      list(group.entries, (panelType) => option(
        panelType.type_key, panelType.icon, panelType.label, panelType.description,
        () => onSelect(panelType.type_key),
        thumb(newPanel(panelType.type_key)),
      )),
    )) : copies.length || defaults.length ? nothing
      : html`<p class="haui-panel-catalog-empty">${t('No panel types match this search.')}</p>`}
    ${defaults.length ? section('popups', 'mdi:card-outline', t('Extend a popup'), defaults.length, html`
      <p class="haui-panel-catalog-hint">${t('Start from a built-in popup; your changes are saved on top of it for this device.')}</p>
      ${list(defaults, (entry) => option(
        entry.key, 'mdi:card-outline', entry.label || entry.key, entry.key,
        () => onSelectPopup(entry), thumb(entry, true),
      ))}`) : nothing}
    ${copies.length ? section('copies', 'mdi:content-copy', t('Copy an existing panel'), copies.length, html`
      <p class="haui-panel-catalog-hint">${t('Start from a panel this hub already has; its options and items are copied.')}</p>
      ${byDevice(copies).map((group) => html`<details class="haui-panel-catalog-group"
        data-device=${group.device} ?open=${normalizedQuery !== ''}>
        <summary>
          <ha-icon icon="mdi:tablet-dashboard"></ha-icon>
          <span>${group.label}</span>
          <span class="haui-panel-catalog-count">${group.entries.length}</span>
          <ha-icon class="haui-panel-catalog-chevron" icon="mdi:chevron-right"></ha-icon>
        </summary>
        <div class="haui-panel-catalog-content">${list(group.entries, (template) => option(
          template.id, template.icon || 'mdi:content-copy', template.label, template.detail,
          () => onSelectTemplate(template.panel),
        ))}</div>
      </details>`)}`) : nothing}
  </section>`;
}
