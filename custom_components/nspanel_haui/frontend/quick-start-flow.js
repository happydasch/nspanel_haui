/**
 * NSPanel HAUI - the quick start flow of a device without panels.
 *
 * Ties the presets (`presets.js`) and their dialog (`dialogs/quick-start.js`)
 * to the editor: which device is being set up, what the user chose, what that
 * resolves to against their Home Assistant, and what creating one writes. Each
 * function takes the editor element (`host`) as its first parameter and the
 * shell keeps thin wrappers, like `crud.js`.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import * as Crud from './crud.js';
import { themePalette } from './preset-colors.js';
import { areaOptions } from './preset-entities.js';
import { presets, presetByKey, resolvePreset } from './presets.js';
import { themeOptions } from './theme-library.js';
import { buildPreviewContext } from './previews/context.js';
import { previewRenderKey } from './previews/previewer.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';

/**
 * The choices the dialog starts with: no preset picked yet, the first area, the
 * theme the device draws in, and the preset's own toggle defaults.
 *
 * @param {string} [areaId]
 * @param {string} [themeId]
 */
export function defaultChoices(areaId = '', themeId = '') {
  return { preset: null, areaId, themeId, toggles: {}, essid: '', password: '' };
}

/**
 * The area a preset resolves against: the one the user chose, else the first
 * area of the installation (the dialog lists the rest).
 *
 * @param {any} hass
 * @param {string} areaId
 */
function chosenArea(hass, areaId) {
  return areaId || areaOptions(hass)[0]?.area_id || '';
}

/**
 * The keys a preset must not take: the device's panels and the hub's system
 * panels (a user panel under a system key would replace that popup).
 *
 * @param {any} host
 * @param {any} device
 */
function takenKeys(host, device) {
  const system = (host._store.getState().hub.systemPanels || []).map((entry) => entry.key);
  return [...(device?.panels || []).map((panel) => panel.key), ...system].filter(Boolean);
}

/**
 * Resolve one preset for the device being set up, with the user's choices.
 *
 * @param {any} host
 * @param {import('./presets.js').Preset} preset
 * @param {any} choices
 * @returns {import('./presets.js').PresetResolution}
 */
function resolveFor(host, preset, choices) {
  const state = host._store.getState();
  const device = state.devices.byName[host._quickStartTarget];
  return resolvePreset(preset, {
    hass: host.hass,
    panelTypes: state.hub.panelTypes || [],
    areaId: preset.needsArea ? chosenArea(host.hass, choices.areaId) : '',
    choices,
    deviceConfig: device?.config || {},
    taken: takenKeys(host, device),
    // The colours the generated pages carry are the ones of the theme the
    // device draws in once the setup is created.
    theme: themePalette(
      state.hub.themes, host._builtinThemes, choices.themeId || device?.config?.theme_id,
    ),
    themeId: choices.themeId || '',
  });
}

/**
 * The preview context of the device being set up, or null.
 *
 * It renders in the theme picked in the dialog, not the stored one: that is the
 * theme the device draws in once the setup is created, so the gallery shows what
 * the pages will look like. The theme is part of the render key, so picking
 * another one renders every card again.
 *
 * @param {any} host
 */
function previewContext(host) {
  const state = host._store.getState();
  const name = host._quickStartTarget;
  const device = name ? state.devices.byName[name] : null;
  if (!name || !device) return null;
  const context = buildPreviewContext(
    state.hub.entryId, name, device, device.status, host.api, state.hub.themes,
  );
  const themeId = host._quickStartChoices?.themeId;
  if (!themeId) return context;
  const library = { ...(host._builtinThemes || {}), ...(host._customThemes || {}) };
  return {
    ...context,
    theme: library[themeId] || context.theme,
    deviceConfig: { ...context.deviceConfig, theme_id: themeId },
  };
}

/**
 * The panel config handed to a page's frame. The same settings give the same
 * object, so a keystroke in the dialog re-renders nothing; a keyless QR panel
 * gets sample credentials from the hub and isn't kept in the thumbnail cache,
 * so the draft network details never reach it.
 *
 * The pages are rendered in the theme the dialog picked, through the render's
 * own `theme_id` override (the panel editor's theme field): the setup writes that
 * theme to the device, so the pages it creates draw in it without carrying it.
 * Only a theme the editor's library knows is passed on - the render resolves it
 * against the hub's library, which refuses an unknown id.
 *
 * @param {any} host
 * @param {any} page
 */
