/**
 * NSPanel HAUI - HAUIItem JS representation.
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
import { t } from './localize.js';
import { formatFieldValue } from './form-fields.js';

/** Item type constants (match Python INTERNAL_ITEM_TYPE). */
export const ITEM_TYPE = {
  ENTITY_ID: 'entity_id',
  SKIP:       'skip',
  TEXT:       'text',
  NAVIGATE:   'navigate',
  ACTION:     'action',
};

/**
 * Labels and placeholders for each item type (single source of truth).
 * A function, not a constant: t() must run after the language has loaded.
 */
export function itemLabels() {
  return {
    entity_id: { label: t("Entity"), placeholder: t("light.bedroom") },
    skip:      { label: "", placeholder: t("No value needed") },
    text:      { label: t("Display Text"), placeholder: t("Hello, World!") },
    navigate:  { label: t("Target Panel"), placeholder: t("grid_0") },
    action:    { label: t("Service"), placeholder: t("light/turn_on") },
  };
}

/** MDI icon per item type — used as fallback when no override icon set. */
export const ITEM_TYPE_ICONS = {
  entity_id: 'mdi:home-assistant',
  skip:      'mdi:minus-circle-outline',
  text:      'mdi:format-text',
  navigate:  'mdi:arrow-right-circle-outline',
  action:    'mdi:flash',
};

/** Short type label shown in row header (a function so t() runs at render time). */
export function itemTypeShort() {
  return {
    entity_id: t('Entity'),
    skip:      t('Skip'),
    text:      t('Text'),
    navigate:  t('Navigate'),
    action:    t('Action'),
  };
}

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
/**
 * Primary display text for a row: name override if set, else type label.
 * @param {object} config
 * @returns {string}
 */
export function itemPrimaryText(config) {
  if (config && config.name) {
    const v = config.name;
    // State-keyed dict → show human-friendly preview
    if (typeof v === "object" && !Array.isArray(v)) {
      return Object.entries(v).map(([k, val]) => `${k}: ${val}`).join(", ");
    }
    return formatFieldValue(v);
  }
  const typeStr = detectItemType(config?.item);
  return itemTypeShort()[typeStr] || t('Item');
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

/* ── navigate target ─────────────────────────────────────────────────── */

/**
 * Options for a navigate item's target: the device's panels, then the system
 * panels, each as "title (key)" (or the key alone). A current value that matches neither stays
 * selectable and is marked, so applying the item doesn't drop it.
 *
 * @param {Array<{key: string, title?: string}>} devicePanels
 * @param {Array<{key: string, label?: string}>} systemPanels
 * @param {string} value - current target panel key
 * @returns {Array<{value: string, label: string}>}
 */
export function panelTargetOptions(devicePanels, systemPanels, value) {
  const options = [
    ...(devicePanels || []).filter((p) => p.key).map((p) => ({
      value: p.key,
      label: p.title ? `${p.title} (${p.key})` : p.key,
    })),
    ...(systemPanels || []).filter((p) => p.key).map((p) => ({
      value: p.key,
      label: p.label ? `${p.label} (${p.key})` : p.key,
    })),
  ];
  if (value && !options.some((o) => o.value === value)) {
    options.unshift({ value, label: `${value} (${t("unknown panel")})` });
  }
  return options;
}


