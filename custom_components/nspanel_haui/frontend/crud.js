/**
 * NSPanel HAUI - CRUD operations.
 * Panel and device create/update/delete helpers.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.  The class methods are thin wrappers:
 *
 *   _openAdd()        { return Crud.openAdd(this); }
 *   _openEdit(index)  { return Crud.openEdit(this, index); }
 *   …etc.
 */
import { clone, defaultPanel } from './constants.js';
import { t } from './localize.js';
import { serializeItem } from './haui-item.js';
import { getSystemPanelKeys } from './panel-utils.js';

/* ── helpers ────────────────────────────────────────────────────────────────── */

/** Generate an unused auto-key like "{type}_{n}" for the given panel type. */
export function generateAutoKey(panels, panelType) {
  const usedKeys = new Set(
    (panels || []).filter(p => p.type === panelType).map(p => p.key)
  );
  let idx = 0;
  while (usedKeys.has(`${panelType}_${idx}`)) idx++;
  return `${panelType}_${idx}`;
}

/* ── panel lifecycle ──────────────────────────────────────────────────────── */

/** Reset the edit-dialog session state and open `data` for editing. */
export function openPanelDialog(host, index, data, type) {
  host._dialogVersion = (host._dialogVersion || 0) + 1;
  host._itemListData = {};
  host._editingPanel = { index, data };
  host._editingPanelType = type;
  host._error = null;
  host._deleteTarget = null;
  const overlay = {
    kind: 'panel-editor',
    anchorKey: `panel:${data.key}`,
    subject: data.key,
    draft: { index, type },
  };
  const overlays = host.store.getState().ui.overlays;
  if (overlays.at(-1)?.kind === 'panel-catalog') host.store.actions.replaceTopOverlay(overlay);
  else {
    host.store.actions.closeOverlay('panel-editor');
    host.store.actions.pushOverlay(overlay);
  }
}

export function openAdd(host, selectedType) {
  const firstType = selectedType || (host._panelTypes.length > 0 ? host._panelTypes[0].type_key : "clock");
  // Auto-generate an unused key like "grid_0", "grid_1", etc.
  // Compute key BEFORE setting _editingPanel so Lit sees it in the initial render.
  const data = defaultPanel(firstType);
  data.key = generateAutoKey(host._devicePanels(), firstType);
  openPanelDialog(host, -1, data, firstType);
}

/**
 * Open the editor for a new panel that starts as a copy of `source` (a panel of
 * this or another device), under a key that is free on this device.
 *
 * @param {any} host - editor component
 * @param {any} source - the panel config to copy
 */
export function openAddFrom(host, source) {
  const data = clone(source);
  data.type = data.type || "clock";
  data.key = generateAutoKey(host._devicePanels(), data.type);
  openPanelDialog(host, -1, data, data.type);
}

/**
 * Open the editor for a new panel that starts from a starter template, under a
 * key that is free on this device. The slots' preview-only `domain` hints are
 * dropped; their empty entities stay for the user to choose.
 *
 * @param {any} host - editor component
 * @param {any} template - the template's panel config (keyless)
 */
export function openAddFromTemplate(host, template) {
  const data = clone(template);
  for (const value of Object.values(data)) {
    if (!Array.isArray(value)) continue;
    for (const entry of value) {
      if (entry && typeof entry === 'object') delete entry.domain;
    }
  }
  data.key = generateAutoKey(host._devicePanels(), data.type);
  openPanelDialog(host, -1, data, data.type);
}

export function openEdit(host, index) {
  const panels = host._devicePanels();
  if (index < 0 || index >= panels.length) {
    host._dialogVersion = (host._dialogVersion || 0) + 1;
    host._itemListData = {};
    return;
  }
  const data = clone(panels[index]);
  openPanelDialog(host, index, data, data.type || "clock");
}

export function closeEdit(host) {
  host.store.actions.closeOverlay('panel-editor');
  host._itemListData = {};
  host._editingPanel = null;
  host._editingPanelType = null;
  host._error = null;
}

/* ── list actions ─────────────────────────────────────────────────────────── */