function previewPanel(host, page) {
  const panel = page.panel;
  const themeId = host._quickStartChoices?.themeId || '';
  const known = !!(host._builtinThemes?.[themeId] || host._customThemes?.[themeId]);
  const wanted = {
    ...(panel.type === 'qr' ? {
      key: '',
      type: panel.type,
      title: panel.title,
      start_big_qr: panel.start_big_qr,
      show_info: panel.show_info,
    } : panel),
    ...(known ? { theme_id: themeId } : {}),
  };
  const cache = host.__quickStartPanels instanceof Map ? host.__quickStartPanels : new Map();
  host.__quickStartPanels = cache;
  const signature = JSON.stringify(wanted);
  const hit = cache.get(signature);
  if (hit) return hit;
  cache.set(signature, wanted);
  // A dialog resolves a handful of pages; keep the cache no larger than that.
  if (cache.size > 64) cache.delete(cache.keys().next().value);
  return wanted;
}

/**
 * The hub's render of one page of a setup, or null without a device to render it on.
 *
 * @param {any} host
 * @param {ReturnType<typeof previewContext>} context
 * @param {any} page
 * @param {string} renderKey
 */
function previewPage(host, context, page, renderKey) {
  if (!context || !page) return null;
  return renderSimulatorPreview(context, previewPanel(host, page), 0, renderKey);
}

/**
 * The preset catalog as the quick start's first step lists it: each preset
 * resolved with the user's current choices (its own defaults for the presets
 * they have not picked), with the hub's render of the home page it creates.
 *
 * A preset that cannot be resolved is still listed, with the reason: one
 * broken configuration must not empty the chooser. Without a device to render
 * on the cards keep their placeholder.
 *
 * @param {any} host
 * @returns {Array<any>}
 */
export function quickStartPresets(host) {
  const context = previewContext(host);
  const renderKey = context ? previewRenderKey(context) : '';
  const choices = host._quickStartChoices || defaultChoices();
  // Built here rather than at import, so the catalog carries the language the
  // editor loaded its translations in.
  return presets().map((preset) => {
    const own = choices.preset === preset.key
      ? choices
      : { ...defaultChoices(choices.areaId, choices.themeId), preset: preset.key };
    let resolution = null;
    let error = '';
    try {
      resolution = resolveFor(host, preset, own);
    } catch (err) {
      error = (err && err.message) || String(err);
    }
    const home = resolution?.pages.find((page) => page.role === 'home') || null;
    return {
      key: preset.key,
      label: preset.label,
      description: preset.description,
      icon: preset.icon,
      needsArea: preset.needsArea === true,
      error,
      preview: previewPage(host, context, home, renderKey),
    };
  });
}

/**
 * Where a page sits on the device, as the setup's gallery describes it: the
 * home screen, an idle panel (the idle page or one the automatic page switch
 * cycles to after it), a navigation page (reached by swiping and from the
 * header buttons) or one only reached from another page.
 * @param {import('./presets.js').ResolvedPresetPage} page
 */
function pageNode(page) {
  if (page.role === 'home') return 'home';
  if (page.role === 'idle' || page.role === 'idle_extra') return 'idle';
  return page.panel.show_in_navigation === false ? 'hidden' : 'navigation';
}

/** The order the gallery lists the pages in. */
const NODE_ORDER = { home: 0, idle: 1, navigation: 2, hidden: 3 };

/**
 * The selected preset resolved with the user's choices, as the second step
 * shows it: its pages with their render and their panel type, the settings it
 * writes and the home page's render.
 *
 * @param {any} host
 * @returns {(import('./presets.js').PresetResolution & { label: string,
 *   description: string, icon: string, preview: unknown })|null}
 */
