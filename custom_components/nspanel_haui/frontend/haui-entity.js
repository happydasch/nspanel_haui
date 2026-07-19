/**
 * NSPanel HAUI - HAUIEntity JS representation.
 *
 * Clean, reusable helpers for Home Assistant entity IDs in the frontend.
 * Mirrors the Python ``HAUIEntity`` class (haui/abstract/entity.py) but
 * operates on plain strings since the frontend has no HA runtime access.
 */

import { html } from './lit-import.js';
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
function getDomains(entities) {
  const counts = {};
  for (const { entityId } of entities) {
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

export function renderEntityPicker(host, { id, value, label, hint, placeholder, hass, domain, onInput, onSelect }) {
  const allEntities = Object.entries(hass?.states || {})
    .filter(([entityId]) => !domain || entityId.startsWith(`${domain}.`))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([entityId, state]) => ({
      entityId,
      name: state?.attributes?.friendly_name || entityId,
    }));

  const domains = getDomains(allEntities);
  let activeDomain = '__all';

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
    const dropdown = wrap?.querySelector(".entity-dropdown");
    if (dropdown) dropdown.style.display = "none";
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const showMatches = (input, rawValue = null) => {
    const wrap = input?.closest(".entity-picker-wrap");
    const dropdown = wrap?.querySelector(".entity-dropdown");
    if (!dropdown) return;
    // Only show the dropdown when the input has focus
    if (!wrap?._entityFocused) {
      dropdown.style.display = "none";
      return;
    }
    const query = ((rawValue ?? input.value) || "").toLowerCase();
    const items = dropdown.querySelectorAll(".entity-dropdown-item");
    let any = false;
    items.forEach((item) => {
      const entityId = (item.getAttribute("data-entity-id") || "").toLowerCase();
      const name = (item.getAttribute("data-entity-name") || "").toLowerCase();
      const domainMatch = activeDomain === "__all" || entityId.startsWith(activeDomain + ".");
      const queryMatch = !query || entityId.includes(query) || name.includes(query);
      const match = domainMatch && queryMatch;
      item.style.display = match ? "" : "none";
      item.classList.remove("active");
      if (match) any = true;
    });
    dropdown.style.display = any ? "" : "none";
    if (any) positionPickerDropdown(dropdown, input);
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const setActiveDomain = (wrap, d) => {
    activeDomain = d;
    // Update chip active states
    const chips = wrap?.querySelectorAll(".domain-filter-chip");
    if (chips) {
      chips.forEach((chip) => {
        chip.classList.toggle("active", chip.getAttribute("data-domain") === d);
      });
    }
    const input = wrap?.querySelector(".entity-picker-input");
    showMatches(input, "");
  };

  const picker = html`
    <div class="entity-picker-wrap">
      <input
        id=${id}
        class="entity-picker-input native-input"
        .value=${value || ""}
        placeholder=${placeholder || (domain ? `${domain}.…` : "")}
        autocomplete="off"
        @input=${(e) => {
          updateTypedValue(e.target, eventValue(e));
        }}
        @focus=${(e) => {
          activeDomain = "__all";
          const wrap = e.target.closest(".entity-picker-wrap");
          if (wrap) wrap._entityFocused = true;
          const chips = wrap?.querySelectorAll(".domain-filter-chip");
          if (chips) chips.forEach(c => c.classList.remove("active"));
          showMatches(e.target, eventValue(e));
        }}
        @blur=${(e) => {
          const wrap = e.target?.closest(".entity-picker-wrap");
          if (wrap) wrap._entityFocused = false;
          setTimeout(() => hideDropdown(wrap), 80);
        }}
        @keydown=${createDropdownKeyboardController({
          getWrap: (e) => e.target.closest('.entity-picker-wrap'),
          dropdownSelector: '.entity-dropdown',
          itemSelector: '.entity-dropdown-item',
          indexField: '_entityActiveIndex',
          onSelect: (visibleItems, idx, e) => {
            const entityId = visibleItems[idx].getAttribute('data-entity-id') || '';
            applyValue(e.target, entityId);
            hideDropdown(e.target.closest('.entity-picker-wrap'));
          },
          onDismiss: (e) => hideDropdown(e.target.closest('.entity-picker-wrap')),
        })}
      />
      <div class="dropdown-filter-area">
        ${domains.length > 1 ? html`
          <div class="domain-filter-bar">
            <button
              class="domain-filter-chip active"
              data-domain="__all"
              @mousedown=${(e) => { e.preventDefault(); setActiveDomain(e.target.closest(".entity-picker-wrap"), "__all"); }}
            >${t("All")}</button>
            ${domains.slice(0, 10).map(d => html`
              <button
                class="domain-filter-chip"
                data-domain=${d}
                @mousedown=${(e) => { e.preventDefault(); setActiveDomain(e.target.closest(".entity-picker-wrap"), d); }}
              >${d}</button>
            `)}
          </div>
        ` : ""}
      </div>
      <div
        class="entity-dropdown"
        style="display:none;"
      >
        ${allEntities.map((entity) => html`
          <div
            class="entity-dropdown-item"
            data-entity-id=${entity.entityId}
            data-entity-name=${entity.name}
            @mousedown=${(e) => {
              e.preventDefault();
              const wrap = e.target.closest(".entity-picker-wrap");
              const input = wrap?.querySelector(".entity-picker-input");
              applyValue(input, entity.entityId);
              hideDropdown(wrap);
            }}
          >
            <div class="entity-friendly-name">${entity.name}</div>
            <div class="entity-id">${entity.entityId}</div>
          </div>
        `)}
      </div>
    </div>
  `;

  if (label || hint) {
    return html`
      <div class="form-group">
        <label for=${id}>${label || ""}</label>
        ${picker}
        ${hint ? html`<div class="field-hint">${hint}</div>` : ""}
      </div>
    `;
  }

  return picker;
}