/**
 * Move a listed panel into a group at `beforeKey`, flipping its navigation
 * visibility when it crosses groups. One save for the whole move.
 *
 * @param {HTMLElement} host - editor component
 * @param {string} panelKey - the dragged panel
 * @param {'navigation'|'hidden'} group - the group it was dropped into
 * @param {string|null} [beforeKey] - the panel it was dropped before, or null for the group's end
 */
export function movePanelToGroup(host, panelKey, group, beforeKey = null) {
  if (group !== 'navigation' && group !== 'hidden') return;
  if (panelKey === beforeKey) return;
  const panels = host._devicePanels();
  const systemKeys = getSystemPanelKeys(host);
  const source = panels.find((panel) => panel.key === panelKey);
  if (!source || systemKeys.has(source.key)) return;
  if (beforeKey && systemKeys.has(beforeKey)) return;

  const showInNavigation = group === 'navigation';
  const moving = { ...source, show_in_navigation: showInNavigation };
  const isListed = (panel) => !systemKeys.has(panel.key)
    && (panel.show_in_navigation !== false) === showInNavigation;
  const crosses = (source.show_in_navigation !== false) !== showInNavigation;

  /** @type {Array} */
  let next;
  if (crosses) {
    // The moved panel leaves its old group and takes the drop position in the
    // new one, pushing the rows below it down.
    const others = panels.filter((panel) => panel !== source);
    const slots = others.map((_, position) => position).filter((position) => isListed(others[position]));
    const at = beforeKey ? others.findIndex((panel) => panel.key === beforeKey) : -1;
    next = [...others];
    next.splice(at >= 0 ? at : (slots.length ? slots[slots.length - 1] + 1 : others.length), 0, moving);
  } else {
    // Within a group the rows keep their slots, so a drop reorders the group
    // without moving the rows of the other group in between.
    const slots = panels.map((_, position) => position).filter((position) => isListed(panels[position]));
    const members = slots.map((position) => panels[position]);
    const ordered = members.filter((panel) => panel !== source);
    const to = beforeKey ? ordered.findIndex((panel) => panel.key === beforeKey) : ordered.length;
    if (to < 0) return;
    ordered.splice(to, 0, source);
    next = [...panels];
    slots.forEach((slot, position) => { next[slot] = ordered[position]; });
  }

  const unchanged = next.length === panels.length
    && next.every((panel, position) => panel === panels[position]);
  if (unchanged) return;

  const message = t('Panel moved to {group}')
    .replace('{group}', showInNavigation ? t('Navigation') : t('Non-Navigation'));
  host._savePanels(next, message);
}


/* ── duplicate ────────────────────────────────────────────────────────────── */

/**
 * Copy a panel with all its options under a new key, directly after the original.
 *
 * @param {any} host - editor component
 * @param {string} panelKey
 */
export function duplicatePanel(host, panelKey) {
  const panels = host._devicePanels();
  const index = panels.findIndex((panel) => panel.key === panelKey);
  if (index < 0 || getSystemPanelKeys(host).has(panelKey)) return;
  const source = panels[index];
  const copy = {
    ...clone(source),
    key: generateAutoKey(panels, source.type),
    ...(source.title ? { title: t('{name} (copy)').replace('{name}', source.title) } : {}),
  };
  const next = [...panels];
  next.splice(index + 1, 0, copy);
  host._savePanels(next, t('Panel duplicated'));
}

/* ── delete ───────────────────────────────────────────────────────────────── */

export function confirmDelete(host, index) {
  host._deleteTarget = index;
}

export function cancelDelete(host) {
  host._deleteTarget = null;
}

export async function doDelete(host) {
  const index = host._deleteTarget;
  host._deleteTarget = null;
  if (index === null || index === undefined) return;
  const panels = host._devicePanels();
  if (index < 0 || index >= panels.length) return;
  const newPanels = panels.filter((_, i) => i !== index);
  await host._savePanels(newPanels, t("Panel deleted"));
}

/* ── save ─────────────────────────────────────────────────────────────────── */

/**
 * Why `key` cannot be saved for the panel at `index` (-1 for a new one), or ''.
 *
 * @param {string|undefined} key
 * @param {{ panels: Array<any>, index: number, systemPanels: Array<any> }} context
 * @returns {string}
 */