function quickStartResolution(host) {
  const preset = presetByKey(host._quickStartChoices?.preset);
  if (!preset) return null;
  const state = host._store.getState();
  const context = previewContext(host);
  const types = state.hub.panelTypes || [];
  let resolution;
  try {
    resolution = resolveFor(host, preset, host._quickStartChoices);
  } catch (err) {
    // The dialog stays usable and says what went wrong instead of rendering nothing.
    return {
      preset: preset.key,
      area: null,
      areaName: '',
      toggles: [],
      pages: [],
      dropped: [],
      config: {},
      ready: false,
      blocked: [],
      needsInput: [],
      warnings: [(err && err.message) || String(err)],
      entityCount: 0,
      label: preset.label,
      description: preset.description,
      icon: preset.icon,
      preview: null,
    };
  }
  const renderKey = context ? previewRenderKey(context) : '';
  // What the gallery beside the choices describes: every page with the hub's
  // render of it, its role and the panel type it is.
  const pages = resolution.pages
    .map((page) => {
      const descriptor = types.find((type) => type.type_key === page.panel.type) || null;
      return {
        ...page,
        node: pageNode(page),
        entityCount: page.filled,
        typeLabel: descriptor?.label || page.panel.type,
        typeIcon: descriptor?.icon || '',
        typeDescription: descriptor?.description || '',
        preview: previewPage(host, context, page, renderKey),
      };
    })
    .map((page, index) => ({ page, index }))
    .sort((a, b) => NODE_ORDER[a.page.node] - NODE_ORDER[b.page.node] || a.index - b.index)
    .map((entry) => entry.page);
  const home = resolution.pages.find((page) => page.role === 'home') || null;
  return {
    ...resolution,
    pages,
    label: preset.label,
    description: preset.description,
    icon: preset.icon,
    preview: previewPage(host, context, home, renderKey),
  };
}

/** Refresh the presets and the resolution the dialog shows. @param {any} host */
function refresh(host) {
  host._quickStartPresets = quickStartPresets(host);
  host._quickStartResolution = quickStartResolution(host);
}

/**
 * The themes the dialog's **Theme** field offers: the hub's built-in and saved
 * ones, with the device's own theme while the library is still loading so the
 * preselected one stays selectable.
 *
 * @param {any} host
 * @returns {{value: string, label: string}[]}
 */
export function quickStartThemes(host) {
  const options = themeOptions({
    ...(host._builtinThemes || {}),
    ...(host._customThemes || {}),
  });
  const stored = host._quickStartChoices?.themeId || '';
  if (stored && !options.some((option) => option.value === stored)) {
    options.push({ value: stored, label: stored });
  }
  return options;
}

/**
 * Open the quick start for one device. The route moves to that device's Panels
 * view, because a device without panels has no display to preview.
 *
 * The presets are resolved against the hub's panel type descriptors: without
 * them a page cannot be filled in, so they are loaded (once) before the dialog
 * resolves anything.
 *
 * @param {any} host
 * @param {string|null|undefined} name
 */
export async function openQuickStart(host, name) {
  const state = host._store.getState();
  const deviceName = name
    || (state.ui.route?.view === 'device' ? state.ui.route.device : null)
    || host._selectedDevice
    || state.devices.order?.[0]
    || null;
  if (!deviceName) return;
  if (deviceName !== host._selectedDevice) host._selectDevice(deviceName);
  if (state.ui.route.view !== 'device' || state.ui.route.device !== deviceName
    || state.ui.route.panelView !== 'panels') {
    host._router?.navigate({ view: 'device', device: deviceName, panelView: 'panels' });
  }
  // The store's action answers at once when the descriptors are already loaded;
  // without them no page can be filled in, so the dialog waits for them.
  if (!Array.isArray(state.hub.panelTypes) || state.hub.panelTypes.length === 0) {
    await host._store.actions.loadPanelTypes?.();
  }
  host._quickStartTarget = deviceName;
  host._quickStartError = '';
  host._quickStartSaving = false;
  host._quickStartAreas = areaOptions(host.hass);
  // The theme the setup preselects is the one the device draws in already.
  const deviceTheme = host._store.getState().devices.byName[deviceName]?.config?.theme_id || '';
  host._quickStartChoices = defaultChoices(
    host._quickStartAreas[0]?.area_id || '', deviceTheme,
  );
  refresh(host);
}

/** @param {any} host */
export function closeQuickStart(host) {
  host._quickStartTarget = null;
  host._quickStartError = '';
  host._quickStartSaving = false;
  host._quickStartAreas = [];
  host._quickStartChoices = null;
  host._quickStartPresets = [];
  host._quickStartResolution = null;
  host.__quickStartPanels = new Map();
}

/**
 * Apply what the user chose in the dialog (a preset, an area, a toggle, the
 * network name) and resolve the result again. Picking a different preset
 * starts from its own switches, not the previous preset's.
 *
 * @param {any} host
 * @param {Object<string, any>} choices
 */
