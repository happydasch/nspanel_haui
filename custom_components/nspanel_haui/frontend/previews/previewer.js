/**
 * NSPanel HAUI - Static panel preview generation.
 *
 * Preview generation drives every panel card preview (user panels, system panels and
 * popup aliases, in both orientations). Instead of hand-authored per-type
 * layouts it loads the real virtual-panel layout JSON (the same files the live
 * preview uses), instantiates a NextionDisplay, jumps to the panel type's
 * physical HMI page and renders the whole page with nextion-view.js
 * (`renderDisplay`), so a preview is the actual HMI screen scaled to the card.
 *
 * Dynamic values (the hub's populated text, sliders and selections) cannot be
 * recreated without a live device/entity session: the static preview is a
 * deterministic illustration, so `seedPreviewState` writes representative
 * values derived from the panel config (titles, entity items + names/icons)
 * and, for pages without items, a fixed placeholder clock/date. The static
 * path never starts a VirtualPanelSession and opens no WebSocket; it only
 * fetches the committed layout + icon-map assets.
 */
import { t } from '../localize.js';
import { NextionDisplay } from '../virtual/nextion-display.js';
import {
  devicePalette,
  getItems,
  itemColorRgb565,
  itemDisplay,
  itemDisplayType,
  itemEntityState,
  itemStateColor,
  itemSupportedFeatures,
} from './utils.js';
import { noopScheduler } from './simulator.js';

const MODULE_URL = import.meta.url;

// ---------------------------------------------------------------------------
// Page resolution and shared display helpers
// ---------------------------------------------------------------------------

/** Physical page id fallback (type key -> id), mirrored from the descriptors. */
const TYPE_PAGE_ID = {
  system: 0,
  blank: 1,
  system_about: 2,
  system_settings: 3,
  notify: 4,
  select: 5,
  weather: 6,
  clock: 7,
  clocktwo: 8,
  grid: 9,
  row: 10,
  qr: 11,
  timer: 12,
  light: 13,
  media: 14,
  vacuum: 15,
  climate: 16,
  alarm: 17,
  popup_unlock: 17,
  cover: 18,
};

/**
 * Resolve the physical Nextion page id for a panel.
 * Prefers the descriptor/system-entry `page_id` (authoritative), falling back
 * to a static map so a preview still works when the metadata is not present.
 *
 * @param {object} panel     - the panel config (has `.type`)
 * @param {object|null} panelType - matched descriptor or system entry
 * @returns {number}
 */
export function resolvePageId(panel, panelType) {
  if (panelType && panelType.page_id != null && panelType.page_id !== '') {
    return Number(panelType.page_id);
  }
  const typeKey = (panel && panel.type) || (panelType && panelType.type_key) || (panelType && panelType.type);
  return TYPE_PAGE_ID[typeKey] != null ? TYPE_PAGE_ID[typeKey] : 0;
}

/** The panel's type key from either the panel config or its descriptor/entry. */
function typeKeyOf(panel, panelType) {
  return (panel && panel.type)
    || (panelType && panelType.type_key)
    || (panelType && panelType.key)
    || (panelType && panelType.type)
    || '';
}

/** Whether the page/panel shows the popup variant of its physical page. */
function isPopup(typeKey) {
  return String(typeKey || '').startsWith('popup_');
}

let PREVIEW_STATE_PROMISE = null;

/** Safe widget text write; ignores widgets missing from the page. */
function setTxt(display, name, text) {
  const comp = display.component(name);
  if (comp && text != null && String(text) !== '') {
    display.exec(`${name}.txt="${String(text).replace(/"/g, '\\"')}"`);
  }
}

/** Safe visibility; ignores widgets missing from the page. */
function show(display, name, visible = true) {
  if (display.component(name)) display.exec(`vis ${name},${visible ? 1 : 0}`);
}

const setComponentVisible = show;

/** Char for an mdi icon name, or a fallback char from the map. */
function charForIcon(byName, mdiName, fallbackChar = '') {
  if (mdiName && typeof mdiName === 'string' && mdiName.startsWith('mdi:')) {
    const found = byName[mdiName.slice(4)];
    if (found) return found;
  }
  return fallbackChar;
}

const ITEM_ICON_FALLBACK = 'lightbulb';

/** First available representative item icon char (deterministic). */
function fallbackIconChar(byName) {
  return byName[ITEM_ICON_FALLBACK] || Object.values(byName)[0] || '';
}

function loadJson(url, loader) {
  if (loader) return Promise.resolve(loader(url));
  return fetch(url).then((response) => {
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  });
}

// ---------------------------------------------------------------------------
// Deterministic fallback state
// ---------------------------------------------------------------------------

/**
 * Populate a sequential item group (e.g. grid `g<N>`, row `r<N>` or the
 * `bEntity<N>` buttons) from the panel's item config.
 */
function seedItemGroup(display, panel, opts, prefix, count, { power = false } = {}) {
  const items = getItems(panel).slice(0, count);
  const byName = opts.byName || {};
  const fallbackChar = fallbackIconChar(byName);
  for (let i = 0; i < count; i += 1) {
    const n = i + 1;
    const name = `${prefix}${n}`;
    if (items[i]) {
      const { icon, name: label } = itemDisplay(items[i], opts.host);
      show(display, `${name}Name`, true);
      show(display, `${name}Icon`, true);
      if (prefix === 'g' || prefix === 'r') show(display, `${prefix}${n}Btn`, power);
      setTxt(display, `${name}Name`, label);
      const ch = charForIcon(byName, icon, fallbackChar);
      if (ch) setTxt(display, `${name}Icon`, ch);
    } else {
      // Empty tile: hide it and its button (the HMI preinitialise hides these).
      show(display, `${name}Name`, false);
      show(display, `${name}Icon`, false);
      if (prefix === 'g' || prefix === 'r') show(display, `${prefix}${n}Btn`, false);
    }
  }
}

function seedClock(display, panel, opts) {
  setTxt(display, 'tTime', '10:08');
  setTxt(display, 'tDate', 'Mon 24');
  seedItemGroup(display, panel, opts, 'bEntity', 6);
}

function seedWeather(display) {
  setTxt(display, 'tTime', '10:08');
  setTxt(display, 'tDate', 'Mon 24');
  setTxt(display, 'tMainText', '18°');
  setTxt(display, 'tSubText', 'Partly cloudy');
  setTxt(display, 'd1Val', '');
  setTxt(display, 'd2Val', '');
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  for (let i = 1; i <= days.length; i += 1) setTxt(display, `f${i}Name`, days[i - 1]);
}

function seedLight(display, panel) {
  setTxt(display, 'tInfo', 'Brightness');
  if (display.component('hBrightness')) display.exec('hBrightness.val=60');
  if (display.component('hColorTemp')) display.exec('hColorTemp.val=50');
}

function seedClimate(display) {
  setTxt(display, 'tTemp', '21.0');
  setTxt(display, 'tUnit', '°C');
  if (display.component('xSet')) display.exec('xSet.val=210');
  show(display, 'btMode2', true);
}

function seedNotify(display) {
  setTxt(display, 'tText', 'Notification preview');
  show(display, 'bBtnLeft', true);
  show(display, 'bBtnRight', false);
}

function seedSelect(display, panel) {
  const n = Math.max(1, Math.min(getItems(panel).length || 4, 4));
  for (let i = 1; i <= 4; i += 1) show(display, `bSelFull${i}`, i <= n);
  show(display, 'bSel1', true);
}

function seedTimer(display) {
  setTxt(display, 'tMin', '0');
  setTxt(display, 'tSpace', ':');
  setTxt(display, 'tSec', '00');
  show(display, 'bStart', true);
}

function seedGrid(display, panel, opts) {
  seedItemGroup(display, panel, opts, 'g', 6, { power: true });
}

function seedRow(display, panel, opts) {
  seedItemGroup(display, panel, opts, 'r', 5);
}

