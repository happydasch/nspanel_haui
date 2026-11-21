// @ts-check
/**
 * NSPanel HAUI - the quick start's configurations, one per use case.
 *
 * A device with no panels is set up by choosing a whole configuration, not one
 * page: a preset is several pages plus the device settings that make them work
 * (the home page, the idle page, the header). Picking one resolves it against
 * the user's own Home Assistant - the area they chose and the entities that
 * area (or, without an area, the whole installation) has - and offers the few
 * optional pages it can add.
 *
 * A page is a panel config without a `key`. Its entity slots are empty and
 * carry what fills them: `domain` ("an entity of this domain belongs here") or
 * `sensor` ("the area's temperature"). The resolver fills each and drops the
 * hint, because a saved panel names entities, not the domains it expected. A
 * slot it cannot fill is left out of an item list (an empty entry breaks the
 * option rules, `haui/option_rules.py`, mirrored by `option-rules.js`), so a
 * grid or a row holds the entities the room has - none of them is required.
 * Only a page that shows one entity (a light, a blind, a keypad) needs it, and
 * the setup then says why it cannot be created yet.
 */
import { clone } from './constants.js';
import { t } from './localize.js';
import { paletteHex, tileColors } from './preset-colors.js';
import { areaSensor, domainEntities, entitiesInArea, hasEntities } from './preset-entities.js';
import { panelExists } from './panel-roles.js';

/**
 * An entity slot of a preset page: the entity is chosen when the preset is
 * created, so `item` is empty and `domain` - or `sensor`, for a sensor's
 * device class - says what fills it.
 *
 * `when` and `optional` make a slot one the setup works without: a slot whose
 * `when` domain the area (or the installation) does not have, or an `optional`
 * one that cannot be filled, is dropped without a warning - a clock's weather
 * entity or its temperature card is a bonus, not a requirement. A tile of a grid
 * or row list is always optional (`slot()`), since such a page shows the
 * entities the room has. `installation` reads the whole installation instead of
 * the area: the weather outside is not a room's.
 * @typedef {{ item?: string, domain?: string, sensor?: 'temperature'|'humidity'|'power'|'battery',
 *   icon?: string, show_power_button?: boolean, when?: string, optional?: boolean,
 *   installation?: boolean }} PresetSlot
 */

/**
 * What a page is for on the device: its home screen, its idle panel (the idle
 * page), a further idle panel the automatic page switch cycles to after the
 * idle page (`idle_panel_extra`), or a page the user reaches by swiping.
 * @typedef {'home'|'idle'|'idle_extra'|'page'} PresetRole
 */

/**
 * One page of a preset.
 * @typedef {Object} PresetPage
 * @property {string} id - names the page in the keys it creates
 * @property {PresetRole} role - what the page is for on the device
 * @property {string} [when] - the toggle that includes this page
 * @property {(palette: Record<string, any>|null) => Object<string, any>} [colors]
 *   - the page's own colours, derived from the device's theme palette
 * @property {any} panel - the panel config, its entity slots still empty
 */

/**
 * An optional page or setting the dialog offers as a switch.
 * @typedef {Object} PresetToggle
 * @property {string} key
 * @property {string} label
 * @property {string} description
 * @property {boolean} [default] - on unless the user says otherwise
 * @property {string} [when] - a domain; the toggle is on when the user has one
 */

/**
 * A configuration the quick start offers.
 * @typedef {Object} Preset
 * @property {string} key
 * @property {string} label
 * @property {string} description
 * @property {string} icon
 * @property {boolean} [needsArea] - resolves against one area of the user's
 * @property {PresetPage[]} pages
 * @property {PresetToggle[]} toggles
 */

/**
 * A page resolved against the user's Home Assistant.
 * @typedef {Object} ResolvedPresetPage
 * @property {string} id
 * @property {PresetRole} role
 * @property {string} key - the free key the page is saved under
 * @property {string} label
 * @property {any} panel - the panel config with its entity slots filled
 * @property {string[]} missing - domains a slot that is not optional found no entity of
 * @property {string[]} blocked - domains a required slot needs and Home Assistant has none of
 * @property {Array<{ key: string, label: string }>} needsInput - required fields the editor asks for
 * @property {number} filled - how many entity slots were filled
 * @property {boolean} empty - the page declared entity slots and none could be filled, so a
 *   page that is not the home screen or an idle panel is left out of the setup
 * @property {boolean} typeKnown - the hub's descriptors know this page's panel type
 */

