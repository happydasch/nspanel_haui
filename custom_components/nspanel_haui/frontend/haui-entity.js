/**
 * NSPanel HAUI - HAUIEntity JS representation.
 *
 * Clean, reusable helpers for Home Assistant entity IDs in the frontend.
 * Mirrors the Python ``HAUIEntity`` class (haui/abstract/entity.py) but
 * operates on plain strings since the frontend has no HA runtime access.
 */

import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { positionPickerDropdown, createDropdownKeyboardController } from './dom-helpers.js';

/** Override field names that can be set on any item config.
 *  Must match the Python HAUIItem config keys. */
export const ENTITY_OVERRIDE_FIELDS = [
  'name',
  'icon',
  'color',
  'value',
  'state',
  'popup_key',
  'service_data',
];

/* ── helper: collect domains from entity list ─────────────────────────── */

/** Extract unique domains from a list of entity IDs, sorted by count. */
function getDomains(entityIds) {
  const counts = {};
  for (const entityId of entityIds) {
    const dot = entityId.indexOf('.');
    if (dot > 0) {
      const d = entityId.slice(0, dot);
      counts[d] = (counts[d] || 0) + 1;
    }
  }
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([d]) => d);
}

/* ── entity picker field ───────────────────────────────────────────────── */

/** Entity lists per `hass.states` object, then per domain filter. */
const _entityListCache = new WeakMap();

/** Rows a picker's dropdown shows at once; a longer list is narrowed by typing. */
const ENTITY_MATCH_LIMIT = 100;

/**
 * The picker's entities and their domains. HA replaces `hass.states` on every
 * state change, so caching per states object lets all pickers rendered for one
 * hass share a single scan. The sorted list is built on first use: a render
 * needs only the domains, an open dropdown needs the entities.
 */
function entityListFor(states, domain) {
  let byDomain = _entityListCache.get(states);
  if (!byDomain) {
    byDomain = new Map();
    _entityListCache.set(states, byDomain);
  }
  const key = domain || '';
  if (!byDomain.has(key)) {
    const entityIds = Object.keys(states)
      .filter((entityId) => !domain || entityId.startsWith(`${domain}.`));
    let entities = null;
    byDomain.set(key, {
      domains: getDomains(entityIds),
      entities: () => (entities ??= entityIds
        .sort((a, b) => a.localeCompare(b))
        .map((entityId) => {
          const name = states[entityId]?.attributes?.friendly_name || entityId;
          return { entityId, name, search: `${entityId}\n${name}`.toLowerCase() };
        })),
    });
  }
  return byDomain.get(key);
}

/**
 * The entities a dropdown offers: those of `domain` ("__all": any) whose id or
 * name contains `query`, in list order and at most `limit`, with the number of
 * all matches.
 *
 * @param {Array<{entityId: string, name: string, search: string}>} entities
 * @param {string} query - lower-case fragment of an entity id or name
 * @param {string} [domain]
 * @param {number} [limit]
 * @returns {{ matches: Array<{entityId: string, name: string}>, total: number }}
 */
export function matchEntities(entities, query, domain = '__all', limit = ENTITY_MATCH_LIMIT) {
  const prefix = domain === '__all' ? '' : `${domain}.`;
  const matches = [];
  let total = 0;
  for (const entity of entities) {
    if (!entity.entityId.startsWith(prefix) || !entity.search.includes(query)) continue;
    total++;
    if (matches.length < limit) matches.push(entity);
  }
  return { matches, total };
}

/**
 * Replace the dropdown's rows with `matches`, and say how many more there are.
 *
 * Rows are built here rather than in the Lit template, like the icon picker's:
 * a row per entity in every picker is thousands of elements to create and to
 * compare on each render, and the dropdown has no Lit parts inside, so
 * replacing its children does not interfere with Lit's re-render.
 */
export function fillEntityDropdown(dropdown, { matches, total }) {
  const rows = matches.map((entity, index) => {
    const item = document.createElement('div');
    item.className = 'haui-entity-dropdown-item';
    item.id = `${dropdown.id}-opt-${index}`;
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', 'false');
    item.setAttribute('data-entity-id', entity.entityId);
    const name = document.createElement('div');
    name.className = 'haui-entity-friendly-name';
    name.textContent = entity.name;
    const entityId = document.createElement('div');
    entityId.className = 'haui-entity-id';
    entityId.textContent = entity.entityId;
    item.append(name, entityId);
    return item;
  });
  if (total > matches.length) {
    const more = document.createElement('div');
    more.className = 'haui-entity-dropdown-more';
    more.setAttribute('role', 'presentation');
    more.textContent = t('{count} more: type to narrow the list')
      .replace('{count}', String(total - matches.length));
    rows.push(more);
  }
  dropdown.replaceChildren(...rows);
}