function seedMedia(display, panel, opts) {
  const items = getItems(panel).slice(0, 3);
  const byName = opts.byName || {};
  const fallbackChar = fallbackIconChar(byName);
  for (let i = 0; i < 3; i += 1) {
    const n = i + 1;
    show(display, `m${n}Btn`, true);
    show(display, `m${n}Icon`, true);
    show(display, `m${n}Name`, true);
    if (items[i]) {
      const { icon, name } = itemDisplay(items[i], opts.host);
      setTxt(display, `m${n}Name`, name);
      const ch = charForIcon(byName, icon, fallbackChar);
      if (ch) setTxt(display, `m${n}Icon`, ch);
    }
  }
  setTxt(display, 'tMTitle', 'Playing now');
  setTxt(display, 'tMInterpret', 'Artist');
}

function seedVacuum(display, panel, opts) {
  seedItemGroup(display, panel, opts, 'bEntity', 6);
  setTxt(display, 'tStatus', 'Cleaning');
  show(display, 'bAction', true);
}

function seedAbout(display) {
  setTxt(display, 'tDeviceName', 'Living Room Panel');
  setTxt(display, 'tTftVersVal', '4.3"');
  setTxt(display, 'tYamlVersVal', '0.4.5');
}

function seedSettings(display) {
  setTxt(display, 'tBrghtPct', '60%');
  setTxt(display, 'tBrghtDimPct', '30%');
  if (display.component('hBrght')) display.exec('hBrght.val=60');
  if (display.component('hBrghtDim')) display.exec('hBrghtDim.val=30');
}

function seedAlarm(display, opts) {
  show(display, 'bKey1', true);
  show(display, 'bKey2', true);
  show(display, 'bKey3', true);
  show(display, 'b1Fnc', !opts.popup);
}

/**
 * Seed representative, deterministic state for the current display page.
 * `opts` carries `{ byName, host, type }` for item resolution. Values that
 * cannot be known without a live entity session are fixed placeholders; pages
 * without special handling keep their HMI defaults.
 */
export function seedPreviewState(display, panel, panelType, opts = {}) {
  const typeKey = opts.typeKey || typeKeyOf(panel, panelType);
  const popup = opts.popup || isPopup(typeKey);
  // Popup aliases seed their base page content.
  const baseType = popup ? typeKey.replace(/^popup_/, '') : typeKey;
  opts = { ...opts, popup };

  const title = (panel && panel.title) || '';
  const page = display.page ? display.page.name : '';
  if (title && TITLE_PAGES.has(baseType)) {
    setTxt(display, 'tTitle', title);
  }

  const seed = PREVIEW_SEEDERS[page];
  if (seed) seed(display, panel, opts);
}

const TITLE_PAGES = new Set([
  'grid', 'row', 'qr', 'timer', 'light', 'media', 'vacuum', 'climate', 'cover',
  'notify', 'select', 'settings', 'about',
]);

const PREVIEW_SEEDERS = {
  grid: seedGrid,
  row: seedRow,
  clock: seedClock,
  weather: seedWeather,
  light: seedLight,
  climate: seedClimate,
  media: seedMedia,
  vacuum: seedVacuum,
  select: seedSelect,
  notify: seedNotify,
  timer: seedTimer,
  alarm: seedAlarm,
  about: seedAbout,
  settings: seedSettings,
};

// ---------------------------------------------------------------------------
// Captured hub state
// ---------------------------------------------------------------------------

/**
 * Memoised preview-state loader. `preview_state.json` holds the hub's own
 * display commands per page (colours, default values, control visibility),
 * captured by scripts/gen_preview_state/gen_preview_state.py.
 */
export function loadPreviewState(loader) {
  if (!PREVIEW_STATE_PROMISE) {
    PREVIEW_STATE_PROMISE = loadJson(new URL('../virtual/preview_state.json', MODULE_URL), loader)
      .catch((err) => {
        PREVIEW_STATE_PROMISE = null;
        throw err;
      });
  }
  return PREVIEW_STATE_PROMISE;
}

/** The snapshot entry for a page id, if captured. */
export function previewStateFor(state, pageId) {
  return (state && state[String(pageId)]) || null;
}

/**
 * Replay the hub's captured commands for a page. This is what makes previews
 * show the real widget colours, values and visibility (the HMI hides most
 * widgets until the hub shows them).
 *
 * `colorMap` ({defaultRgb565: overrideRgb565}) swaps the device palette for the
 * user's colour overrides, so a preview matches the configured theme.
 */
export function applyPreviewState(display, entry, colorMap, skip) {
  if (!entry || !Array.isArray(entry.commands)) return false;
  const replayed = skip ? entry.commands.filter((cmd) => !skip(cmd)) : entry.commands;
  const commands = colorMap && Object.keys(colorMap).length
    ? replayed.map((cmd) => substituteColors(cmd, colorMap))
    : replayed;
  display.exec(commands);
  return true;
}

/** Replace palette colour values in a command (`obj.pco=6339`, `cls 4226`). */
export function substituteColors(command, colorMap) {
  return String(command)
    .replace(/(^|\s)(cls\s+)(\d+)$/, (m, pre, head, value) => (
      colorMap[Number(value)] !== undefined ? `${pre}${head}${colorMap[Number(value)]}` : m
    ))
    .replace(/\.(pco|bco|pco2|bco2)=(\d+)/g, (m, attr, value) => (
      colorMap[Number(value)] !== undefined ? `.${attr}=${colorMap[Number(value)]}` : m
    ));
}

// ---------------------------------------------------------------------------
// Configured panel content helpers
// ---------------------------------------------------------------------------

/** Colour commands for one widget: text/back, pressed variants. */
function colorCmds(display, name, { pco, bco, pco2, bco2 }) {
  if (!display.component(name)) return [];
  const cmds = [];
  if (pco != null) cmds.push(`${name}.pco=${pco}`);
  if (pco2 != null) cmds.push(`${name}.pco2=${pco2}`);
  if (bco != null) cmds.push(`${name}.bco=${bco}`);
  if (bco2 != null) cmds.push(`${name}.bco2=${bco2}`);
  return cmds;
}

/** Hub `GridPage.is_item_active`: entities are active when on or playing. */
function isItemActive(item, host) {
  if (!item || typeof item !== 'object') return false;
  const eid = item.item || item.entity_id;
  const state = eid ? host?.hass?.states?.[eid]?.state : null;
  return state === 'on' || state === 'playing';
}

/** Hide the named widgets that exist on the current page. */
function hideWidgets(display, names) {
  const cmds = names.filter((name) => display.component(name)).map((name) => `vis ${name},0`);
  if (cmds.length) display.exec(cmds);
}

/** The hub trims grid/row labels to 15 characters (`GridPage.LEN_NAME`). */
const NAME_LIMIT = 15;
const trimName = (text) => (text.length > NAME_LIMIT ? text.slice(0, NAME_LIMIT) : text);

/** Option values the editor may store as booleans or as strings. */
function asBool(value) {
  if (typeof value === 'string') {
    return ['true', '1', 'yes', 'on'].includes(value.trim().toLowerCase());
  }
  return Boolean(value);
}

/** Whether a tile shows its power button (hub: `show_power_button`). */
const hasPowerButton = (item) => Boolean(item) && asBool(item.show_power_button);

/**
 * Grid tiles: name/icon plus the per-item colours the panel configures
 * (text_color, back_color, pressed variants, power colour/visibility).
 */
