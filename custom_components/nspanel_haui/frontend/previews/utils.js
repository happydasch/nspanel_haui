/**
 * NSPanel HAUI - Editor - Panel preview utilities.
 *
 * Shared utility functions for panel preview renderers.
 */
import { t } from '../localize.js';
import { colorToCss } from '../color-utils.js';

/**
 * Pick a background class for the screen based on the panel's `background` option.
 * Returns a CSS class string (e.g. 'pg-preview-bg-spring') or empty string.
 */
export function backgroundClass(panel) {
  const bg = panel && panel.background;
  if (!bg || bg === 'default') return '';
  return 'pg-preview-bg-' + bg;
}

/**
 * Extract the "items" array from a panel config, defaulting to empty array.
 * Both grid and row panels store items under the `items` key.
 */
export function getItems(panel) {
  return (panel && panel.items) || [];
}

/**
 * Default device color palette (RGB565 ints), matching `haui/mapping/color.py`.
 * Only the keys that affect device-level theming are included — weather, entity,
 * alarm, and climate sub-colors are panel-type specific and not part of the
 * user-visible `color_overrides` schema.
 */
const DEFAULT_COLORS = {
  background: 6339,
  text: 55002,
  text_inactive: 29582,
  header_background: 6339,
  header_text: 65535,
  header_accent: 62694,
  component_text: 65535,
  component_active: 19773,
  component_accent: 62694,
  component_background: 8452,
};

/**
 * Build a merged device colour palette from defaults + persisted overrides.
 * Every key in the default palette is guaranteed a value.
 *
 * @param {object} host - the Lit element instance (carries _deviceConfig)
 * @returns {object.<string, string>} colour-name -> CSS colour string
 */
export function getDeviceColors(host) {
  const overrides = (host && host._deviceConfig && host._deviceConfig.color_overrides) || {};
  const merged = {};
  for (const [k, v] of Object.entries(DEFAULT_COLORS)) {
    merged[k] = colorToCss(overrides[k] !== undefined ? overrides[k] : v);
  }
  return merged;
}

/**
 * Build an inline style string that sets the device-theme CSS custom properties.
 * Applying this on the preview container lets all `var(--primary-text-color, ...)`
 * references resolve to the device's colour scheme automatically.
 *
 * @param {object} deviceColors - output of getDeviceColors()
 * @returns {string} computed inline style
 */
export function deviceThemeCss(deviceColors) {
  return [
    '--primary-text-color:' + (deviceColors.text || '#ddd'),
    '--secondary-text-color:' + (deviceColors.text_inactive || '#888'),
    '--primary-color:' + (deviceColors.component_active || '#4fc3f7'),
    '--accent-color:' + (deviceColors.header_accent || '#f69d31'),
  ].join(';');
}

/**
 * Build a CSS background-color string for a tile given item config fields.
 * Falls back to null (no custom background).
 */
export function tileBgColor(item) {
  if (!item) return null;
  const bc = item.back_color;
  if (bc != null && bc !== '' && bc !== '0') {
    const css = colorToCss(bc);
    if (css) return css;
  }
  return null;
}

/**
 * Build a CSS color string for icon/text in a tile given item config fields.
 */
export function tileIconColor(item) {
  if (!item) return null;
  // Check grid-specific text_color override first, then fall back to the
  // standard HAUIItem color override (the same field used by get_color()).
  const tc = item.text_color || item.color;
  if (tc != null && tc !== '' && tc !== '0') {
    const css = colorToCss(tc);
    if (css) return css;
  }
  return null;
}

/**
 * Extract the entity ID from an item config.
 * Items can be:
 *   - A plain string (the entity_id itself)
 *   - An object with { item: "...", icon, name, ... }
 *   - An object with { entity_id: "...", icon, name, ... }
 * Returns the entity_id string or empty string.
 */
export function itemEntityId(item) {
  if (!item) return '';
  if (typeof item === 'string') return item;
  if (typeof item.item === 'string') return item.item;
  if (typeof item.entity_id === 'string') return item.entity_id;
  return '';
}

/**
 * Domain→icon mapping for entities that don't have an explicit icon
 * attribute. Covers the most common HA domains with their default icon.
 */