export function renderEntityPicker({ id, value, label, hint, placeholder, hass, domain, onInput, onSelect }) {
  const entityList = entityListFor(hass?.states || {}, domain);
  const { domains } = entityList;
  const dropdownId = `${id}-dropdown`;

  const applyValue = (input, rawValue) => {
    const val = rawValue || "";
    if (input) input.value = val;
    if (onInput) onInput(val);
    if (onSelect) onSelect(val);
  };

  const eventValue = (event) =>
    event.detail?.value ?? event.target?.value ?? event.composedPath?.()[0]?.value ?? "";

  const updateTypedValue = (input, rawValue) => {
    const val = rawValue || "";
    if (onInput) onInput(val);
    showMatches(input, val);
  };

  const hideDropdown = (wrap) => {
    const dropdown = wrap?.querySelector(".haui-entity-dropdown");
    if (dropdown) {
      dropdown.hidden = true;
      dropdown.replaceChildren();
    }
    const input = wrap?.querySelector(".haui-entity-picker-input");
    if (input) {
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const showMatches = (input, rawValue = null) => {
    const wrap = input?.closest(".haui-entity-picker-wrap");
    const dropdown = wrap?.querySelector(".haui-entity-dropdown");
    if (!dropdown) return;
    // Only show the dropdown when the input has focus
    if (!wrap?._entityFocused) {
      dropdown.hidden = true;
      return;
    }
    const query = ((rawValue ?? input.value) || "").toLowerCase();
    const found = matchEntities(entityList.entities(), query, wrap._entityDomain || "__all");
    fillEntityDropdown(dropdown, found);
    const any = found.total > 0;
    dropdown.hidden = !any;
    // The combobox state changes without a re-render, so sync the ARIA state
    // on the live elements rather than binding it in the template.
    if (input) {
      input.setAttribute("aria-expanded", any ? "true" : "false");
      input.removeAttribute("aria-activedescendant");
    }
    if (any) positionPickerDropdown(dropdown, input);
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const setActiveDomain = (wrap, d) => {
    // Kept on the element, like the chips' highlight: a render while the
    // dropdown is open must not drop the chosen domain.
    if (wrap) wrap._entityDomain = d;
    // Update chip active states
    const chips = wrap?.querySelectorAll(".haui-domain-filter-chip");
    if (chips) {
      chips.forEach((chip) => {
        chip.classList.toggle("is-active", chip.getAttribute("data-domain") === d);
      });
    }
    const input = wrap?.querySelector(".haui-entity-picker-input");
    showMatches(input, "");
  };

  const picker = html`
    <div class="haui-entity-picker-wrap">
      <input
        id=${id}
        class="haui-entity-picker-input haui-input"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded="false"
        aria-autocomplete="list"
        aria-controls=${dropdownId}
        .value=${value || ""}
        placeholder=${placeholder || (domain ? `${domain}.…` : "")}
        autocomplete="off"
        @input=${(e) => {
          updateTypedValue(e.target, eventValue(e));
        }}
        @focus=${(e) => {
          const wrap = e.target.closest(".haui-entity-picker-wrap");
          if (wrap) {
            wrap._entityFocused = true;
            wrap._entityDomain = "__all";
          }
          const chips = wrap?.querySelectorAll(".haui-domain-filter-chip");
          if (chips) chips.forEach(c => c.classList.remove("is-active"));
          showMatches(e.target, eventValue(e));
        }}
        @blur=${(e) => {
          const wrap = e.target?.closest(".haui-entity-picker-wrap");
          if (wrap) wrap._entityFocused = false;
          setTimeout(() => hideDropdown(wrap), 80);
        }}
        @keydown=${createDropdownKeyboardController({
          getWrap: (e) => e.target.closest('.haui-entity-picker-wrap'),
          dropdownSelector: '.haui-entity-dropdown',
          itemSelector: '.haui-entity-dropdown-item',
          indexField: '_entityActiveIndex',
          onSelect: (visibleItems, idx, e) => {
            const entityId = visibleItems[idx].getAttribute('data-entity-id') || '';
            applyValue(e.target, entityId);
            hideDropdown(e.target.closest('.haui-entity-picker-wrap'));
          },
          onDismiss: (e) => hideDropdown(e.target.closest('.haui-entity-picker-wrap')),
        })}
      />
      <div class="haui-dropdown-filter-area">
        ${domains.length > 1 ? html`
          <div class="haui-domain-filter-bar">
            <button
              class="haui-domain-filter-chip is-active"
              data-domain="__all"
              @mousedown=${(e) => { e.preventDefault(); setActiveDomain(e.target.closest(".haui-entity-picker-wrap"), "__all"); }}
            >${t("All")}</button>
            ${domains.slice(0, 10).map(d => html`
              <button
                class="haui-domain-filter-chip"
                data-domain=${d}
                @mousedown=${(e) => { e.preventDefault(); setActiveDomain(e.target.closest(".haui-entity-picker-wrap"), d); }}
              >${d}</button>
            `)}
          </div>
        ` : ""}
      </div>
      <div
        class="haui-entity-dropdown"
        id=${dropdownId}
        role="listbox"
        aria-labelledby=${label ? `${id}-label` : nothing}
        hidden
        @mousedown=${(e) => {
          // One listener for every row: the rows are filled in by showMatches.
          e.preventDefault();
          const item = e.target.closest(".haui-entity-dropdown-item");
          if (!item) return;
          const wrap = item.closest(".haui-entity-picker-wrap");
          applyValue(wrap?.querySelector(".haui-entity-picker-input"), item.getAttribute("data-entity-id"));
          hideDropdown(wrap);
        }}
      ></div>
    </div>
  `;

  if (label || hint) {
    return html`
      <div class="haui-field">
        <label for=${id} id=${id}-label>${label || ""}</label>
        ${picker}
        ${hint ? html`<div class="haui-field-hint">${hint}</div>` : ""}
      </div>
    `;
  }

  return picker;
}