function applyGridContent(display, panel, opts) {
  const items = getItems(panel).slice(0, 6);
  const byName = opts.byName || {};
  const palette = devicePalette(opts.host);
  const fallbackChar = fallbackIconChar(byName);
  for (let i = 0; i < 6; i += 1) {
    const n = i + 1;
    const item = items[i];
    if (!item) {
      // Unused tile: the hub hides every component of the slot.
      hideWidgets(display, ['Btn', 'Icon', 'Name', 'Overlay', 'Power'].map((suffix) => `g${n}${suffix}`));
      continue;
    }
    const { icon, name } = itemDisplay(item, opts.host);
    // Hub defaults (`get_grid_colors`), then the item's own overrides.
    const textColor = itemColorRgb565(item, 'text_color', opts.host)
      ?? itemColorRgb565(item, 'color', opts.host)
      ?? palette.text;
    const backColor = itemColorRgb565(item, 'back_color', opts.host) ?? palette.background;
    const colorPressed = itemColorRgb565(item, 'color_pressed', opts.host)
      ?? palette.component_text;
    const backPressed = itemColorRgb565(item, 'back_color_pressed', opts.host)
      ?? palette.component_pressed;
    const ch = charForIcon(byName, icon, fallbackChar);
    const cmds = [
      `vis g${n}Btn,1`, `vis g${n}Icon,1`, `vis g${n}Name,1`,
      `g${n}Name.txt="${trimName(name).replace(/"/g, '\\"')}"`,
    ];
    if (ch) cmds.push(`g${n}Icon.txt="${ch}"`);
    // The hub colours the icon by the item's state (update_grid_entry),
    // and the name/button by its text colour.
    const iconColor = itemStateColor(item, opts.host, palette);
    cmds.push(...colorCmds(display, `g${n}Name`, { pco: textColor, bco: backColor }));
    cmds.push(...colorCmds(display, `g${n}Icon`, { pco: iconColor, bco: backColor }));
    cmds.push(...colorCmds(display, `g${n}Btn`,
      { pco: textColor, bco: backColor, pco2: colorPressed, bco2: backPressed }));
    display.exec(cmds);
    // Power button: visible only when configured, coloured by power_color.
    const power = `g${n}Power`;
    if (display.component(power)) {
      if (hasPowerButton(item)) {
        const active = isItemActive(item, opts.host);
        const powerColor = itemColorRgb565(item, 'power_color', opts.host)
          ?? (active ? palette.component_active : backPressed);
        display.exec([
          `vis ${power},1`,
          ...colorCmds(display, power, { pco: powerColor, bco: backColor }),
        ]);
      } else {
        display.exec(`vis ${power},0`);
      }
    }
    display.exec(`ref g${n}Icon`);
  }
}

/** Row entries: the common per-item colours, without the power button. */
/** Detail widget names on a row slot (`r1Slider`, `r1BtnUp`, …). */
const ROW_DETAIL = ['BtnUp', 'BtnStop', 'BtnDown', 'Slider', 'SliderTxt', 'BtnText', 'Toggle'];

/**
 * Row entries: name/icon plus the control the item's type calls for — the same
 * mapping as the hub's `RowPage.get_item_display_type` / `set_row_entry`:
 * cover → three buttons, button/timer/text → the value cell, number → slider,
 * switch/light/… → toggle. Every other detail widget of the slot is hidden, so
 * a slot never shows a control left over from the sample.
 */
function applyRowContent(display, panel, opts) {
  const items = getItems(panel).slice(0, 5);
  const byName = opts.byName || {};
  const palette = devicePalette(opts.host);
  const fallbackChar = fallbackIconChar(byName);
  for (let i = 0; i < 5; i += 1) {
    const n = i + 1;
    const item = items[i];
    if (!item) {
      hideWidgets(display, ['Icon', 'Name', 'Overlay', ...ROW_DETAIL].map((s) => `r${n}${s}`));
      continue;
    }
    const { icon, name } = itemDisplay(item, opts.host);
    const textColor = itemColorRgb565(item, 'text_color', opts.host) ?? palette.text;
    const backColor = itemColorRgb565(item, 'back_color', opts.host) ?? palette.background;
    const iconColor = itemStateColor(item, opts.host, palette);
    const ch = charForIcon(byName, icon, fallbackChar);
    const cmds = [
      `vis r${n}Icon,1`, `vis r${n}Name,1`, `vis r${n}Overlay,1`,
      `r${n}Name.txt="${trimName(name).replace(/"/g, '\\"')}"`,
    ];
    if (ch) cmds.push(`r${n}Icon.txt="${ch}"`);
    cmds.push(...colorCmds(display, `r${n}Name`, { pco: textColor, bco: backColor }));
    cmds.push(...colorCmds(display, `r${n}Icon`, { pco: iconColor, bco: backColor }));
    display.exec(cmds);

    const type = itemDisplayType(item);
    const show = rowDetailVisibility(type);
    const hide = ROW_DETAIL.filter((suffix) => !show.includes(suffix))
      .map((suffix) => `r${n}${suffix}`);
    hideWidgets(display, hide);
    if (show.length) display.exec(show.map((suffix) => `vis r${n}${suffix},1`));

    if (type === 'toggle') {
      const state = itemEntityState(item, opts.host);
      display.exec(`r${n}Toggle.val=${state === 'off' ? 0 : 1}`);
    } else if (type === 'slider') {
      display.exec(rowSliderCommands(display, item, n, opts));
    } else if (show.includes('BtnText')) {
      // Value cell: text/timer use the text colour, buttons the active colour.
      const valueState = itemEntityState(item, opts.host);
      const valueColor = type === 'button' ? palette.component_active : palette.component_text;
      const valueCmds = [];
      if (valueState) {
        valueCmds.push(`r${n}BtnText.txt="${valueState.replace(/"/g, '\\"')}"`);
      }
      valueCmds.push(`r${n}BtnText.pco=${valueColor}`, `r${n}BtnText.bco=${backColor}`);
      valueCmds.push(`r${n}BtnText.bco2=${type === 'button'
        ? palette.component_pressed : backColor}`);
      display.exec(valueCmds);
    }
  }
}

/** Which detail widgets a row slot shows for an item display type. */
function rowDetailVisibility(type) {
  if (type === 'cover') return ['BtnUp', 'BtnStop', 'BtnDown'];
  if (type === 'toggle') return ['Toggle'];
  if (type === 'slider') return ['Slider', 'SliderTxt'];
  return ['BtnText'];
}

/**
 * Slider value/text for a row entry. The Nextion slider holds integers, so the
 * hub scales by the step's decimals; mirror that here.
 */
function rowSliderCommands(display, item, n, opts) {
  const eid = itemEntityIdOf(item);
  const state = eid ? opts.host?.hass?.states?.[eid] : null;
  const attributes = (state && state.attributes) || {};
  const min = Number(attributes.min ?? 0);
  const max = Number(attributes.max ?? 100);
  const step = Number(attributes.step ?? 1);
  const decimals = step >= 1 ? 0 : String(step).split('.')[1].length;
  const factor = 10 ** decimals;
  const offset = Math.round(min * factor);
  const raw = state && state.state;
  const numeric = raw != null && raw !== '' && Number.isFinite(Number(raw));
  const value = numeric ? Math.round(Number(raw) * factor) - offset : 0;
  const text = numeric ? String(raw) : (raw || '');
  const cmds = [`r${n}Slider.minval=${Math.round(min * factor)}`];
  cmds.push(`r${n}Slider.maxval=${Math.round(max * factor)}`);
  cmds.push(`r${n}Slider.val=${value}`);
  cmds.push(`r${n}SliderTxt.txt="${text.replace(/"/g, '\\"')}"`);
  return cmds.filter((cmd) => display.component(cmd.split('.')[0]));
}

/** The entity id of an item config (empty for internal items). */
function itemEntityIdOf(item) {
  if (!item || typeof item !== 'object') return '';
  if (typeof item.item === 'string' && !item.item.includes(':')) return item.item;
  if (typeof item.entity_id === 'string') return item.entity_id;
  return '';
}

/**
 * A sequential button group. `bEntity<N>` are single buttons carrying the icon
 * as their text; `m<N>` media sources have `Btn`/`Icon`/`Name`/`Overlay` parts.
 */
