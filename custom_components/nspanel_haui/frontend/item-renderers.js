/**
 * NSPanel HAUI - Item field renderers.
 *
 * Item editing helpers extracted from form-fields.js: item list row, item list
 * field, single item field, item option fields, and item edit inline form.
 * These handle the item/list editing UI that was historically part of the
 * big option-field switch statement.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS, renderEntityPicker } from './haui-entity.js';
import {
  detectItemType,
  parseItemValue,
  encodeItemValue,
  renderPanelKeyPicker,
  ITEM_TYPE,
  ITEM_LABELS,
  ITEM_TYPE_ICONS,
  ITEM_TYPE_SHORT,
  itemPrimaryText,
  itemSecondaryText,
} from './haui-item.js';
import {
  formatFieldValue,
  parseFieldValue,
  scheduleTemplateRender,
  renderIconPicker,
  renderSelect,
  renderToggle,
  saveColor,
  renderColorPresets,
} from './form-fields.js';
import { parseRgbListToHex, hexToColorMatching } from './color-utils.js';
import { formVal } from './dom-helpers.js';

/* ── color popover helpers ──────────────────────────────────────────────── */

/**
 * Toggle a color popover, closing all others first.
 * Also installs a one-shot document mousedown handler to close on outside
 * click when the popover is opened.
 * @param {Event} e - click event from the palette button
 */
function toggleColorPopover(e) {
  const btn = e.currentTarget;
  const root = btn.getRootNode();
  // Close all other open color popovers in this shadow root
  root.querySelectorAll(".color-popover.open").forEach(el => el.classList.remove("open"));
  const pop = btn.closest(".form-group").querySelector(".color-popover");
  if (!pop) return;
  const wasOpen = pop.classList.contains("open");
  pop.classList.toggle("open");
  // When opening, install a one-shot outside-click handler
  if (!wasOpen) {
    const close = (ev) => {
      if (!pop.contains(ev.target) && !btn.contains(ev.target)) {
        pop.classList.remove("open");
        document.removeEventListener("mousedown", close);
      }
    };
    // Use setTimeout to avoid the current click event triggering the handler
    setTimeout(() => document.addEventListener("mousedown", close), 0);
  }
}

/* ── item list row (shared by all item list UIs) ─────────────────────── */

/**
 * Render a single item list row with type icon, primary/secondary text,
 * override badge, and action buttons.
 *
 * @param {object} host - Lit host element
 * @param {object} item - the item config
 * @param {object} actions - { onEdit, onRemove?, onMoveUp?, onMoveDown? }
 * @param {object} flags - { canMoveUp, canMoveDown }
 */
export function renderItemListRow(host, item, actions, flags = {}) {
  const type = detectItemType(item?.item);
  const icon = (item && item.icon) || ITEM_TYPE_ICONS[type] || 'mdi:circle-outline';
  const typeLabel = ITEM_TYPE_SHORT[type] || t('Item');
  const primary = itemPrimaryText(item);
  const secondary = itemSecondaryText(item);
  const showTypeChip = !item?.name;
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
              <ha-icon icon="mdi:pencil-outline"></ha-icon>
            </ha-icon-button>`
          : ''}
        ${actions.onRemove
          ? html`<ha-icon-button title=${t("Remove")} @click=${actions.onRemove}>
              <ha-icon icon="mdi:delete-outline"></ha-icon>
            </ha-icon-button>`
          : ''}
      </div>
    </div>
  `;
}

/* ── list-items / list-entities field ───────────────────────────────── */