/**
 * A preset resolved against the user's Home Assistant.
 * @typedef {Object} PresetResolution
 * @property {string} preset
 * @property {any} area - the area it resolved against, or null
 * @property {string} areaName
 * @property {Array<PresetToggle & { on: boolean, available: boolean }>} toggles
 * @property {ResolvedPresetPage[]} pages
 * @property {ResolvedPresetPage[]} dropped - optional pages left out because they would show nothing
 * @property {Object<string, any>} config - the device settings the preset changes
 * @property {boolean} ready
 * @property {string[]} blocked
 * @property {Array<{ key: string, label: string }>} needsInput
 * @property {string[]} warnings
 * @property {number} entityCount
 */

/* ── the presets ─────────────────────────────────────────────────────────── */

/**
 * An item-list slot for an entity of `domain`: the entity brings its own icon,
 * so no icon is imposed here (only a sensor usually has none).
 *
 * A tile list takes what the room (or the installation) has: a domain without
 * an entity is left out of the panel instead of being demanded, and the tile is
 * added in the editor once such an entity exists.
 * @param {string} domain
 * @param {boolean} [power] - the item's on/off button as well as its tile
 */
const slot = (domain, power = false) => {
  /** @type {PresetSlot} */
  const entry = { item: '', domain, optional: true };
  if (power) entry.show_power_button = true;
  return entry;
};

/**
 * A slot for a sensor that measures the given quantity.
 * @param {NonNullable<PresetSlot['sensor']>} kind
 * @param {string} icon
 * @param {boolean} [optional] - dropped without a warning when it cannot be filled
 */
const sensorSlot = (kind, icon, optional = false) => {
  /** @type {PresetSlot} */
  const entry = { item: '', sensor: kind, icon };
  if (optional) entry.optional = true;
  return entry;
};

/** The installation's weather entity, when it has a weather integration. */
const weatherSlot = () => ({
  item: '', domain: 'weather', when: 'weather', installation: true,
});

/**
 * The preset's pages as navigation pages - the setting the panel editor calls
 * **Show in navigation**, which decides whether a page is reached by swiping and
 * from the header buttons, or stays a stacked page only something opens.
 * @param {boolean} on
 */
const navigationToggle = (on) => ({
  key: 'navigation',
  label: t('Show entities in navigation'),
  description: t('Reach them by swiping or with the header buttons. Off, they stay hidden until something opens them.'),
  default: on,
});

/** @param {boolean} on */
const idleToggle = (on) => ({
  key: 'idle',
  label: t('Add an idle panel'),
  description: t('A clock the panel shows while nobody uses it. It becomes the idle page.'),
  default: on,
});

/**
 * A word clock in the device theme's accent: the colour is materialised here
 * because a saved panel carries values, not theme variables.
 *
 * The unlit letters are left to the page, which draws them in the unlit tone of
 * the picture the panel ends up on; a stored value would be wrong under another
 * picture, and the theme's muted text tone sits nearly as dark as the lit
 * letters on a light page.
 * @param {Record<string, any>|null} palette
 */
const clockTwoColors = (palette) => ({
  special_color: paletteHex(palette, 'header_accent'),
});

/**
 * The configurations the quick start offers, in the order it shows them. Their
 * labels, descriptions and titles are the editor's own text (`t()`), so a
 * created page carries the user's language.
 *
 * Built per call, not once at import: the editor fetches the translations after
 * this module is loaded, so a catalog built at import time would keep its
 * English names (and write them into the pages it creates) for the whole
 * session.
 * @returns {Preset[]}
 */
