/**
 * NSPanel HAUI - Editor - CRUD operations.
 * Extracted from panel-editor.js; see that file for the class that delegates to these helpers.
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

/* ── helpers ────────────────────────────────────────────────────────────────── */

/** Generate an unused auto-key like "{type}_{n}" for the given panel type. */
export function generateAutoKey(host, panelType) {
  const panels = host._devicePanels();
  const usedKeys = new Set(
    panels.filter(p => p.type === panelType).map(p => p.key)
  );
  let idx = 0;
  while (usedKeys.has(`${panelType}_${idx}`)) idx++;
  return `${panelType}_${idx}`;
}

/* ── panel lifecycle ──────────────────────────────────────────────────────── */

export function openAdd(host) {
  host._dialogVersion = (host._dialogVersion || 0) + 1;
  host._itemListData = {};
  const firstType =
    host._panelTypes.length > 0 ? host._panelTypes[0].type_key : "clock";
  // Auto-generate an unused key like "grid_0", "grid_1", etc.
  // Compute key BEFORE setting _editingPanel so Lit sees it in the initial render.
  const data = defaultPanel(firstType);
  data.key = generateAutoKey(host, firstType);
  host._editingPanel = { index: -1, data };
  host._editingPanelType = firstType;
  host._error = null;
  host._deleteTarget = null;
}

export function openEdit(host, index) {
  host._dialogVersion = (host._dialogVersion || 0) + 1;
  host._itemListData = {};
  const panels = host._devicePanels();
  if (index < 0 || index >= panels.length) return;
  const data = clone(panels[index]);
  host._editingPanel = { index, data };
  host._editingPanelType = data.type || "clock";
  host._error = null;
  host._deleteTarget = null;
}

export function closeEdit(host) {
  host._itemListData = {};
  host._editingPanel = null;
  host._editingPanelType = null;
  host._error = null;
}

/* ── list actions ─────────────────────────────────────────────────────────── */

export function moveUp(host, panelKey) {
  const panels = host._devicePanels();
  const idx = panels.findIndex(p => p.key === panelKey);
  if (idx < 0) return;
  const isNav = panels[idx].show_in_navigation !== false;
  let prevIdx = idx - 1;
  if (isNav) {
    while (prevIdx >= 0 && panels[prevIdx].show_in_navigation === false) prevIdx--;
  } else {
    while (prevIdx >= 0 && panels[prevIdx].show_in_navigation !== false) prevIdx--;
  }
  if (prevIdx < 0) return;
  const newPanels = [...panels];
  [newPanels[prevIdx], newPanels[idx]] = [newPanels[idx], newPanels[prevIdx]];
  host._savePanels(newPanels, t("Panel moved up"));
}

export function moveDown(host, panelKey) {
  const panels = host._devicePanels();
  const idx = panels.findIndex(p => p.key === panelKey);
  if (idx < 0) return;
  const isNav = panels[idx].show_in_navigation !== false;
  let nextIdx = idx + 1;
  if (isNav) {
    while (nextIdx < panels.length && panels[nextIdx].show_in_navigation === false) nextIdx++;
  } else {
    while (nextIdx < panels.length && panels[nextIdx].show_in_navigation !== false) nextIdx++;
  }
  if (nextIdx >= panels.length) return;
  const newPanels = [...panels];
  [newPanels[idx], newPanels[nextIdx]] = [newPanels[nextIdx], newPanels[idx]];
  host._savePanels(newPanels, t("Panel moved down"));
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
 * Save panel data that was serialized by ha-dialog-edit-panel.
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
  if (host._saving) return;
  host._error = null;

  const panels = host._devicePanels();

  // Reject duplicate keys (case-insensitive comparison)
  const duplicateKey = panels.some(
    (p, i) => i !== index && p.key && p.key.toLowerCase() === (panel.key || "").toLowerCase()
  );
  if (duplicateKey) {
    host._error = `${t('Key')} "${panel.key}" ${t('is already used by another panel')}`;
    host.requestUpdate();
    return;
  }

  // Read type-specific fields from descriptor
  // Use panel.type (resolved user type) for descriptor lookup
  const panelType = panel.type || "clock";
  const descriptor = host._panelTypes.find((pt) => pt.type_key === panelType);

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
  const itemListData = host._itemListData || {};
  const descriptorPt = host._panelTypes.find(pt => pt.type_key === panelType);
  if (descriptorPt?.options) {
    for (const opt of descriptorPt.options) {
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
  if (index >= 0) {
    const existing = host._devicePanels()[index];
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
  }

  const newPanels = [...panels];
  if (index >= 0) {
    newPanels[index] = newPanel;
  } else {
    newPanels.push(newPanel);
  }

  const action = index >= 0 ? `${t('Saved')} "${panel.key || t('panel')}"` : `${t('Added')} "${panel.key || t('panel')}"`;
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
  const label = nowShown ? t('shown') : t('hidden');
  host._savePanels(newPanels, `${t('Panel')} "${panelKey}" ${label} ${t('in navigation')}`);
}

/* ── persist ──────────────────────────────────────────────────────────────── */

export async function savePanels(host, newPanels, toastMessage) {
  if (!host._selectedDevice || !host.entryId) return;

  host._saving = true;
  try {
    const payload = clone(host._panels);
    if (!payload.devices) payload.devices = {};
    if (!payload.devices[host._selectedDevice]) {
      payload.devices[host._selectedDevice] = {};
    }
    payload.devices[host._selectedDevice].panels = newPanels;
    // Preserve device config if present
    if (host._deviceConfig) {
      payload.devices[host._selectedDevice].config = clone(host._deviceConfig);
    }

    const resp = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/panels/${host.entryId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (resp.ok) {
      host._panels = payload;
      host._editingPanel = null;
      host._editingPanelType = null;
      host._showToast(toastMessage, "success");
    } else {
      const err = await resp.json().catch(() => ({}));
      host._error = err.message || `${t('Save failed')} (HTTP ${resp.status})`;
      host._showToast(host._error, "error");
    }
  } catch (e) {
    console.error("Save failed:", e);
    host._error = e.message || t("Network error");
    host._showToast(host._error, "error");
  }
  host._saving = false;
}
