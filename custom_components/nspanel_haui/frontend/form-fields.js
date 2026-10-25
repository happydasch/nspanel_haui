/**
 * NSPanel HAUI - form field render helpers.
 * Renders panel option and item fields for the panel and item edit dialogs.
 */

import { positionPickerDropdown, createDropdownKeyboardController, readStorage, writeStorage } from './dom-helpers.js';
import { renderListItemsField, renderItemListField, renderItemListRow, renderItemEditFields } from './item-renderers.js';
import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';
import {
  parseRgbListToHex,
  hexToColorMatching,
  COLOR_PRESETS,
} from './color-utils.js';
import { detectItemType } from './haui-item.js';


/* ── shared form field helpers ──────────────────────────────────────────── */

/**
 * Render a native <select> element replacing ha-select.
 * Options may be {value, label} objects or [value, label] pairs.
 * Fires onChange(newValue) on user selection.
 *
 * @param {string}  id        - DOM id
 * @param {string}  value     - Current selected value
 * @param {Array}   options   - Array of {value, label} or [value, label]
 * @param {function} onChange - Called with new value on change
 * @param {object}  [opts]
 * @param {string}  [opts.className] - Additional CSS class
 * @param {string}  [opts.placeholder] - Placeholder option label (no value)
 * @param {boolean} [opts.disabled] - Disabled state
 * @returns {import('lit-html').TemplateResult}
 */
export function renderSelect(id, value, options, onChange, opts = {}) {
  const cls = ["native-select", opts.className].filter(Boolean).join(" ");
  return html`
    <select
      id=${id}
      class=${cls}
      .value=${String(value != null ? value : "")}
      @change=${(e) => { onChange(e.target.value); }}
      ?disabled=${opts.disabled}
    >
      ${opts.placeholder ? html`<option value="" disabled ?selected=${value == null || value === ""}>${opts.placeholder}</option>` : ""}
      ${options.map((c) => {
        const opt = Array.isArray(c) ? { value: c[0], label: c[1] } : c;
        return html`<option value=${opt.value} ?selected=${String(value) === String(opt.value)}>${opt.label}</option>`;
      })}
    </select>
  `;
}

/**
 * Render a native toggle checkbox replacing ha-switch.
 *
 * @param {string}  id       - DOM id
 * @param {boolean} checked  - Checked state
 * @param {function} onChange - Called with new checked state
 * @param {object}  [opts]
 * @param {string}  [opts.className] - Additional CSS class
 * @param {boolean} [opts.disabled] - Disabled state
 * @returns {import('lit-html').TemplateResult}
 */
