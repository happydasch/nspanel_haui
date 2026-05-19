/**
 * NSPanel HAUI - Editor - HAUIItem JS representation.
 *
 * Clean, reusable helpers for item configs in the frontend.
 * Mirrors the Python ``HAUIItem`` class (haui/abstract/item.py) but
 * operates on plain config objects since the frontend has no HA runtime access.
 *
 * An item config looks like:
 *   { item: "light.kitchen", name: "Kitchen", icon: "mdi:lamp", ... }
 *
 * The ``item`` field can be:
 *   - An entity ID string   → "light.kitchen"
 *   - An internal type      → "text:Hello", "navigate:my_panel", "action:light/turn_on"
 *   - null / undefined      → skip
 *   - ""                    → entity type, no entity chosen yet
 */

import { html } from './lit-import.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';

/** Item type constants (match Python INTERNAL_ITEM_TYPE). */
export const ITEM_TYPE = {
  ENTITY_ID: 'entity_id',
  SKIP:       'skip',
  TEXT:       'text',
  NAVIGATE:   'navigate',
  ACTION:     'action',
};

/** All known item type keys. */
export const ALL_ITEM_TYPES = Object.values(ITEM_TYPE);

/** Labels and placeholders for each item type (single source of truth). */
export const ITEM_LABELS = {
  entity_id: { label: "Entity", placeholder: "light.bedroom" },
  skip:      { label: "", placeholder: "No value needed" },
  text:      { label: "Display Text", placeholder: "Hello, World!" },
  navigate:  { label: "Target Panel", placeholder: "grid_0" },
  action:    { label: "Service", placeholder: "light/turn_on" },
};

/** MDI icon per item type — used as fallback when no override icon set. */
export const ITEM_TYPE_ICONS = {
  entity_id: 'mdi:home-assistant',
  skip:      'mdi:minus-circle-outline',
  text:      'mdi:format-text',
  navigate:  'mdi:arrow-right-circle-outline',
  action:    'mdi:flash',
};

/** Short type label shown in row header. */
export const ITEM_TYPE_SHORT = {
  entity_id: 'Entity',
  skip:      'Skip',
  text:      'Text',
  navigate:  'Navigate',
  action:    'Action',
};

/** Prefix markers for each internal item type (for string encoding). */
const INTERNAL_PREFIX = {
  [ITEM_TYPE.TEXT]:     'text:',
  [ITEM_TYPE.NAVIGATE]: 'navigate:',
  [ITEM_TYPE.ACTION]:   'action:',
};

const PREFIX_LENGTH = {
  [ITEM_TYPE.TEXT]:     5,
  [ITEM_TYPE.NAVIGATE]: 9,
  [ITEM_TYPE.ACTION]:   7,
};

/* ── type detection ─────────────────────────────────────────────────────── */

/**
 * Detect the item type from a raw ``item`` field value.
 * @param {string|null|undefined} raw - the config's ``item`` value
 * @returns {string} one of ITEM_TYPE constants
 */
export function detectItemType(raw) {
  if (raw === null || raw === undefined) return ITEM_TYPE.SKIP;
  // Empty string '' means ENTITY_ID with no entity chosen yet — the type is
  // known even though no value has been filled in.
  if (typeof raw === 'string') {
    if (raw.startsWith(INTERNAL_PREFIX.text))      return ITEM_TYPE.TEXT;
    if (raw.startsWith(INTERNAL_PREFIX.navigate))  return ITEM_TYPE.NAVIGATE;
    if (raw.startsWith(INTERNAL_PREFIX.action))    return ITEM_TYPE.ACTION;
  }
  return ITEM_TYPE.ENTITY_ID;
}

/* ── value encoding / decoding ──────────────────────────────────────────── */

/**
 * Extract the value portion from a raw item string for a given type.
 * Strips the internal prefix for text/navigate/action; returns entity ID as-is.
 * Returns empty string when the raw value doesn't match the expected type.
 * @param {string|null|undefined} raw - the config's ``item`` value
 * @param {string} type - one of ITEM_TYPE constants
 * @returns {string} the decoded value (empty string for skip or mismatch)
 */
