// @ts-check
/**
 * Field-level rules for panel options, checked as the panel editor's form changes.
 *
 * Mirrors haui/option_rules.py: the hub refuses a save that breaks one of these
 * rules, and tests/fixtures/option_rules_cases.json runs through both engines so
 * they cannot disagree. A rule is data on the option the panel types endpoint
 * serves (`required`, `min`, `max`, `domain`, `choices`, `max_items`).
 */
import { t } from './localize.js';

/**
 * @typedef {{ key: string, kind: string, domain?: string|null, required?: boolean,
 *   min?: number|null, max?: number|null, max_items?: number|null,
 *   allow_template?: boolean, choices?: Array<{ value: string, label?: string }> }} RuleOption
 * @typedef {{ field: string, kind: string, message: string }} RuleError
 * @typedef {{ options?: RuleOption[] }|null|undefined} RuleDescriptor
 */

/** Item types that are not entities (InternalItemType in haui/mapping/const.py). */
const INTERNAL_TYPES = ['skip', 'text', 'navigate', 'action'];
const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;

/** @param {unknown} value */
const itemId = (value) => (value && typeof value === 'object' && !Array.isArray(value)
  ? /** @type {{ item?: unknown }} */ (value).item
  : value);

/** @param {string} id */
const isInternal = (id) => INTERNAL_TYPES.some((type) => id === type || id.startsWith(`${type}:`));

/** @param {unknown} value */
const isNumber = (value) => typeof value === 'number' && Number.isFinite(value);

/**
 * @param {string} field
 * @param {unknown} id
 * @param {string|null|undefined} domain
 * @returns {RuleError[]}
 */
function domainErrors(field, id, domain) {
  if (!domain || typeof id !== 'string' || !id || isInternal(id)) return [];
  if (id.split('.')[0] === domain) return [];
  return [{ field, kind: 'domain', message: t('Use a {domain} entity').replace('{domain}', domain) }];
}

/**
 * Whether the hub's parse_color_value reads `value` as a colour.
 * @param {unknown} value
 */
function isColor(value) {
  if (typeof value === 'number') return Number.isInteger(value) && value >= 0 && value <= 0xffff;
  if (Array.isArray(value)) {
    return value.length === 3 && value.every((part) => Number.isInteger(part) && part >= 0 && part <= 255);
  }
  if (typeof value === 'string') {
    const text = value.trim();
    return HEX_COLOR.test(text) || (/^\d+$/.test(text) && Number(text) <= 0xffff);
  }
  return false;
}

/** @param {RuleOption} option */
const choiceValues = (option) => (option.choices || []).map((choice) => choice.value);

/** @param {unknown} value */
const isTemplate = (value) => typeof value === 'string' && (value.includes('{{') || value.includes('{%'));

/**
 * The rules one option's value breaks; `field` is the option key, or
 * `<key>.<index>` for one entry of a list, as the hub names it.
 *
 * @param {RuleOption} option
 * @param {unknown} value - the value; null or undefined means not set
 * @param {{ popup?: boolean }} [context] - a popup override takes its `item` from context
 * @returns {RuleError[]}
 */
export function optionValueErrors(option, value, { popup = false } = {}) {
  const { key, kind } = option;
  if (kind === 'item') {
    const id = itemId(value);
    if (id === '' || ((value === null || value === undefined) && option.required)) {
      return option.required && !(popup && key === 'item')
        ? [{ field: key, kind: 'required', message: t('Choose an entity') }]
        : [];
    }
    return domainErrors(key, id, option.domain);
  }
  if (value === null || value === undefined) return [];
  if (kind === 'int' || kind === 'float') {
    if (!isNumber(value) || (kind === 'int' && !Number.isInteger(value))) {
      return [{ field: key, kind: 'number', message: t('Enter a number') }];
    }
    const number = /** @type {number} */ (value);
    if (isNumber(option.min) && number < /** @type {number} */ (option.min)) {
      return [{ field: key, kind: 'min', message: t('Use {min} or more').replace('{min}', String(option.min)) }];
    }
    if (isNumber(option.max) && number > /** @type {number} */ (option.max)) {
      return [{ field: key, kind: 'max', message: t('Use {max} or less').replace('{max}', String(option.max)) }];
    }
    return [];
  }
  if (kind === 'select') {
    if (choiceValues(option).includes(/** @type {string} */ (value))
      || (option.allow_template && isTemplate(value))) return [];
    return [{ field: key, kind: 'choice', message: t('Choose one of the listed values') }];
  }
  if (kind === 'color') {
    if (value === '' || isColor(value)) return [];
    return [{ field: key, kind: 'color', message: t('Enter a colour as #rrggbb, [r,g,b] or a number') }];
  }
  if (kind === 'str' || kind === 'generic') {
    return option.required && !String(value).trim()
      ? [{ field: key, kind: 'required', message: t('Fill in this field') }]
      : [];
  }
  if (!Array.isArray(value)) return [];
  if (kind === 'list_items') {
    const choices = choiceValues(option);
    if (!choices.length) return [];
    return value.flatMap((entry, index) => (choices.includes(entry)
      ? []
      : [{ field: `${key}.${index}`, kind: 'choice', message: t('Choose one of the listed values') }]));
  }
  if (kind === 'list_entities') {
    return value.flatMap((entry, index) => domainErrors(`${key}.${index}`, itemId(entry), option.domain));
  }
  if (kind === 'item_list') {
    /** @type {RuleError[]} */
    const errors = [];
    if (isNumber(option.max_items) && value.length > /** @type {number} */ (option.max_items)) {
      errors.push({
        field: key,
        kind: 'max_items',
        message: t('Use at most {max} items').replace('{max}', String(option.max_items)),
      });
    }
    value.forEach((entry, index) => {
      if (itemId(entry) === '') errors.push({ field: `${key}.${index}`, kind: 'required', message: t('Choose an entity') });
    });
    return errors;
  }
  return [];
}