export function renderToggle(id, checked, onChange, opts = {}) {
  const cls = ["native-toggle", opts.className].filter(Boolean).join(" ");
  return html`
    <input
      id=${id}
      type="checkbox"
      class=${cls}
      ?checked=${Boolean(checked)}
      @change=${(e) => { onChange(e.target.checked); }}
      ?disabled=${opts.disabled}
    />
  `;
}

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
  if (str.includes("{{")) {
    // If the entire string is wrapped in {{...}} and the inner content is valid JSON
    // (object or array), parse the inner content as JSON instead of treating it
    // as a template. This allows users to write {{"on": "Lights"}} as well as
    // the bare {"on": "Lights"}.
    const m = str.match(/^\{\{\s*(\{.*\}|\[.*\])\s*\}\}$/s);
    if (m) {
      const inner = m[1].trim();
      try { return JSON.parse(inner); } catch {}
      try { return JSON.parse(inner.replace(/'/g, '"')); } catch {}
    }
    return s;
  }
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
      const raw = readStorage("haui_savedColors", null);
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
  writeStorage("haui_savedColors", JSON.stringify(trimmed));
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

/** Most icons listed in the dropdown at once; the full list has ~13k names. */
const ICON_MATCH_LIMIT = 100;

/** Fetch the full icon list from the backend (once). */
function _ensureIcons(hass) {
  if (_iconCache) return Promise.resolve(_iconCache);
  if (_iconFetchPromise) return _iconFetchPromise;
  _iconFetchPromise = (async () => {
    try {
      const resp = await hass.fetchWithAuth("/api/nspanel_haui/icons");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const icons = await resp.json();
      if (!Array.isArray(icons)) throw new Error("icon list is not an array");
      _iconCache = icons;
    } catch (e) {
      console.warn("Icon list unavailable, offering only common icons:", e);
      _iconCache = MDI_ICONS;
    }
    _iconFetchPromise = null;
    return _iconCache;
  })();
  return _iconFetchPromise;
}

/**
 * Icon names containing `query`, those starting with it first, at most `limit`.
 *
 * @param {string[]} icons
 * @param {string} query - lower-case name fragment without the "mdi:" prefix
 * @param {number} [limit]
 * @returns {string[]}
 */
export function matchIcons(icons, query, limit = ICON_MATCH_LIMIT) {
  const starts = [];
  const contains = [];
  for (const icon of icons) {
    if (icon.startsWith(query)) {
      starts.push(icon);
      if (starts.length >= limit) break;
    } else if (contains.length < limit && icon.includes(query)) {
      contains.push(icon);
    }
  }
  return [...starts, ...contains].slice(0, limit);
}

/**
 * Replace the dropdown's items with the icons matching `value`.
 *
 * Items are built here rather than in the Lit template: the full list is too
 * large to render and filter, and the dropdown has no Lit parts inside, so
 * replacing its children does not interfere with Lit's re-render.
 */
export function fillIconDropdown(wrap, value, hass, onInput) {
  const dropdown = wrap?.querySelector(".icon-dropdown");
  if (!dropdown) return;
  const query = iconNameOnly(value).toLowerCase();
  const icons = query ? matchIcons(_iconCache || MDI_ICONS, query) : MDI_ICONS;
  dropdown.replaceChildren(...icons.map((icon) => {
    const item = document.createElement("div");
    item.className = "icon-dropdown-item";
    item.setAttribute("data-icon", icon);
    const preview = document.createElement("ha-icon");
    preview.setAttribute("icon", `mdi:${icon}`);
    const label = document.createElement("span");
    label.textContent = icon;
    item.append(preview, label);
    item.addEventListener("mousedown", (ev) => _selectIcon(ev, wrap, hass, onInput));
    return item;
  }));
  wrap._activeIndex = -1;
  dropdown.hidden = icons.length === 0;
}

/** Show the icons matching `value`, attach a click-outside listener, and
 *  reposition to avoid clipping by dialog scroll containers. */
function _openIconDropdown(wrap, value, hass, onInput) {
  fillIconDropdown(wrap, value, hass, onInput);
  const dropdown = wrap?.querySelector(".icon-dropdown");
  if (!dropdown || dropdown.hidden) return;

  const input = wrap.querySelector(".icon-picker-input");
  if (input) positionPickerDropdown(dropdown, input);

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
 * Render a template once through HA's `render_template` websocket command.
 *
 * The command is a subscription: its result message is empty and the rendered
 * text arrives as an event, so it cannot be read through `callWS`. The
 * subscription is closed after the first result or error.
 *
 * @param {object} hass
 * @param {string} template
 * @returns {Promise<string>} rendered text; rejects on a template error
 */
function renderTemplateOnce(hass, template) {
  return new Promise((resolve, reject) => {
    let done = false;
    let unsubscribe = null;
    const finish = (settle, value) => {
      if (done) return;
      done = true;
      if (unsubscribe) unsubscribe();
      settle(value);
    };
    hass.connection.subscribeMessage(
      (msg) => {
        if ("result" in msg) finish(resolve, msg.result);
        // Warnings (e.g. deprecations) precede the real result; only errors end it.
        else if (msg.level === "ERROR") finish(reject, new Error(msg.error));
      },
      { type: "render_template", template, report_errors: true },
      { resubscribe: false },
    ).then((unsub) => {
      unsubscribe = unsub;
      if (done) unsub();
    }, (err) => finish(reject, err));
  });
}

/**
 * Schedule a template render via the HA template API.
 * Debounces rapid input by 500ms and caches results.
 *
 * @param {object}   hass        - HA hass object (for its websocket connection)
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
      const result = await renderTemplateOnce(hass, str);
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

  const hasTpl = String(currentVal).includes("{{");

  return html`
    <div class="icon-picker-wrap">
      <div class="field-row">
      <div class="input-preview-wrap">
        <ha-icon class="icon-preview input-preview" style="pointer-events:none;"
          icon=${currentVal && !currentVal.startsWith("{") && !currentVal.startsWith("[") ? currentVal : "mdi:puzzle"}
          title=${currentVal || t("no icon selected")}
        ></ha-icon>
        <input
          id=${id}
          class="native-input icon-picker-input"
          .value=${currentVal}
        placeholder=${t("mdi:home")}
        @input=${(e) => {
          const tf = e.target;
          const val = tf.value || "";
          const wrap = tf.closest(".icon-picker-wrap");
          const preview = wrap?.querySelector(".icon-preview");
          if (preview) preview.icon = val || "mdi:puzzle";
          _openIconDropdown(wrap, val, hass, onInput);
          if (hass) scheduleTemplateRender(hass, val, `tp-${id}`, tf);
          if (onInput) onInput(val);
        }}
        @focus=${async (e) => {
          const wrap = e.target.closest(".icon-picker-wrap");
          if (hass) await _ensureIcons(hass);
          _openIconDropdown(wrap, e.target.value, hass, onInput);
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
      />
      </div>
      <div class="icon-dropdown" hidden></div>
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
 * Render a native number input.
 *
 * @param {string} id
 * @param {*} value - current value; null/undefined renders empty
 * @param {function(string)} onInput - called with the raw input text
 * @param {{step?: string, min?: number, max?: number}} [opts]
 */
export function renderNumberInput(id, value, onInput, { step, min, max } = {}) {
  return html`
    <input
      id=${id}
      type="number"
      inputmode="numeric"
      step=${step ?? nothing}
      min=${min ?? nothing}
      max=${max ?? nothing}
      class="native-input"
      .value=${String(value ?? "")}
      @input=${(e) => onInput(e.target.value)}
    />
  `;
}


/** Write one option value into the edit dialog's panel state. */
function setPanelOption(host, key, value) {
  host._editingPanel = {
    ...host._editingPanel,
    data: { ...host._editingPanel.data, [key]: value },
  };
  host.requestUpdate();
}

/** Label, control and hint in the standard form group. */
function optionGroup(id, opt, control, extra = "") {
  const desc = opt.description || "";
  return html`
    <div class="form-group">
      <label for=${id} title=${desc}>${opt.label || ""}</label>
      ${control}
      ${desc ? html`<div class="field-hint">${desc}</div>` : ""}
      ${extra}
    </div>
  `;
}

/** Re-render a template preview when a field holding a template gets focus. */
function templateFocusHandler(host, id) {
  return (e) => {
    if (host.hass && String(e.target.value || "").includes("{{")) {
      scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target);
    }
  };
}

function templatePreview(host, id, val) {
  if (!host.hass) return "";
  const hasTpl = String(val).includes("{{");
  return html`
    <div class="template-preview" ?hidden=${!hasTpl}>
      <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
    </div>
  `;
}

/** Text input; `parse` turns the raw text into the stored value. */
function renderTextOption(host, opt, id, val, displayStr, parse) {
  const input = html`
    <input
      id=${id}
      class="native-input"
      .value=${displayStr}
      @input=${(e) => {
        const raw = e.target.value;
        if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
        setPanelOption(host, opt.key, parse(raw));
      }}
      @focus=${templateFocusHandler(host, id)}
    />
  `;
  return optionGroup(id, opt, input, templatePreview(host, id, val));
}

function renderBoolOption(host, opt, id, val) {
  const desc = opt.description || "";
  return html`
    <div class="checkbox-wrap">
      <div class="checkbox-row">
        ${renderToggle(id, val, (checked) => setPanelOption(host, opt.key, checked))}
        <label for=${id} title=${desc}>${opt.label || ""}</label>
      </div>
      ${desc ? html`<div class="field-hint">${desc}</div>` : ""}
    </div>
  `;
}

/**
 * Text shown in a colour field: #rrggbb for a plain colour (RGB list, RGB565
 * or hex), the raw text for a template or a state map.
 */
export function colorFieldText(val) {
  const raw = formatFieldValue(val);
  return parseRgbListToHex(val) || raw;
}

function renderColorOption(host, opt, id, val) {
  const desc = opt.description || "";
  const colorHex = parseRgbListToHex(val);
  const hasTpl = formatFieldValue(val).includes("{{");
  const pickHex = (hex) => {
    const newVal = hexToColorMatching(hex, host._editingPanel?.data?.[opt.key]);
    saveColor(hex);
    setPanelOption(host, opt.key, newVal);
    return newVal;
  };
  return html`
    <div class="form-group color-form-group">
      <label for=${id} title=${desc}>${opt.label || ""}</label>
      <div class="color-picker-wrap">
        <input id=${id} class="native-input" .value=${colorFieldText(val)}
          @input=${(e) => {
            const raw = e.target.value;
            if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
            setPanelOption(host, opt.key, parseFieldValue(raw));
          }}
          @focus=${templateFocusHandler(host, id)}
        />
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
            const group = e.target.closest(".color-form-group");
            const tf = group?.querySelector(".color-picker-wrap .native-input");
            const newVal = pickHex(e.target.value);
            if (tf) tf.value = colorFieldText(newVal);
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
      ${!hasTpl ? renderColorPresets(colorHex, pickHex) : ""}
      ${desc ? html`<div class="field-hint">${desc}</div>` : ""}
      <div class="template-preview" ?hidden=${!hasTpl}>
        <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
      </div>
    </div>
  `;
}

/** Single-item field; uses the same inline editor as item_list. */
function renderItemOption(host, opt, val) {
  const desc = opt.description || "";
  // Stored as a one-element array in _itemListData for consistent handling.
  if (!host._itemListData) host._itemListData = {};
  if (!host._itemListData[opt.key]) {
    // Normalize: if val is a dict (new format), use it; if string (legacy/encoded), wrap it.
    const itemConfig = val && typeof val === "object" ? { ...val } : { item: val || null };
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
  const isEditing =
    host._editingItem != null &&
    host._editingItem.optKey === opt.key &&
    host._editingItem.index === 0;

  return html`
    <div class="form-group" id="fld-${opt.key}">
      <label title=${desc}>${opt.label || ""}</label>
      ${desc ? html`<div class="field-hint">${desc}</div>` : ""}

      ${isEditing
        ? renderItemEditFields(host)
        : renderItemListRow(host, item, {
            onEdit: () => {
              host._editingItem = {
                optKey: opt.key,
                index: 0,
                config: { ...item },
                domain: opt.domain || "",
              };
              host._editingItemType = detectItemType(item?.item);
              host.requestUpdate();
            },
          })}
    </div>
  `;
}

/** Select value standing for "a template instead of a fixed choice". */
const TEMPLATE_CHOICE = "__template__";

/**
 * A select that also accepts a Home Assistant template (``allow_template``).
 * A value that is none of the choices is a template; choosing "Template…"
 * shows a text field for it.
 */
function renderSelectWithTemplate(host, opt, id, val, set) {
  const choices = (opt.choices || []).map((c) => (Array.isArray(c) ? { value: c[0], label: c[1] } : c));
  const isTemplate = !choices.some((c) => String(c.value) === String(val ?? ""));
  const tplId = `${id}-template`;
  const control = html`
    ${renderSelect(
      id,
      isTemplate ? TEMPLATE_CHOICE : val,
      [...choices, { value: TEMPLATE_CHOICE, label: t("Template…") }],
      (v) => set(v === TEMPLATE_CHOICE ? "" : v),
    )}
    ${isTemplate
      ? html`
          <input
            id=${tplId}
            class="native-input template-input"
            .value=${String(val ?? "")}
            placeholder="{{ 'dark' if is_state('sun.sun', 'below_horizon') else 'modern' }}"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${tplId}`, e.target);
              set(e.target.value);
            }}
            @focus=${templateFocusHandler(host, tplId)}
          />`
      : ""}
  `;
  return optionGroup(id, opt, control, isTemplate ? templatePreview(host, tplId, val) : "");
}

/** Render a form control for a single PageOption. */
export function renderOptionField(host, opt, currentValue, descriptor) {
  const id = `fld-${opt.key}`;
  const val =
    currentValue !== undefined && currentValue !== null
      ? currentValue
      : opt.default;
  const set = (v) => setPanelOption(host, opt.key, v);

  switch (opt.kind) {
    case "bool":
      return renderBoolOption(host, opt, id, val);

    case "int":
      return optionGroup(id, opt,
        renderNumberInput(id, val, (raw) => set(parseInt(raw, 10) || 0), { step: "1" }));

    case "float":
      return optionGroup(id, opt,
        renderNumberInput(id, val, (raw) => set(parseFloat(raw) || 0.0), { step: "any" }));

    case "color":
      return renderColorOption(host, opt, id, val);

    case "item":
      return renderItemOption(host, opt, val);

    case "select":
      if (opt.allow_template) return renderSelectWithTemplate(host, opt, id, val, set);
      return optionGroup(id, opt, renderSelect(id, val, opt.choices || [], set));

    case "list_items":
      return renderListItemsField(host, opt, val, id);

    case "list_entities":
      return renderListItemsField(host, opt, val, id, { entityPicker: true });

    case "list_str":
      // val may be an array of {item: "light.x"} dicts or plain strings.
      // Normalize to a newline-separated list of HA entity IDs for the textarea.
      return optionGroup(id, opt, html`
        <textarea
          id=${id}
          class="w-full"
          .value=${Array.isArray(val)
            ? val.map((v) => (typeof v === "string" ? v : v?.item || "")).join("\n")
            : String(val != null ? val : "")}
          @input=${(e) => set(e.target.value)}
        ></textarea>
      `);

    case "item_list":
      return renderItemListField(host, opt, currentValue);

    case "icon":
      return optionGroup(id, opt, renderIconPicker(id, val, host.hass, set));

    case "generic":
      return renderTextOption(host, opt, id, val, formatFieldValue(val), parseFieldValue);

    default:
      // str or unknown → text field
      return renderTextOption(host, opt, id, val, String(val != null ? val : ""), (raw) => raw);
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