export function presets() {
  return [
    {
      key: 'room',
      label: t('Room panel'),
      description: t('One room: its lights, blind, thermostat and media, with a clock at night.'),
      icon: 'mdi:sofa-outline',
      needsArea: true,
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: {
            type: 'grid',
            title: '',
            items: [
              slot('light', true),
              slot('cover'),
              slot('climate'),
              slot('media_player'),
              slot('switch', true),
              slot('scene'),
            ],
          },
        },
        {
          id: 'light',
          role: 'page',
          when: 'light',
          panel: { type: 'light', title: t('Light'), item: { item: '', domain: 'light' } },
        },
        {
          id: 'cover',
          role: 'page',
          when: 'cover',
          panel: { type: 'cover', title: t('Blind'), item: { item: '', domain: 'cover' } },
        },
        {
          id: 'climate',
          role: 'page',
          when: 'climate',
          panel: { type: 'climate', title: t('Thermostat'), item: { item: '', domain: 'climate' } },
        },
        {
          id: 'media',
          role: 'page',
          when: 'media',
          panel: { type: 'media', title: t('Media'), item: { item: '', domain: 'media_player' } },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: {
            type: 'clock',
            title: t('Clock'),
            show_time_date: true,
            show_weather: true,
            show_home_temp: true,
            show_notifications: true,
            item: weatherSlot(),
            inside_temp_item: { item: '', sensor: 'temperature', optional: true },
            items: [
              sensorSlot('temperature', 'mdi:thermometer', true),
              sensorSlot('humidity', 'mdi:water-percent', true),
              sensorSlot('power', 'mdi:flash', true),
              sensorSlot('battery', 'mdi:battery', true),
            ],
          },
        },
      ],
      toggles: [
        navigationToggle(false),
        idleToggle(true),
        {
          key: 'light',
          label: t('Add a light page'),
          description: t('Brightness and colour for the room\'s light.'),
          when: 'light',
        },
        {
          key: 'cover',
          label: t('Add a blind page'),
          description: t('Position control for the room\'s blind.'),
          when: 'cover',
        },
        {
          key: 'climate',
          label: t('Add a thermostat page'),
          description: t('Climate control for its thermostat.'),
          default: false,
          when: 'climate',
        },
        {
          key: 'media',
          label: t('Add a media page'),
          description: t('Playback control for its media player.'),
          default: false,
        },
      ],
    },
    {
      key: 'home',
      label: t('Home overview'),
      description: t('The whole home at a glance, with a page for lights and one for switches.'),
      icon: 'mdi:home-outline',
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: {
            type: 'grid',
            title: t('Home'),
            items: [
              slot('scene'),
              slot('light', true),
              slot('cover'),
              slot('media_player'),
              slot('switch', true),
              slot('alarm_control_panel'),
            ],
          },
        },
        {
          id: 'lights',
          role: 'page',
          panel: {
            type: 'row',
            title: t('Lights'),
            items: Array.from({ length: 5 }, () => slot('light')),
          },
        },
        {
          id: 'switches',
          role: 'page',
          panel: {
            type: 'row',
            title: t('Switches'),
            items: Array.from({ length: 5 }, () => slot('switch')),
          },
        },
        {
          id: 'vacuum',
          role: 'page',
          when: 'vacuum',
          panel: { type: 'vacuum', title: t('Vacuum'), item: { item: '', domain: 'vacuum' } },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: {
            type: 'clocktwo',
            title: t('Clock'),
            show_notifications: true,
          },
          colors: clockTwoColors,
        },
      ],
      toggles: [
        navigationToggle(true),
        idleToggle(true),
        {
          key: 'vacuum',
          label: t('Add a vacuum page'),
          description: t('Start, pause and dock the robot.'),
          when: 'vacuum',
        },
      ],
    },
    {
      key: 'status',
      label: t('Status board'),
      description: t('Read-only rows for temperature, humidity, power and battery readings, with an optional forecast.'),
      icon: 'mdi:pulse',
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: {
            type: 'row',
            title: t('Status'),
            items: [
              sensorSlot('temperature', 'mdi:thermometer'),
              sensorSlot('humidity', 'mdi:water-percent'),
              sensorSlot('power', 'mdi:flash'),
              sensorSlot('battery', 'mdi:battery'),
            ],
          },
        },
        {
          id: 'weather',
          role: 'idle_extra',
          when: 'weather',
          panel: {
            type: 'weather',
            title: t('Weather'),
            forecast_type: 'daily',
            show_time_date: true,
            show_home_temp: true,
            item: weatherSlot(),
            inside_temp_item: { item: '', sensor: 'temperature', optional: true },
            info_items: [sensorSlot('temperature', 'mdi:thermometer'), sensorSlot('humidity', 'mdi:water-percent')],
          },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: { type: 'clocktwo', title: t('Clock'), show_notifications: true },
          colors: clockTwoColors,
        },
      ],
      toggles: [
        navigationToggle(true),
        idleToggle(true),
        {
          key: 'weather',
          label: t('Add a weather screen'),
          description: t('The forecast with the temperatures you have, as a second idle panel.'),
          default: true,
          when: 'weather',
        },
      ],
    },
    {
      key: 'security',
      label: t('Entry & alarm'),
      description: t('An alarm keypad with a separate page for doors and locks.'),
      icon: 'mdi:shield-home-outline',
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: {
            type: 'alarm',
            title: t('Alarm'),
            item: { item: '', domain: 'alarm_control_panel' },
            action_icons: true,
          },
        },
        {
          id: 'doors',
          role: 'page',
          panel: {
            type: 'row',
            title: t('Doors & locks'),
            items: [
              slot('cover'),
              slot('lock'),
              slot('lock'),
              slot('cover'),
              slot('cover'),
            ],
          },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: { type: 'clock', title: t('Clock'), show_time_date: true },
        },
      ],
      toggles: [
        navigationToggle(true),
        idleToggle(false),
      ],
    },
    {
      key: 'kitchen',
      label: t('Kitchen timer'),
      description: t('A cooking countdown with a finish notification and an optional clock. No entities needed.'),
      icon: 'mdi:timer-outline',
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: { type: 'timer', title: t('Kitchen timer'), show_notification: true },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: { type: 'clocktwo', title: t('Clock'), show_notifications: true },
          colors: clockTwoColors,
        },
      ],
      toggles: [idleToggle(false)],
    },
    {
      key: 'guest',
      label: t('Guest Wi-Fi'),
      description: t('Put a scannable code for your guest network on the home screen, without exposing any device controls.'),
      icon: 'mdi:qrcode',
      pages: [
        {
          id: 'home',
          role: 'home',
          panel: {
            type: 'qr', title: t('Guest Wi-Fi'), essid: '', password: '', start_big_qr: true, show_info: false,
          },
        },
        {
          id: 'clock',
          role: 'idle',
          when: 'idle',
          panel: { type: 'clocktwo', title: t('Clock') },
          colors: clockTwoColors,
        },
      ],
      toggles: [idleToggle(false)],
    },
  ];
}

