/**
 * NSPanel HAUI - Editor - form field render helpers.
 * Extracted from panel-editor.js _renderOptionField and _renderTypeFields methods.
 */

import { html } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS, renderEntityPicker } from './haui-entity.js';
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
function formatFieldValue(v) {
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
function parseFieldValue(s) {
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

/** Convert hex #rrggbb to RGB565 integer (0-65535). */
function hexToRgb565(hex) {
  const m = hex.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (!m) return 0;
  const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
  return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}


/** Convert hex #rrggbb to "[r, g, b]" string. */
function hexToRgbList(hex) {
  const m = hex.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (!m) return "";
  return `[${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}]`;
}

/** Convert hex #rrggbb to [r, g, b] number array. */
function hexToRgbArray(hex) {
  const m = hex.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (!m) return null;
  return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
}

/** Convert a [r5,g6,b5] RGB565 integer to a `#rrggbb` hex string. */
function rgb565ToHex(num) {
  const n = num | 0;
  const r5 = (n >> 11) & 0x1F;
  const g6 = (n >> 5) & 0x3F;
  const b5 = n & 0x1F;
  const r = Math.round((r5 * 255) / 31);
  const g = Math.round((g6 * 255) / 63);
  const b = Math.round((b5 * 255) / 31);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * Parse any color value to hex #rrggbb, or "" if unparseable.
 * Accepts: number (RGB565), [r,g,b] array, "[r, g, b]" string, "#rrggbb" / "rrggbb".
 */
function parseRgbListToHex(val) {
  if (val === null || val === undefined || val === "") return "";
  // Number → RGB565
  if (typeof val === "number") return rgb565ToHex(val);
  // [r, g, b] array
  if (Array.isArray(val) && val.length === 3) {
    const r = Math.min(255, Math.max(0, parseInt(val[0], 10)));
    const g = Math.min(255, Math.max(0, parseInt(val[1], 10)));
    const b = Math.min(255, Math.max(0, parseInt(val[2], 10)));
    if ([r, g, b].every(Number.isFinite)) {
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }
    return "";
  }
  const s = String(val).trim();
  // Template string — skip (no preview available)
  if (s.includes("{{")) return "";
  // RGB565 integer string (e.g., "12345") — convert to hex for preview
  if (/^\d{1,5}$/.test(s)) return rgb565ToHex(parseInt(s, 10));
  // "[r, g, b]" format
  const rgbMatch = s.match(/\[\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]/);
  if (rgbMatch) {
    const r = Math.min(255, Math.max(0, parseInt(rgbMatch[1])));
    const g = Math.min(255, Math.max(0, parseInt(rgbMatch[2])));
    const b = Math.min(255, Math.max(0, parseInt(rgbMatch[3])));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
  // "#rrggbb" or "rrggbb" format
  const hexMatch = s.match(/^#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/);
  if (hexMatch) {
    return `#${hexMatch[1].toLowerCase()}${hexMatch[2].toLowerCase()}${hexMatch[3].toLowerCase()}`;
  }
  return "";
}

/**
 * Convert a hex #rrggbb to a new color value, matching the type of the
 * previous value: number (RGB565), array [r,g,b], "[r, g, b]" string, "#rrggbb"
 * string, or number as a default fallback.
 */
function hexToColorMatching(hex, prevVal) {
  if (Array.isArray(prevVal)) return hexToRgbArray(hex);
  if (typeof prevVal === "number") return hexToRgb565(hex);
  if (typeof prevVal === "string") {
    const t = prevVal.trim();
    if (t.startsWith("[")) return hexToRgbList(hex);
    if (t.startsWith("#")) return hex;
  }
  return hexToRgb565(hex);
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

/** Show the icon dropdown and attach a click-outside listener. */
function _openIconDropdown(wrap) {
  const dropdown = wrap?.querySelector(".icon-dropdown");
  if (!dropdown) return;
  const items = dropdown.querySelectorAll(".icon-dropdown-item");
  items.forEach((item) => { item.hidden = false; });
  dropdown.hidden = items.length === 0;
  if (items.length === 0) return;

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
  if (dropdown) dropdown.hidden = true;
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
function scheduleTemplateRender(hass, value, previewId, contextEl) {
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
function renderIconPicker(id, value, hass = null, onInput = null) {
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
        @keydown=${(e) => {
          const wrap = e.target.closest(".icon-picker-wrap");
          const dropdown = wrap?.querySelector(".icon-dropdown");
          if (!dropdown || dropdown.hidden) return;

          const visibleItems = [...dropdown.querySelectorAll(".icon-dropdown-item")]
            .filter((el) => !el.hidden);
          if (!visibleItems.length) return;

          let idx = wrap._activeIndex != null ? wrap._activeIndex : -1;

          if (e.key === "ArrowDown") {
            e.preventDefault();
            idx = Math.min(idx + 1, visibleItems.length - 1);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            idx = Math.max(idx - 1, 0);
          } else if (e.key === "Enter") {
            if (idx >= 0) {
              e.preventDefault();
              _selectIconItem(wrap, visibleItems[idx], hass, onInput);
            }
            return;
          } else if (e.key === "Escape") {
            e.preventDefault();
            _hideIconDropdown(wrap);
            return;
          } else {
            return;
          }

          wrap._activeIndex = idx;
          dropdown.querySelectorAll(".icon-dropdown-item").forEach((item, i) => {
            item.classList.toggle("active", i === idx);
          });
          if (visibleItems[idx]) {
            visibleItems[idx].scrollIntoView({ block: "nearest" });
          }
        }}
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
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: newVal },
                };
                host.requestUpdate();
              }}
            />
          </div>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          ${val != null && val !== ""
            ? html`
                <div class="color-preview-row">
                  <div class="color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
                  <span class="color-preview-label">${colorHex || t("no color")}</span>
                </div>`
            : ""}
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
 * Render a single item list row with type icon, primary/secondary text,
 * override badge, and action buttons.
 *
 * @param {object} host - Lit host element
 * @param {object} item - the item config
 * @param {object} actions - { onEdit, onRemove?, onMoveUp?, onMoveDown? } —
 *   omit handlers to omit the corresponding button.
 * @param {object} flags - { canMoveUp, canMoveDown }
 */
function renderItemListRow(host, item, actions, flags = {}) {
  const type = detectItemType(item?.item);
  const icon = (item && item.icon) || ITEM_TYPE_ICONS[type] || 'mdi:circle-outline';
  const typeLabel = ITEM_TYPE_SHORT[type] || t('Item');
  const primary = itemPrimaryText(item);
  const secondary = itemSecondaryText(item);
  const showTypeChip = !item?.name; // primary already is the type label when no name
  // Resolve colors to hex for visual preview — skip template strings and
  // state-based dicts (those depend on runtime state).
  const parseItemColor = (val) =>
    val && !(typeof val === 'object' && !Array.isArray(val))
      ? parseRgbListToHex(val)
      : '';
  const itemColor = parseItemColor(item?.color);
  const itemBackColor = parseItemColor(item?.back_color);
  const iconBgStyle = itemBackColor
    ? `background-color:${itemBackColor};`
    : '';
  const iconColorStyle = itemColor
    ? `color:${itemColor};`
    : '';
  return html`
    <div class="item-list-row">
      <span class="item-row-icon" style=${iconBgStyle || ''}>
        <ha-icon icon=${icon} style=${iconColorStyle || ''}></ha-icon>
        ${itemColor
          ? html`<span
              class="item-row-color-dot"
              style="background-color:${itemColor}"
              title=${`${t("Color")}: ${itemColor}`}
            ></span>`
          : ''}
      </span>
      <div class="item-row-text">
        <div class="item-row-primary">
          <span class="item-row-name">${primary}</span>
          ${showTypeChip
            ? ''
            : html`<span class="item-row-chip">${typeLabel}</span>`}
          ${hasOverrides(item)
            ? html`<span class="item-list-override-badge" title=${t("Has override fields")}>⚙</span>`
            : ''}
        </div>
        ${secondary
          ? html`<div class="item-row-secondary">${secondary}</div>`
          : ''}
      </div>
      <div class="item-row-actions">
        ${actions.onMoveUp
          ? html`<ha-icon-button
              title=${t("Move up")}
              ?disabled=${!flags.canMoveUp}
              @click=${actions.onMoveUp}
            ><ha-icon icon="mdi:arrow-up"></ha-icon></ha-icon-button>`
          : ''}
        ${actions.onMoveDown
          ? html`<ha-icon-button
              title=${t("Move down")}
              ?disabled=${!flags.canMoveDown}
              @click=${actions.onMoveDown}
            ><ha-icon icon="mdi:arrow-down"></ha-icon></ha-icon-button>`
          : ''}
        ${actions.onEdit
          ? html`<ha-icon-button title=${t("Edit")} @click=${actions.onEdit}>
              <ha-icon icon="mdi:pencil"></ha-icon>
            </ha-icon-button>`
          : ''}
        ${actions.onRemove
          ? html`<ha-icon-button title=${t("Remove")} @click=${actions.onRemove}>
              <ha-icon icon="mdi:delete"></ha-icon>
            </ha-icon-button>`
          : ''}
      </div>
    </div>
  `;
}

/**
 * Render a list-of-strings editor for `kind: list_items` and `kind: list_entities`.
 * One input per item with remove button, plus an add button.
 * Uses select only when `opt.choices` has entries. `list_entities` uses the
 * Home Assistant entity picker when hass is available.
 */
export function renderListItemsField(host, opt, currentValue, id, options = {}) {
  const ep = host._editingPanel || { index: -1, data: {} };
  let list = ep.data?.[opt.key];
  if (!Array.isArray(list)) {
    list = Array.isArray(currentValue)
      ? currentValue.map((v) => (typeof v === "string" ? v : v?.item || ""))
      : [];
    host._editingPanel = { ...ep, data: { ...ep.data, [opt.key]: list } };
  }

  const domain = opt.domain || "";
  const choices = Array.isArray(opt.choices) ? opt.choices : null;
  const max = opt.max_items;

  const mutate = (fn) => {
    const cur = host._editingPanel?.data?.[opt.key];
    const arr = Array.isArray(cur) ? [...cur] : [];
    fn(arr);
    host._editingPanel = {
      ...host._editingPanel,
      data: { ...host._editingPanel.data, [opt.key]: arr },
    };
    host.requestUpdate();
  };

  const renderRowInput = (item, i) => {
    const rowId = `${id}-${i}`;
    if (choices?.length > 0 && !options.entityPicker) {
      return html`
        <ha-select
          id=${rowId}
          class="w-full"
          .value=${String(item != null ? item : "")}
          .options=${choices.map((c) =>
            Array.isArray(c) ? { value: c[0], label: c[1] } : c
          )}
          @selected=${(e) => {
            const v = e.detail.value;
            mutate((arr) => { arr[i] = v; });
          }}
          @closed=${(e) => e.stopPropagation()}
        >
        </ha-select>
      `;
    }
    if (options.entityPicker && host.hass) {
      return renderEntityPicker(host, {
        id: rowId,
        value: item || "",
        hass: host.hass,
        domain,
        placeholder: `${domain}.…`,
        onInput: (v) => {
          const cur = host._editingPanel?.data?.[opt.key];
          if (Array.isArray(cur)) cur[i] = v;
        },
        onSelect: (v) => {
          mutate((arr) => { arr[i] = v; });
        },
      });
    }
    return html`
      <ha-input
        id=${rowId}
        class="w-full"
        placeholder=${domain ? `${domain}.…` : ""}
        .value=${String(item != null ? item : "")}
        @input=${(e) => {
          const v = e.target.value;
          const cur = host._editingPanel?.data?.[opt.key];
          if (Array.isArray(cur)) cur[i] = v;
        }}
        @change=${(e) => {
          const v = e.target.value;
          mutate((arr) => { arr[i] = v; });
        }}
      ></ha-input>
    `;
  };

  const atMax = max != null && list.length >= max;

  return html`
    <div class="form-group" id=${id}>
      <label title=${opt.description}>${opt.label}</label>
      ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
      <div class="list-items">
        ${list.length === 0
          ? html`<div class="item-list-empty">${t("No items yet")}. ${t("Click")} "${t("+ Add")}" ${t("below")}.</div>`
          : list.map((item, i) => {
              return html`
                <div class="list-items-row">
                  <div class="list-items-input">${renderRowInput(item, i)}</div>
                  <ha-icon-button
                    title=${t("Remove")}
                    class="list-items-remove"
                    @click=${() => mutate((arr) => { arr.splice(i, 1); })}
                  >
                    <ha-icon icon="mdi:delete"></ha-icon>
                  </ha-icon-button>
                </div>
              `;
            })}
      </div>
      ${atMax
        ? html`<div class="item-list-limit">${t("Maximum")} ${max} ${t("items")}</div>`
        : html`
            <button
              class="add-item-btn"
              @click=${(e) => {
                e.preventDefault();
                const seed = choices && choices.length
                  ? (Array.isArray(choices[0]) ? choices[0][0] : choices[0].value)
                  : "";
                mutate((arr) => { arr.push(seed); });
              }}
            >${t("+ Add")}</button>
          `}
    </div>
  `;
}

/**
 * Render a rich entity list editor for `kind: item_list`.
 * Stores per-option data on host._itemListData so the UI remains
 * interactive between renders.
 */
export function renderItemListField(host, opt, currentValue) {
  // Initialize host._itemListData if needed
  if (!host._itemListData) host._itemListData = {};
  if (!host._itemListData[opt.key]) {
    // Load from currentValue (array of item config dicts, or legacy strings)
    let list = Array.isArray(currentValue) ? [...currentValue] : [];
    // Normalize legacy strings to {item: string}
    list = list.map((item) =>
      typeof item === "string" ? { item: item } : { ...item }
    );
    host._itemListData[opt.key] = list;
  }

  const id = `fld-${opt.key}`;
  const entities = host._itemListData[opt.key] || [];
  const domain = opt.domain || "";
  const isEditing =
    host._editingItem != null && host._editingItem.optKey === opt.key;
  const editingIndex = isEditing ? host._editingItem.index : null;

  return html`
    <div class="form-group" id=${id}>
      <label title=${opt.description}>${opt.label}</label>
      ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}

      <div class="item-list">
        ${entities.length === 0 && editingIndex !== -1
          ? html`<div class="item-list-empty">${t("No items yet")}. ${t("Click")} "${t("+ Add Item")}" ${t("below")}.</div>`
          : ''}
        ${entities.map((item, i) => {
          if (editingIndex === i) {
            return renderItemEditFields(host);
          }
          return renderItemListRow(
            host,
            item,
            {
              onEdit: () => {
                host._editingItem = {
                  optKey: opt.key,
                  index: i,
                  config: { ...item },
                  domain,
                };
                host._editingItemType = detectItemType(item?.item);
                host.requestUpdate();
              },
              onRemove: () => {
                host._itemListData[opt.key] = host._itemListData[opt.key].filter((_, idx) => idx !== i);
                host.requestUpdate();
              },
              onMoveUp: () => {
                const list = host._itemListData[opt.key];
                if (i <= 0) return;
                [list[i - 1], list[i]] = [list[i], list[i - 1]];
                host.requestUpdate();
              },
              onMoveDown: () => {
                const list = host._itemListData[opt.key];
                if (i >= list.length - 1) return;
                [list[i + 1], list[i]] = [list[i], list[i + 1]];
                host.requestUpdate();
              },
            },
            {
              canMoveUp: i > 0,
              canMoveDown: i < entities.length - 1,
            }
          );
        })}
      </div>

      ${editingIndex === -1
        ? renderItemEditFields(host)
        : ""}

      ${editingIndex === -1
        ? ""
        : (() => {
              const max = opt.max_items;
              if (max != null && entities.length >= max) {
                return html`<div class="item-list-limit">${t("Maximum")} ${max} ${t("items")}</div>`;
              }
              return html`
          <button
            class="add-item-btn"
            @click=${() => {
              host._editingItem = {
                optKey: opt.key,
                index: -1,
                config: {},
                domain,
              };
              host._editingItemType = "entity_id";  // default for new
              host.requestUpdate();
            }}
          >
            ${t("+ Add Item")}
          </button>
        `;
            })()}
    </div>
  `;
}


/**
 * Render inline item edit form (replaces the full-screen item-config dialog).
 * Shows type selector, value field, and collapsible advanced overrides
 * embedded directly in the item list row or single-item field.
 */
/**
 * Render a single per-item override field, mirroring renderOptionField but
 * writing to host._editingItem.config instead of host._editingPanel.data.
 * @param {object} host - LitElement host
 * @param {object} opt - PageOption-like descriptor ({key, kind, label, choices})
 * @param {*} currentValue - current value from host._editingItem.config
 */
function renderItemOptionField(host, opt, currentValue) {
  const id = `item-${opt.key}`;
  const val =
    currentValue !== undefined && currentValue !== null
      ? currentValue
      : null;

  const setVal = (v) => {
    host._editingItem = {
      ...host._editingItem,
      config: { ...host._editingItem.config, [opt.key]: v },
    };
    host.requestUpdate();
  };

  switch (opt.kind) {
    case "bool":
      return html`
        <div class="checkbox-wrap">
          <div class="checkbox-row">
            <ha-switch
              id=${id}
              ?checked=${Boolean(val)}
              @change=${(e) => setVal(e.target.checked)}
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
              setVal(parseInt(e.target.value, 10) || 0);
            }}
          ></ha-input>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "color": {
      const colorHex = parseRgbListToHex(val);
      const displayStr = formatFieldValue(val);
      const hasTpl = displayStr.includes("{{");
      return html`
        <div class="form-group color-form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <div class="color-picker-wrap">
            <ha-input id=${id} .value=${displayStr}
              @input=${(e) => {
                const raw = e.target.value;
                if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
                setVal(parseFieldValue(raw));
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
                const prevVal = host._editingItem?.config?.[opt.key];
                const newVal = hexToColorMatching(hex, prevVal);
                setVal(newVal);
              }}
            />
          </div>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          ${val != null && val !== ""
            ? html`
                <div class="color-preview-row">
                  <div class="color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
                  <span class="color-preview-label">${colorHex || t("no color")}</span>
                </div>`
            : ""}
          <div class="template-preview" ?hidden=${!hasTpl}>
            <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
          </div>
        </div>
      `;
    }

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
              setVal(e.detail.value);
            }}
          >
          </ha-select>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "str":
    default:
      // str or unknown → text field (mirrors renderOptionField default)
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <ha-input
            id=${id}
            .value=${String(val != null ? val : "")}
            class="w-full"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target);
              setVal(e.target.value);
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

export function renderItemEditFields(host, descriptor) {
  if (!host._editingItem) return "";
  // Derive descriptor from panel type if not explicitly provided.
  // Prefer _editingPanelType, with fallback to _editingPanel?.data?.type
  // for cases where _editingPanelType hasn't been set yet.
  // Check both host._panelTypes (NSPanelEditor) and host.panelTypes
  // (EditPanelDialog) since the two components use different naming
  // conventions for this property.
  if (!descriptor) {
    const panelTypes = host._panelTypes || host.panelTypes;
    if (panelTypes) {
      const pt = host._editingPanelType || host._editingPanel?.data?.type;
      if (pt) {
        descriptor = panelTypes.find(d => d.type_key === pt) || null;
      }
    }
  }
  const ee = host._editingItem;
  const isAdd = ee.index < 0;
  const raw = ee.config?.item;
  let itemType =
    host._editingItemType != null
      ? host._editingItemType
      : detectItemType(raw);
  let itemValue = parseItemValue(raw, itemType);
  const uid = `item-edit-${ee.optKey}-${ee.index}`;

  return html`
    <div class="item-edit-inline" id="${uid}">
      <div class="form-group">
        <label for="item-type" title=${t("Type of item this entity slot represents")}>${t("Type")}</label>
        <ha-select
          id="item-type"
          .value=${itemType}
          .options=${[
            { value: ITEM_TYPE.ENTITY_ID, label: t("Entity") },
            { value: ITEM_TYPE.SKIP, label: t("Skip") },
            { value: ITEM_TYPE.TEXT, label: t("Text") },
            { value: ITEM_TYPE.NAVIGATE, label: t("Navigate") },
            { value: ITEM_TYPE.ACTION, label: t("Action") },
          ]}
          @selected=${(e) => {
            const v = e.detail.value;
            host._editingItemType = v;
            host.requestUpdate();
          }}
        >
        </ha-select>
      </div>

      <div class="form-group">
        ${(() => {
          const info = ITEM_LABELS[itemType] || ITEM_LABELS.entity_id;
          if (itemType === ITEM_TYPE.SKIP) return "";
          if (itemType === ITEM_TYPE.ENTITY_ID) {
            return renderEntityPicker(host, {
              id: "item-entity",
              value: itemValue,
              label: info.label,
              placeholder: info.placeholder,
              hass: host.hass,
              onSelect: (eid) => {
                if (!host._editingItem) return;
                host._editingItem.config = host._editingItem.config || {};
                host._editingItem.config.item = eid;
              },
            });
          }
          if (itemType === ITEM_TYPE.NAVIGATE) {
            const panelKeys = (host.devicePanels || [])
              .filter(p => p.key)
              .map(p => p.key);
            return renderPanelKeyPicker(host, {
              id: "item-entity",
              value: itemValue,
              label: info.label,
              placeholder: info.placeholder,
              panelKeys,
            });
          }
          return html`
            <label for="item-entity" title=${`${info.label} — ${t("enter an entity ID, panel key, service name, or custom text")}`}>${info.label}</label>
            <ha-input
              id="item-entity"
              class="w-full"
              .value=${itemValue}
              placeholder=${info.placeholder}
              @input=${(e) => {
                if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`, e.target);
                host._editingItem = {
                  ...host._editingItem,
                  config: {
                    ...host._editingItem.config,
                    item: e.target.value,
                  },
                };
                host.requestUpdate();
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`, e.target); }}
            ></ha-input>
            ${host.hass
              ? html`
                  <div class="template-preview" ?hidden=${!(String(itemValue).includes("{{"))}>
                  <span id="tp-item-entity">${(String(itemValue).includes("{{")) ? "..." : ""}</span>
                </div>
                `
              : ""}
          `;
        })()}
      </div>

      <div
        class="item-advanced-toggle"
        @click=${(e) => {
          const toggle = e.currentTarget;
          const arrow = toggle.querySelector(".toggle-arrow");
          const section = toggle.nextElementSibling;
          if (arrow) arrow.classList.toggle("open");
          if (section) section.classList.toggle("open");
        }}
      >
        <ha-icon icon="mdi:chevron-right" class="toggle-arrow"></ha-icon>
        ${t("Advanced")}
      </div>
      <div class="item-advanced-section">
        ${ENTITY_OVERRIDE_FIELDS.map(
          (f) => {
            const fieldLabels = {
              name: t("Name"),
              icon: t("Icon"),
              color: t("Color"),
              value: t("Value"),
              state: t("State"),
              popup_key: t("Popup key"),
            };
            const hints = {
              name: t("Custom display name or Home Assistant template ({{ ... }}) that replaces the default entity name shown on the panel."),
              icon: t("An MDI icon name (e.g., mdi:lightbulb) or a Home Assistant template that overrides the default entity icon."),
              color: t("A CSS hex color (#rrggbb), RGB triplet ([r,g,b]), RGB565 integer (0\u201365535), or a Home Assistant template that overrides the default entity color."),
              value: t("A display value or Home Assistant template that overrides what is shown for this item on the panel. Supports typed values (integers, floats, JSON arrays/objects)."),
              state: t("A JSON state dictionary or Home Assistant template that overrides the entity state used for display logic. Useful for testing or conditional display."),
              popup_key: t("The key of a popup panel configuration that opens when this item is tapped. Leave empty to use the default popup behavior."),
            };
            return html`
            <div class="form-group">
              <label for="item-${f}" title=${hints[f]}>${fieldLabels[f]}</label>
              ${f === "color"
                ? (() => {
                    const cv = ee.config?.[f];
                    const cHex = parseRgbListToHex(cv);
                    const displayStr = formatFieldValue(cv);
                    const hasTpl = displayStr.includes("{{");
                    return html`
                    <div class="color-picker-wrap">
                      <ha-input
                        id="item-${f}"
                        .value=${displayStr}
                        @input=${(e) => {
                          const raw = e.target.value;
                          if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`, e.target);
                          host._editingItem = {
                            ...host._editingItem,
                            config: { ...host._editingItem.config, [f]: parseFieldValue(raw) },
                          };
                          host.requestUpdate();
                        }}
                        @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`, e.target); }}
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
                        .value=${cHex}
                        @input=${(e) => {
                          const hex = e.target.value;
                          const prevVal = host._editingItem?.config?.[f];
                          const newVal = hexToColorMatching(hex, prevVal);
                          const formGroup = e.target.closest(".form-group");
                          const tf = formGroup?.querySelector(".color-picker-wrap ha-input");
                          if (tf) tf.value = formatFieldValue(newVal);
                          host._editingItem = {
                            ...host._editingItem,
                            config: { ...host._editingItem.config, [f]: newVal },
                          };
                          host.requestUpdate();
                        }}
                      />
                    </div>
                    ${cv != null && cv !== ""
                      ? html`
                          <div class="color-preview-row">
                            <div class="color-preview-swatch" style=${`background-color:${cHex || "#888888"}`}></div>
                            <span class="color-preview-label">${cHex || t("no color")}</span>
                          </div>`
                      : ""}
                    <div class="template-preview" ?hidden=${!hasTpl}>
                      <span id="tp-item-${f}">${hasTpl ? "..." : ""}</span>
                    </div>
                  `;})()
                : f === "icon"
                ? renderIconPicker(`item-${f}`, ee.config?.[f] || "", host.hass, (newVal) => {
                    host._editingItem = {
                      ...host._editingItem,
                      config: {
                        ...host._editingItem.config,
                        [f]: newVal,
                      },
                    };
                    host.requestUpdate();
                  })
                : (() => {
                    // Override fields that should preserve typed values
                    // (lists, ints, dicts). Other fields (name, popup_key)
                    // stay as plain strings.
                    const typedFields = new Set(["value", "state"]);
                    const isTyped = typedFields.has(f);
                    const rawVal = ee.config?.[f];
                    const displayStr = isTyped
                      ? formatFieldValue(rawVal)
                      : (rawVal != null ? String(rawVal) : "");
                    return html`
                    <ha-input
                      id="item-${f}"
                      .value=${displayStr}
                      class="w-full"
                      @input=${(e) => {
                        const raw = e.target.value;
                        if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`, e.target);
                        host._editingItem = {
                          ...host._editingItem,
                          config: {
                            ...host._editingItem.config,
                            [f]: isTyped ? parseFieldValue(raw) : raw,
                          },
                        };
                        host.requestUpdate();
                      }}
                      @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`, e.target); }}
                    ></ha-input>
                    ${host.hass
                      ? html`
                          <div class="template-preview" ?hidden=${!displayStr.includes("{{")}>
                            <span id="tp-item-${f}">${displayStr.includes("{{") ? "..." : ""}</span>
                          </div>
                        `
                      : ""}
                  `;
                  })()
                }
              <div class="field-hint">${hints[f]}</div>
            </div>
          `;
          }
        )}
        ${host._editingItemType === ITEM_TYPE.ACTION
          ? html`
            <div class="form-group">
              <label for="item-service_data" title=${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts.")}>${t("Service data")}</label>
              <textarea
                id="item-service_data"
                class="w-full"
                style="min-height:80px;font-family:var(--code-font-family,monospace);font-size:13px;"
                .value=${(() => {
                  const sd = host._editingItem?.config?.service_data;
                  if (sd && typeof sd === 'object') return JSON.stringify(sd, null, 2);
                  return sd != null ? String(sd) : '';
                })()}
                @input=${(e) => {
                  const raw = e.target.value;
                  let parsed;
                  try { parsed = JSON.parse(raw); } catch { parsed = raw; }
                  host._editingItem = host._editingItem
                    ? { ...host._editingItem, config: { ...host._editingItem.config, service_data: parsed } }
                    : { config: { service_data: parsed } };
                  host.requestUpdate();
                }}
                placeholder='{"vacuum_repeat": 1, "mode": "turbo"}'
              ></textarea>
              <div class="field-hint">${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts. Example: {\"vacuum_repeat\": 2}")}</div>
            </div>`
          : ""}
        ${descriptor?.item_options?.length
          ? descriptor.item_options.map((itemKey) => {
              const opt = descriptor.options.find(o => o.key === itemKey);
              if (!opt) return "";
              return renderItemOptionField(
                host,
                { key: opt.key, kind: opt.kind, label: opt.label, description: opt.description, choices: opt.choices },
                ee.config?.[itemKey]
              );
            })
          : ""}
      </div>

      <div class="item-edit-actions">
        <ha-button variant="neutral" appearance="plain" @click=${host._cancelItemEdit}>
          ${t("Cancel")}
        </ha-button>
        <ha-button variant="brand" @click=${host._saveItemEdit}>
          ${isAdd ? t("Add") : t("Save")}
        </ha-button>
      </div>
    </div>
  `;
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