export function parseItemValue(raw, type) {
  if (raw === null || raw === undefined) return '';
  if (type === ITEM_TYPE.SKIP) return '';
  // Internal type: raw must start with the matching prefix
  if (PREFIX_LENGTH[type]) {
    return (typeof raw === 'string' && raw.startsWith(INTERNAL_PREFIX[type]))
      ? raw.slice(PREFIX_LENGTH[type])
      : '';
  }
  // Entity ID: must NOT be an internal-typed value
  if (type === ITEM_TYPE.ENTITY_ID) {
    const isInternal = Object.values(INTERNAL_PREFIX).some(p => typeof raw === 'string' && raw.startsWith(p));
    return isInternal ? '' : (raw || '');
  }
  return raw || '';
}

/**
 * Encode a value and type into the raw ``item`` field string.
 * @param {string} value - the decoded value
 * @param {string} type - one of ITEM_TYPE constants
 * @returns {string|null} the encoded ``item`` field value (null for skip)
 */
export function encodeItemValue(value, type) {
  if (type === ITEM_TYPE.SKIP) return null;
  if (INTERNAL_PREFIX[type]) return INTERNAL_PREFIX[type] + value;
  // Preserve empty string for ENTITY_ID with no entity chosen yet —
  // detectItemType needs '' to recognise the type.
  return value || '';
}

/* ── display helpers ────────────────────────────────────────────────────── */

/**
 * Summarise an item config for display in list rows.
 * @param {object} config - item config dict with at least an ``item`` key
 * @returns {string} human-readable summary
 */
export function itemSummary(config) {
  if (!config || config.item === null || config.item === undefined) {
    return 'Skip';
  }
  // Empty string means entity type with no entity chosen yet
  if (config.item === '') return 'Entity';
  const raw = config.item;
  if (typeof raw === 'string') {
    if (raw.startsWith(INTERNAL_PREFIX.text))      return `Text: ${raw.slice(5)}`;
    if (raw.startsWith(INTERNAL_PREFIX.navigate))  return `Navigate: ${raw.slice(9)}`;
    if (raw.startsWith(INTERNAL_PREFIX.action))    return `Action: ${raw.slice(7)}`;
  }
  // Gracefully handle objects by extracting entity_id, falling back to unknown
  return (raw && typeof raw === 'object') ? (raw.item || raw.entity_id || '(unknown)') : String(raw);
}

/**
 * Primary display text for a row: name override if set, else type label.
 * @param {object} config
 * @returns {string}
 */
export function itemPrimaryText(config) {
  if (config && config.name) return String(config.name);
  const t = detectItemType(config?.item);
  return ITEM_TYPE_SHORT[t] || 'Item';
}

/**
 * Secondary display text for a row: the underlying value (entity id, target,
 * service, text content). Empty when skip.
 * @param {object} config
 * @returns {string}
 */
export function itemSecondaryText(config) {
  if (!config) return '';
  const t = detectItemType(config.item);
  if (t === ITEM_TYPE.SKIP) return '';
  const val = parseItemValue(config.item, t);
  return val || '';
}

/* ── override helpers ───────────────────────────────────────────────────── */

/**
 * Check whether an item config has any override fields set.
 * @param {object} config - item config dict
 * @returns {boolean}
 */
export function hasOverrides(config) {
  if (!config) return false;
  return ENTITY_OVERRIDE_FIELDS.some(f => !!config[f]);
}

/* ── serialization ──────────────────────────────────────────────────────── */

/**
 * Serialize an item config dict to API-ready format.
 * Ensures null item → null, strips empty override fields.
 * @param {object} config - item config dict
 * @returns {object} API-ready item dict
 */
export function serializeItem(config) {
  const item = {};
  const raw = config.item;
  if (raw === null || raw === undefined) {
    item.item = null;
  } else {
    item.item = raw;
  }
  // Serialize all keys from config except 'item' (already handled).
  // ENTITY_OVERRIDE_FIELDS and panel-type-specific item_options
  // are both included. Empty/null values are stripped.
  for (const f of Object.keys(config)) {
    if (f === 'item') continue;
    const v = config[f];
    if (v !== null && v !== undefined && v !== '') item[f] = v;
  }
  return item;
}

/* ── panel key picker ────────────────────────────────────────────────── */

/**
 * Open the panel key dropdown and attach a click-outside listener.
 */