/**
 * The preset with this key, or null.
 * @param {string|null|undefined} key
 * @returns {Preset|null}
 */
export function presetByKey(key) {
  return presets().find((preset) => preset.key === key) || null;
}

/* ── keys ────────────────────────────────────────────────────────────────── */

/** A name as a panel key may carry it: lowercase, one separator between words. */
const slug = (text) => String(text || '')
  .toLowerCase()
  .normalize('NFKD')
  .replace(/[^a-z0-9]+/g, '_')
  .replace(/^_+|_+$/g, '');

/**
 * The keys a preset's pages are saved under, by page id: the home page is the
 * configuration itself (`room_kitchen`) and every other page hangs off it
 * (`room_kitchen_climate`). A key already taken gets a counter (`_2`), so a
 * second room of the same name keeps both.
 *
 * @param {Preset} preset
 * @param {string} [areaName]
 * @param {Iterable<string>} [taken] - keys the device (and the hub) already use
 * @returns {Map<string, string>} page id → key
 */
export function presetKeys(preset, areaName = '', taken = []) {
  const used = new Set(taken);
  const base = [preset.key, slug(areaName)].filter(Boolean).join('_');
  const keys = new Map();
  for (const page of preset.pages) {
    const wanted = page.role === 'home' ? base : `${base}_${page.id}`;
    let key = wanted;
    let counter = 2;
    while (used.has(key)) key = `${wanted}_${counter++}`;
    used.add(key);
    keys.set(page.id, key);
  }
  return keys;
}

