/**
 * NSPanel HAUI - Editor - form field render helpers.
 * Extracted from panel-editor.js _renderOptionField and _renderTypeFields methods.
 */

import { positionPickerDropdown, createDropdownKeyboardController } from './dom-helpers.js';
import { renderListItemsField, renderItemListField, renderItemListRow, renderItemEditFields } from './item-renderers.js';
import { html } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS, renderEntityPicker } from './haui-entity.js';
import {
  hexToRgb565,
  rgb565ToHex,
  hexToRgbList,
  hexToRgbArray,
  parseRgbListToHex,
  hexToColorMatching,
  COLOR_PRESETS,
} from './color-utils.js';
import {
  hasOverrides,
  detectItemType,
  parseItemValue,
  renderPanelKeyPicker,
  ITEM_TYPE,
  ITEM_LABELS,
  ITEM_TYPE_ICONS,
  ITEM_TYPE_SHORT,
  itemPrimaryText,
  itemSecondaryText,
} from './haui-item.js';


/**
 * Format a typed value (list, dict, number, bool, string) into a string suitable
 * for display in a form input. Lists render with brackets and ", " separators,
 * dicts render as JSON, primitives via String(). null/undefined → "".
 *
 * Preserves the original repr so editing a list value doesn't strip its brackets
 * when piped through `String(arr)` (which would join with commas only).
 */
export function formatFieldValue(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return "[" + v.map((x) => formatFieldValue(x)).join(", ") + "]";
  if (typeof v === "object") {
    try { return JSON.stringify(v); } catch { return String(v); }
  }
  return String(v);
}

/**
 * Parse a string from a form input back to its likely typed value.
 * Recognises integers, floats, JSON lists, JSON dicts. Templates and any
 * unrecognised string pass through unchanged. null/empty → "".
 *
 * Accepts both single-quoted and double-quoted JSON-like inputs.
 */
