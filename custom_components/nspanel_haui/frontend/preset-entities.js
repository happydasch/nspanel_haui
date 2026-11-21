// @ts-check
/**
 * NSPanel HAUI - which of the user's entities a quick start preset may use.
 *
 * A preset is resolved against the user's own Home Assistant: the area they
 * chose and the entities that area (or, without an area, the whole
 * installation) actually has, by domain. This module owns those lookups; the
 * presets themselves and their entity slots live in `presets.js`.
 *
 * "In area A" is Home Assistant's own rule: an entity in that area, or one
 * without an area of its own on a device in that area. Hidden entities and
 * configuration/diagnostic ones are never offered: they are not something a
 * wall panel should show.
 *
 * The records (`hass.areas`, `hass.devices`, `hass.entities`) are subscribed at
 * startup and can be briefly null after a reconnect, so every read is guarded.
 * A lookup is memoised per registry snapshot: states move on, the registry does
 * not, and a resolution runs for every preset card and again on every choice.
 */

/**
 * @typedef {{ area_id?: string, name?: string, temperature_entity_id?: string|null,
 *   humidity_entity_id?: string|null }} AreaEntry
 * @typedef {{ id?: string, area_id?: string|null, name?: string|null }} DeviceEntry
 * @typedef {{ entity_id?: string, device_id?: string|null, area_id?: string|null,
 *   name?: string|null, original_name?: string|null, hidden?: boolean,
 *   entity_category?: string|null, disabled_by?: string|null }} EntityEntry
 * @typedef {{ areas?: Record<string, AreaEntry>|null, devices?: Record<string, DeviceEntry>|null,
 *   entities?: Record<string, EntityEntry>|null, states?: Record<string, any>|null }} Registries
 */

/** @type {WeakMap<object, Map<string, { devices: object|null, ids: string[] }>>} */
const LOOKUPS = new WeakMap();

/** @param {unknown} id */
const domainOf = (id) => (typeof id === 'string' ? id.slice(0, id.indexOf('.')) : '');

/**
 * The areas the user can choose from, by name.
 *
 * @param {Registries|null|undefined} hass
 * @returns {Array<{ area_id: string, name: string }>}
 */
export function areaOptions(hass) {
  return Object.entries(hass?.areas || {})
    .map(([area_id, area]) => ({ area_id, name: area?.name || area_id }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * The name an entity is shown by: the registry's name, else the state's
 * friendly name, else its id.
 *
 * @param {string} id
 * @param {EntityEntry|undefined} entry
 * @param {Record<string, any>|null|undefined} states
 */
function nameOf(id, entry, states) {
  return entry?.name || states?.[id]?.attributes?.friendly_name || id;
}

/**
 * Whether an entity is in a state a panel can show: a missing state is fine
 * (Home Assistant keeps entities it has not run yet), `unavailable` and
 * `unknown` are not.
 *
 * @param {Record<string, any>|null|undefined} states
 * @param {string} id
 */
function isUsable(states, id) {
  const state = states?.[id]?.state;
  return state !== 'unavailable' && state !== 'unknown';
}

/**
 * Whether a registry entry may be offered to a preset.
 *
 * @param {EntityEntry|undefined} entry
 */
function isOfferable(entry) {
  return !entry?.hidden && !entry?.entity_category && !entry?.disabled_by;
}

/**
 * Whether an entity belongs to `areaId` under Home Assistant's own rule.
 *
 * @param {EntityEntry|undefined} entry
 * @param {Record<string, DeviceEntry>} devices
 * @param {string} areaId
 */
function isInArea(entry, devices, areaId) {
  if (entry?.area_id) return entry.area_id === areaId;
  if (entry?.device_id) return devices[entry.device_id]?.area_id === areaId;
  return false;
}

/**
 * Entity ids of `domains` in one area (or, with no area, in the whole
 * installation), the ones in a usable state first and then by name.
 *
 * @param {Registries|null|undefined} hass
 * @param {string} areaId - '' for the whole installation
 * @param {string[]} [domains] - the domains wanted; empty means any
 * @returns {string[]}
 */
export function lookupEntities(hass, areaId = '', domains = []) {
  const entries = hass?.entities || {};
  const devices = hass?.devices || {};
  const wanted = new Set(domains);
  const key = `${areaId}|${[...wanted].sort().join(',')}`;
  const snapshot = hass?.entities;
  const cache = snapshot && typeof snapshot === 'object' ? LOOKUPS.get(snapshot) : undefined;

  /** @param {string[]} ids */
  const rank = (ids) => {
    const rankOf = (id) => (isUsable(hass?.states, id) ? 0 : 1);
    return ids.sort((a, b) => rankOf(a) - rankOf(b)
      || nameOf(a, entries[a], hass?.states).localeCompare(nameOf(b, entries[b], hass?.states))
      || a.localeCompare(b));
  };

  if (cache) {
    const hit = cache.get(key);
    // The devices record decides area membership, so a new one invalidates the list.
    if (hit && hit.devices === (hass?.devices || null)) return hit.ids;
  }

  const ids = [];
  for (const [id, entry] of Object.entries(entries)) {
    if (!isOfferable(entry)) continue;
    if (wanted.size && !wanted.has(domainOf(id))) continue;
    if (areaId && !isInArea(entry, devices, areaId)) continue;
    ids.push(id);
  }
  rank(ids);

  if (cache) cache.set(key, { devices: hass?.devices || null, ids });
  else if (snapshot && typeof snapshot === 'object') {
    LOOKUPS.set(snapshot, new Map([[key, { devices: hass?.devices || null, ids }]]));
  }
  return ids;
}

/**
 * The entities of one area, by domain.
 *
 * @param {Registries|null|undefined} hass
 * @param {string} areaId
 * @param {string[]} [domains]
 * @returns {string[]}
 */
export function entitiesInArea(hass, areaId, domains = []) {
  return areaId ? lookupEntities(hass, areaId, domains) : [];
}

/**
 * The entities of the whole installation, by domain.
 *
 * @param {Registries|null|undefined} hass
 * @param {string[]} [domains]
 * @returns {string[]}
 */
export function domainEntities(hass, domains = []) {
  return lookupEntities(hass, '', domains);
}

/**
 * Whether the area (or, with no area, the installation) has an entity of one
 * of `domains`: a preset offers that page by default only when it would show
 * something.
 *
 * @param {Registries|null|undefined} hass
 * @param {string[]} domains
 * @param {string} [areaId]
 * @returns {boolean}
 */
export function hasEntities(hass, domains, areaId = '') {
  return lookupEntities(hass, areaId, domains).length > 0;
}

/** @param {string[]} ids @param {Registries|null|undefined} hass @param {'temperature'|'humidity'} kind */
function byDeviceClass(ids, hass, kind) {
  return ids.find((id) => hass?.states?.[id]?.attributes?.device_class === kind) || '';
}

/**
 * The area's own temperature or humidity sensor: the registry's configured
 * entity for the area, else a sensor of the area that measures it.
 *
 * @param {Registries|null|undefined} hass
 * @param {string} areaId
 * @param {'temperature'|'humidity'} kind
 * @returns {string} the entity id, or '' when the area has none
 */
export function areaSensor(hass, areaId, kind) {
  if (!areaId) return '';
  const area = hass?.areas?.[areaId];
  const configured = kind === 'temperature' ? area?.temperature_entity_id : area?.humidity_entity_id;
  if (configured && hass?.entities?.[configured]) return configured;
  return byDeviceClass(entitiesInArea(hass, areaId, ['sensor']), hass, kind);
}