/* ── resolution ──────────────────────────────────────────────────────────── */

/** Whether an option's value is still empty. @param {unknown} value */
const isBlank = (value) => value === undefined || value === null
  || (typeof value === 'string' && value.trim() === '')
  || (Array.isArray(value) && value.length === 0);

/**
 * Whether a value is an entity slot of a preset, rather than a value the page
 * already holds.
 * @param {unknown} value
 */
const isSlot = (value) => !!value && typeof value === 'object' && !Array.isArray(value)
  && (/** @type {PresetSlot} */ (value).domain !== undefined
    || /** @type {PresetSlot} */ (value).sensor !== undefined);

/**
 * Whether a toggle is on: what the user chose, else what Home Assistant makes
 * sensible (a page for an entity they do not have is not offered), else the
 * preset's default.
 *
 * @param {PresetToggle} toggle
 * @param {{ hass: any, areaId: string, choices: any }} world
 */
function toggleOn(toggle, { hass, areaId, choices }) {
  const chosen = choices?.toggles?.[toggle.key];
  if (typeof chosen === 'boolean') return chosen;
  // A page for an entity the user does not have is not offered.
  if (toggle.when) return hasEntities(hass, [toggle.when], areaId);
  return toggle.default === true;
}

/**
 * Fill one page's entity slots from the user's entities.
 *
 * The page decides which slots exist; the panel type's descriptor supplies
 * what each one is (`domain`) and whether the page works without it
 * (`required`). No entity is used twice on one page.
 *
 * @param {PresetPage} page
 * @param {{ hass: any, areaId: string, areaName: string, panelTypes: any[], choices: any,
 *   preset: Preset, key: string, theme: Record<string, any>|null }} world
 * @returns {ResolvedPresetPage}
 */