export function parseFieldValue(s) {
  if (s === null || s === undefined) return "";
  if (typeof s !== "string") return s;
  const str = s.trim();
  if (str === "") return "";
  // Templates pass through unchanged
  if (str.includes("{{")) return s;
  // Integer
  if (/^-?\d+$/.test(str)) {
    const n = parseInt(str, 10);
    if (Number.isFinite(n)) return n;
  }
  // Float
  if (/^-?\d+\.\d+$/.test(str)) {
    const n = parseFloat(str);
    if (Number.isFinite(n)) return n;
  }
  // List or dict (try JSON, then Python-style with single quotes)
  if ((str.startsWith("[") && str.endsWith("]")) ||
      (str.startsWith("{") && str.endsWith("}"))) {
    try { return JSON.parse(str); } catch {}
    try { return JSON.parse(str.replace(/'/g, '"')); } catch {}
  }
  return s;
}

/** Common MDI icons relevant to smart-home / NSPanel UI controls. */
const MDI_ICONS = [
  "home", "lightbulb", "lamp", "ceiling-light", "power",
  "thermometer", "water", "weather-sunny", "fan", "window-shutter",
  "door", "lock", "music", "speaker", "television",
  "timer", "alarm", "bell", "account", "cog",
  "wrench", "lightning-bolt", "flash", "palette", "brightness-5",
  "thermostat", "tune", "gesture-tap", "arrow-left", "arrow-right",
  "dots-grid", "view-dashboard", "remote", "motion-sensor", "smoke-detector",
  "fire", "snowflake", "leaf", "tree", "flower",
  "weather-night", "weather-rainy", "weather-windy", "weather-cloudy", "weather-fog",
  "weather-lightning", "weather-hail", "weather-snowy", "weather-partly-cloudy",
  "garage", "gate", "blinds", "curtains", "roller-shade",
  "light-recessed", "light-strip", "string-lights", "floor-lamp", "desk-lamp",
  "wall-sconce",
];

/** Quick-selected saved colors (persisted to localStorage). */
let _savedColors = null;
function getSavedColors() {
  if (_savedColors === null) {
    try {
      const raw = localStorage.getItem("haui_savedColors");
      _savedColors = raw ? JSON.parse(raw) : [];
    } catch { _savedColors = []; }
  }
  return _savedColors;
}
export function saveColor(hex) {
  const saved = getSavedColors();
  const filtered = saved.filter(c => c !== hex);
  filtered.unshift(hex);
  const trimmed = filtered.slice(0, 8);
  _savedColors = trimmed;
  try { localStorage.setItem("haui_savedColors", JSON.stringify(trimmed)); } catch {}
}

/** Render a row of preset color swatches that call onPick(hex) on click. */
export function renderColorPresets(currentHex, onPick) {
  const saved = getSavedColors();
  const showSaved = saved.length > 0;
  return html`
    ${showSaved ? html`
      <div class="color-presets">
        <span class="color-preset-label" style="margin-bottom:2px">${t("Recent")}</span>
        ${saved.map(h => html`
          <div
            class="color-preset-swatch"
            style="background:${h}"
            title=${h}
            @click=${() => onPick(h)}
          ></div>
        `)}
      </div>
    ` : ""}
    <div class="color-presets">
      <span class="color-preset-label">${t("Presets")}</span>
      ${COLOR_PRESETS.map(h => html`
        <div
          class="color-preset-swatch"
          style="background:${h}"
          title=${h}
          @click=${() => onPick(h)}
        ></div>
      `)}
    </div>
  `;
}

/** Cache of MDI icon names fetched from the backend. */
let _iconCache = null;
let _iconFetchPromise = null;

/** Fetch the full icon list from the backend (once). */
function _ensureIcons(hass) {
  if (_iconCache) return Promise.resolve(_iconCache);
  if (_iconFetchPromise) return _iconFetchPromise;
  _iconFetchPromise = (async () => {
    try {
      const url = "/api/nspanel_haui/icons";
      const resp = await (await hass.fetchWithAuth(url)).json();
      _iconCache = Array.isArray(resp) ? resp : [];
    } catch {
      // Fallback to a small curated set if the API fails
      _iconCache = [
        "home","lightbulb","lamp","ceiling-light","power",
        "thermometer","water","weather-sunny","fan","window-shutter",
        "door","lock","music","speaker","television",
        "timer","alarm","bell","account","cog",
        "wrench","lightning-bolt","flash","palette","brightness-5",
        "thermostat","tune","gesture-tap","arrow-left","arrow-right",
        "dots-grid","view-dashboard","remote","motion-sensor","smoke-detector",
        "fire","snowflake","leaf","tree","flower",
        "weather-night","weather-rainy","weather-windy","weather-cloudy","weather-fog",
        "weather-lightning","weather-hail","weather-snowy","weather-partly-cloudy",
        "garage","gate","blinds","curtains","roller-shade",
        "light-recessed","light-strip","string-lights","floor-lamp","desk-lamp",
        "wall-sconce",
      ];
    }
    _iconFetchPromise = null;
    return _iconCache;
  })();
  return _iconFetchPromise;
}

/** Show the icon dropdown attach a click-outside listener, and reposition to
 *  avoid clipping by dialog scroll containers. */
function _openIconDropdown(wrap) {
  const dropdown = wrap?.querySelector(".icon-dropdown");
  if (!dropdown) return;
  const items = dropdown.querySelectorAll(".icon-dropdown-item");
  items.forEach((item) => { item.hidden = false; });
  dropdown.hidden = items.length === 0;
  if (items.length === 0) return;

  const input = wrap?.querySelector(".icon-picker-input");
  if (dropdown && input) positionPickerDropdown(dropdown, input);

  if (wrap._outsideHandler) return;
  wrap._outsideHandler = (ev) => {
    if (!wrap || wrap.contains(ev.target)) return;
    _hideIconDropdown(wrap);
  };
  document.addEventListener("mousedown", wrap._outsideHandler);
}

/** Hide the icon dropdown and detach the outside listener. */
function _hideIconDropdown(wrap) {
  const dropdown = wrap?.querySelector(".icon-dropdown");
  if (dropdown) {
    dropdown.hidden = true;
    dropdown.style.visibility = '';
    dropdown.style.pointerEvents = '';
  }
  if (wrap) wrap._activeIndex = -1;
  if (wrap?._outsideHandler) {
    document.removeEventListener("mousedown", wrap._outsideHandler);
    delete wrap._outsideHandler;
  }
}
function iconNameOnly(val) {
  return String(val || "").replace(/^mdi:/, "");
}
/** Cache of rendered templates: template_string → rendered_text */
const _templateCache = {};
/** Debounce timers keyed by preview element id */
const _templateTimers = {};

/**
 * Resolve the preview <span> for a given previewId. Searches the contextEl's
 * own root (shadow root or document) first; falls back to scanning all shadow
 * roots reachable from the document.
 */
function _findPreviewEl(previewId, contextEl) {
  const sel = "#" + (typeof CSS !== "undefined" && CSS.escape ? CSS.escape(previewId) : previewId);
  if (contextEl?.getRootNode) {
    const r = contextEl.getRootNode();
    if (r && r.querySelector) {
      const hit = r.querySelector(sel);
      if (hit) return hit;
    }
  }
  // Fallback: traverse all shadow roots under document.
  const stack = [document];
  while (stack.length) {
    const root = stack.pop();
    if (!root) continue;
    if (root.querySelector) {
      const hit = root.querySelector(sel);
      if (hit) return hit;
    }
    const all = root.querySelectorAll ? root.querySelectorAll("*") : [];
    for (const node of all) {
      if (node.shadowRoot) stack.push(node.shadowRoot);
    }
  }
  return null;
}

/**
 * Schedule a template render via the HA template API.
 * Debounces rapid input by 500ms and caches results.
 *
 * @param {object}   hass        - HA hass object (for callWS)
 * @param {string}   value       - Raw field value (may contain {{ ... }} templates)
 * @param {string}   previewId   - DOM id of the <span> to update
 * @param {Element}  [contextEl] - Any element inside the host's render root —
 *                                 used to locate the span across shadow DOM.
 */
export function scheduleTemplateRender(hass, value, previewId, contextEl) {
  if (!hass) return;

  const el = _findPreviewEl(previewId, contextEl);
  const wrapper = el?.closest(".template-preview");
  const str = String(value || "");

  if (!str.includes("{{")) {
    if (wrapper) wrapper.hidden = true;
    return;
  }

  if (wrapper) wrapper.hidden = false;
  if (el) el.textContent = "...";

  if (_templateCache[str] !== undefined) {
    if (el) el.textContent = _templateCache[str];
    return;
  }

  if (_templateTimers[previewId]) clearTimeout(_templateTimers[previewId]);

  _templateTimers[previewId] = setTimeout(async () => {
    try {
      const result = await hass.callWS({ type: "render_template", template: str });
      _templateCache[str] = result;
      const el2 = _findPreviewEl(previewId, contextEl);
      if (el2) {
        el2.textContent = result;
        el2.style.color = "";
      }
    } catch (e) {
      const el2 = _findPreviewEl(previewId, contextEl);
      if (el2) {
        el2.textContent = t("(template error)");
        el2.style.color = "var(--error-color, red)";
      }
    }
  }, 500);
}

/**
 * Render an MDI icon picker: full-width autocomplete text field with a live
 * icon preview on the right and a filtered suggestion dropdown below.
 *
 * Icons are fetched from the backend API on first use and cached.
 * The dropdown closes on click-outside (document mousedown listener).
 *
 * @param {string}  id      - DOM id of the <ha-input> for the icon value
 * @param {string}  value   - Current value (e.g. "mdi:home")
 * @param {object}  [hass=null]   - HA hass object (needed for API call + template rendering)
 * @param {function} [onInput=null] - Called with the new value on every input/dropdown selection
 */
export function renderIconPicker(id, value, hass = null, onInput = null) {
  const currentVal = value || "";

  // Kick off background fetch (result used when focused)
  if (hass) _ensureIcons(hass);

  const iconList = _iconCache || MDI_ICONS;  // fall back to curated list until fetched

  const hasTpl = String(currentVal).includes("{{");

  return html`
    <div class="icon-picker-wrap">
      <ha-input
        id=${id}
        class="icon-picker-input"
        .value=${currentVal}
        placeholder=${t("mdi:home")}
        @input=${(e) => {
          const tf = e.target;
          const val = tf.value || "";
          const wrap = tf.closest(".icon-picker-wrap");
          const preview = wrap?.querySelector(".icon-preview");
          if (preview) preview.icon = val || "mdi:puzzle";
          const dropdown = wrap?.querySelector(".icon-dropdown");
          if (dropdown) {
            const name = iconNameOnly(val);
            const items = dropdown.querySelectorAll(".icon-dropdown-item");
            let any = false;
            items.forEach((item) => {
              const icon = item.getAttribute("data-icon") || "";
              const match = !name || icon.includes(name.toLowerCase());
              item.hidden = !match;
              if (match) any = true;
            });
            dropdown.hidden = !any;
          }
          if (hass) scheduleTemplateRender(hass, val, `tp-${id}`, tf);
          if (onInput) onInput(val);
        }}
        @focus=${async (e) => {
          const wrap = e.target.closest(".icon-picker-wrap");
          if (hass && _iconCache === null) {
            await _ensureIcons(hass);
            const dropdown = wrap?.querySelector(".icon-dropdown");
            if (dropdown) {
              dropdown.innerHTML = _iconCache.map((icon) =>
                '<div class="icon-dropdown-item" data-icon="' + icon + '">' +
                '<ha-icon icon="mdi:' + icon + '"></ha-icon>' +
                '<span>' + icon + '</span>' +
                '</div>'
              ).join("");
              dropdown.querySelectorAll(".icon-dropdown-item").forEach((item) => {
                item.addEventListener("mousedown", (ev) => {
                  _selectIcon(ev, wrap, hass);
                });
              });
            }
          }
          _openIconDropdown(wrap);
          if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`, e.target);
        }}
        @blur=${(e) => {
          const wrap = e.target?.closest(".icon-picker-wrap");
          setTimeout(() => { if (wrap) _hideIconDropdown(wrap); }, 80);
        }}
        @keydown=${createDropdownKeyboardController({
          getWrap: (e) => e.target.closest('.icon-picker-wrap'),
          dropdownSelector: '.icon-dropdown',
          itemSelector: '.icon-dropdown-item',
          indexField: '_activeIndex',
          onSelect: (visibleItems, idx) => {
            _selectIconItem(visibleItems[idx].closest('.icon-picker-wrap'), visibleItems[idx], hass, onInput);
          },
          onDismiss: (e) => _hideIconDropdown(e.target.closest('.icon-picker-wrap')),
        })}
      ></ha-input>
      <div class="icon-dropdown" hidden>
        ${iconList.map((icon) => html`
          <div class="icon-dropdown-item" data-icon="${icon}"
            @mousedown=${(e) => _selectIcon(e, e.target.closest(".icon-picker-wrap"), hass, onInput)}
          >
            <ha-icon icon="mdi:${icon}"></ha-icon>
            <span>${icon}</span>
          </div>
        `)}
      </div>
      <div class="icon-preview-row">
        <ha-icon class="icon-preview" icon=${currentVal || "mdi:puzzle"}></ha-icon>
        <span class="icon-preview-label">${currentVal || t("no icon selected")}</span>
      </div>
      <div class="template-preview" ?hidden=${!hasTpl}>
        <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
      </div>
    </div>
  `;
}

/** Handle icon mousedown selection (event delegation). */
function _selectIcon(e, wrap, hass, onInput) {
  e.preventDefault();
  const item = e.currentTarget;
  _selectIconItem(wrap, item, hass, onInput);
}

/** Apply icon selection: set value, update preview, hide dropdown. */
function _selectIconItem(wrap, item, hass, onInput) {
  const tf = wrap?.querySelector(".icon-picker-input");
  const preview = wrap?.querySelector(".icon-preview");
  const icon = item.getAttribute("data-icon") || "";
  const val = `mdi:${icon}`;
  if (tf) tf.value = val;
  if (preview) preview.icon = val;
  if (hass) scheduleTemplateRender(hass, val, `tp-${tf?.id || ""}`, tf);
  if (onInput) onInput(val);
  _hideIconDropdown(wrap);
}


/**
 * Render a plain <ha-input> with an optional full-width style.
 *
 * @param {string}  id              - DOM id for the field
 * @param {string}  value           - Current value
 * @param {boolean} [fullWidth=false] - When true, add ``style="width:100%"``
 * @param {object}  [hass=null]     - HA hass object for template rendering
 * @returns {import('./lit-import.js').TemplateResult}
 */
function renderTextField(id, value, fullWidth = false, hass = null) {
  const val = String(value != null ? value : "");
  const hasTemplate = val.includes("{{");

  const field = fullWidth
    ? html`
        <ha-input
          id=${id}
          .value=${val}
          class="w-full"
          @input=${(e) => { if (hass) scheduleTemplateRender(hass, e.target.value, `tp-${id}`, e.target); }}
          @focus=${(e) => { if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`, e.target); }}
        ></ha-input>
      `
    : html`
        <ha-input
          id=${id}
          .value=${val}
          @input=${(e) => { if (hass) scheduleTemplateRender(hass, e.target.value, `tp-${id}`, e.target); }}
          @focus=${(e) => { if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`, e.target); }}
        ></ha-input>
      `;

  if (!hass) return field;

  return html`
    ${field}
    <div class="template-preview" ?hidden=${!hasTemplate}>
      <span id="tp-${id}">${hasTemplate ? "..." : ""}</span>
    </div>
  `;
}

/** Inline template-preview block matching the .template-preview class. */
function templatePreview(id, value) {
  const has = String(value || "").includes("{{");
  return html`
    <div class="template-preview" ?hidden=${!has}>
      <span id="tp-${id}">${has ? "..." : ""}</span>
    </div>
  `;
}

/** Render a form control for a single PageOption. */
export function renderOptionField(host, opt, currentValue) {
  const id = `fld-${opt.key}`;
  const val =
    currentValue !== undefined && currentValue !== null
      ? currentValue
      : opt.default;

  switch (opt.kind) {
    case "bool":
      return html`
        <div class="checkbox-wrap">
          <div class="checkbox-row">
            <ha-switch
              id=${id}
              ?checked=${Boolean(val)}
              @change=${(e) => {
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: e.target.checked },
                };
                host.requestUpdate();
              }}
            ></ha-switch>
            <label for=${id} title=${opt.description}>${opt.label}</label>
          </div>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "int":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-input
            id=${id}
            type="number"
            .inputMode="numeric"
            step="1"
            .value=${String(val != null ? val : "")}
            @input=${(e) => {
              const v = e.target.value;
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: parseInt(v, 10) || 0,
                },
              };
              host.requestUpdate();
            }}
          ></ha-input>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "float":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-input
            id=${id}
            type="number"
            .inputMode="numeric"
            step="any"
            .value=${String(val != null ? val : "")}
            @input=${(e) => {
              const v = e.target.value;
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: parseFloat(v) || 0.0,
                },
              };
              host.requestUpdate();
            }}
          ></ha-input>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "color": {
      const colorHex = parseRgbListToHex(val);
      const displayStr = formatFieldValue(val);
      const hasTpl = displayStr.includes("{{");
      const handlePresetPick = (hex) => {
        const prevVal = host._editingPanel?.data?.[opt.key];
        const newVal = hexToColorMatching(hex, prevVal);
        host._editingPanel = {
          ...host._editingPanel,
          data: { ...host._editingPanel.data, [opt.key]: newVal },
        };
        saveColor(hex);
        host.requestUpdate();
      };
      return html`
        <div class="form-group color-form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <div class="color-picker-wrap">
            <ha-input id=${id} .value=${displayStr}
              @input=${(e) => {
                const raw = e.target.value;
                if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: parseFieldValue(raw) },
                };
                host.requestUpdate();
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target); }}
            ></ha-input>
            <ha-icon-button
              class="color-picker-btn"
              @click=${(e) => {
                const wrap = e.target.closest(".color-picker-wrap");
                const input = wrap?.querySelector("input[type=color]");
                if (input) input.click();
              }}
              title=${t("Pick color")}
            >
              <ha-icon icon="mdi:palette"></ha-icon>
            </ha-icon-button>
            <input
              type="color"
              class="color-input-hidden"
              .value=${colorHex || "#000000"}
              @input=${(e) => {
                const hex = e.target.value;
                const prevVal = host._editingPanel?.data?.[opt.key];
                const newVal = hexToColorMatching(hex, prevVal);
                const group = e.target.closest(".color-form-group");
                const tf = group?.querySelector(".color-picker-wrap ha-input");
                if (tf) tf.value = formatFieldValue(newVal);
                saveColor(hex);
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: newVal },
                };
                host.requestUpdate();
              }}
            />
          </div>
          ${!hasTpl && val != null && val !== ""
            ? html`
                <div class="color-preview-row">
                  <div class="color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
                  <span class="color-preview-label">${colorHex || t("no color")}</span>
                </div>`
            : ""}
          ${!hasTpl ? renderColorPresets(colorHex, handlePresetPick) : ""}
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          <div class="template-preview" ?hidden=${!hasTpl}>
            <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
          </div>
        </div>
      `;
    }

    case "item":
      // Single-item field uses the same dialog as item_list.
      // Store as a one-element array in _itemListData for consistent handling.
      if (!host._itemListData) host._itemListData = {};
      if (!host._itemListData[opt.key]) {
        // Normalize: if val is a dict (new format), use it; if string (legacy/encoded), wrap it.
        let itemConfig = {};
        if (val && typeof val === "object") {
          itemConfig = { ...val };
        } else {
          itemConfig = { item: val || null };
        }
        // Merge any override fields already stored at the panel level.
        // Skip 'value' merging — the value should come from the entity or be empty,
        // not from the panel's legacy flat field.
        for (const f of ENTITY_OVERRIDE_FIELDS) {
          if (f === 'value') continue;
          const panelVal = host._editingPanel?.data?.[f];
          if (panelVal && !itemConfig[f]) itemConfig[f] = panelVal;
        }
        host._itemListData[opt.key] = [itemConfig];
      }

      const item = host._itemListData[opt.key][0] || {};
      const domain = opt.domain || "";
      const isEditing =
        host._editingItem != null &&
        host._editingItem.optKey === opt.key &&
        host._editingItem.index === 0;

      return html`
        <div class="form-group" id="fld-${opt.key}">
          <label title=${opt.description}>${opt.label}</label>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}

          ${isEditing
            ? renderItemEditFields(host)
            : renderItemListRow(host, item, {
                onEdit: () => {
                  host._editingItem = {
                    optKey: opt.key,
                    index: 0,
                    config: { ...item },
                    domain,
                  };
                  host._editingItemType = detectItemType(item?.item);
                  host.requestUpdate();
                },
              })}
        </div>
      `;

    case "select":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-select
            id=${id}
            .value=${String(val != null ? val : "")}
            .options=${(opt.choices || []).map((c) =>
              Array.isArray(c) ? { value: c[0], label: c[1] } : c
            )}
            @selected=${(e) => {
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: e.detail.value,
                },
              };
              host.requestUpdate();
            }}
          >
          </ha-select>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "list_items":
      return renderListItemsField(host, opt, val, id);

    case "list_entities":
      return renderListItemsField(host, opt, val, id, { entityPicker: true });

    case "list_str":
      // val may be an array of {item: "light.x"} dicts or plain strings.
      // Normalize to a newline-separated list of HA entity IDs for the textarea.
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <textarea
            id=${id}
            class="w-full"
            .value=${Array.isArray(val)
              ? val.map((v) => (typeof v === "string" ? v : v?.item || "")).join("\n")
              : String(val != null ? val : "")}
            @input=${(e) => {
              const v = e.target.value;
              const ep = host._editingPanel || { index: -1, data: {} };
              host._editingPanel = {
                ...ep,
                data: {
                  ...ep.data,
                  [opt.key]: v,
                },
              };
              host.requestUpdate();
            }}
          ></textarea>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "item_list":
      return renderItemListField(host, opt, currentValue);

    case "icon":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          ${renderIconPicker(id, val, host.hass, (newVal) => {
            host._editingPanel = {
              ...host._editingPanel,
              data: {
                ...host._editingPanel.data,
                [opt.key]: newVal,
              },
            };
            host.requestUpdate();
          })}
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "generic": {
      const displayStr = formatFieldValue(val);
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-input
            id=${id}
            .value=${displayStr}
            class="w-full"
            @input=${(e) => {
              const raw = e.target.value;
              if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: parseFieldValue(raw),
                },
              };
              host.requestUpdate();
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target); }}
          ></ha-input>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          ${host.hass
            ? html`
                <div class="template-preview" ?hidden=${!(String(val).includes("{{"))}>
                  <span id="tp-${id}">${(String(val).includes("{{")) ? "..." : ""}</span>
                </div>
              `
            : ""}
        </div>
      `;
    }

    default:
      // str or unknown → text field
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-input
            id=${id}
            .value=${String(val != null ? val : "")}
            class="w-full"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target);
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: e.target.value,
                },
              };
              host.requestUpdate();
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target); }}
          ></ha-input>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          ${host.hass
            ? html`
                <div class="template-preview" ?hidden=${!(String(val).includes("{{"))}>
                  <span id="tp-${id}">${(String(val).includes("{{")) ? "..." : ""}</span>
                </div>
              `
            : ""}
        </div>
      `;
  }
}