export function panelKeyError(key, { panels, index, systemPanels }) {
  const wanted = (key || "").toLowerCase();
  if (!wanted) return "";
  // Reject duplicate keys (case-insensitive comparison)
  if ((panels || []).some((p, i) => i !== index && p.key && p.key.toLowerCase() === wanted)) {
    return t('Key "{key}" is already used by another panel').replace('{key}', key);
  }
  // Only the popups can be replaced; the hub refuses a panel under the key
  // of System, Blank, Settings or About.
  if ((systemPanels || []).some((sp) => !sp.editable && sp.key.toLowerCase() === wanted)) {
    return t('Key "{key}" belongs to a system panel').replace('{key}', key);
  }
  return "";
}

/**
 * The panel config a save stores, built from the editor's form data.
 *
 * @param {any} panel - the form's panel data (type, key, title, options)
 * @param {any} descriptor - the panel type's descriptor
 * @param {Object<string, Array>} [itemLists] - the editor's item lists by option key
 * @param {any} [existing] - the saved panel an edit replaces
 * @returns {any}
 */
export function buildPanelConfig(panel, descriptor, itemLists = {}, existing = null) {
  const panelType = panel.type || "clock";

  // Build the new panel config from the serialized panel data.
  // Item / item_list fields are handled separately from _itemListData below.
  const newPanel = Object.keys(panel).reduce((acc, k) => {
    if (descriptor?.options?.some(o => o.key === k)) {
      acc[k] = panel[k];
    } else if (!["type", "key", "title", "show_in_navigation"].includes(k)) {
      acc[k] = panel[k];
    }
    return acc;
  }, {});

  // Set the standard keys
  newPanel.type = panelType;
  newPanel.key = panel.key || "";
  if (panel.title) newPanel.title = panel.title;
  newPanel.show_in_navigation = panel.show_in_navigation !== false;

  // Handle item and item_list fields from _itemListData.
  // The dialog serializes option values via el.value, but item container divs
  // have no .value — the actual item data lives in _itemListData.
  // Also handle list_str (raw textarea string → item array).
  // We serialize it properly here, matching the original crud.js save().
  // Copy: this object is the edit dialog's own state, and a failed save must
  // leave its item lists intact for the next attempt.
  const itemListData = { ...(itemLists || {}) };
  if (descriptor?.options) {
    for (const opt of descriptor.options) {
      if (opt.kind === "item_list" && itemListData[opt.key]) {
        newPanel[opt.key] = itemListData[opt.key].map(serializeItem);
        delete itemListData[opt.key];
      } else if (opt.kind === "item") {
        const list = itemListData[opt.key] || [];
        const itemConfig = list[0];
        if (itemConfig) {
          newPanel[opt.key] = serializeItem(itemConfig);
        } else {
          newPanel[opt.key] = null;
        }
        delete itemListData[opt.key];
      } else if (opt.kind === "list_str") {
        // The dialog sends raw textarea string; convert to string array.
        // Only convert if the key was actually set by the user — otherwise
        // an empty array would override the entity's runtime default.
        if (opt.key in newPanel) {
          const raw = newPanel[opt.key];
          if (Array.isArray(raw)) {
            // Already the correct format (array of strings or {item: ...} objects).
            newPanel[opt.key] = raw
              .map((s) => (typeof s === "string" ? s : s.item || ""))
              .filter(Boolean);
          } else {
            newPanel[opt.key] = (typeof raw === "string" ? raw : "")
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean);
          }
        }
      } else if (opt.kind === "list_items" || opt.kind === "list_entities") {
        // Array of strings from renderListItemsField. Strip empties; drop the
        // key entirely if everything was blank so runtime defaults survive.
        if (opt.key in newPanel) {
          const raw = newPanel[opt.key];
          if (Array.isArray(raw)) {
            const cleaned = raw
              .map((s) => (typeof s === "string" ? s.trim() : s?.item || ""))
              .filter(Boolean);
            if (cleaned.length === 0) delete newPanel[opt.key];
            else newPanel[opt.key] = cleaned;
          }
        }
      } else if (itemListData[opt.key]) {
        // Generic fallback for any other kind with _itemListData
        newPanel[opt.key] = [...itemListData[opt.key]];
      }
    }
  }

  // Merge existing data for edits, but only for fields the form does NOT own.
  // Descriptor-declared options and standard fields (type/key/title/show_in_navigation/unlock_code)
  // come from the form — if the user cleared them, that absence is intentional
  // and must not be undone by merging stale values.
  if (existing) {
    const formOwned = new Set(
      ["type", "key", "title", "show_in_navigation", "unlock_code"]
        .concat((descriptor?.options || []).map(o => o.key))
    );
    for (const k of Object.keys(existing)) {
      if (formOwned.has(k)) continue;
      if (!(k in newPanel)) newPanel[k] = existing[k];
    }
  }
  return newPanel;
}