function applyNamedButtons(display, items, prefix, opts, count) {
  const byName = opts.byName || {};
  const palette = devicePalette(opts.host);
  const fallbackChar = fallbackIconChar(byName);
  // Hide the slots this panel does not fill (the sample may have shown more).
  for (let i = Math.min(count, items.length); i < count; i += 1) {
    const n = i + 1;
    hideWidgets(display, prefix === 'bEntity'
      ? [`${prefix}${n}`]
      : [`${prefix}${n}Name`, `${prefix}${n}Icon`, `${prefix}${n}Btn`, `${prefix}${n}Overlay`]);
  }
  for (let i = 0; i < Math.min(count, items.length); i += 1) {
    const n = i + 1;
    const item = items[i];
    const { icon, name } = itemDisplay(item, opts.host);
    const ch = charForIcon(byName, icon, fallbackChar);
    if (prefix === 'bEntity') {
      const color = itemStateColor(item, opts.host, palette);
      const cmds = [`vis ${prefix}${n},1`];
      if (ch) cmds.push(`${prefix}${n}.txt="${ch}"`);
      cmds.push(`${prefix}${n}.pco=${color}`);
      display.exec(cmds);
      continue;
    }
    const cmds = [`vis ${prefix}${n}Name,1`, `vis ${prefix}${n}Icon,1`, `vis ${prefix}${n}Btn,1`];
    cmds.push(`${prefix}${n}Name.txt="${name.replace(/"/g, '\\"')}"`);
    if (ch) cmds.push(`${prefix}${n}Icon.txt="${ch}"`);
    display.exec(cmds);
  }
}

/** `MediaPlayerFeatures` (haui/features.py). */
const MEDIA = {
  PAUSE: 1, VOLUME_SET: 4, PREVIOUS_TRACK: 16, NEXT_TRACK: 32, TURN_ON: 128,
  PLAY: 16384, SHUFFLE_SET: 32768, REPEAT_SET: 262144,
};

/** `VacuumFeatures` (haui/features.py). */
const VACUUM = { PAUSE: 4, STOP: 8, RETURN_HOME: 16, FAN_SPEED: 32, LOCATE: 512, START: 8192 };

/** Icon chars for the media controls, resolved through the display icon map. */
const MEDIA_ICONS = {
  shuffle: 'shuffle',
  shuffle_disabled: 'shuffle-disabled',
  repeat: 'repeat',
  repeat_one: 'repeat-once',
  repeat_off: 'repeat-off',
  play: 'play',
  pause: 'pause',
  stop: 'stop',
  power: 'power',
  prev: 'skip-previous',
  next: 'skip-next',
  vol_down: 'volume-minus',
  vol_up: 'volume-plus',
};

function iconChar(byName, key) {
  const name = MEDIA_ICONS[key];
  return name ? charForIcon(byName, `mdi:${name}`) : '';
}

/** Whether the entity reports a feature bit; `null` when unknown (show it). */
function supports(features, bit) {
  if (features === null || features === undefined) return true;
  return (features & bit) !== 0;
}

/** Show a widget with an icon, or hide it. */
function showControl(display, byName, name, visible, iconKey) {
  if (!display.component(name)) return;
  if (!visible) {
    display.exec(`vis ${name},0`);
    return;
  }
  const cmds = [`vis ${name},1`];
  const ch = iconKey ? iconChar(byName, iconKey) : '';
  if (ch) cmds.push(`${name}.txt="${ch}"`);
  display.exec(cmds);
}

/**
 * Media controls. The hub shows each button only when the configured media
 * player supports the matching feature (`MediaPlayerFeatures`), so the
 * preview must recompute that from the panel's entity rather than keep the
 * sample player's set.
 */
function applyMediaControls(display, panel, opts) {
  const item = panel.item || null;
  const features = itemSupportedFeatures(item, opts.host);
  const state = itemEntityState(item, opts.host);
  const byName = opts.byName || {};
  showControl(display, byName, 'bShuffle', supports(features, MEDIA.SHUFFLE_SET), 'shuffle_disabled');
  showControl(display, byName, 'bRepeat', supports(features, MEDIA.REPEAT_SET), 'repeat_off');
  showControl(display, byName, 'bPlay', supports(features, MEDIA.PLAY | MEDIA.PAUSE),
    state === 'playing' ? 'pause' : 'play');
  showControl(display, byName, 'bPrev', supports(features, MEDIA.PREVIOUS_TRACK), 'prev');
  showControl(display, byName, 'bNext', supports(features, MEDIA.NEXT_TRACK), 'next');
  const volume = supports(features, MEDIA.VOLUME_SET);
  showControl(display, byName, 'bVolDown', volume, 'vol_down');
  showControl(display, byName, 'bVolUp', volume, 'vol_up');
  if (display.component('hVolume')) display.exec(`vis hVolume,${volume ? 1 : 0}`);
  // The device's power control is the header function button (bFncRSec); the
  // page's own bPower is unused by the hub and must stay hidden.
  showControl(display, byName, 'bPower', false);
  if (item) {
    const { name } = itemDisplay(item, opts.host);
    if (name) display.exec(`tMTitle.txt="${name.replace(/"/g, '\\"')}"`);
  }
}

/** Labels the hub uses for vacuum states (`get_state_translation`). */
const VACUUM_STATES = {
  cleaning: 'Cleaning',
  docked: 'Docked',
  error: 'Error',
  idle: 'Idle',
  off: 'Off',
  on: 'On',
  paused: 'Paused',
  returning: 'Returning to dock',
};

/**
 * Vacuum controls: fan/action/home/locate are feature-gated by the configured
 * vacuum entity, and `tStatus` shows its state.
 */
function applyVacuumControls(display, panel, opts) {
  const item = panel.item || null;
  const features = itemSupportedFeatures(item, opts.host);
  const state = itemEntityState(item, opts.host);
  const byName = opts.byName || {};
  const palette = devicePalette(opts.host);

  /**
   * The hub's `get_button_colors`/`button_color_args`: an active control is
   * `component_active`, a disabled one `text_disabled`; the pressed background
   * lifts only while active. `touch` matches (a disabled control ignores taps).
   */
  const button = ({ name, visible, active, iconKey, color }) => {
    if (!display.component(name)) return;
    if (!visible) {
      display.exec(`vis ${name},0`);
      return;
    }
    const textColor = color ?? (active ? palette.component_active : palette.text_disabled);
    const cmds = [
      `vis ${name},1`,
      `tsw ${name},${active ? 1 : 0}`,
      `${name}.pco=${textColor}`,
      `${name}.pco2=${active ? palette.component_text : palette.text_disabled}`,
      `${name}.bco2=${active ? palette.component_pressed : palette.background}`,
    ];
    const ch = iconKey ? iconChar(byName, iconKey) : '';
    if (ch) cmds.push(`${name}.txt="${ch}"`);
    display.exec(cmds);
  };

  // Status text: the translated state, as the hub shows it.
  if (state && display.component('tStatus')) {
    const label = VACUUM_STATES[state] || state.charAt(0).toUpperCase() + state.slice(1);
    display.exec(`tStatus.txt="${label.replace(/"/g, '\\"')}"`);
  }

  // The action button's icon follows the state: pause while working (with
  // PAUSE), stop while working (with STOP), play to start when docked/idle.
  const cleaning = state === 'cleaning' || state === 'returning';
  let actionIcon = 'play';
  let actionActive = false;
  if (cleaning) {
    if (supports(features, VACUUM.PAUSE)) {
      actionIcon = 'pause';
      actionActive = true;
    } else if (supports(features, VACUUM.STOP)) {
      actionIcon = 'stop';
      actionActive = true;
    }
  } else if (supports(features, VACUUM.START)) {
    actionActive = true;
  }
  // Visibility is the feature gate (`set_function_component(..., visible=…)`);
  // the state only decides whether the control is touchable and bright.
  button({
    name: 'bAction', visible: supports(features, VACUUM.START),
    active: actionActive, iconKey: actionIcon,
  });
  button({
    name: 'bFan', visible: supports(features, VACUUM.FAN_SPEED),
    active: true, iconKey: 'fan',
  });
  button({
    name: 'bHome', visible: supports(features, VACUUM.RETURN_HOME),
    active: state !== 'docked', iconKey: 'home',
  });
  button({
    name: 'bLocate', visible: supports(features, VACUUM.LOCATE),
    active: supports(features, VACUUM.LOCATE), iconKey: 'locate',
    color: palette.component_accent,
  });

  // The battery level rides on the header's right-secondary function button,
  // fed by the panel's optional `battery_sensor` — never by the vacuum itself.
  applyVacuumBattery(display, panel, opts);
}

