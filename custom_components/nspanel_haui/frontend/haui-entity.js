/**
 * NSPanel HAUI - Editor - HAUIEntity JS representation.
 *
 * Clean, reusable helpers for Home Assistant entity IDs in the frontend.
 * Mirrors the Python ``HAUIEntity`` class (haui/abstract/entity.py) but
 * operates on plain strings since the frontend has no HA runtime access.
 */

import { html } from './lit-import.js';

/** Override field names that can be set on any item config.
 *  Must match the Python HAUIItem config keys. */
export const ENTITY_OVERRIDE_FIELDS = [
  'name',
  'icon',
  'color',
  'value',
  'state',
  'popup_key',
];

/* ── entity picker field ───────────────────────────────────────────────── */

export function renderEntityPicker(host, { id, value, label, hint, placeholder, hass, domain, onInput, onSelect }) {
  const entities = Object.entries(hass?.states || {})
    .filter(([entityId]) => !domain || entityId.startsWith(`${domain}.`))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([entityId, state]) => ({
      entityId,
      name: state?.attributes?.friendly_name || entityId,
    }));

  const applyValue = (input, rawValue) => {
    const val = rawValue || "";
    if (input) input.value = val;
    if (onInput) onInput(val);
    if (onSelect) onSelect(val);
  };

  const updateTypedValue = (input, rawValue) => {
    const val = rawValue || "";
    if (onInput) onInput(val);
    showMatches(input, val);
  };

  const eventValue = (event) =>
    event.detail?.value ?? event.target?.value ?? event.composedPath?.()[0]?.value ?? "";

  const hideDropdown = (wrap) => {
    const dropdown = wrap?.querySelector(".entity-dropdown");
    if (dropdown) dropdown.style.display = "none";
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const showMatches = (input, rawValue = null) => {
    const wrap = input?.closest(".entity-picker-wrap");
    const dropdown = wrap?.querySelector(".entity-dropdown");
    if (!dropdown) return;
    const query = ((rawValue ?? input.value) || "").toLowerCase();
    const items = dropdown.querySelectorAll(".entity-dropdown-item");
    let any = false;
    items.forEach((item) => {
      const entityId = (item.getAttribute("data-entity-id") || "").toLowerCase();
      const name = (item.getAttribute("data-entity-name") || "").toLowerCase();
      const match = !query || entityId.includes(query) || name.includes(query);
      item.style.display = match ? "" : "none";
      item.classList.remove("active");
      if (match) any = true;
    });
    dropdown.style.display = any ? "" : "none";
    if (wrap) wrap._entityActiveIndex = -1;
  };

  const picker = html`
    <div class="entity-picker-wrap" style="position:relative;">
      <ha-input
        id=${id}
        class="entity-picker-input"
        .value=${value || ""}
        placeholder=${placeholder || (domain ? `${domain}.…` : "")}
        autocomplete="off"
        @input=${(e) => {
          updateTypedValue(e.target, eventValue(e));
        }}
        @value-changed=${(e) => {
          updateTypedValue(e.target, eventValue(e));
        }}
        @focus=${(e) => showMatches(e.target, eventValue(e))}
        @blur=${(e) => {
          const wrap = e.target?.closest(".entity-picker-wrap");
          setTimeout(() => hideDropdown(wrap), 80);
        }}
        @keydown=${(e) => {
          const wrap = e.target.closest(".entity-picker-wrap");
          const dropdown = wrap?.querySelector(".entity-dropdown");
          if (!dropdown || dropdown.style.display === "none") return;

          const visibleItems = [...dropdown.querySelectorAll(".entity-dropdown-item")]
            .filter((el) => el.style.display !== "none");
          if (!visibleItems.length) return;

          let idx = wrap._entityActiveIndex != null ? wrap._entityActiveIndex : -1;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            idx = Math.min(idx + 1, visibleItems.length - 1);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            idx = Math.max(idx - 1, 0);
          } else if (e.key === "Enter") {
            if (idx >= 0) {
              e.preventDefault();
              const entityId = visibleItems[idx].getAttribute("data-entity-id") || "";
              applyValue(e.target, entityId);
              hideDropdown(wrap);
            }
            return;
          } else if (e.key === "Escape") {
            e.preventDefault();
            hideDropdown(wrap);
            return;
          } else {
            return;
          }

          wrap._entityActiveIndex = idx;
          dropdown.querySelectorAll(".entity-dropdown-item").forEach((item) => {
            item.classList.toggle("active", item === visibleItems[idx]);
          });
          visibleItems[idx]?.scrollIntoView({ block: "nearest" });
        }}
      ></ha-input>
      <div
        class="entity-dropdown"
        style="display:none; position:absolute; z-index:10; left:0; right:0; max-height:220px; overflow-y:auto; border:1px solid var(--divider-color,#ddd); border-radius:4px; background:var(--card-background-color,#fff); margin-top:2px;"
      >
        ${entities.map((entity) => html`
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
            style="cursor:pointer; padding:6px 10px;"
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