/**
 * Render a list-of-strings editor for `kind: list_items` and `kind: list_entities`.
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

  return html`
    <div class="form-group" id=${id}>
      <label title=${opt.description}>${opt.label}</label>
      ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}

      <div class="item-list">
        ${list.map((val, i) => {
          const rem = html`
            <ha-icon-button
              class="list-remove-btn"
              title=${t("Remove")}
              @click=${() => mutate((arr) => { arr.splice(i, 1); })}
            ><ha-icon icon="mdi:close-circle"></ha-icon></ha-icon-button>
          `;
          if (choices) {
            return html`
              <div class="list-item-row">
                ${renderSelect(`${id}-${i}`, val, choices, (v) => {
                  mutate((arr) => { arr[i] = v; });
                })}
                ${rem}
              </div>
            `;
          }
          if (options.entityPicker && host.hass) {
            const eid = typeof val === "string" ? val : val?.item || "";
            return html`
              <div class="list-item-row">
                ${rem}
              </div>
              ${(() => {
                const { renderEntityPicker: picker } = { renderEntityPicker };
                return picker(host, {
                  id: `${id}-${i}`,
                  value: eid,
                  domain,
                  hass: host.hass,
                  onSelect: (entityId) => {
                    mutate((arr) => { arr[i] = entityId; });
                  },
                });
              })()}
            `;
          }
          return html`
            <div class="list-item-row">
              ${rem}
              <input
                class="native-input"
                .value=${String(val != null ? val : "")}
                @input=${(e) => {
                  mutate((arr) => { arr[i] = e.target.value; });
                }}
              />
            </div>
          `;
        })}
      </div>

      ${max != null && list.length >= max
        ? html`<div class="item-list-limit">${t("Maximum")} ${max} ${t("items")}</div>`
        : html`
            <button
              class="add-item-btn"
              @click=${() => {
                const seed = choices
                  ? (Array.isArray(choices[0]) ? choices[0][0] : choices[0].value)
                  : "";
                mutate((arr) => { arr.push(seed); });
              }}
            >${t("+ Add")}</button>
          `}
    </div>
  `;
}

/* ── rich item-list field ───────────────────────────────────────────── */

/**
 * Render a rich entity list editor for `kind: item_list`.
 */