export function setChoices(host, choices) {
  if (!host._quickStartTarget) return;
  const previous = host._quickStartChoices || defaultChoices();
  const next = { ...previous, ...choices };
  // A different preset starts from its own switches.
  if (choices.preset !== undefined && choices.preset !== previous.preset) {
    next.toggles = choices.toggles ?? {};
  }
  host._quickStartChoices = next;
  host._quickStartError = '';
  refresh(host);
}

/**
 * One-line reason a save failed: the editor's own copy, and the hub's message.
 *
 * @param {string} copy
 * @param {string|null|undefined} reason
 */
function failed(copy, reason) {
  return [copy, reason].filter(Boolean).join(' ');
}

/**
 * Bring the row of a panel the setup just created into view. Focus stays where
 * it is: the dialog restores it to the control that opened it.
 *
 * @param {any} host
 * @param {string} key
 */
function revealPanel(host, key) {
  if (!key) return;
  const reduced = typeof matchMedia === 'function'
    && matchMedia('(prefers-reduced-motion: reduce)').matches;
  requestAnimationFrame(() => {
    const row = host.shadowRoot?.querySelector(`.haui-panel-row[data-panel-key="${key}"]`);
    row?.scrollIntoView?.({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' });
  });
}

/**
 * Create the resolved preset: its pages first, so the device settings saved
 * after them can refer to their keys, then the settings it changed. A preset
 * whose settings did not change writes the pages only.
 *
 * @param {any} host
 */
export async function createFromPreset(host) {
  const deviceName = host._quickStartTarget;
  if (!deviceName || host._quickStartSaving) return;
  const preset = presetByKey(host._quickStartChoices?.preset);
  if (!preset) return;
  const resolution = resolveFor(host, preset, host._quickStartChoices);
  if (!resolution.ready) {
    host._quickStartError = t('This setup is not ready yet: check the entities and fields above.');
    return;
  }
  host._quickStartSaving = true;
  host._quickStartError = '';
  let created = false;
  try {
    const device = host._store.getState().devices.byName[deviceName];
    const pages = resolution.pages.map((page) => page.panel);
    const saved = await Crud.savePanels(
      host, [...(device?.panels || []), ...pages],
      t('Added {count} pages to {device}')
        .replace('{count}', String(pages.length))
        .replace('{device}', device?.friendlyName || deviceName),
      deviceName,
    );
    if (!saved) {
      host._quickStartError = failed(t('The pages could not be saved.'), host._error);
      return;
    }
    created = true;
    // The store is the source of truth again once the save came back, and the
    // pages are saved before the settings that name them.
    const config = host._store.getState().devices.byName[deviceName]?.config || {};
    if (Object.entries(resolution.config).some(([key, value]) => config[key] !== value)) {
      const applied = await Crud.saveDeviceConfig(
        host, { ...config, ...resolution.config }, t('Updated the device pages'), deviceName,
      );
      if (!applied) {
        host._quickStartError = failed(
          t('The pages were added, but the device settings could not be saved.'), host._error,
        );
      }
    }
    const home = resolution.pages.find((page) => page.role === 'home');
    if (home && deviceName === host._selectedDevice) host._selectedPanelKey = home.key;
    // The rows of what was just created say so, and the home page's is in view.
    host._markNewPanels?.(pages.map((panel) => panel.key));
    if (!host._quickStartError) revealPanel(host, home?.key || '');
  } finally {
    host._quickStartSaving = false;
  }
  // A setup that failed halfway stays open, with its reason.
  if (created && !host._quickStartError) closeQuickStart(host);
}

/** The quick start dialog for the device being set up, or nothing. @param {any} host */
export function renderQuickStart(host) {
  const deviceName = host._quickStartTarget;
  if (!deviceName) return '';
  const device = host._store.getState().devices.byName[deviceName];
  return html`<nspanel-dialog-quick-start
    .hass=${host.hass} .open=${true}
    .deviceName=${device?.friendlyName || deviceName}
    .presets=${host._quickStartPresets || []}
    .resolution=${host._quickStartResolution || null}
    .choices=${host._quickStartChoices || null}
    .areas=${host._quickStartAreas || []}
    .themeOptions=${quickStartThemes(host)}
    .saving=${host._quickStartSaving === true}
    .error=${host._quickStartError || ''}
    @dialog-closed=${() => host._closeQuickStart()}
    @quick-start-choose=${(event) => host._applyQuickStartChoices(event.detail || {})}
    @quick-start-create=${() => host._createFromPreset()}
  ></nspanel-dialog-quick-start>`;
}
