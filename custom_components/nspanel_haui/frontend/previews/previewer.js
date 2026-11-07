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
 * placeholder, not a guess.
 */
import { NextionDisplay } from '../virtual/nextion-display.js';
import { noopScheduler } from './simulator.js';

const RENDERS = new Map();
// Entity states move on; a card re-mounted within this window reuses its render.
const RENDER_MAX_AGE_MS = 30_000;

/**
 * Everything a card's render depends on besides the panel itself: the hub, the
 * device, its device info and saved settings and panels (header buttons follow
 * the navigation order). A frame renders again when this changes.
 *
 * @param {object} host - the editor element
 * @returns {string}
 */
export function previewRenderKey(host) {
  const panels = typeof host?._devicePanels === 'function' ? host._devicePanels() : null;
  const deviceInfo = host?._deviceStatuses?.[host?._selectedDevice]?.device_info || null;
  return JSON.stringify([
    host?.entryId,
    host?._selectedDevice,
    host?._deviceConfig,
    panels,
    deviceInfo,
  ]);
}

/**
 * The hub's render of a card's panel, `{page, before, commands}`, or null
 * without a Home Assistant connection.
 *
 * @param {object} host - the editor element (`hass`, `entryId`, `_selectedDevice`)
 * @param {object} panel - a user panel's config (unsaved edits included) or a
 *   system panel entry
 * @param {boolean} byKey - render the device's configured panel with
 *   `panel.key` (system panels, with their defaults or saved override)
 * @returns {Promise<object|null>}
 */
export function loadPanelRender(host, panel, byKey) {
  const connection = host?.hass?.connection;
  const device = host?._selectedDevice;
  if (!connection || !host.entryId || !device || !panel) return Promise.resolve(null);
  const target = byKey ? { key: panel.key } : { panel };
  const key = JSON.stringify([previewRenderKey(host), target]);
  const cached = RENDERS.get(key);
  if (cached && Date.now() - cached.time < RENDER_MAX_AGE_MS) return cached.promise;
  const promise = connection.sendMessagePromise({
    type: 'nspanel_haui/virtual_panel/render',
    entry_id: host.entryId,
    device,
    ...target,
  }).catch((err) => {
    RENDERS.delete(key);
    throw new Error(err?.message || String(err));
  });
  RENDERS.set(key, { time: Date.now(), promise });
  return promise;
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
  if (!display.page && layout && layout.pages && layout.pages['0']) {
    display.gotoPage(0);
  }
  if (render) display.exec(render.commands);
  return display;
}