export function renderItemListField(host, opt, currentValue) {
  if (!host._itemListData) host._itemListData = {};
  if (!host._itemListData[opt.key]) {
    let list = Array.isArray(currentValue) ? [...currentValue] : [];
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
                  host._editingItemType = "entity_id";
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

/* ── per-item option field (mirrors renderOptionField for item configs) ─ */

/**
 * Render a single per-item override field, mirroring renderOptionField but
 * writing to host._editingItem.config instead of host._editingPanel.data.
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
            ${renderToggle(id, val, setVal)}
            <label for=${id} title=${opt.description}>${opt.label}</label>
          </div>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "int":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <input
            id=${id}
            type="number"
            inputmode="numeric"
            step="1"
            class="native-input"
            .value=${String(val != null ? val : "")}
            @input=${(e) => { setVal(parseInt(e.target.value, 10) || 0); }}
          />
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "color": {
      const colorHex = parseRgbListToHex(val);
      const displayStr = formatFieldValue(val);
      const hasTpl = displayStr.includes("{{");
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <div class="field-row">
            <div class="input-preview-wrap">
              <div class="cp-sw input-preview" style="pointer-events:auto;background-color:${colorHex || "#888"};border-radius:4px;border:1px solid rgba(0,0,0,0.18);"
                title=${colorHex || t("no color")}
                @click=${(e) => {
                  const inp = e.currentTarget.querySelector("input[type=color]");
                  if (inp) inp.click();
                }}
              >
                <input type="color" .value=${colorHex || "#000000"}
                  @input=${(e) => {
                    const hex = e.target.value;
                    const prevVal = host._editingItem?.config?.[opt.key];
                    const newVal = hexToColorMatching(hex, prevVal);
                    saveColor(hex);
                    setVal(newVal);
                  }}
                />
              </div>
              <input
                id=${id}
                class="native-input"
                .value=${displayStr}
              @input=${(e) => {
                const raw = e.target.value;
                if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-${id}`, e.target);
                setVal(parseFieldValue(raw));
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target); }}
            />
            </div>
            <ha-icon-button class="color-picker-btn"
              @click=${toggleColorPopover}
              title=${t("Presets")}
            >
              <ha-icon icon="mdi:palette-swatch-outline"></ha-icon>
            </ha-icon-button>
          </div>
          <div class="color-popover" @click=${(e) => e.stopPropagation()}>
            ${!hasTpl ? renderColorPresets(colorHex, (hex) => {
              const prevVal = host._editingItem?.config?.[opt.key];
              const newVal = hexToColorMatching(hex, prevVal);
              saveColor(hex);
              setVal(newVal);
              const el = e.currentTarget.closest(".color-popover");
              if (el) el.classList.remove("open");
            }) : ""}
          </div>
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
          <div class="template-preview" ?hidden=${!hasTpl}>
            <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
          </div>
        </div>`;
    }

    case "select":
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          ${renderSelect(id, val, opt.choices || [], setVal)}
          ${opt.description ? html`<div class="field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "str":
    default:
      return html`
        <div class="form-group">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <input
            id=${id}
            class="native-input"
            .value=${String(val != null ? val : "")}
            @input=${(e) => {
              if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target);
              setVal(e.target.value);
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-${id}`, e.target); }}
          />
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

/* ── promoted field helper (name, icon, color) ──────────────────── */

/**
 * Render a single promoted field (name, icon, or color) for the inline
 * item editor. These sit above the Advanced fold so users see them immediately.
 */
function renderPromotedField(host, ee, f, label, hint) {
  if (f === 'color') {
    const cv = ee.config?.[f];
    const cHex = parseRgbListToHex(cv);
    const displayStr = formatFieldValue(cv);
    const hasTpl = displayStr.includes("{{");
    return html`
      <div class="form-group">
        <label for="item-${f}" title=${hint}>${label}</label>
        <div class="field-row">
          <div class="input-preview-wrap">
            <div class="cp-sw input-preview" style="pointer-events:auto;background-color:${cHex || "#888"};border-radius:4px;border:1px solid rgba(0,0,0,0.18);"
              title=${cHex || t("no color")}
              @click=${(e) => {
                const inp = e.currentTarget.querySelector("input[type=color]");
                if (inp) inp.click();
              }}
            >
              <input type="color" .value=${cHex || "#000000"}
                @input=${(e) => {
                  const hex = e.target.value;
                  const prevVal = host._editingItem?.config?.[f];
                  const newVal = hexToColorMatching(hex, prevVal);
                  saveColor(hex);
                  host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: newVal } };
                  setTimeout(() => host.requestUpdate(), 0);
                }}
              />
            </div>
            <input
              id="item-${f}"
              class="native-input"
              .value=${displayStr}
            @input=${(e) => {
              const raw = e.target.value;
              if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`, e.target);
              host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: parseFieldValue(raw) } };
              setTimeout(() => host.requestUpdate(), 0);
            }}
            @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`, e.target); }}
          />
          </div>
          <ha-icon-button class="color-picker-btn"
            @click=${toggleColorPopover}
            title=${t("Presets")}
          >
            <ha-icon icon="mdi:palette-swatch-outline"></ha-icon>
          </ha-icon-button>
        </div>
        <div class="color-popover" @click=${(e) => e.stopPropagation()}>
          ${!hasTpl ? renderColorPresets(cHex, (hex) => {
            const prevVal = host._editingItem?.config?.[f];
            const newVal = hexToColorMatching(hex, prevVal);
            host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: newVal } };
            saveColor(hex);
            const el = e.currentTarget.closest(".color-popover");
            if (el) el.classList.remove("open");
            setTimeout(() => host.requestUpdate(), 0);
          }) : ""}
        </div>
        ${hasTpl ? html`<div class="template-preview"><span id="tp-item-${f}">...</span></div>` : html`<div class="template-preview" hidden><span id="tp-item-${f}"></span></div>`}
      </div>`;
  }
  if (f === 'icon') {
    const rawIcon = ee.config?.[f];
    const displayStr = formatFieldValue(rawIcon) || "";
    const showDictPreview = rawIcon != null && typeof rawIcon === "object" && !Array.isArray(rawIcon);
    const dictPreviewText = showDictPreview
      ? t("State-keyed") + ": " + Object.entries(rawIcon).map(([k, v]) => `${k} → ${v}`).join(", ")
      : "";
    return html`
      <div class="form-group">
        <label for="item-${f}" title=${hint}>${label}</label>
        ${renderIconPicker(`item-${f}`, displayStr, host.hass, (newVal) => {
          host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: parseFieldValue(newVal) } };
          setTimeout(() => host.requestUpdate(), 0);
        })}
        <div class="state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
      </div>`;
  }
  const rawVal = ee.config?.[f];
  const displayStr = formatFieldValue(rawVal);
  const showDictPreview = rawVal != null && typeof rawVal === "object" && !Array.isArray(rawVal);
  const dictPreviewText = showDictPreview
    ? t("State-keyed") + ": " + Object.entries(rawVal).map(([k, v]) => `${k} → ${v}`).join(", ")
    : "";
  const hasTpl = displayStr.includes("{{");
  return html`
    <div class="form-group">
      <label for="item-${f}" title=${hint}>${label}</label>
      <input id="item-${f}" .value=${displayStr} class="native-input"
        @input=${(e) => {
          const raw = e.target.value;
          if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`, e.target);
          host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: parseFieldValue(raw) } };
          setTimeout(() => host.requestUpdate(), 0);
        }}
        @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`, e.target); }}
      />
      ${host.hass
        ? html`<div class="template-preview" ?hidden=${!hasTpl}>
            <span id="tp-item-${f}">${hasTpl ? "..." : ""}</span>
          </div>`
        : ""}
      <div class="state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
    </div>`;
}

