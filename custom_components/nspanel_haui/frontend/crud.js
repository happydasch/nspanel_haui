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
import { serializeItem } from './haui-item.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';
import { formVal } from './dom-helpers.js';

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
  let prevIdx = idx - 1;
  while (prevIdx >= 0 && panels[prevIdx].show_in_navigation === false) {
    prevIdx--;
  }
  if (prevIdx < 0) return;
  const newPanels = [...panels];
  [newPanels[prevIdx], newPanels[idx]] = [newPanels[idx], newPanels[prevIdx]];
  host._savePanels(newPanels, "Panel moved up");
}

export function moveDown(host, panelKey) {
  const panels = host._devicePanels();
  const idx = panels.findIndex(p => p.key === panelKey);
  if (idx < 0) return;
  let nextIdx = idx + 1;
  while (nextIdx < panels.length && panels[nextIdx].show_in_navigation === false) {
    nextIdx++;
  }
  if (nextIdx >= panels.length) return;
  const newPanels = [...panels];
  [newPanels[idx], newPanels[nextIdx]] = [newPanels[nextIdx], newPanels[idx]];
  host._savePanels(newPanels, "Panel moved down");
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
  await host._savePanels(newPanels, "Panel deleted");
}

/* ── save ─────────────────────────────────────────────────────────────────── */

export async function save(host) {
  if (host._saving) return;
  host._error = null;

  const form = host.renderRoot ? host.renderRoot.querySelector("#panel-edit-form") : null;
  if (!form) return;

  const ep = host._editingPanel;
  if (!ep) return;

  // Read base fields from form (query custom elements directly - FormData
  // only reads native inputs and won't see ha-input / ha-select).
  const panelType = host._editingPanelType || formVal(form, "fld-type") || "clock";
  const panel = clone(ep.data);
  panel.type = panelType;
  panel.key = formVal(form, "fld-key") || panel.key;
  panel.title = formVal(form, "fld-title") || "";
  // Read show_in_navigation checkbox
  const showInNavEl = form.querySelector("#fld-show-in-nav");
  if (showInNavEl) {
    panel.show_in_navigation = showInNavEl.checked;
  } else if (panel.show_in_navigation == null) {
    panel.show_in_navigation = true;
  }
  // Defensive fallback: if key is still empty, auto-generate one
  if (!panel.key) {
    panel.key = generateAutoKey(host, panelType);
  }

  // Reject duplicate keys (case-insensitive comparison)
  const panels = host._devicePanels();
  const duplicateKey = panels.some(
    (p, i) => i !== ep.index && p.key && p.key.toLowerCase() === panel.key.toLowerCase()
  );
  if (duplicateKey) {
    host._error = `Key "${panel.key}" is already used by another panel`;
    return;
  }

  // Read type-specific fields from descriptor (panelType already set above)
  const descriptor = host._panelTypes.find(
    (pt) => pt.type_key === panelType
  );
  if (descriptor && descriptor.options) {
    for (const opt of descriptor.options) {
      const el = form.querySelector(`#fld-${opt.key}`);
      if (!el) continue;

      if (opt.kind === "bool") {
        panel[opt.key] = el.checked || false;
      } else if (opt.kind === "int") {
        const v = parseInt(el.value, 10);
        panel[opt.key] = isNaN(v) ? (opt.default != null ? opt.default : 0) : v;
      } else if (opt.kind === "color_seed") {
        const v = parseInt(el.value, 10);
        panel[opt.key] = isNaN(v) ? (opt.default != null ? opt.default : 0) : v;
      } else if (opt.kind === "float") {
        const v = parseFloat(el.value);
        panel[opt.key] = isNaN(v) ? (opt.default != null ? opt.default : 0.0) : v;
      } else if (opt.kind === "list_str") {
        panel[opt.key] = (el.value || "")
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((entity_id) => ({ item: entity_id }));
      } else if (opt.kind === "item_list") {
        const list = host._itemListData?.[opt.key] || [];
        panel[opt.key] = list.map(serializeItem);
        // Clean up after save
        delete host._itemListData[opt.key];
      } else if (opt.kind === "item") {
        // Read from shared _itemListData (single item stored at index 0).
        const list = host._itemListData?.[opt.key] || [];
        const itemConfig = list[0];
        if (itemConfig) {
          panel[opt.key] = serializeItem(itemConfig);
        } else {
          panel[opt.key] = null;
        }
        // Remove any legacy flat override fields from panel level
        for (const f of ENTITY_OVERRIDE_FIELDS) {
          delete panel[f];
        }
        delete host._itemListData[opt.key];
      } else {
        // str, color, select
        panel[opt.key] = el.value || "";
      }
    }
  }

  // Merge existing data for any fields we might be missing
  // (preserve fields not rendered in the form)
  // Only do this for edit (not add)
  if (ep.index >= 0) {
    const existing = host._devicePanels()[ep.index];
    if (existing) {
      for (const k of Object.keys(existing)) {
        if (!(k in panel)) panel[k] = existing[k];
      }
    }
  }

  const newPanels =
    ep.index >= 0
      ? panels.map((p, i) => (i === ep.index ? panel : p))
      : [...panels, panel];

  const action =
    ep.index >= 0 ? `Saved "${panel.key || "panel"}"` : `Added "${panel.key || "panel"}"`;
  await host._savePanels(newPanels, action);
}

/**
 * Save panel data that was serialized by ha-dialog-edit-panel.
 * Called when the edit dialog fires dialog-save with detail.panel.
 * Performs duplicate-key validation before saving.
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
    host._error = `Key "${panel.key}" is already used by another panel`;
    host.requestUpdate();
    return;
  }

  // Read type-specific fields from descriptor
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
  newPanel.title = panel.title || "";
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
        // The dialog sends raw textarea string; convert to item array.
        const raw = newPanel[opt.key];
        newPanel[opt.key] = (typeof raw === "string" ? raw : "")
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((entity_id) => ({ item: entity_id }));
      } else if (itemListData[opt.key]) {
        // Generic fallback for any other kind with _itemListData
        newPanel[opt.key] = [...itemListData[opt.key]];
      }
    }
  }

  // Merge existing data for edits (preserve fields not in the current form)
  if (index >= 0) {
    const existing = host._devicePanels()[index];
    if (existing) {
      for (const k of Object.keys(existing)) {
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

  const action = index >= 0 ? `Saved "${panel.key || "panel"}"` : `Added "${panel.key || "panel"}"`;
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
  const label = nowShown ? "shown" : "hidden";
  host._savePanels(newPanels, `Panel "${panelKey}" ${label} in navigation`);
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
      host._error = err.message || `Save failed (HTTP ${resp.status})`;
      host._showToast(host._error, "error");
    }
  } catch (e) {
    console.error("Save failed:", e);
    host._error = e.message || "Network error";
    host._showToast(host._error, "error");
  }
  host._saving = false;
}