/** Binary-search-free MDI battery icon step, like the hub's `_battery_icon_name`. */
function batteryIconName(level) {
  const pct = Number(level);
  if (!Number.isFinite(pct)) return 'battery';
  const step = Math.round(Math.max(0, Math.min(100, pct)) / 10) * 10;
  return `battery-${step}`;
}

/** Resolve the first configured value of an option (list or single). */
function firstRef(value) {
  const ref = Array.isArray(value) ? value[0] : value;
  if (!ref) return '';
  if (typeof ref === 'string') return ref.includes(':') ? '' : ref;
  return typeof ref.item === 'string' ? ref.item : '';
}

function applyVacuumBattery(display, panel, opts) {
  const eid = firstRef(panel.battery_sensor);
  const state = eid && opts.host?.hass?.states?.[eid];
  if (!state || !display.component('bFncRSec')) return;
  // A sensor may publish its own `icon`; otherwise derive one from the level.
  const icon = (state.attributes && state.attributes.icon) || `mdi:${batteryIconName(state.state)}`;
  const byName = opts.byName || {};
  // Fall back to the plain battery glyph; without any icon, leave the header
  // slot hidden rather than showing an unrelated sample icon.
  const ch = charForIcon(byName, icon, charForIcon(byName, 'mdi:battery', ''));
  if (!ch) return;
  display.exec(['vis bFncRSec,1', `bFncRSec.txt="${ch}"`]);
}

/**
 * Notification severity defaults: the controller falls back to these icons when
 * a notification carries none, and colours them by severity
 * (`_NOTIF_TYPE_COLORS` in the notify page).
 */
const NOTIF_TYPES = {
  info: { icon: 'information-outline', color: 'component_text' },
  warning: { icon: 'alert-outline', color: 'header_accent' },
  critical: { icon: 'alert-octagon-outline', color: 'component_active' },
};

/** Font size the hub picks for a message when `text_size` is "auto". */
function notifyFontSize(message) {
  if (message.length < 50) return 3;   // large
  if (message.length < 150) return 2;  // medium
  return 1;                            // small
}

/**
 * Notification popup content.
 *
 * A notification stores none of its content in the panel config — the hub
 * renders it from the service call — so a preview would otherwise be blank.
 * Show the panel's own icon/buttons when it configures them, and a
 * representative example message, laid out exactly as the hub does it.
 */
function applyNotifyContent(display, panel, opts) {
  const byName = opts.byName || {};
  const palette = devicePalette(opts.host);
  const type = String(panel.notif_type || 'info');
  const severity = NOTIF_TYPES[type] || NOTIF_TYPES.info;

  // Icon: the configured one, else the severity default (hub fallback).
  const iconChar = charForIcon(byName, panel.icon || `mdi:${severity.icon}`, '');
  if (iconChar && display.component('tIcon')) {
    const color = itemColorRgb565(panel, 'icon_color', opts.host) ?? palette[severity.color];
    display.exec(['vis tIcon,1', `tIcon.txt="${iconChar}"`, `tIcon.pco=${color}`]);
  }

  // Message: an explicit text when the panel has one, else an example.
  const message = String(panel.notification
    || t('Example notification: your message text appears here.'));
  if (display.component('tText')) {
    display.exec([
      `tText.font=${notifyFontSize(message)}`,
      `tText.txt="${message.replace(/"/g, '\\"')}"`,
      'vis tText,1',
    ]);
  }

  // The action buttons are part of the notification, not the panel: show each
  // one only when the panel provides it, like the hub.
  for (const [component, key] of [['bBtnLeft', 'btn_left'], ['bBtnRight', 'btn_right']]) {
    if (!display.component(component)) continue;
    const btnChar = panel[key] ? charForIcon(byName, String(panel[key]), '') : '';
    if (!btnChar) {
      display.exec(`vis ${component},0`);
      continue;
    }
    display.exec([
      `vis ${component},1`,
      `${component}.txt="${btnChar}"`,
      `${component}.pco=${itemColorRgb565(panel, `${key}_color`, opts.host)
        ?? palette.component_text}`,
      `${component}.bco=${itemColorRgb565(panel, `${key}_back_color`, opts.host)
        ?? palette.background}`,
    ]);
  }
}

const HEADER_BUTTONS = {
  leftPrimary: 'bFncLPri',
  leftSecondary: 'bFncLSec',
  rightPrimary: 'bFncRPri',
  rightSecondary: 'bFncRSec',
};

function setHeaderButton(display, component, icon, opts, accent = false) {
  if (!display.component(component)) return;
  const iconCharValue = icon && opts.byName ? opts.byName[icon.replace(/^mdi:/, '')] : '';
  if (icon && !iconCharValue) return;

  const palette = devicePalette(opts.host);
  const cmds = [`vis ${component},${icon ? 1 : 0}`];
  if (icon) {
    cmds.push(`${component}.txt="${iconCharValue}"`);
    cmds.push(`${component}.pco=${accent ? palette.header_accent : palette.header_text}`);
    cmds.push(`${component}.bco=${palette.header_background}`);
  }
  display.exec(cmds);
}

function navigationPanelCount(host) {
  if (!host || typeof host._devicePanels !== 'function') return null;
  const panels = host._devicePanels();
  if (!Array.isArray(panels)) return null;
  return panels.filter((item) => item.show_in_navigation !== false).length;
}

function moveHeaderButton(display, sourceName, targetName) {
  const source = display.component(sourceName);
  const target = display.component(targetName);
  if (!source || !target) return;

  const cmds = [];
  if (source.attrs.txt !== undefined && String(source.attrs.txt) !== '') {
    setTxt(display, targetName, source.attrs.txt);
  }
  for (const attr of ['pco', 'bco']) {
    if (source.attrs[attr] !== undefined) cmds.push(`${targetName}.${attr}=${source.attrs[attr]}`);
  }
  cmds.push(`vis ${targetName},${source.hidden ? 0 : 1}`);
  cmds.push(`vis ${sourceName},0`);
  display.exec(cmds);
}

// ---------------------------------------------------------------------------
// Navigation-owned header buttons
// ---------------------------------------------------------------------------