/**
 * The form's field id for a rule's field: `fld-<key>` or `fld-<key>-<index>`.
 * @param {string} field
 */
export const fieldId = (field) => `fld-${field.replace('.', '-')}`;

/**
 * An option's value as the editor holds it: item and item-list fields live in
 * the editor's item lists while the form is open (a single item as a one-entry
 * list), every other option in the panel data.
 *
 * @param {RuleOption} option
 * @param {Record<string, any>} data
 * @param {Record<string, any[]>} itemLists
 */
function editorValue(option, data, itemLists) {
  const list = itemLists?.[option.key];
  if (option.kind === 'item' && Array.isArray(list)) return list[0] ?? null;
  if (option.kind === 'item_list' && Array.isArray(list)) return list;
  return data?.[option.key];
}

/**
 * Every rule the panel in the editor breaks, by the field id it is shown at.
 *
 * @param {RuleDescriptor} descriptor
 * @param {Record<string, any>} data - the panel data
 * @param {Record<string, any[]>} itemLists - the editor's item lists
 * @param {{ popup?: boolean }} context
 * @returns {Map<string, { kind: string, message: string }>}
 */
export function optionErrors(descriptor, data, itemLists, { popup = false } = {}) {
  /** @type {Map<string, { kind: string, message: string }>} */
  const errors = new Map();
  for (const option of descriptor?.options || []) {
    for (const error of optionValueErrors(option, editorValue(option, data, itemLists), { popup })) {
      const id = fieldId(error.field);
      if (!errors.has(id)) errors.set(id, { kind: error.kind, message: error.message });
    }
  }
  return errors;
}

/**
 * Entities the panel names that Home Assistant does not know right now. They
 * may be offline or not created yet, so they warn instead of blocking the save.
 *
 * @param {RuleDescriptor} descriptor
 * @param {Record<string, any>} data
 * @param {Record<string, any[]>} itemLists
 * @param {Record<string, unknown>|undefined} states - `hass.states`
 * @returns {Map<string, string>}
 */
export function entityWarnings(descriptor, data, itemLists, states) {
  /** @type {Map<string, string>} */
  const warnings = new Map();
  if (!states) return warnings;
  /** @param {string} field @param {unknown} value */
  const check = (field, value) => {
    const id = itemId(value);
    if (typeof id !== 'string' || !id || isInternal(id) || id in states) return;
    warnings.set(fieldId(field), t('Home Assistant does not know {entity} right now').replace('{entity}', id));
  };
  for (const option of descriptor?.options || []) {
    const value = editorValue(option, data, itemLists);
    if (option.kind === 'item') check(option.key, value);
    else if ((option.kind === 'item_list' || option.kind === 'list_entities') && Array.isArray(value)) {
      value.forEach((entry, index) => check(`${option.key}.${index}`, entry));
    }
  }
  return warnings;
}

/**
 * Whether a saved panel breaks a rule of its type, e.g. one saved before the rule existed.
 *
 * @param {RuleDescriptor} descriptor
 * @param {Record<string, any>} panel
 * @param {{ popup?: boolean }} context
 */
export function panelHasOptionErrors(descriptor, panel, { popup = false } = {}) {
  return optionErrors(descriptor, panel, {}, { popup }).size > 0;
}