const DOMAIN_DEFAULT_ICONS = {
  alarm_control_panel: 'mdi:shield',
  alert: 'mdi:alert',
  automation: 'mdi:robot',
  binary_sensor: 'mdi:radiobox-blank',
  button: 'mdi:button-pointer',
  calendar: 'mdi:calendar',
  camera: 'mdi:video',
  climate: 'mdi:thermostat',
  conversation: 'mdi:forum-outline',
  counter: 'mdi:counter',
  date: 'mdi:calendar',
  datetime: 'mdi:calendar-clock',
  device_tracker: 'mdi:account',
  fan: 'mdi:fan',
  group: 'mdi:google-circles-communities',
  humidifier: 'mdi:water-percent',
  image: 'mdi:image',
  input_boolean: 'mdi:toggle-switch',
  input_button: 'mdi:button-pointer',
  input_datetime: 'mdi:calendar-clock',
  input_number: 'mdi:ray-vertex',
  input_select: 'mdi:format-list-bulleted',
  input_text: 'mdi:form-textbox',
  lawn_mower: 'mdi:robot-mower',
  light: 'mdi:lightbulb',
  lock: 'mdi:lock',
  media_player: 'mdi:cast',
  notify: 'mdi:comment-alert',
  number: 'mdi:ray-vertex',
  persistent_notification: 'mdi:bell',
  person: 'mdi:account',
  plant: 'mdi:flower',
  remote: 'mdi:remote',
  scene: 'mdi:palette',
  schedule: 'mdi:calendar-clock',
  script: 'mdi:script-text',
  select: 'mdi:format-list-bulleted',
  sensor: 'mdi:eye',
  siren: 'mdi:bullhorn',
  stt: 'mdi:microphone-message',
  switch: 'mdi:toggle-switch-variant',
  text: 'mdi:form-textbox',
  time: 'mdi:clock',
  timer: 'mdi:timer-outline',
  todo: 'mdi:clipboard-list',
  tts: 'mdi:speaker-message',
  update: 'mdi:package-up',
  vacuum: 'mdi:robot-vacuum',
  wake_word: 'mdi:chat-sleep',
  water_heater: 'mdi:water-boiler',
  weather: 'mdi:weather-partly-cloudy',
};

/**
 * Device-class icons for domains that distinguish subtypes.
 * Values are the default icon for each device_class.
 */
const DEVICE_CLASS_ICONS = {
  cover: {
    _: 'mdi:window-open',
    awning: 'mdi:window-open',
    blind: 'mdi:blinds-horizontal',
    curtain: 'mdi:curtains',
    damper: 'mdi:circle',
    door: 'mdi:door-open',
    garage: 'mdi:garage-open',
    gate: 'mdi:gate-open',
    shade: 'mdi:roller-shade',
    shutter: 'mdi:window-shutter-open',
    window: 'mdi:window-open',
  },
  media_player: {
    _: 'mdi:cast',
    receiver: 'mdi:audio-video',
    speaker: 'mdi:speaker',
    tv: 'mdi:television',
  },
};

/**
 * Resolve an entity icon from domain, device_class and state.
 * Returns the icon string or null if unknown domain.
 */
function resolveDomainIcon(eid, stateObj) {
  if (!eid || !stateObj) return null;
  const dot = eid.indexOf('.');
  if (dot <= 0) return null;
  const domain = eid.slice(0, dot);
  const deviceClass = stateObj.attributes?.device_class;

  // Device-class-aware lookup
  const dcMap = DEVICE_CLASS_ICONS[domain];
  if (dcMap) {
    return dcMap[deviceClass] || dcMap._;
  }

  // Simple domain → default icon
  return DOMAIN_DEFAULT_ICONS[domain] || null;
}

/**
 * Normalise an item into { icon, name } for display in a tile.
 * When no icon override is set on the item, falls back to the real HA entity
 * icon from the host's state registry (host.hass.states), then to a
 * domain/device_class-based default icon.
 *
 * @param {object} item - item config with optional icon, name, entity_id
 * @param {object} [host] - optional Lit host element carrying host.hass.states
 * @returns {{ icon: string, name: string }}
 */
export function itemDisplay(item, host) {
  if (!item) return { icon: 'mdi:help-circle-outline', name: t('?') };
  const eid = itemEntityId(item);
  let icon = (item.icon && typeof item.icon === 'string' && item.icon !== '')
    ? item.icon : null;
  if (!icon && host && eid) {
    // Try the real HA entity icon (set via entity registry or attributes)
    const state = host.hass?.states?.[eid];
    if (state?.attributes?.icon) {
      icon = state.attributes.icon;
    }
    // Fall back to domain/device_class default icon
    if (!icon) {
      icon = resolveDomainIcon(eid, state);
    }
  }
  if (!icon) icon = 'mdi:help-circle-outline';
  let name = (item.name && typeof item.name === 'string' && item.name !== '')
    ? item.name : null;
  if (!name && host && eid) {
    const state = host.hass?.states?.[eid];
    if (state?.attributes?.friendly_name) {
      name = state.attributes.friendly_name;
    }
  }
  if (!name) name = eid;
  return { icon, name };
}