/** Recompute navigation-owned header slots using the current panel settings. */
function applyHeaderFunctionButtons(display, panel, panelType, opts) {
  if (!panel) return;
  const typeKey = typeKeyOf(panel, panelType);
  if (typeKey === 'system' || typeKey.startsWith('system_')) return;

  const deviceConfig = opts.host?._deviceConfig || {};
  const showInNavigation = panel.show_in_navigation !== false;
  const homeKey = deviceConfig.home_panel;
  const isHome = Boolean(homeKey && panel.key === homeKey);
  const showHome = panel.show_home_button ?? deviceConfig.show_home_button ?? false;
  const showIdle = panel.show_idle_button ?? deviceConfig.show_idle_button ?? false;
  const canShowPopup = panelType?.can_show_popup === true || isPopup(typeKey);

  const leftPrimaryIcon = canShowPopup && !isHome && showHome
    ? 'mdi:home-outline'
    : (showInNavigation ? 'mdi:chevron-left' : 'mdi:chevron-up');
  const rightPrimaryIcon = showInNavigation ? 'mdi:chevron-right' : 'mdi:close';
  let leftSecondaryIcon = null;
  if (!canShowPopup) {
    if (!isHome && showHome) leftSecondaryIcon = 'mdi:home-outline';
    else if (isHome && showIdle) leftSecondaryIcon = 'mdi:sleep';
  }

  setHeaderButton(display, HEADER_BUTTONS.leftPrimary, leftPrimaryIcon, opts);
  setHeaderButton(display, HEADER_BUTTONS.leftSecondary, leftSecondaryIcon, opts);
  setHeaderButton(display, HEADER_BUTTONS.rightPrimary, rightPrimaryIcon, opts);

  const page = display.page?.name;
  const paginationLimit = page === 'grid' ? 6 : page === 'row' ? 5 : null;
  const hasPagination = paginationLimit != null && getItems(panel).length > paginationLimit;
  if (hasPagination) {
    const paginationSlot = showInNavigation
      ? HEADER_BUTTONS.rightSecondary
      : HEADER_BUTTONS.rightPrimary;
    setHeaderButton(display, paginationSlot, 'mdi:chevron-double-down', opts, true);
  }

  const navCount = navigationPanelCount(opts.host);
  if (showInNavigation && navCount !== null && navCount <= 1) {
    if (leftPrimaryIcon === 'mdi:chevron-left') {
      moveHeaderButton(display, HEADER_BUTTONS.leftSecondary, HEADER_BUTTONS.leftPrimary);
    }
    if (rightPrimaryIcon === 'mdi:chevron-right') {
      moveHeaderButton(display, HEADER_BUTTONS.rightSecondary, HEADER_BUTTONS.rightPrimary);
    }
  }

  if (page === 'qr') {
    const zoomSlot = showInNavigation && navCount !== null && navCount <= 1
      ? HEADER_BUTTONS.rightPrimary
      : HEADER_BUTTONS.rightSecondary;
    if (display.component(zoomSlot)) {
      display.exec(`${zoomSlot}.pco=${devicePalette(opts.host).header_accent}`);
    }
  }
}

function panelEntity(panel, opts, key = 'item') {
  const configured = panel && panel[key];
  const item = typeof configured === 'string' ? { item: configured } : configured;
  const id = itemEntityIdOf(item);
  const state = id ? opts.host?.hass?.states?.[id] : null;
  return { item, state, attributes: state?.attributes || {} };
}

// ---------------------------------------------------------------------------
// Entity-backed page overlays
// ---------------------------------------------------------------------------

function numericValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function setComponentValue(display, name, value) {
  if (display.component(name) && Number.isFinite(value)) display.exec(`${name}.val=${value}`);
}

function applyCoverContent(display, panel, opts) {
  const { state, attributes } = panelEntity(panel, opts);
  if (!state) return;

  const position = numericValue(attributes.current_position);
  if (position !== null) {
    setComponentValue(display, 'hVertPos', Math.max(0, Math.min(100, position)));
    setTxt(display, 'tInfo', `${Math.round(position)}%`);
  } else if (state.state && display.component('tInfo')) {
    setTxt(display, 'tInfo', state.state);
  }

  const features = numericValue(attributes.supported_features);
  const moving = state.state === 'opening' || state.state === 'closing';
  const buttons = [
    ['bUp', 1, state.state !== 'open' && position !== 100],
    ['bStop', 8, moving],
    ['bDown', 2, state.state !== 'closed' && position !== 0],
  ];
  for (const [name, bit, enabled] of buttons) {
    const supported = features === null || (features & bit) !== 0;
    setComponentVisible(display, name, supported);
    if (display.component(name)) display.exec(`tsw ${name},${supported && enabled ? 1 : 0}`);
  }
  const supportsPosition = features === null || (features & 4) !== 0;
  setComponentVisible(display, 'hVertPos', supportsPosition && position !== null);
  if (display.component('hVertPos')) {
    display.exec(`tsw hVertPos,${supportsPosition && position !== null ? 1 : 0}`);
  }
}

function applyClimateContent(display, panel, opts) {
  const { state, attributes } = panelEntity(panel, opts);
  if (!state) return;

  const palette = devicePalette(opts.host);
  const unit = attributes.temperature_unit || '°C';
  const current = numericValue(attributes.current_temperature);
  if (current !== null) setTxt(display, 'tTemp', `${current}${unit}`);
  for (const name of ['tUnit', 'tUnit1', 'tUnit2']) {
    if (display.component(name)) setTxt(display, name, unit);
  }

  const targets = [
    ['xSet', 'tUnit', 'bUp', 'bDown', numericValue(attributes.temperature)],
    ['xSet1', 'tUnit1', 'bUp1', 'bDown1', numericValue(attributes.target_temp_low)],
    ['xSet2', 'tUnit2', 'bUp2', 'bDown2', numericValue(attributes.target_temp_high)],
  ];
  const hasRange = targets[1][4] !== null && targets[2][4] !== null;
  for (const [slider, unitName, up, down, target] of targets) {
    const visible = hasRange ? slider !== 'xSet' : slider === 'xSet' && target !== null;
    setComponentVisible(display, slider, visible);
    setComponentVisible(display, unitName, visible);
    setComponentVisible(display, up, visible);
    setComponentVisible(display, down, visible);
    if (visible && target !== null) setComponentValue(display, slider, Math.round(target * 10));
  }

  const availableModes = Array.isArray(attributes.hvac_modes)
    ? attributes.hvac_modes
    : panel.hvac_modes;
  if (Array.isArray(availableModes)) {
    const modes = Array.isArray(attributes.hvac_modes) && Array.isArray(panel.hvac_modes)
      && panel.hvac_modes.length
      ? availableModes.filter((mode) => panel.hvac_modes.includes(mode))
      : availableModes;
    const modeIcons = {
      auto: 'sun-snowflake-variant', heat_cool: 'sun-snowflake-variant', heat: 'fire',
      off: 'power', cool: 'snowflake', dry: 'water-percent', fan_only: 'fan',
    };
    const byName = opts.byName || {};
    for (let i = 0; i < 6; i += 1) {
      const name = `btMode${i + 1}`;
      const mode = modes[i];
      setComponentVisible(display, name, mode !== undefined);
      if (mode !== undefined && display.component(name)) {
        setComponentValue(display, name, mode === state.state ? 1 : 0);
        const icon = byName[modeIcons[mode]];
        if (icon) setTxt(display, name, icon);
      }
    }
  }

  const features = numericValue(attributes.supported_features);
  for (const [name, bit] of [['bFan', 8], ['bPreset', 16], ['bSwing', 32]]) {
    const supported = features === null || (features & bit) !== 0;
    if (display.component(name)) {
      display.exec(`tsw ${name},${supported ? 1 : 0}`);
      display.exec(colorCmds(display, name, {
        pco: supported ? palette.component_active : palette.text_disabled,
      }));
    }
  }
}

function applyLightContent(display, panel, opts) {
  const { state, attributes } = panelEntity(panel, opts);
  if (!state) return;

  const palette = devicePalette(opts.host);
  const active = state.state === 'on';
  const brightness = numericValue(attributes.brightness);
  const modes = attributes.supported_color_modes || [];
  const hasColor = modes.some((mode) => ['hs', 'rgb', 'rgbw', 'rgbww', 'xy'].includes(mode));
  const min = numericValue(attributes.min_color_temp_kelvin);
  const max = numericValue(attributes.max_color_temp_kelvin);
  const kelvin = numericValue(attributes.color_temp_kelvin);
  const hasColorTemp = modes.includes('color_temp') && min !== null && max !== null && max > min;
  const functions = [
    brightness !== null && 'brightness',
    hasColor && 'color',
    hasColorTemp && 'color_temp',
    Array.isArray(attributes.effect_list) && attributes.effect_list.length > 0 && 'effect',
  ].filter(Boolean);
  const selected = functions.includes('brightness') ? 'brightness' : null;
  setComponentVisible(display, 'hBrightness', selected === 'brightness');
  setComponentVisible(display, 'pColorWheel', selected === 'color');
  setComponentVisible(display, 'hColorTemp', selected === 'color_temp');
  setComponentVisible(display, 'bPower', !selected);
  for (let i = 1; i <= 4; i += 1) {
    const name = `btLightFnc${i}`;
    setComponentVisible(display, name, i <= functions.length);
    if (display.component(name)) setComponentValue(display, name, i === 1 ? 1 : 0);
  }
  if (selected === 'brightness' && brightness !== null) {
    const percent = Math.round(brightness / 255 * 100);
    setComponentValue(display, 'hBrightness', percent);
    setTxt(display, 'tInfo', `${percent}%`);
  } else if (selected === 'color_temp' && kelvin !== null) {
    setComponentValue(display, 'hColorTemp', Math.round((max - kelvin) / (max - min) * 100));
    setTxt(display, 'tInfo', panel.show_kelvin === false
      ? `${Math.round(1_000_000 / kelvin)} Mired`
      : `${kelvin}K`);
  }
  if (display.component('bPower')) {
    display.exec(`bPower.pco=${active ? palette.component_active : palette.component_text}`);
  }
}

