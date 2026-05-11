/**
 * NSPanel HAUI - Editor - form field render helpers.
 * Extracted from panel-editor.js _renderOptionField and _renderTypeFields methods.
 */

import { html } from './lit-import.js';
import { ENTITY_OVERRIDE_FIELDS, renderEntityPicker } from './haui-entity.js';
import {
  hasOverrides,
  detectItemType,
  parseItemValue,
  ITEM_TYPE,
  ITEM_LABELS,
  ITEM_TYPE_ICONS,
  ITEM_TYPE_SHORT,
  itemPrimaryText,
  itemSecondaryText,
} from './haui-item.js';


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

/**
 * Parse a color string to hex #rrggbb, or return "" if unparseable or empty.
 * Accepts "[r, g, b]" list format and "#rrggbb" / "rrggbb" hex format.
 */
function parseRgbListToHex(val) {
  if (!val) return "";
  const s = String(val).trim();
  // Template string — skip (no preview available)
  if (s.includes("{{")) return "";
  // RGB565 integer (e.g., "12345") — convert to hex for preview
  if (/^\d{1,5}$/.test(s)) {
    const num = parseInt(s, 10);
    const r5 = (num >> 11) & 0x1F;
    const g6 = (num >> 5) & 0x3F;
    const b5 = num & 0x1F;
    const r = Math.round((r5 * 255) / 31);
    const g = Math.round((g6 * 255) / 63);
    const b = Math.round((b5 * 255) / 31);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
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


/**
 * Generate a palette of N colors from a seed + palette type.
 * JS port of haui/utils/color.py:generate_color_palette().
 * @param {number} seed - Integer seed for the PRNG
 * @param {string} paletteType - "vibrant" | "pastel" | "light" | "lighten" | "dark" | "darken" | ""
 * @param {number} numColors - Number of colors to generate
 * @returns {Array<[number, number, number]>} Array of [r, g, b] tuples (0-255)
 */
function generatePalette(seed, paletteType, numColors) {
  if (!paletteType || paletteType === "") paletteType = "vibrant";
  // Simple seeded PRNG (mulberry32)
  let s = seed | 0;
  function next() { s = (s + 0x6d2b79f5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }

  const bgV = 0.094;
  const colors = [];
  for (let i = 0; i < numColors; i++) {
    let hue, sat, val;
    if (paletteType === "vibrant") {
      hue = next(); sat = 0.7 + next() * 0.3; val = 0.7 + next() * 0.3;
    } else if (paletteType === "pastel") {
      hue = next(); sat = 0.2 + next() * 0.3; val = 0.7 + next() * 0.3;
    } else if (paletteType === "light") {
      hue = 0; sat = 0; val = 0.7 + next() * 0.1;
    } else if (paletteType === "lighten") {
      hue = 0; sat = 0; val = 0.8;
    } else if (paletteType === "dark") {
      hue = 0; sat = 0; val = 0.2 + next() * 0.1;
    } else if (paletteType === "darken") {
      hue = 0; sat = 0; val = 0.2;
    } else {
      hue = next(); sat = 0.7 + next() * 0.3; val = 0.7 + next() * 0.3;
    }
    // HSV → RGB
    const h = hue * 6;
    const hi = Math.floor(h);
    const f = h - hi;
    const p = val * (1 - sat);
    const q = val * (1 - sat * f);
    const t2 = val * (1 - sat * (1 - f));
    let r, g, b;
    switch (hi % 6) {
      case 0: r=val; g=t2; b=p; break;
      case 1: r=q; g=val; b=p; break;
      case 2: r=p; g=val; b=t2; break;
      case 3: r=p; g=q; b=val; break;
      case 4: r=t2; g=p; b=val; break;
      case 5: r=val; g=p; b=q; break;
    }
    colors.push([
      Math.round(r * 255),
      Math.round(g * 255),
      Math.round(b * 255),
    ]);
  }
  return colors;
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
      const resp = await hass.callApi("GET", url.replace("/api/", ""));
      // hass.callApi strips "/api/" prefix automatically
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
 * Schedule a template render via the HA template API.
 * Debounces rapid input by 500ms and caches results.
 *
 * @param {object}   hass      - HA hass object (for callApi)
 * @param {string}   value     - Raw field value (may contain {{ ... }} templates)
 * @param {string}   previewId - DOM id of the <span> to update
 */
function scheduleTemplateRender(hass, value, previewId) {
  if (!hass) return;

  const el = document.getElementById(previewId);
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
      const result = await hass.callApi("POST", "template", { template: str });
      _templateCache[str] = result;
      const el2 = document.getElementById(previewId);
      if (el2) {
        el2.textContent = result;
        el2.style.color = "";
      }
    } catch (e) {
      const el2 = document.getElementById(previewId);
      if (el2) {
        el2.textContent = "(template error)";
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
        placeholder="mdi:home"
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
          if (hass) scheduleTemplateRender(hass, val, `tp-${id}`);
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
          if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`);
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
        <span class="icon-preview-label">${currentVal || "no icon selected"}</span>
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
  if (hass) scheduleTemplateRender(hass, val, `tp-${tf?.id || ""}`);
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
          style="display:block; width:100%;"
          @input=${(e) => { if (hass) scheduleTemplateRender(hass, e.target.value, `tp-${id}`); }}
          @focus=${(e) => { if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`); }}
        ></ha-input>
      `
    : html`
        <ha-input
          id=${id}
          .value=${val}
          @input=${(e) => { if (hass) scheduleTemplateRender(hass, e.target.value, `tp-${id}`); }}
          @focus=${(e) => { if (hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(hass, e.target.value, `tp-${id}`); }}
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
        <div class="checkbox-row">
          <input
            type="checkbox"
            id=${id}
            .checked=${Boolean(val)}
            @change=${(e) => {
              host._editingPanel = {
                ...host._editingPanel,
                data: { ...host._editingPanel.data, [opt.key]: e.target.checked },
              };
              host.requestUpdate();
            }}
          />
          <label for=${id}>${opt.label || opt.key}</label>
        </div>
      `;

    case "int":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "color_seed":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <div class="field-row">
            <ha-input
              id=${id}
              type="number"
              .inputMode="numeric"
              step="1"
              class="field-row-grow"
              .value=${String(val != null ? val : "0")}
              @input=${(e) => {
                const raw = e.target.value;
                const num = parseInt(raw, 10);
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: isNaN(num) ? 0 : num },
                };
                host.requestUpdate();
              }}
            ></ha-input>
            <ha-icon-button
              @click=${() => {
                const tf = host.renderRoot?.querySelector("#" + id);
                if (tf) {
                  const newSeed = Math.floor(Math.random() * 100000);
                  tf.value = String(newSeed);
                  host._editingPanel = {
                    ...host._editingPanel,
                    data: { ...host._editingPanel.data, [opt.key]: newSeed },
                  };
                  host.requestUpdate();
                }
              }}
              title="Randomize seed"
            >
              <ha-icon icon="mdi:dice-3"></ha-icon>
            </ha-icon-button>
          </div>
          ${(() => {
            const mode = host._editingPanel?.data?.color_mode || "";
            if (!mode) return "";
            const seedVal = parseInt(String(val != null ? val : "0"), 10) || 0;
            const colors = generatePalette(seedVal, mode, 6);
            return html`
              <div class="palette-preview-row">
                ${colors.map(c => html`
                  <div class="palette-swatch"
                    style=${`background:rgb(${c[0]},${c[1]},${c[2]})`}
                    title="rgb(${c[0]}, ${c[1]}, ${c[2]})">
                  </div>
                `)}
              </div>
              <span class="palette-caption">
                Preview: ${mode || "vibrant"} palette · seed ${seedVal}
              </span>
            `;
          })()}
        </div>
      `;

    case "float":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "color": {
      const colorHex = parseRgbListToHex(val);
      const hasTpl = String(val).includes("{{");
      return html`
        <div class="form-group color-form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <div class="color-picker-wrap">
            <ha-input id=${id} .value=${String(val != null ? val : "")}
              @input=${(e) => {
                const raw = e.target.value;
                if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`);
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: raw },
                };
                host.requestUpdate();
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`); }}
            ></ha-input>
            <ha-icon-button
              class="color-picker-btn"
              @click=${(e) => {
                const wrap = e.target.closest(".color-picker-wrap");
                const input = wrap?.querySelector("input[type=color]");
                if (input) input.click();
              }}
              title="Pick color"
            >
              <ha-icon icon="mdi:palette"></ha-icon>
            </ha-icon-button>
            <input
              type="color"
              class="color-input-hidden"
              .value=${colorHex}
              @input=${(e) => {
                const hex = e.target.value;
                const rgb565 = hexToRgb565(hex);
                const group = e.target.closest(".color-form-group");
                const tf = group?.querySelector(".color-picker-wrap ha-input");
                if (tf) tf.value = String(rgb565);
                host._editingPanel = {
                  ...host._editingPanel,
                  data: { ...host._editingPanel.data, [opt.key]: rgb565 },
                };
                host.requestUpdate();
              }}
            />
          </div>
          ${val != null && val !== ""
            ? html`
                <div class="color-preview-row">
                  <div class="color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
                  <span class="color-preview-label">${colorHex || "no color"}</span>
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
          <label>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>

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
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "list_str":
      // val may be an array of {item: "light.x"} dicts or plain strings.
      // Normalize to a newline-separated list of HA entity IDs for the textarea.
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <ha-textarea
            id=${id}
            .value=${Array.isArray(val)
              ? val.map((v) => (typeof v === "string" ? v : v?.item || "")).join("\n")
              : String(val != null ? val : "")}
            @input=${(e) => {
              const v = e.target.value;
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: v,
                },
              };
              host.requestUpdate();
            }}
          ></ha-textarea>
        </div>
      `;

    case "item_list":
      return renderItemListField(host, opt, currentValue);

    case "icon":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "generic":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <ha-input
            id=${id}
            .value=${String(val != null ? val : "")}
            style="display:block; width:100%;"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`);
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: e.target.value,
                },
              };
              host.requestUpdate();
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`); }}
          ></ha-input>
          ${host.hass
            ? html`
                <div class="template-preview" ?hidden=${!(String(val).includes("{{"))}>
                  <span id="tp-${id}">${(String(val).includes("{{")) ? "..." : ""}</span>
                </div>
              `
            : ""}
        </div>
      `;

    default:
      // str or unknown → text field
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <ha-input
            id=${id}
            .value=${String(val != null ? val : "")}
            style="display:block; width:100%;"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`);
              host._editingPanel = {
                ...host._editingPanel,
                data: {
                  ...host._editingPanel.data,
                  [opt.key]: e.target.value,
                },
              };
              host.requestUpdate();
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`); }}
          ></ha-input>
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
  const typeLabel = ITEM_TYPE_SHORT[type] || 'Item';
  const primary = itemPrimaryText(item);
  const secondary = itemSecondaryText(item);
  const showTypeChip = !item?.name; // primary already is the type label when no name
  return html`
    <div class="item-list-row">
      <span class="item-row-icon"><ha-icon icon=${icon}></ha-icon></span>
      <div class="item-row-text">
        <div class="item-row-primary">
          <span class="item-row-name">${primary}</span>
          ${showTypeChip
            ? ''
            : html`<span class="item-row-chip">${typeLabel}</span>`}
          ${hasOverrides(item)
            ? html`<span class="item-list-override-badge" title="Has override fields">⚙</span>`
            : ''}
        </div>
        ${secondary
          ? html`<div class="item-row-secondary">${secondary}</div>`
          : ''}
      </div>
      <div class="item-row-actions">
        ${actions.onMoveUp
          ? html`<ha-icon-button
              title="Move up"
              ?disabled=${!flags.canMoveUp}
              @click=${actions.onMoveUp}
            ><ha-icon icon="mdi:arrow-up"></ha-icon></ha-icon-button>`
          : ''}
        ${actions.onMoveDown
          ? html`<ha-icon-button
              title="Move down"
              ?disabled=${!flags.canMoveDown}
              @click=${actions.onMoveDown}
            ><ha-icon icon="mdi:arrow-down"></ha-icon></ha-icon-button>`
          : ''}
        <ha-icon-button title="Edit" @click=${actions.onEdit}>
          <ha-icon icon="mdi:pencil"></ha-icon>
        </ha-icon-button>
        ${actions.onRemove
          ? html`<ha-icon-button title="Remove" @click=${actions.onRemove}>
              <ha-icon icon="mdi:delete"></ha-icon>
            </ha-icon-button>`
          : ''}
      </div>
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
      <label>
        ${opt.label || opt.key}
        ${opt.description
          ? html`<span class="hint">${opt.description}</span>`
          : ""}
      </label>

      <div class="item-list">
        ${entities.length === 0 && editingIndex !== -1
          ? html`<div class="item-list-empty">No items yet. Click "+ Add Item" below.</div>`
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
                return html`<div class="item-list-limit">Maximum ${max} items</div>`;
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
            + Add Item
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
        <div class="checkbox-row">
          <input
            type="checkbox"
            id=${id}
            .checked=${Boolean(val)}
            @change=${(e) => setVal(e.target.checked)}
          />
          <label for=${id}>${opt.label || opt.key}</label>
        </div>
      `;

    case "int":
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "color_seed": {
      // For palette preview, resolve color_mode: item override → panel-level
      const itemMode = host._editingItem?.config?.color_mode;
      const panelMode = host._editingPanel?.data?.color_mode || "";
      const mode = itemMode != null && itemMode !== "" ? itemMode : panelMode;
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <div class="field-row">
            <ha-input
              id=${id}
              type="number"
              .inputMode="numeric"
              step="1"
              class="field-row-grow"
              .value=${String(val != null ? val : "0")}
              @input=${(e) => {
                const raw = e.target.value;
                const num = parseInt(raw, 10);
                setVal(isNaN(num) ? 0 : num);
              }}
            ></ha-input>
            <ha-icon-button
              @click=${() => {
                const newSeed = Math.floor(Math.random() * 100000);
                setVal(newSeed);
              }}
              title="Randomize seed"
            >
              <ha-icon icon="mdi:dice-3"></ha-icon>
            </ha-icon-button>
          </div>
          ${(() => {
            if (!mode) return "";
            const seedVal = parseInt(String(val != null ? val : "0"), 10) || 0;
            const colors = generatePalette(seedVal, mode, 6);
            return html`
              <div class="palette-preview-row">
                ${colors.map(c => html`
                  <div class="palette-swatch"
                    style=${`background:rgb(${c[0]},${c[1]},${c[2]})`}
                    title="rgb(${c[0]}, ${c[1]}, ${c[2]})">
                  </div>
                `)}
              </div>
              <span class="palette-caption">
                Preview: ${mode} palette · seed ${seedVal}
              </span>
            `;
          })()}
        </div>
      `;
    }

    case "color": {
      const colorHex = parseRgbListToHex(val);
      const hasTpl = String(val || "").includes("{{");
      return html`
        <div class="form-group color-form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <div class="color-picker-wrap">
            <ha-input id=${id} .value=${String(val != null ? val : "")}
              @input=${(e) => {
                const raw = e.target.value;
                if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`);
                setVal(raw);
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`); }}
            ></ha-input>
            <ha-icon-button
              class="color-picker-btn"
              @click=${(e) => {
                const wrap = e.target.closest(".color-picker-wrap");
                const input = wrap?.querySelector("input[type=color]");
                if (input) input.click();
              }}
              title="Pick color"
            >
              <ha-icon icon="mdi:palette"></ha-icon>
            </ha-icon-button>
            <input
              type="color"
              class="color-input-hidden"
              .value=${colorHex}
              @input=${(e) => {
                const hex = e.target.value;
                const rgb565 = hexToRgb565(hex);
                setVal(rgb565);
              }}
            />
          </div>
          ${val != null && val !== ""
            ? html`
                <div class="color-preview-row">
                  <div class="color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
                  <span class="color-preview-label">${colorHex || "no color"}</span>
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
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
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
        </div>
      `;

    case "str":
    default:
      // str or unknown → text field (mirrors renderOptionField default)
      return html`
        <div class="form-group">
          <label for=${id}>
            ${opt.label || opt.key}
            ${opt.description
              ? html`<span class="hint">${opt.description}</span>`
              : ""}
          </label>
          <ha-input
            id=${id}
            .value=${String(val != null ? val : "")}
            style="display:block; width:100%;"
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`);
              setVal(e.target.value);
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`); }}
          ></ha-input>
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
  if (!descriptor && host._panelTypes) {
    const pt = host._editingPanelType || host._editingPanel?.data?.type;
    if (pt) {
      descriptor = host._panelTypes.find(d => d.type_key === pt) || null;
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
        <label for="item-type">Type</label>
        <ha-select
          id="item-type"
          .value=${itemType}
          .options=${[
            { value: ITEM_TYPE.ENTITY_ID, label: "Entity" },
            { value: ITEM_TYPE.SKIP, label: "Skip" },
            { value: ITEM_TYPE.TEXT, label: "Text" },
            { value: ITEM_TYPE.NAVIGATE, label: "Navigate" },
            { value: ITEM_TYPE.ACTION, label: "Action" },
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
              onInput: () => host.requestUpdate(),
            });
          }
          return html`
            <label for="item-entity">${info.label}</label>
            <ha-input
              id="item-entity"
              style="width:100%"
              .value=${itemValue}
              placeholder=${info.placeholder}
              @input=${(e) => {
                if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`);
                host._editingItem = {
                  ...host._editingItem,
                  config: {
                    ...host._editingItem.config,
                    item: e.target.value,
                  },
                };
                host.requestUpdate();
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`); }}
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
        Advanced
      </div>
      <div class="item-advanced-section">
        ${ENTITY_OVERRIDE_FIELDS.map(
          (f) => {
            const hints = {
              name: "Custom display name or template",
              icon: "mdi icon or template",
              color: "CSS color or template",
              value: "Display value or template",
              state: "JSON state dict or template",
              popup_key: "Custom popup target key",
            };
            return html`
            <div class="form-group">
              <label for="item-${f}">
                ${f}
                <span class="hint">${hints[f]}</span>
              </label>
              ${f === "color"
                ? (() => {
                    const cv = ee.config?.[f] || "";
                    const cHex = parseRgbListToHex(cv);
                    const hasTpl = String(cv).includes("{{");
                    return html`
                    <div class="color-picker-wrap">
                      <ha-input
                        id="item-${f}"
                        .value=${cv}
                        @input=${(e) => {
                          const raw = e.target.value;
                          if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`);
                          host._editingItem = {
                            ...host._editingItem,
                            config: { ...host._editingItem.config, [f]: raw },
                          };
                          host.requestUpdate();
                        }}
                        @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`); }}
                      ></ha-input>
                      <ha-icon-button
                        class="color-picker-btn"
                        @click=${(e) => {
                          const wrap = e.target.closest(".color-picker-wrap");
                          const input = wrap?.querySelector("input[type=color]");
                          if (input) input.click();
                        }}
                        title="Pick color"
                      >
                        <ha-icon icon="mdi:palette"></ha-icon>
                      </ha-icon-button>
                      <input
                        type="color"
                        class="color-input-hidden"
                        .value=${cHex}
                        @input=${(e) => {
                          const hex = e.target.value;
                          const rgb565 = hexToRgb565(hex);
                          const formGroup = e.target.closest(".form-group");
                          const tf = formGroup?.querySelector(".color-picker-wrap ha-input");
                          if (tf) tf.value = String(rgb565);
                          host._editingItem = {
                            ...host._editingItem,
                            config: { ...host._editingItem.config, [f]: rgb565 },
                          };
                          host.requestUpdate();
                        }}
                      />
                    </div>
                    ${cv
                      ? html`
                          <div class="color-preview-row">
                            <div class="color-preview-swatch" style=${`background-color:${cHex || "#888888"}`}></div>
                            <span class="color-preview-label">${cHex || "no color"}</span>
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
                : html`
                    <ha-input
                      id="item-${f}"
                      .value=${ee.config?.[f] || ""}
                      style="display:block; width:100%;"
                      @input=${(e) => {
                        if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`);
                        host._editingItem = {
                          ...host._editingItem,
                          config: {
                            ...host._editingItem.config,
                            [f]: e.target.value,
                          },
                        };
                        host.requestUpdate();
                      }}
                      @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`); }}
                    ></ha-input>
                    ${host.hass
                      ? html`
                          <div class="template-preview" ?hidden=${!(String(ee.config?.[f] || "").includes("{{"))}>
                  <span id="tp-item-${f}">${(String(ee.config?.[f] || "").includes("{{")) ? "..." : ""}</span>
                </div>
                        `
                      : ""}
                  `
                }
            </div>
          `;
          }
        )}
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
        <ha-button appearance="plain" @click=${host._cancelItemEdit}>
          Cancel
        </ha-button>
        <ha-button variant="brand" @click=${host._saveItemEdit}>
          ${isAdd ? "Add" : "Save"}
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
      No additional options for this panel type.
    </p>`;
  }

  const groups = getPanelOptionGroups(descriptor);
  return html`
    ${groups.map((group) =>
      group.options.map((opt) => renderOptionField(host, opt, currentData[opt.key]))
    )}
  `;
}