function resolvePage(page, { hass, areaId, areaName, panelTypes, choices, preset, key, theme }) {
  // The preset names the page's panel type itself: a home page is a grid or a row.
  const typeKey = page.panel.type;
  const types = Array.isArray(panelTypes) ? panelTypes : [];
  const descriptor = types.find((type) => type.type_key === typeKey) || null;
  const options = descriptor?.options || [];
  const panel = clone(page.panel);
  // The key is part of the config the hub stores, not only of the resolution.
  panel.key = key;
  if (!panel.title) panel.title = areaName || preset.label;

  const ids = (domains, installation = false) => (
    areaId && !installation ? entitiesInArea(hass, areaId, domains) : domainEntities(hass, domains)
  );
  const used = new Set();
  /** @type {Set<string>} */
  const missing = new Set();
  /** @type {Set<string>} */
  const blocked = new Set();
  let slots = 0;
  let filled = 0;

  /**
   * Whether a slot the setup works without: a domain the user has no entity
   * of, or one the preset marked optional. Neither is reported as missing.
   * @param {PresetSlot} entry
   */
  const silent = (entry) => entry.optional === true
    || (!!entry.when && !hasEntities(hass, [entry.when], entry.installation ? '' : areaId));

  /**
   * An unused entity for one slot, or '' while Home Assistant has none.
   * @param {PresetSlot} entry
   */
  const take = (entry) => {
    slots += 1;
    const kind = entry.sensor;
    const preferred = kind === 'temperature' || kind === 'humidity'
      ? areaSensor(hass, areaId, kind) : '';
    const candidates = kind
      ? [preferred, ...ids(['sensor']).filter((id) => hass?.states?.[id]?.attributes?.device_class === kind)]
      : (entry.domain ? ids([entry.domain], entry.installation === true) : []);
    const id = candidates.filter(Boolean).find((candidate) => !used.has(candidate)) || '';
    if (!id) {
      if (!silent(entry)) missing.add(entry.domain || 'sensor');
      return '';
    }
    used.add(id);
    filled += 1;
    return id;
  };

  for (const option of options) {
    const value = panel[option.key];
    if (option.kind === 'item' && isSlot(value)) {
      const slotValue = /** @type {PresetSlot} */ (value);
      const id = take(slotValue);
      const filledSlot = { ...slotValue, item: id };
      delete filledSlot.domain;
      delete filledSlot.sensor;
      delete filledSlot.when;
      delete filledSlot.optional;
      delete filledSlot.installation;
      panel[option.key] = filledSlot;
      if (!id && option.required && !silent(slotValue)) blocked.add(slotValue.domain || 'sensor');
    } else if (option.kind === 'item_list' && Array.isArray(value)) {
      /** @type {any[]} */
      const entries = [];
      for (const raw of value) {
        if (!isSlot(raw)) {
          entries.push(raw);
          continue;
        }
        const id = take(raw);
        // An empty item-list entry breaks the option rules, so an unfillable slot is left out.
        if (!id) continue;
        const entry = { ...raw, item: id };
        delete entry.domain;
        delete entry.sensor;
        delete entry.when;
        delete entry.optional;
        entries.push(entry);
      }
      panel[option.key] = entries;
    } else if ((option.kind === 'str' || option.kind === 'generic')
      && typeof choices?.[option.key] === 'string') {
      // A field only the user knows, e.g. the Wi-Fi network name.
      panel[option.key] = choices[option.key];
    }
  }

  const needsInput = options
    .filter((option) => option.required === true && option.kind !== 'item' && option.kind !== 'item_list')
    .filter((option) => isBlank(panel[option.key]))
    .map((option) => ({ key: option.key, label: option.label || option.key }));

  // A page may take its own colours from the device theme, and a grid tile is
  // the one item that carries them - a tile shows the theme background until
  // the item is on. Neither overrides a colour the preset set explicitly.
  for (const [colorKey, colorValue] of Object.entries(page.colors?.(theme) || {})) {
    if (colorValue && isBlank(panel[colorKey])) panel[colorKey] = colorValue;
  }
  if (typeKey === 'grid' && Array.isArray(panel.items)) {
    const colors = tileColors(theme);
    if (Object.keys(colors).length) {
      panel.items = panel.items.map((entry) => (isBlank(entry?.back_color) ? { ...entry, ...colors } : entry));
    }
  }

  return {
    id: page.id,
    role: page.role,
    key,
    label: panel.title || page.id,
    panel,
    missing: [...missing],
    blocked: [...blocked],
    needsInput,
    filled,
    empty: slots > 0 && filled === 0,
    typeKnown: !!descriptor,
  };
}

/**
 * Resolve a preset against the user's Home Assistant: its pages with their
 * entity slots filled, the optional pages the toggles include, and the device
 * settings that make the result work - only what the device does not set
 * already, so the flow can write them when they are non-empty.
 *
 * @param {Preset} preset
 * @param {{ hass?: any, panelTypes?: any[], areaId?: string, choices?: any,
 *   deviceConfig?: Object<string, any>, taken?: Iterable<string>,
 *   theme?: Record<string, any>|null, themeId?: string }} [world] - `theme` is the
 *   chosen theme's colour map, which a preset derives its own colours from, and
 *   `themeId` the theme the device draws in afterwards
 * @returns {PresetResolution}
 */
