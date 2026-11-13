/**
 * NSPanel HAUI - form field render helpers.
 * Renders panel option and item fields for the panel and item edit dialogs.
 */

import { renderListItemsField, renderItemListField, renderItemListRow, renderItemEditFields } from './item-renderers.js';
import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';
import {
  parseRgbListToHex,
  hexToColorMatching,
} from './color-utils.js';
import { detectItemType } from './haui-item.js';
import {
  renderSelect, renderToggle, formatFieldValue, parseFieldValue, saveColor,
  renderColorPresets, colorFieldText, matchIcons, fillIconDropdown, scheduleTemplateRender,
  renderIconPicker, renderNumberInput,
} from './form-field-controls.js';
export {
  renderSelect, renderToggle, formatFieldValue, parseFieldValue, saveColor,
  renderColorPresets, colorFieldText, matchIcons, fillIconDropdown, scheduleTemplateRender,
  renderIconPicker, renderNumberInput,
};
/**
 * Label, control, optional hint and trailing content in the shared field layout.
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

/** A shared checkbox-style toggle row with an optional description. */
export function renderToggleField({ id, checked, label, hint = "", title, onChange }) {
  return html`
    <div class="haui-checkbox-wrap">
      <div class="haui-checkbox-row">
        ${renderToggle(id, checked, onChange)}
        <label for=${id} title=${title ?? nothing}>${label}</label>
      </div>
      ${hint ? html`<div class="haui-field-hint">${hint}</div>` : nothing}
    </div>
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
function optionGroup(id, opt, control, extra = nothing) {
  const desc = opt.description || "";
  return renderField({
    id,
    label: opt.label || "",
    title: desc,
    control,
    hint: desc,
    extra,
  });
}

/** Re-render a template preview when a field holding a template gets focus. */
function templateFocusHandler(host, id) {
  return (e) => {
    if (host.hass && String(e.target.value || "").includes("{{")) {
      scheduleTemplateRender(host.api, e.target.value, `tp-${id}`, e.target);
    }
  };
}

function templatePreview(host, id, val) {
  if (!host.hass) return "";
  const hasTpl = String(val).includes("{{");
  return html`
    <div class="haui-template-preview" ?hidden=${!hasTpl}>
      <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
    </div>
  `;
}

/** Text input; `parse` turns the raw text into the stored value. */
function renderTextOption(host, opt, id, val, displayStr, parse) {
  const input = html`
    <input
      id=${id}
      class="haui-input"
      .value=${displayStr}
      @input=${(e) => {
        const raw = e.target.value;
        if (host.api) scheduleTemplateRender(host.api, raw, `tp-${id}`, e.target);
        setPanelOption(host, opt.key, parse(raw));
      }}
      @focus=${templateFocusHandler(host, id)}
    />
  `;
  return optionGroup(id, opt, input, templatePreview(host, id, val));
}

function renderBoolOption(host, opt, id, val) {
  const desc = opt.description || "";
  return renderToggleField({
    id,
    checked: val,
    label: opt.label || "",
    title: desc,
    hint: desc,
    onChange: (checked) => setPanelOption(host, opt.key, checked),
  });
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
    <div class="haui-field haui-color-form-group">
      <label for=${id} title=${desc}>${opt.label || ""}</label>
      <div class="haui-color-picker-wrap">
        <input id=${id} class="haui-input" .value=${colorFieldText(val)}
          @input=${(e) => {
            const raw = e.target.value;
            if (host.api) scheduleTemplateRender(host.api, raw, `tp-${id}`, e.target);
            setPanelOption(host, opt.key, parseFieldValue(raw));
          }}
          @focus=${templateFocusHandler(host, id)}
        />
        <ha-icon-button
          class="haui-color-picker-btn"
          @click=${(e) => {
            const wrap = e.target.closest(".haui-color-picker-wrap");
            const input = wrap?.querySelector("input[type=color]");
            if (input) input.click();
          }}
          title=${t("Pick color")}
        >
          <ha-icon icon="mdi:palette"></ha-icon>
        </ha-icon-button>
        <input
          type="color"
          class="haui-color-input-hidden"
          .value=${colorHex || "#000000"}
          @input=${(e) => {
            const group = e.target.closest(".haui-color-form-group");
            const tf = group?.querySelector(".haui-color-picker-wrap .haui-input");
            const newVal = pickHex(e.target.value);
            if (tf) tf.value = colorFieldText(newVal);
          }}
        />
      </div>
      ${!hasTpl && val != null && val !== ""
        ? html`
            <div class="haui-color-preview-row">
              <div class="haui-color-preview-swatch" style=${`background-color:${colorHex || "#888888"}`}></div>
              <span class="haui-color-preview-label">${colorHex || t("no color")}</span>
            </div>`
        : ""}
      ${!hasTpl ? renderColorPresets(colorHex, pickHex) : ""}
      ${desc ? html`<div class="haui-field-hint">${desc}</div>` : ""}
      <div class="haui-template-preview" ?hidden=${!hasTpl}>
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
    <div class="haui-field" id="fld-${opt.key}">
      <label title=${desc}>${opt.label || ""}</label>
      ${desc ? html`<div class="haui-field-hint">${desc}</div>` : ""}

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
            class="haui-input template-input"
            .value=${String(val ?? "")}
            placeholder="{{ 'dark' if is_state('sun.sun', 'below_horizon') else 'modern' }}"
            @input=${(e) => {
              if (host.api) scheduleTemplateRender(host.api, e.target.value, `tp-${tplId}`, e.target);
              set(e.target.value);
            }}
            @focus=${templateFocusHandler(host, tplId)}
          />`
      : ""}
  `;
  return optionGroup(id, opt, control, isTemplate ? templatePreview(host, tplId, val) : "");
}

/** Render a form control for a single PageOption. */
export function renderOptionField(host, opt, currentValue) {
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
      // an empty field unsets the option, so the panel uses its default again
      return optionGroup(id, opt,
        renderNumberInput(id, val, (raw) => set(raw === "" ? undefined : parseInt(raw, 10)), { step: "1" }));

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
          class="haui-w-full"
          .value=${Array.isArray(val)
            ? val.map((v) => (typeof v === "string" ? v : v?.item || "")).join("\n")
            : String(val != null ? val : "")}
          @input=${(e) => set(e.target.value)}
        ></textarea>
      `);

    case "item_list":
      return renderItemListField(host, opt, currentValue);

    case "icon":
      return optionGroup(id, opt, renderIconPicker(id, val, host.api, set));

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