/**
 * Return an array of {section, options} groups from a descriptor's options,
 * preserving order of first appearance.  Options with `section===null` (or
 * undefined/falsy) are grouped under `{section: null}` — the "default" group.
 */
export function getPanelOptionGroups(descriptor) {
  if (!descriptor || !descriptor.options || descriptor.options.length === 0) {
    return [];
  }
  const groups = [];
  const sectionOrder = [];
  const seenSections = {};
  for (const opt of descriptor.options) {
    const section = opt.section || null;
    if (!seenSections[section]) {
      seenSections[section] = true;
      sectionOrder.push(section);
      groups.push({ section, options: [] });
    }
    groups[sectionOrder.indexOf(section)].options.push(opt);
  }
  return groups;
}

/** Render type-specific form fields from the descriptor. */
export function renderTypeFields(host, panelType, currentData) {
  const descriptor = host._panelTypes.find(
    (pt) => pt.type_key === panelType
  );
  if (!descriptor || !descriptor.options || descriptor.options.length === 0) {
    return html`<p style="color:var(--secondary-text-color,#666)">
      ${t("No additional options for this panel type.")}
    </p>`;
  }

  const groups = getPanelOptionGroups(descriptor);
  return html`
    ${groups.map(
      (group) => html`
        ${group.section
          ? html`<h3 class="section-header">${group.section}</h3>`
          : ""}
        ${group.options.map((opt) => renderOptionField(host, opt, currentData[opt.key]))}
      `
    )}
  `;
}