function applyWeatherContent(display, panel, opts) {
  const { state, attributes } = panelEntity(panel, opts);
  const showWeather = panel.show_weather !== false;
  const showTemp = panel.show_temp !== false;
  setComponentVisible(display, 'tMainIcon', showWeather);
  setComponentVisible(display, 'tMainText', showTemp);
  setComponentVisible(display, 'tSubText', showTemp);

  if (state) {
    const temp = numericValue(attributes.temperature);
    const unit = attributes.temperature_unit || '°C';
    const parts = [];
    if (temp !== null) parts.push(`${temp}${unit}`);
    if (parts.length) setTxt(display, 'tMainText', parts.join('  '));
    const weatherIcons = {
      'clear-night': 'weather-night', cloudy: 'weather-cloudy', exceptional: 'weather-cloudy-alert',
      fog: 'weather-fog', hail: 'weather-hail', lightning: 'weather-lightning',
      'lightning-rainy': 'weather-lightning-rainy', partlycloudy: 'weather-partly-cloudy',
      pouring: 'weather-pouring', rainy: 'weather-rainy', snowy: 'weather-snowy',
      'snowy-rainy': 'weather-snowy-rainy', sunny: 'weather-sunny', windy: 'weather-windy',
      'windy-variant': 'weather-windy-variant',
    };
    const icon = opts.byName?.[weatherIcons[state.state]];
    if (icon) setTxt(display, 'tMainIcon', icon);
    const pressure = numericValue(attributes.pressure);
    if (pressure !== null) {
      setTxt(display, 'tSubText', `${pressure}${attributes.pressure_unit || ''}`);
    }
  }

  if (panel.show_home_temp === true) {
    const inside = panelEntity(panel, opts, 'inside_temp_item').state;
    const insideTemp = numericValue(inside?.state);
    if (insideTemp !== null) {
      const unit = attributes.temperature_unit || '°C';
      const outsideTemp = numericValue(attributes.temperature);
      setTxt(display, 'tMainText', [insideTemp, outsideTemp]
        .filter((value) => value !== null).map((value) => `${value}${unit}`).join('  '));
    }
  }

  const info = Array.isArray(panel.info_items) ? panel.info_items.slice(0, 2) : [];
  const byName = opts.byName || {};
  for (let i = 0; i < 2; i += 1) {
    const item = info[i];
    const slot = i + 1;
    const { icon } = item ? itemDisplay(item, opts.host) : {};
    const character = icon ? charForIcon(byName, icon, '') : '';
    setComponentVisible(display, `d${slot}Icon`, Boolean(item));
    setComponentVisible(display, `d${slot}Val`, Boolean(item));
    if (!item) {
      if (display.component(`d${slot}Val`)) setTxt(display, `d${slot}Val`, '');
      continue;
    }
    if (character) setTxt(display, `d${slot}Icon`, character);
    const itemState = itemEntityState(item, opts.host);
    if (itemState) setTxt(display, `d${slot}Val`, itemState);
  }

  const showForecast = Boolean(panel.forecast_type);
  for (let i = 1; i <= 5; i += 1) {
    for (const suffix of ['Name', 'Icon', 'Val', 'SubVal']) {
      setComponentVisible(display, `f${i}${suffix}`, showForecast);
    }
  }
}

function applyClockTwoContent(display, panel, opts) {
  const palette = devicePalette(opts.host);
  const offColor = itemColorRgb565(panel, 'off_color', opts.host) ?? palette.component_background;
  const letterColor = itemColorRgb565(panel, 'letter_color', opts.host) ?? palette.component_text;
  const specialColor = itemColorRgb565(panel, 'special_color', opts.host) ?? palette.header_accent;
  for (let i = 1; i <= 110; i += 1) {
    const name = `l${i}`;
    const component = display.component(name);
    if (!component) continue;
    const color = Number(component.attrs.pco);
    if ([8452, 10565, palette.component_background].includes(color)) {
      display.exec(`${name}.pco=${offColor}`);
    } else if ([65535, palette.component_text].includes(color)) {
      display.exec(`${name}.pco=${letterColor}`);
    }
  }
  for (let i = 1; i <= 4; i += 1) {
    const name = `s${i}`;
    const component = display.component(name);
    if (!component) continue;
    const color = Number(component.attrs.pco);
    if ([8452, 10565, palette.component_background].includes(color)) {
      display.exec(`${name}.pco=${offColor}`);
    } else if ([62694, palette.header_accent].includes(color)) {
      display.exec(`${name}.pco=${specialColor}`);
    }
  }
  setComponentVisible(display, 'tNotif', panel.show_notifications !== false);
}

function applyAlarmContent(display, panel, opts) {
  const palette = devicePalette(opts.host);
  const keypadFont = numericValue(panel.keypad_font) ?? 2;
  const keypadBack = itemColorRgb565(panel, 'keypad_bg_color', opts.host) ?? palette.background;
  const keypadText = itemColorRgb565(panel, 'keypad_text_color', opts.host) ?? palette.component_text;
  for (const name of ['bKey0', 'bKey1', 'bKey2', 'bKey3', 'bKey4', 'bKey5', 'bKey6',
    'bKey7', 'bKey8', 'bKey9', 'bKeyClr', 'bKeyDel']) {
    if (!display.component(name)) continue;
    display.exec(`${name}.font=${keypadFont}`);
    display.exec(colorCmds(display, name, { bco: keypadBack, pco: keypadText }));
  }

  const typeKey = opts.typeKey || panel.type;
  if (typeKey === 'popup_unlock') return;
  const { state, attributes } = panelEntity(panel, opts);
  if (!state) return;
  const alarmState = state.state || '';
  setTxt(display, 'tTitle', alarmState.replaceAll('_', ' '));

  const hidden = Array.isArray(panel.hidden_arm_modes) ? panel.hidden_arm_modes : [];
  const disarmed = ['', 'unknown', 'unavailable', 'disarmed'].includes(alarmState);
  const armModes = [
    ['home', 'Home', 1], ['away', 'Away', 2], ['night', 'Night', 4],
    ['vacation', 'Vacation', 32], ['custom_bypass', 'Bypass', 16],
  ].filter(([mode]) => !hidden.includes(mode));
  const features = numericValue(attributes.supported_features) || 7;
  const actions = disarmed
    ? armModes.filter(([, , bit]) => (features & bit) !== 0).slice(0, 4).map(([, label]) => label)
    : ['Disarm'];
  for (let i = 1; i <= 4; i += 1) {
    const name = `b${i}Fnc`;
    const label = actions[i - 1];
    setComponentVisible(display, name, Boolean(label));
    if (!label) continue;
    setTxt(display, name, label);
    const prefix = label === 'Disarm' ? 'disarm' : 'arm';
    const textColor = itemColorRgb565(panel, `${prefix}_button_color`, opts.host);
    const backColor = itemColorRgb565(panel, `${prefix}_button_back_color`, opts.host);
    display.exec(colorCmds(display, name, { pco: textColor, bco: backColor }));
  }
}