/* ── inline item edit form ──────────────────────────────────────────── */

export function renderItemEditFields(host, descriptor) {
  if (!host._editingItem) return "";
  if (!descriptor) {
    const panelTypes = host._panelTypes || host.panelTypes;
    if (panelTypes) {
      const pt = host._editingPanelType || host._editingPanel?.data?.type;
      descriptor = panelTypes.find((d) => d.type_key === pt) || null;
    }
  }

  const ee = host._editingItem;
  const isAdd = ee.index === -1;
  const raw = ee.config?.item;
  const itemType = host._editingItemType != null
    ? host._editingItemType
    : detectItemType(raw);
  let itemValue = parseItemValue(raw, itemType);
  const uid = `item-edit-${ee.optKey}-${ee.index}`;

  return html`
    <div class="item-edit-inline" id="${uid}">
      <div class="form-group">
        <label for="item-type" title=${t("Type of item this entity slot represents")}>${t("Type")}</label>
        ${renderSelect("item-type", itemType, [
          { value: ITEM_TYPE.ENTITY_ID, label: t("Entity") },
          { value: ITEM_TYPE.SKIP, label: t("Skip") },
          { value: ITEM_TYPE.TEXT, label: t("Text") },
          { value: ITEM_TYPE.NAVIGATE, label: t("Navigate") },
          { value: ITEM_TYPE.ACTION, label: t("Action") },
        ], (v) => {
          host._editingItemType = v;
          host.requestUpdate();
        })}
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
              domain: ee.domain,
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
            <input
              id="item-entity"
              class="native-input"
              .value=${itemValue}
              placeholder=${info.placeholder}
              @input=${(e) => {
                if (host.hass) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`, e.target);
                host._editingItem = {
                  ...host._editingItem,
                  config: { ...host._editingItem.config, item: e.target.value },
                };
                setTimeout(() => host.requestUpdate(), 0);
              }}
              @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-entity`, e.target); }}
            />
            ${host.hass
              ? html`<div class="template-preview" ?hidden=${!(String(itemValue).includes("{{"))}>
                  <span id="tp-item-entity">${(String(itemValue).includes("{{")) ? "..." : ""}</span>
                </div>`
              : ""}
          `;
        })()}
      </div>

      ${[/* ── name, icon, color — promoted above Advanced fold ── */
        { f: 'name', label: t("Name"), hint: t("Custom display name or Home Assistant template ({{ ... }}) that replaces the default entity name shown on the panel.") },
        { f: 'icon', label: t("Icon"), hint: t("An MDI icon name (e.g., mdi:lightbulb) or a Home Assistant template that overrides the default entity icon.") },
        { f: 'color', label: t("Color"), hint: t("A CSS hex color (#rrggbb), RGB triplet ([r,g,b]), RGB565 integer (0-65535), or a Home Assistant template that overrides the default entity color.") },
      ].map(fd => renderPromotedField(host, ee, fd.f, fd.label, fd.hint))}
      <div
        class="collapsible-title"
        @click=${(e) => {
          const toggle = e.currentTarget;
          const arrow = toggle.querySelector(".collapsible-icon");
          const section = toggle.nextElementSibling;
          if (arrow) arrow.classList.toggle("is-open");
          if (section) section.classList.toggle("open");
        }}
      >
        <ha-icon icon="mdi:chevron-right" class="collapsible-icon"></ha-icon>
        ${t("Advanced")}
      </div>
      <div class="item-advanced-section">
        ${ENTITY_OVERRIDE_FIELDS.filter(f => f !== 'service_data' && f !== 'name' && f !== 'icon' && f !== 'color').map(
          (f) => {
            const fieldLabels = {
              value: t("Value"),
              state: t("State"),
              popup_key: t("Popup key"),
            };
            const hints = {
              value: t("A display value or Home Assistant template that overrides what is shown for this item on the panel. Supports typed values (integers, floats, JSON arrays/objects)."),
              state: t("A JSON state dictionary or Home Assistant template that overrides the entity state used for display logic. Useful for testing or conditional display."),
              popup_key: t("The key of a popup panel configuration that opens when this item is tapped. Leave empty to use the default popup behavior."),
            };
            const typedFields = new Set(["value", "state"]);
            const isTyped = typedFields.has(f);
            const rawVal = ee.config?.[f];
            const displayStr = formatFieldValue(rawVal);
            const showDictPreview = rawVal != null && typeof rawVal === "object" && !Array.isArray(rawVal);
            const dictPreviewText = showDictPreview
              ? t("State-keyed") + ": " + Object.entries(rawVal).map(([k, v]) => `${k} → ${v}`).join(", ")
              : "";
            return html`
              <div class="form-group">
                <label for="item-${f}" title=${hints[f]}>${fieldLabels[f]}</label>
                <input
                  id="item-${f}"
                  class="native-input"
                  .value=${displayStr}
                  @input=${(e) => {
                    const raw = e.target.value;
                    if (host.hass) scheduleTemplateRender(host.hass, raw, `tp-item-${f}`, e.target);
                    host._editingItem = {
                      ...host._editingItem,
                      config: { ...host._editingItem.config, [f]: isTyped ? parseFieldValue(raw) : raw },
                    };
                    setTimeout(() => host.requestUpdate(), 0);
                  }}
                  @focus=${(e) => { if (host.hass && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.hass, e.target.value, `tp-item-${f}`, e.target); }}
                />
                ${host.hass
                  ? html`<div class="template-preview" ?hidden=${!displayStr.includes("{{")}>
                      <span id="tp-item-${f}">${displayStr.includes("{{") ? "..." : ""}</span>
                    </div>`
                  : ""}
                <div class="state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
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
                  setTimeout(() => host.requestUpdate(), 0);
                }}
                placeholder='{"vacuum_repeat": 1, "mode": "turbo"}'
              ></textarea>
              <div class="field-hint">${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts. Example: {\\\"vacuum_repeat\\\": 2}")}</div>
            </div>`
          : ""}
        ${(() => {
          if (!descriptor?.item_options?.length) return "";
          return descriptor.item_options.map((itemKey) => {
            let opt = descriptor.options.find(o => o.key === itemKey);
            if (!opt) {
              // Infer field type from key name when no PageOption entry exists
              const kind = itemKey.includes("color") ? "color"
                : itemKey.startsWith("show_") || itemKey.startsWith("is_") || itemKey.startsWith("enable_") ? "bool"
                : "str";
              const label = itemKey
                .replace(/_/g, " ")
                .replace(/\b\w/g, c => c.toUpperCase());
              opt = { key: itemKey, kind, label, description: "", choices: null };
            }
            return renderItemOptionField(
              host,
              { key: opt.key, kind: opt.kind, label: opt.label, description: opt.description, choices: opt.choices },
              ee.config?.[itemKey]
            );
          });
        })()}
      </div>

      <div class="item-edit-actions">
        <ha-button variant="neutral" appearance="plain" @click=${() => { host._editingItem = null; host._editingItemType = null; host.requestUpdate(); }}>
          ${t("Cancel")}
        </ha-button>
        <ha-button variant="brand" @click=${() => {
          if (!host._editingItem) return;
          const { optKey, index } = host._editingItem;
          const uid = `item-edit-${optKey}-${index}`;
          const inline = host.renderRoot.querySelector(`#${uid}`);
          if (!inline) return;
          const typeVal = host._editingItemType || inline.querySelector("#item-type")?.value || "entity_id";
          const inputVal = formVal(inline, "item-entity");
          const config = { item: encodeItemValue(inputVal, typeVal) };
          for (const f of ENTITY_OVERRIDE_FIELDS) {
            const fv = host._editingItem.config?.[f];
            if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
          }
          const savePt = host._editingPanelType || host._editingPanel?.data?.type;
          const panelTypes = host._panelTypes || host.panelTypes;
          const desc = (savePt && panelTypes)
            ? panelTypes.find(d => d.type_key === savePt) || null
            : null;
          if (desc?.item_options) {
            for (const f of desc.item_options) {
              const fv = host._editingItem.config?.[f];
              if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
            }
          }
          if (!host._itemListData) host._itemListData = {};
          if (!host._itemListData[optKey]) host._itemListData[optKey] = [];
          if (index >= 0) {
            const updated = [...host._itemListData[optKey]];
            updated[index] = config;
            host._itemListData[optKey] = updated;
          } else {
            host._itemListData[optKey] = [...host._itemListData[optKey], config];
          }
          host._editingItem = null;
          host._editingItemType = null;
          host.requestUpdate();
        }}>
          ${isAdd ? t("Add") : t("Save")}
        </ha-button>
      </div>
    </div>
  `;
}