export function resolvePreset(preset, {
  hass = null, panelTypes = [], areaId = '', choices = {}, deviceConfig = {}, taken = [],
  theme = null, themeId = '',
} = {}) {
  const area = areaId ? hass?.areas?.[areaId] || null : null;
  const areaName = area?.name || '';
  const keys = presetKeys(preset, areaName, taken);
  // Without the hub's panel type descriptors no page can be filled in, so a
  // resolution without them is never a setup that can be created.
  const types = Array.isArray(panelTypes) ? panelTypes : [];
  /** @type {Array<PresetToggle & { on: boolean, available: boolean }>} */
  const toggles = preset.toggles.map((toggle) => ({
    ...toggle,
    on: toggleOn(toggle, { hass, areaId, choices }),
    // A switch for a page that could never fill itself is not offered at all.
    available: !toggle.when || hasEntities(hass, [toggle.when], areaId),
  }));
  const on = (key) => toggles.find((toggle) => toggle.key === key)?.on === true;
  const navigation = on('navigation');

  /** @type {ResolvedPresetPage[]} */
  const pages = [];
  /** @type {ResolvedPresetPage[]} */
  const dropped = [];
  /** @type {string[]} */
  const warnings = [];
  let entityCount = 0;

  for (const page of preset.pages) {
    if (page.when && !on(page.when)) continue;
    const resolved = resolvePage(page, {
      hass, areaId, areaName, panelTypes: types, choices, preset, theme, key: keys.get(page.id) || '',
    });
    entityCount += resolved.filled;
    // An optional page that would show nothing is not worth creating; one that
    // was asked for but cannot be filled in stays, so the setup says why.
    if (page.role !== 'home' && page.role !== 'idle' && resolved.empty
      && resolved.blocked.length === 0) {
      dropped.push(resolved);
      warnings.push(t('{page} is left out: it would show nothing').replace('{page}', resolved.label));
      continue;
    }
    // Only a page the user swipes to is a navigation page; the home screen, the
    // idle panels and a page the setup leaves out are not.
    if ((page.role === 'page' && !navigation) || page.role === 'idle' || page.role === 'idle_extra') {
      resolved.panel.show_in_navigation = false;
    }
    if (resolved.missing.length) {
      warnings.push(t('{page} has no entity for: {domains}')
        .replace('{page}', resolved.label)
        .replace('{domains}', resolved.missing.join(', ')));
    }
    pages.push(resolved);
  }

  const home = pages.find((page) => page.role === 'home') || null;
  const idle = pages.find((page) => page.role === 'idle') || null;
  const idleExtras = pages.filter((page) => page.role === 'idle_extra');
  const known = new Set(pages.flatMap((page) => page.blocked));
  if (home?.empty) for (const domain of home.missing) known.add(domain);
  const blocked = [...known];
  const needsInput = pages
    .flatMap((page) => page.needsInput)
    .filter((input, index, all) => all.findIndex((other) => other.key === input.key) === index);
  // A page whose panel type the hub does not know cannot be filled in, and a
  // panel created from it would be refused when it is saved.
  const unknownTypes = pages.filter((page) => page.typeKnown === false);
  if (unknownTypes.length) {
    warnings.push(t('The panel types could not be loaded. Reload the page to set this device up.'));
  }

  /** @type {Object<string, any>} */
  const config = {};
  // The keys the device already has; a role that names a key without a panel
  // counts as unset, because the hub ignores such a reference.
  const knownKeys = [...taken].map((key) => ({ key }));
  if (home && !panelExists(deviceConfig.home_panel, knownKeys)) config.home_panel = home.key;
  if (idle && !panelExists(deviceConfig.idle_panel, knownKeys)) config.idle_panel = idle.key;
  // The idle panels after the idle page: the automatic page switch cycles
  // through them on each switch, so they need it switched on.
  const extraKeys = idleExtras.map((page) => page.key).join(',');
  if (extraKeys && deviceConfig.idle_panel_extra !== extraKeys) config.idle_panel_extra = extraKeys;
  if ((idle || idleExtras.length) && deviceConfig.use_auto_page !== true) config.use_auto_page = true;
  if (navigation && deviceConfig.show_home_button !== true) config.show_home_button = true;
  // The theme the pages draw in: the one the user picked, unless the device
  // already draws in it.
  if (themeId && deviceConfig.theme_id !== themeId) config.theme_id = themeId;

  // A home page is always created, with the entities it could fill: a room the
  // preset knows no control for yet still gets the screen it is set up on. Only
  // a required slot it could not fill (a page showing one entity) blocks it.
  const ready = (!preset.needsArea || !!areaId)
    && !!home
    && blocked.length === 0
    && needsInput.length === 0
    && unknownTypes.length === 0;

  return {
    preset: preset.key,
    area,
    areaName,
    toggles,
    pages,
    dropped,
    config,
    ready,
    blocked,
    needsInput,
    warnings,
    entityCount,
  };
}