function _openPanelKeyDropdown(wrap) {
  const dropdown = wrap?.querySelector(".entity-dropdown");
  if (!dropdown) return;
  const items = dropdown.querySelectorAll(".entity-dropdown-item");
  items.forEach((item) => { item.style.display = ""; });
  dropdown.style.display = items.length ? "" : "none";
  if (items.length === 0) return;

  // Close on click outside — install once on the document
  if (wrap._panelOutsideHandler) return;
  wrap._panelOutsideHandler = (ev) => {
    if (!wrap || wrap.contains(ev.target)) return;
    _hidePanelKeyDropdown(wrap);
  };
  document.addEventListener("mousedown", wrap._panelOutsideHandler);
}

/** Hide the panel key dropdown and detach the outside listener. */
function _hidePanelKeyDropdown(wrap) {
  const dropdown = wrap?.querySelector(".entity-dropdown");
  if (dropdown) dropdown.style.display = "none";
  if (wrap) wrap._panelActiveIndex = -1;
  if (wrap?._panelOutsideHandler) {
    document.removeEventListener("mousedown", wrap._panelOutsideHandler);
    delete wrap._panelOutsideHandler;
  }
}

/**
 * Render a panel key picker: text input with an autocomplete dropdown
 * that lists available panel keys for the device.
 *
 * Dropdown filtering is done via DOM (no full re-render on keystroke) to
 * keep the input responsive. The caller reads the value from the DOM on
 * save, so no host.requestUpdate() is needed on selection.
 *
 * @param {object}  host         - The Lit component (host of the inline editor)
 * @param {object}  opts
 * @param {string}  opts.id      - DOM id for the text field
 * @param {string}  opts.value   - Current panel key value
 * @param {string}  [opts.label] - Field label
 * @param {string}  [opts.placeholder]
 * @param {string[]} opts.panelKeys - Available panel key strings
 */
export function renderPanelKeyPicker(host, { id, value, label, placeholder, panelKeys }) {
  const keys = panelKeys || [];

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
            const key = (item.getAttribute("data-panel-key") || "").toLowerCase();
            const match = !val || key.includes(val);
            item.style.display = match ? "" : "none";
            if (match) any = true;
          });
          dropdown.style.display = any ? "" : "none";
        }}
        @focus=${(e) => _openPanelKeyDropdown(e.target.closest(".entity-picker-wrap"))}
        @blur=${(e) => {
          const wrap = e.target?.closest(".entity-picker-wrap");
          setTimeout(() => { if (wrap) _hidePanelKeyDropdown(wrap); }, 80);
        }}
        @keydown=${(e) => {
          const wrap = e.target.closest(".entity-picker-wrap");
          const dropdown = wrap?.querySelector(".entity-dropdown");
          if (!dropdown || dropdown.style.display === "none") return;

          const visibleItems = [...dropdown.querySelectorAll(".entity-dropdown-item")]
            .filter((el) => el.style.display !== "none");
          if (!visibleItems.length) return;

          let idx = wrap._panelActiveIndex != null ? wrap._panelActiveIndex : -1;

          if (e.key === "ArrowDown") {
            e.preventDefault();
            idx = Math.min(idx + 1, visibleItems.length - 1);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            idx = Math.max(idx - 1, 0);
          } else if (e.key === "Enter") {
            if (idx >= 0) {
              e.preventDefault();
              _selectPanelKey(wrap, visibleItems[idx]);
            }
            return;
          } else if (e.key === "Escape") {
            e.preventDefault();
            _hidePanelKeyDropdown(wrap);
            return;
          } else {
            return;
          }

          wrap._panelActiveIndex = idx;
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
        ${keys.map((key) => html`
          <div class="entity-dropdown-item"
            data-panel-key="${key}"
            @mousedown=${(e) => {
              e.preventDefault();
              _selectPanelKey(e.target.closest(".entity-picker-wrap"), e.currentTarget);
            }}
            style="cursor:pointer; padding:6px 10px;"
          >${key}</div>
        `)}
      </div>
    </div>
  `;

  if (label) {
    return html`
      <div class="form-group">
        <label for=${id}>${label}</label>
        ${picker}
      </div>
    `;
  }

  return picker;
}

/** Internal: set the input value from a selected dropdown item. */
function _selectPanelKey(wrap, item) {
  const tf = wrap?.querySelector(".entity-picker-input");
  const key = item.getAttribute("data-panel-key") || "";
  if (tf) tf.value = key;
  _hidePanelKeyDropdown(wrap);
}


