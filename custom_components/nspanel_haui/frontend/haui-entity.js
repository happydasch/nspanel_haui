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

/** Show the entity dropdown and attach a click-outside listener. */
function _openDropdown(wrap) {
  const dropdown = wrap?.querySelector(".entity-dropdown");
  if (!dropdown) return;
  const items = dropdown.querySelectorAll(".entity-dropdown-item");
  items.forEach((item) => { item.style.display = ""; });
  dropdown.style.display = items.length ? "" : "none";
  if (items.length === 0) return;

  // Close on click outside — install once on the document
  if (wrap._outsideHandler) return;
  wrap._outsideHandler = (ev) => {
    if (!wrap || wrap.contains(ev.target)) return;
    _hideDropdown(wrap);
  };
  // Use mousedown so it fires before click/ focus events on other elements
  document.addEventListener("mousedown", wrap._outsideHandler);
}

/** Hide the entity dropdown and detach the outside listener. */
function _hideDropdown(wrap) {
  const dropdown = wrap?.querySelector(".entity-dropdown");
  if (dropdown) dropdown.style.display = "none";
  if (wrap) wrap._activeIndex = -1;
  if (wrap?._outsideHandler) {
    document.removeEventListener("mousedown", wrap._outsideHandler);
    delete wrap._outsideHandler;
  }
}

/**
 * Render an entity picker: text input with a custom autocomplete dropdown
 * that searches both entity_id and friendly_name (case-insensitive).
 *
 * Dropdown filtering is done via DOM (no full re-render on keystroke) to
 * keep the input responsive.  The caller reads the value from the DOM on
 * save (see `_saveItemEdit`), so `onInput` is present for backwards
 * compatibility only.
 *
 * @param {string} id          - DOM id for the text field
 * @param {string} value       - Current entity_id value
 * @param {string} [label]     - Field label
 * @param {string} [hint]      - Optional hint text
 * @param {string} [placeholder]
 * @param {object} hass        - HA connection object (needs hass.states)
 * @param {string} [domain]    - If set, only show entities in this domain
 * @param {Function} [onInput] - Unused (kept for API compat); value read from DOM on save
 */
export function renderEntityPicker(host, { id, value, label, hint, placeholder, hass, domain, onInput }) {
  const allEntities = Object.entries(hass?.states || {})
    .filter(([eid]) => (domain ? eid.startsWith(domain + ".") : true))
    .map(([eid, s]) => ({
      entity_id: eid,
      friendly_name: s.attributes?.friendly_name || eid,
    }))
    .sort((a, b) => a.entity_id.localeCompare(b.entity_id));

  const picker = html`
    <div class="entity-picker-wrap" style="position:relative;">
      <ha-input
        id=${id}
        class="entity-picker-input"
        .value=${String(value != null ? value : "")}
        placeholder=${placeholder || ""}
        style="width:100%"
        @input=${(e) => {
          const val = (e.target.value || "").toLowerCase();
          const wrap = e.target.closest(".entity-picker-wrap");
          const dropdown = wrap?.querySelector(".entity-dropdown");
          if (!dropdown) return;
          const items = dropdown.querySelectorAll(".entity-dropdown-item");
          let any = false;
          items.forEach((item) => {
            const eid = (item.getAttribute("data-entity-id") || "").toLowerCase();
            const fname = (item.getAttribute("data-friendly-name") || "").toLowerCase();
            const match = !val || eid.includes(val) || fname.includes(val);
            item.style.display = match ? "" : "none";
            if (match) any = true;
          });
          dropdown.style.display = any ? "" : "none";
          // Do NOT call onInput here – DOM-based filtering avoids re-render flicker.
        }}
        @focus=${(e) => _openDropdown(e.target.closest(".entity-picker-wrap"))}
        @blur=${(e) => {
          // Short delay to let a mousedown on a dropdown item fire first
          // (items call preventDefault to block blur on mousedown, but some
          //  browsers may still fire blur — the delay catches that race.)
          const wrap = e.target?.closest(".entity-picker-wrap");
          setTimeout(() => { if (wrap) _hideDropdown(wrap); }, 80);
        }}
        @keydown=${(e) => {
          const wrap = e.target.closest(".entity-picker-wrap");
          const dropdown = wrap?.querySelector(".entity-dropdown");
          if (!dropdown || dropdown.style.display === "none") return;

          const visibleItems = [...dropdown.querySelectorAll(".entity-dropdown-item")]
            .filter((el) => el.style.display !== "none");
          if (!visibleItems.length) return;

          let idx = wrap._activeIndex != null ? wrap._activeIndex : -1;

          if (e.key === "ArrowDown") {
            e.preventDefault();
            idx = Math.min(idx + 1, visibleItems.length - 1);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            idx = Math.max(idx - 1, 0);
          } else if (e.key === "Enter") {
            if (idx >= 0) {
              e.preventDefault();
              _selectEntity(wrap, visibleItems[idx]);
            }
            return;
          } else if (e.key === "Escape") {
            e.preventDefault();
            _hideDropdown(wrap);
            return;
          } else {
            return;
          }

          wrap._activeIndex = idx;
          dropdown.querySelectorAll(".entity-dropdown-item").forEach((item, i) => {
            item.classList.toggle("active", i === idx);
          });
          if (visibleItems[idx]) {
            visibleItems[idx].scrollIntoView({ block: "nearest" });
          }
        }}
      ></ha-input>

      <div class="entity-dropdown"
        style="display:none; position:absolute; z-index:10; left:0; right:0; max-height:200px; overflow-y:auto; border:1px solid var(--divider-color,#ddd); border-radius:4px; background:var(--card-background-color,#fff); margin-top:2px;">
        ${allEntities.map((ent) => html`
          <div class="entity-dropdown-item"
            data-entity-id="${ent.entity_id}"
            data-friendly-name="${ent.friendly_name}"
            @mousedown=${(e) => {
              e.preventDefault();
              _selectEntity(
                e.target.closest(".entity-picker-wrap"),
                e.currentTarget
              );
            }}
            style="cursor:pointer; padding:6px 10px; display:flex; flex-direction:column; gap:2px;"
          >
            <span class="entity-friendly-name" style="font-size:0.95em;">${ent.friendly_name}</span>
            <span class="entity-id" style="font-size:0.8em; opacity:0.7;">${ent.entity_id}</span>
          </div>
        `)}
      </div>
    </div>
  `;

  if (label || hint) {
    return html`
      <div class="form-group">
        <label for=${id}>
          ${label || ""}
          ${hint ? html`<span class="hint">${hint}</span>` : ""}
        </label>
        ${picker}
      </div>
    `;
  }

  return picker;
}

/** Internal: set the input value from a selected dropdown item. */
function _selectEntity(wrap, item) {
  const tf = wrap?.querySelector(".entity-picker-input");
  const eid = item.getAttribute("data-entity-id") || "";
  if (tf) tf.value = eid;
  _hideDropdown(wrap);
  // Do NOT call host.requestUpdate here — it would re-render with the
  // original `value` prop, overwriting the just-set DOM value.  The
  // caller reads the value from the DOM on save (_saveItemEdit).
}
