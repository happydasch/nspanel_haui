/**
 * Shared low-level form controls and value helpers.
 * Kept below the option and item renderers to avoid their import cycle.
 */
import { positionPickerDropdown, createDropdownKeyboardController, readStorage, writeStorage } from './dom-helpers.js';
import { html, noChange, nothing } from './lit-import.js';
import { t } from './localize.js';
import { COLOR_PRESETS, hexToColorMatching, parseRgbListToHex } from './color-utils.js';
import { iconButton } from './ui/button.js';

/**
 * Label, control, optional hint and trailing content in the shared field layout.
 */
/**
 * The message under a field that breaks a rule: an error (announced, blocks
 * the save) or a warning (shown, does not block).
 * @param {string} id - the field id; the message gets `<id>-error` / `<id>-warning`
 * @param {{ error?: string, warning?: string }} [feedback]
 */
export function fieldMessage(id, feedback = {}) {
  if (feedback.error) {
    return html`<span class="haui-field-error" id=${`${id}-error`} role="alert">${feedback.error}</span>`;
  }
  if (feedback.warning) {
    return html`<span class="haui-field-warning" id=${`${id}-warning`}>${feedback.warning}</span>`;
  }
  return nothing;
}

/**
 * Label, control and hint in the standard form group.
 * @param {{ id: string, label: unknown, control: unknown, hint?: unknown, title?: string,
 *   extra?: unknown, className?: string }} options
 */
export function renderField({ id, label, control, hint = "", title, extra = nothing, className = '' }) {
  return html`
    <div class=${`haui-field ${className}`.trim()}>
      <label for=${id} title=${title ?? nothing}>${label}</label>
      ${control}
      ${hint ? html`<div class="haui-field-hint">${hint}</div>` : nothing}
      ${extra}
    </div>
  `;
}