function applySelectContent(display, panel, opts) {
  const full = panel.select_mode === 'full';
  const count = full ? 4 : 12;
  const items = getItems(panel);
  if (!items.length) return;
  const selected = panel.multiple
    ? new Set(Array.isArray(panel.selected) ? panel.selected : [])
    : (Array.isArray(panel.selected) ? panel.selected[0] : panel.selected);
  const palette = devicePalette(opts.host);

  for (const [prefix, total] of [['bSelFull', 4], ['bSel', 12]]) {
    for (let i = 1; i <= total; i += 1) {
      const name = `${prefix}${i}`;
      const item = prefix === (full ? 'bSelFull' : 'bSel') && i <= count
        ? items[i - 1]
        : null;
      setComponentVisible(display, name, Boolean(item));
      if (!item) continue;

      const value = typeof item === 'string' ? item
        : Array.isArray(item) ? item[0]
          : item.value;
      const label = typeof item === 'string' ? item
        : Array.isArray(item) ? item[1]
          : item.name;
      setTxt(display, name, label || String(value || ''));
      const isSelected = panel.multiple ? selected.has(value) : selected === value;
      display.exec(colorCmds(display, name, {
        pco: isSelected ? palette.component_accent : palette.component_active,
        bco: palette.background,
        bco2: palette.component_pressed,
      }));
    }
  }
  setComponentVisible(display, 'bFncRSec', items.length > count);
}

function applyQrCodeContent(display, panel, items) {
  const essid = panel.essid || '';
  const password = panel.password || '';
  const code = essid ? `WIFI:S:${essid};T:WPA;P:${password};;` : '';
  for (const component of ['qrCode', 'qrCodeBig']) {
    if (!display.component(component)) continue;
    if (code) setTxt(display, component, code);
    else display.exec(`${component}.txt=""`);
  }

  const isBig = panel.start_big_qr === true;
  const showText = panel.show_info !== false || items.length > 0;
  for (const component of ['qrCode', 'qrCodeBig']) {
    if (display.component(component)) {
      const visible = component === (isBig ? 'qrCodeBig' : 'qrCode');
      display.exec(`vis ${component},${visible ? 1 : 0}`);
    }
  }
  for (const component of [
    'q1Icon', 'q1Title', 'q1Text', 'q1TextAdd',
    'q2Icon', 'q2Title', 'q2Text', 'q2TextAdd',
  ]) {
    if (display.component(component)) display.exec(`vis ${component},${!isBig && showText ? 1 : 0}`);
  }
  if (!items.length && panel.show_info !== false) {
    for (const [component, value] of [['q1Text', essid], ['q2Text', password]]) {
      if (!display.component(component)) continue;
      if (value) setTxt(display, component, value);
      else display.exec(`${component}.txt=""`);
    }
    for (const component of ['q1TextAdd', 'q2TextAdd']) {
      if (display.component(component)) display.exec(`${component}.txt=""`);
    }
  }
}

// ---------------------------------------------------------------------------
// Page renderer dispatch and final assembly
// ---------------------------------------------------------------------------

function applyClockPageContent(display, panel, opts) {
  applyNamedButtons(display, getItems(panel), 'bEntity', opts, 6);
  applyWeatherContent(display, panel, opts);
  if (panel.show_time_time === false) setComponentVisible(display, 'tTime', false);
  if (panel.show_time_date === false) setComponentVisible(display, 'tDate', false);
}

function applyVacuumPageContent(display, panel, opts) {
  applyVacuumControls(display, panel, opts);
  applyNamedButtons(display, getItems(panel), 'bEntity', opts, 6);
}

function applyMediaPageContent(display, panel, opts) {
  applyMediaControls(display, panel, opts);
  applyNamedButtons(display, getItems(panel), 'm', opts, 3);
}

const CONTENT_RENDERERS = {
  grid: applyGridContent,
  row: applyRowContent,
  cover: applyCoverContent,
  climate: applyClimateContent,
  light: applyLightContent,
  alarm: applyAlarmContent,
  select: applySelectContent,
  clock: applyClockPageContent,
  weather: applyWeatherContent,
  clocktwo: applyClockTwoContent,
  vacuum: applyVacuumPageContent,
  media: applyMediaPageContent,
  qr: (display, panel) => applyQrCodeContent(display, panel, getItems(panel)),
  notify: applyNotifyContent,
};

/**
 * Overlay the configured panel's own content on the replayed snapshot.
 *
 * The snapshot comes from representative sample panels, so its texts, icons,
 * per-item colours and feature-gated controls belong to those samples. Panels
 * the user configured must show their own titles, items and item settings
 * (grid tiles, row entries, entity buttons) instead.
 */
export function applyPanelContent(display, panel, _panelType, opts = {}) {
  if (!panel) return;
  const page = display.page ? display.page.name : '';
  CONTENT_RENDERERS[page]?.(display, panel, opts);
}

/** Popup aliases share a page but hide the mode controls the base page shows. */
function applyPopupMode(display, typeKey) {
  if (typeKey === 'popup_unlock') {
    for (const name of ['b1Fnc', 'b2Fnc', 'b3Fnc', 'b4Fnc']) {
      if (display.component(name)) display.exec(`vis ${name},0`);
    }
  }
}

/** Use the panel's own title over the captured sample title. */
function applyPanelTitle(display, panel) {
  const title = (panel && panel.title) || '';
  if (title && display.component('tTitle')) display.exec(`tTitle.txt="${String(title).replace(/"/g, '\\"')}"`);
}

/**
 * Page background pictures, mirroring `haui/mapping/background.py`.
 *
 * The clock/weather/clocktwo pages read their global `background.val` in the
 * page's Preinitialize code to choose the pictures, so it must be set before
 * the page loads.
 */
const BACKGROUNDS = {
  dark: 1, modern: 2, spring: 3, summer: 4, autumn: 5,
  winter: 6, dog_1: 7, dog_2: 8, cat: 9,
};

function applyPageBackground(display, layout, pageId, panel) {
  const name = (panel && typeof panel.background === 'string') ? panel.background : '';
  const picture = BACKGROUNDS[name];
  if (picture === undefined) return;
  const page = layout && layout.pages && layout.pages[String(pageId)];
  if (!page) return;
  const hasBackground = page.components.some((comp) => comp.name === 'background');
  if (!hasBackground) return;
  display.exec(`${page.name}.background.val=${picture}`);
}

/**
 * Build a seeded NextionDisplay for a static preview.
 * `opts` may inject `{ state, loader, onChange, onWarn, scheduler, byName,
 * host, seed }` — `state` is the parsed preview_state.json (tests pass it).
 */
export function buildPreviewDisplay(layout, pageId, panel, panelType, opts = {}) {
  const display = new NextionDisplay(layout, {
    scheduler: opts.scheduler || noopScheduler(),
    onChange: opts.onChange,
    onWarn: opts.onWarn,
  });
  applyPageBackground(display, layout, pageId, panel);
  display.gotoPage(pageId);
  if (!display.page && layout && layout.pages && layout.pages['0']) {
    display.gotoPage(0);
  }
  if (opts.seed === false) return display;

  const typeKey = opts.typeKey || typeKeyOf(panel, panelType);
  const entry = opts.state ? previewStateFor(opts.state, pageId) : null;
  // A picture background the panel configures was already applied before the
  // page loaded; the sample's own background command must not undo it.
  const backgroundCmd = panel && BACKGROUNDS[panel.background] !== undefined
    && layout.pages[String(pageId)]
    ? `${layout.pages[String(pageId)].name}.background.val=`
    : null;
  const skip = backgroundCmd ? (cmd) => cmd.startsWith(backgroundCmd) : null;
  if (!applyPreviewState(display, entry, opts.colorMap, skip)) {
    // No snapshot for this page: fall back to representative seeding.
    seedPreviewState(display, panel, panelType, opts);
  }
  // Apply the same panel-specific overlay after either initialization path.
  applyPanelTitle(display, panel);
  applyPopupMode(display, typeKey);
  applyPanelContent(display, panel, panelType, { ...opts, typeKey });
  applyHeaderFunctionButtons(display, panel, panelType, opts);
  return display;
}