/**
 * Save panel data serialized by the panel editor view.
 * Called when the edit dialog fires dialog-save with detail.panel.
 * Performs duplicate-key validation before saving.
 *
 * System panel overrides are saved with the resolved user type (e.g. "light"
 * not "popup_light"). Backend resolves overrides by key, and popup aliases in
 * PANEL_MAPPING share their page class with the user-facing type, so the
 * runtime template stays correct.
 *
 * @param {HTMLElement} host - editor component
 * @param {Object} panel - serialized panel data
 * @param {number} index - panel index (-1 for add)
 */
export async function saveFromData(host, panel, index) {
  if (host.store.getState().hub.saving) return;
  host._error = null;

  const panels = host._devicePanels();

  const keyError = panelKeyError(panel.key, {
    panels, index, systemPanels: host.store.getState().hub.systemPanels,
  });
  if (keyError) {
    host._error = keyError;
    host.requestUpdate();
    return;
  }

  const panelType = panel.type || "clock";
  const newPanel = buildPanelConfig(
    panel,
    host._panelTypes.find((pt) => pt.type_key === panelType),
    host._itemListData || {},
    index >= 0 ? panels[index] : null,
  );

  const newPanels = [...panels];
  if (index >= 0) {
    newPanels[index] = newPanel;
  } else {
    newPanels.push(newPanel);
  }

  const action = index >= 0
    ? t('Saved "{name}"').replace('{name}', panel.key || t('panel'))
    : t('Added "{name}"').replace('{name}', panel.key || t('panel'));
  await host._savePanels(newPanels, action);
}

/* ── navigation visibility toggle ──────────────────────────────────────────── */

export function toggleNavVisibility(host, panelKey) {
  const panels = host._devicePanels();
  const idx = panels.findIndex(p => p.key === panelKey);
  if (idx < 0) return;
  const newPanels = panels.map((p, i) =>
    i === idx ? { ...p, show_in_navigation: p.show_in_navigation === false } : p
  );
  const nowShown = newPanels[idx].show_in_navigation;
  const message = nowShown
    ? t('Panel "{key}" shown in navigation')
    : t('Panel "{key}" hidden in navigation');
  host._savePanels(newPanels, message.replace('{key}', panelKey));
}

/* ── persist ──────────────────────────────────────────────────────────────── */

/**
 * POST the store with `newPanels` (and `deviceConfig`) for the selected device.
 * The store only changes once the server accepts the save; the dialog closes
 * here because that is UI state.
 *
/**
 * Save one device's panels; other device data is never part of this write.
 *
 * @returns {Promise<boolean>} whether the save was accepted
 */
export async function savePanels(
  host, newPanels, toastMessage, deviceName = host._selectedDevice
) {
  if (!deviceName || !host.entryId) return false;
  const saved = await host.store.actions.savePanels({
    panels: newPanels,
    toastMessage,
    deviceName,
  });
  if (saved) {
    if (host._editingPanel) host.store.actions.closeOverlay('panel-editor');
    host._editingPanel = null;
    host._editingPanelType = null;
    host._error = null;
  } else {
    host._error = host.store.getState().hub.error;
    host._serverErrors = host.store.getState().hub.fieldErrors;
  }
  return saved;
}

/** Save one device's settings without including its panels. */
export async function saveDeviceConfig(
  host, deviceConfig, toastMessage, deviceName = host._selectedDevice
) {
  if (!deviceName || !host.entryId) return false;
  const saved = await host.store.actions.saveDeviceConfig({
    deviceConfig,
    toastMessage,
    deviceName,
  });
  host._error = saved ? null : host.store.getState().hub.error;
  return saved;
}