export function renderSelect(id, value, options, onChange, opts = {}) {
  const cls = ["haui-select", opts.className].filter(Boolean).join(" ");
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
 * @param {string}  [opts.label] - Accessible name, for a toggle without a visible `<label>`
 * @returns {import('lit-html').TemplateResult}
 */
export function renderToggle(id, checked, onChange, opts = {}) {
  const cls = ["haui-switch", opts.className].filter(Boolean).join(" ");
  return html`
    <input
      id=${id}
      type="checkbox"
      class=${cls}
      aria-label=${opts.label ?? nothing}
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
/**
 * Text shown in a colour field: a normalized hex value for plain colours,
 * otherwise the formatted raw value (for templates and state maps).
 */
export function colorFieldText(value) {
  return parseRgbListToHex(value) || formatFieldValue(value);
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

/** One labelled row of colour swatch buttons that call onPick(hex). */
function colorSwatchRow(label, colors, onPick, className = '') {
  return html`
    <div class=${`haui-color-presets ${className}`.trim()}>
      <span class="haui-color-preset-label">${label}</span>
      ${colors.map((hex) => html`
        <button type="button" class="haui-color-preset-swatch" style="--haui-color-preset:${hex}"
          aria-label=${hex} title=${hex} @click=${() => onPick(hex)}></button>
      `)}
    </div>
  `;
}

/** The recently picked colours (if any) and the preset colours. */
export function renderColorPresets(onPick) {
  const saved = getSavedColors();
  return html`
    ${saved.length ? colorSwatchRow(t("Recent"), saved, onPick, 'is-recent') : nothing}
    ${colorSwatchRow(t("Presets"), COLOR_PRESETS, onPick)}
  `;
}

/**
 * A colour field: a text input that takes a hex colour, an RGB list, an RGB565
 * number or a template, a swatch inside it that opens the browser's colour
 * picker, and a toggle that shows the recent and preset colours below.
 *
 * A picked colour is stored in the format the value already has
 * (`hexToColorMatching`); typed text is stored parsed (`parseFieldValue`).
 * The caller owns whether the presets are shown, so they close with its editing session.
 *
 * @param {{ id: string, value: any, api?: object|null, onChange: (value: any) => void, presetsOpen?: boolean, onTogglePresets: () => void }} options
 */
export function renderColorField({ id, value, api = null, onChange, presetsOpen = false, onTogglePresets }) {
  const colorHex = parseRgbListToHex(value);
  const hasTemplate = formatFieldValue(value).includes("{{");
  const presetsId = `${id}-presets`;
  const pick = (hex) => {
    saveColor(hex);
    onChange(hexToColorMatching(hex, value));
  };
  return html`
    <div class="haui-field-row">
      <div class="haui-input-preview-wrap">
        <span class=${`haui-color-swatch haui-color-editor-swatch haui-input-preview${colorHex ? '' : ' is-empty'}`}
          style=${colorHex ? `--haui-color-swatch:${colorHex}` : nothing} title=${colorHex || t("no color")}>
          <input type="color" aria-label=${t("Pick color")} .value=${colorHex || "#000000"}
            @input=${(event) => pick(event.target.value)} />
        </span>
        <input id=${id} class="haui-input" .value=${colorFieldText(value)}
          @input=${(event) => {
            const raw = event.target.value;
            if (api) scheduleTemplateRender(api, raw, `tp-${id}`, event.target);
            // A value the field shows differently (an RGB565 number or an RGB list, both
            // shown as hex) would rewrite the text being typed: it is stored on change.
            const parsed = parseFieldValue(raw);
            if (colorFieldText(parsed) === raw) onChange(parsed);
          }}
          @change=${(event) => onChange(parseFieldValue(event.target.value))}
          @focus=${(event) => {
            if (api && String(event.target.value || "").includes("{{")) {
              scheduleTemplateRender(api, event.target.value, `tp-${id}`, event.target);
            }
          }}
        />
      </div>
      ${iconButton({
        label: t("Presets"),
        iconName: 'color',
        expanded: presetsOpen,
        controls: presetsId,
        onClick: onTogglePresets,
      })}
    </div>
    <div class="haui-template-preview" ?hidden=${!hasTemplate}>
      <span id="tp-${id}">${hasTemplate ? "..." : ""}</span>
    </div>
    <div id=${presetsId} ?hidden=${!presetsOpen}>${renderColorPresets(pick)}</div>
  `;
}

/** Cache of MDI icon names fetched from the backend. */
let _iconCache = null;
let _iconFetchPromise = null;

/** Most icons listed in the dropdown at once; the full list has ~13k names. */
const ICON_MATCH_LIMIT = 100;

/** Fetch the full icon list from the backend (once). */
function _ensureIcons(api) {
  if (_iconCache) return Promise.resolve(_iconCache);
  if (_iconFetchPromise) return _iconFetchPromise;
  _iconFetchPromise = (async () => {
    try {
      const icons = await api.editor.icons();
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
export function fillIconDropdown(wrap, value, api, onInput) {
  const dropdown = wrap?.querySelector(".haui-icon-dropdown");
  if (!dropdown) return;
  const query = iconNameOnly(value).toLowerCase();
  const icons = query ? matchIcons(_iconCache || MDI_ICONS, query) : MDI_ICONS;
  dropdown.replaceChildren(...icons.map((icon) => {
    const item = document.createElement("div");
    item.className = "haui-icon-dropdown-item";
    item.setAttribute("data-icon", icon);
    const preview = document.createElement("ha-icon");
    preview.setAttribute("icon", `mdi:${icon}`);
    const label = document.createElement("span");
    label.textContent = icon;
    item.append(preview, label);
    item.addEventListener("mousedown", (ev) => _selectIcon(ev, wrap, api, onInput));
    return item;
  }));
  wrap._activeIndex = -1;
  dropdown.hidden = icons.length === 0;
}

/** Show the icons matching `value`, attach a click-outside listener, and
 *  reposition to avoid clipping by dialog scroll containers. */
function _openIconDropdown(wrap, value, api, onInput) {
  fillIconDropdown(wrap, value, api, onInput);
  const dropdown = wrap?.querySelector(".haui-icon-dropdown");
  if (!dropdown || dropdown.hidden) return;

  const input = wrap.querySelector(".haui-icon-picker-input");
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
  const dropdown = wrap?.querySelector(".haui-icon-dropdown");
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
 * @param {object} api
 * @param {string} template
 * @returns {Promise<string>} rendered text; rejects on a template error
 */
function renderTemplateOnce(api, template) {
  return new Promise((resolve, reject) => {
    let done = false;
    let unsubscribe = null;
    const finish = (settle, value) => {
      if (done) return;
      done = true;
      if (unsubscribe) unsubscribe();
      settle(value);
    };
    api.ha.renderTemplate(
      template,
      (msg) => {
        if ("result" in msg) finish(resolve, msg.result);
        // Warnings (e.g. deprecations) precede the real result; only errors end it.
        else if (msg.level === "ERROR") finish(reject, new Error(msg.error));
      },
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
 * @param {object}   api        - HA api object (for its websocket connection)
 * @param {string}   value       - Raw field value (may contain {{ ... }} templates)
 * @param {string}   previewId   - DOM id of the <span> to update
 * @param {Element}  [contextEl] - Any element inside the host's render root —
 *                                 used to locate the span across shadow DOM.
 */
export function scheduleTemplateRender(api, value, previewId, contextEl) {
  if (!api) return;

  const el = _findPreviewEl(previewId, contextEl);
  const wrapper = el?.closest(".haui-template-preview");
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
      const result = await renderTemplateOnce(api, str);
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
 * @param {object}  [api=null]   - HA api object (needed for API call + template rendering)
 * @param {function} [onInput=null] - Called with the new value on every input/dropdown selection
 */
export function renderIconPicker(id, value, api = null, onInput = null) {
  const currentVal = value || "";

  // Kick off background fetch (result used when focused)
  if (api) _ensureIcons(api);

  const hasTpl = String(currentVal).includes("{{");

  return html`
    <div class="haui-icon-picker-wrap">
      <div class="haui-field-row">
      <div class="haui-input-preview-wrap">
        <ha-icon class="haui-icon-preview haui-input-preview haui-icon-preview-static"
          icon=${currentVal && !currentVal.startsWith("{") && !currentVal.startsWith("[") ? currentVal : "mdi:puzzle"}
          title=${currentVal || t("no icon selected")}
        ></ha-icon>
        <input
          id=${id}
          class="haui-input haui-icon-picker-input"
          .value=${currentVal}
        placeholder=${t("mdi:home")}
        @input=${(e) => {
          const tf = e.target;
          const val = tf.value || "";
          const wrap = tf.closest(".haui-icon-picker-wrap");
          const preview = wrap?.querySelector(".haui-icon-preview");
          if (preview) preview.icon = val || "mdi:puzzle";
          _openIconDropdown(wrap, val, api, onInput);
          if (api) scheduleTemplateRender(api, val, `tp-${id}`, tf);
          if (onInput) onInput(val);
        }}
        @focus=${async (e) => {
          const wrap = e.target.closest(".haui-icon-picker-wrap");
          if (api) await _ensureIcons(api);
          _openIconDropdown(wrap, e.target.value, api, onInput);
          if (api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(api, e.target.value, `tp-${id}`, e.target);
        }}
        @blur=${(e) => {
          const wrap = e.target?.closest(".haui-icon-picker-wrap");
          setTimeout(() => { if (wrap) _hideIconDropdown(wrap); }, 80);
        }}
        @keydown=${createDropdownKeyboardController({
          getWrap: (e) => e.target.closest('.haui-icon-picker-wrap'),
          dropdownSelector: '.haui-icon-dropdown',
          itemSelector: '.haui-icon-dropdown-item',
          indexField: '_activeIndex',
          onSelect: (visibleItems, idx) => {
            _selectIconItem(visibleItems[idx].closest('.haui-icon-picker-wrap'), visibleItems[idx], api, onInput);
          },
          onDismiss: (e) => _hideIconDropdown(e.target.closest('.haui-icon-picker-wrap')),
        })}
      />
      </div>
      <div class="haui-icon-dropdown" hidden></div>
      </div>
      <div class="haui-template-preview" ?hidden=${!hasTpl}>
        <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
      </div>
    </div>
  `;
}

/** Handle icon mousedown selection (event delegation). */
function _selectIcon(e, wrap, api, onInput) {
  e.preventDefault();
  const item = e.currentTarget;
  _selectIconItem(wrap, item, api, onInput);
}

/** Apply icon selection: set value, update preview, hide dropdown. */
function _selectIconItem(wrap, item, api, onInput) {
  const tf = wrap?.querySelector(".haui-icon-picker-input");
  const preview = wrap?.querySelector(".haui-icon-preview");
  const icon = item.getAttribute("data-icon") || "";
  const val = `mdi:${icon}`;
  if (tf) tf.value = val;
  if (preview) preview.icon = val;
  if (api) scheduleTemplateRender(api, val, `tp-${tf?.id || ""}`, tf);
  if (onInput) onInput(val);
  _hideIconDropdown(wrap);
}


/**
 * Render a native number input.
 *
 * @param {string} id
 * @param {*} value - current value; null/undefined renders empty
 * @param {function(string)} onInput - called with the raw input text
 * @param {{step?: string, min?: number, max?: number, placeholder?: string}} [opts]
 */
export function renderNumberInput(id, value, onInput, { step, min, max, placeholder } = {}) {
  // The stored value is the parsed (and often clamped) number, not the text in
  // the box. Writing it back while the user types replaces an emptied or
  // unfinished entry: the box is theirs until they leave it.
  const typing = _typingInput?.id === id && _typingInput.isConnected === true;
  return html`
    <input
      id=${id}
      type="number"
      inputmode="numeric"
      step=${step ?? nothing}
      min=${min ?? nothing}
      max=${max ?? nothing}
      placeholder=${placeholder ?? nothing}
      class="haui-input"
      .value=${typing ? noChange : String(value ?? "")}
      @input=${(e) => {
        _typingInput = e.target;
        onInput(e.target.value);
      }}
      @blur=${() => { _typingInput = null; }}
    />
  `;
}

/** The number input that received the last keystroke and still has the focus. */
let _typingInput = null;
