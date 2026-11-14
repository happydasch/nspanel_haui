/**
 * NSPanel HAUI - Panel card previews: the hub's own render, replayed.
 *
 * Every panel card (user panels, system panels and popup aliases, in both
 * orientations) shows what the device shows. The integration renders the
 * panel on the device's virtual app (`nspanel_haui/virtual_panel/render`,
 * `virtual_panel.VirtualPanelHost.async_render`, the app the live preview
 * runs on), and the card replays the hub's display commands in a
 * NextionDisplay built from the real layout. There is no second renderer in
 * the browser: entity values, translations, templates, dates and forecasts
 * are the hub's. A card without a render (no device selected yet) shows a
 * placeholder, not a guess. The browser keeps every card's last render, so a
 * card opened after a reload shows it until the hub's new one arrives.
 */
import { readStorage, writeStorage } from '../dom-helpers.js';
import { NextionDisplay } from '../virtual/nextion-display.js';
import { noopScheduler } from './simulator.js';

const RENDERS = new Map();
// Entity states move on; a card re-mounted within this window reuses its render.
const RENDER_MAX_AGE_MS = 30_000;

const LAST_RENDERS_KEY = 'haui_lastCardRenders';
const LAST_RENDERS_MAX = 200;
// The versioned asset path: a kept render replays only in the layout it was
// drawn for, so an update of the frontend drops them.
const ASSETS = new URL('..', import.meta.url).href;
const LAST_RENDERS_SAVE_DELAY_MS = 500;
let lastRenders = null;
let lastRendersSave = null;

// The device info a page draws (the About page, haui/page/about.py). The rest
// of it (uptime, RSSI, last update) moves on every 5 s status poll and would
// re-render every card each time.
const RENDERED_DEVICE_INFO = ['ip', 'tft_version', 'yaml_version'];

/**
 * Everything a card's render depends on besides the panel itself: the hub, the
 * device, the device info its pages show and its saved settings and panels
 * (header buttons follow the navigation order). A frame renders again when
 * this changes.
 *
 * @param {import('./types.js').PreviewContext} context
 * @returns {string}
 */
export function previewRenderKey(context) {
  const deviceInfo = context?.deviceInfo;
  return JSON.stringify([
    context?.entryId,
    context?.device,
    context?.deviceConfig,
    context?.theme,
    context?.panels,
    deviceInfo ? RENDERED_DEVICE_INFO.map((name) => deviceInfo[name]) : null,
    context?.kwargs ?? null,
  ]);
}

/**
 * The hub's render of a card's panel, `{page, before, commands}`, or null
 * without a Home Assistant connection.
 *
 * @param {import('./types.js').PreviewContext} context
 * @param {object} panel - a user panel's config (unsaved edits included) or a
 *   system panel entry
 * @param {boolean} byKey - render the device's configured panel with
 *   `panel.key` (system panels, with their defaults or saved override)
 * @returns {Promise<object|null>}
 */
export function loadPanelRender(context, panel, byKey) {
  const api = context?.api;
  const device = context?.device;
  if (!api || !api.connection() || !context.entryId || !device || !panel) {
    return Promise.resolve(null);
  }
  const target = {
    ...(byKey ? { key: panel.key } : { panel }),
    ...(context.kwargs ? { kwargs: context.kwargs } : {}),
  };
  const key = JSON.stringify([previewRenderKey(context), target]);
  const now = Date.now();
  // Every edit or settings change keys new renders: drop the expired ones.
  for (const [k, entry] of RENDERS) {
    if (now - entry.time >= RENDER_MAX_AGE_MS) RENDERS.delete(k);
  }
  const cached = RENDERS.get(key);
  if (cached) return cached.promise;
  // A render with the editor's sample is not the card's: the list keeps showing its own.
  const card = context.kwargs ? null : cardId(context, panel, byKey);
  const promise = api.preview.render(context.entryId, device, target).then((render) => {
    if (card) keepRender(card, render);
    return render;
  }, (err) => {
    RENDERS.delete(key);
    throw new Error(err?.message || String(err));
  });
  RENDERS.set(key, { time: now, promise });
  return promise;
}

/**
 * The render a card showed last, kept in the browser across reloads, or null.
 * It may be out of date: a card shows it only until the hub's render arrives.
 *
 * @param {import('./types.js').PreviewContext} context
 * @param {object} panel
 * @param {boolean} byKey
 * @returns {object|null}
 */
export function lastPanelRender(context, panel, byKey) {
  const card = cardId(context, panel, byKey);
  return card ? storedRenders().get(card) || null : null;
}

/**
 * A card by what stays the same while its panel is edited or its device's
 * settings change; null for a panel without a key (a catalog sample).
 */
function cardId(context, panel, byKey) {
  if (!context?.entryId || !context.device || !panel?.key) return null;
  return JSON.stringify([
    context.entryId,
    context.device,
    context.deviceConfig?.display_model ?? null,
    byKey,
    panel.key,
    panel.type ?? null,
  ]);
}

/** @returns {Map<string, object>} card id → render, oldest first */
function storedRenders() {
  if (lastRenders) return lastRenders;
  lastRenders = new Map();
  const raw = readStorage(LAST_RENDERS_KEY, null);
  if (!raw) return lastRenders;
  try {
    const stored = JSON.parse(raw);
    if (stored.assets === ASSETS) lastRenders = new Map(stored.renders);
  } catch (err) {
    // Only a head start is lost: every card asks the hub anyway.
    console.warn('NSPanel HAUI: dropping unreadable kept card renders:', err);
  }
  return lastRenders;
}

function keepRender(card, render) {
  const renders = storedRenders();
  renders.delete(card);
  renders.set(card, render);
  for (const oldest of renders.keys()) {
    if (renders.size <= LAST_RENDERS_MAX) break;
    renders.delete(oldest);
  }
  // A save renders every card again: write them once.
  clearTimeout(lastRendersSave);
  lastRendersSave = setTimeout(() => {
    writeStorage(LAST_RENDERS_KEY, JSON.stringify({ assets: ASSETS, renders: [...renders] }));
  }, LAST_RENDERS_SAVE_DELAY_MS);
}

/**
 * Build the NextionDisplay a card shows: replay the hub's render in the
 * device's order — what the hub sends before switching to the page (its
 * picture background, read by the page's Preinitialize code), the page switch,
 * then the page's commands. Without a render it is the bare HMI page.
 *
 * @param {object} layout - virtual-panel layout JSON
 * @param {number} pageId - the page to show without a render
 * @param {object} [opts] - `{ render, scheduler, onChange, onWarn }`
 * @returns {NextionDisplay}
 */
export function buildPreviewDisplay(layout, pageId, opts = {}) {
  const display = new NextionDisplay(layout, {
    scheduler: opts.scheduler || noopScheduler(),
    onChange: opts.onChange,
    onWarn: opts.onWarn,
  });
  const { render } = opts;
  if (render) display.exec(render.before || []);
  display.gotoPage(render ? render.page : pageId);
  if (render) display.exec(render.commands);
  return display;
}
