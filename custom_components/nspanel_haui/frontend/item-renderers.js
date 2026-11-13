/**
 * NSPanel HAUI - Item field renderers.
 *
 * Item editing helpers extracted from form-fields.js: item list row, item list
 * field, single item field, item option fields, and item edit inline form.
 * These handle the item/list editing UI that was historically part of the
 * big option-field switch statement.
 */
import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { ENTITY_OVERRIDE_FIELDS, renderEntityPicker } from './haui-entity.js';
import {
  detectItemType,
  parseItemValue,
  encodeItemValue,
  panelTargetOptions,
  ITEM_TYPE,
  itemLabels,
  ITEM_TYPE_ICONS,
  itemTypeShort,
  itemPrimaryText,
  itemSecondaryText,
} from './haui-item.js';
import {
  formatFieldValue,
  parseFieldValue,
  scheduleTemplateRender,
  renderIconPicker,
  renderNumberInput,
  renderSelect,
  renderToggle,
  saveColor,
  renderColorPresets,
  colorFieldText,
} from './form-field-controls.js';
import { parseRgbListToHex, hexToColorMatching } from './color-utils.js';
import { formVal } from './dom-helpers.js';
import { dropsAfter } from './ui/panel-row.js';
import { badge } from './ui/badge.js';
import { addButton } from './ui/button.js';
import { emptyState } from './ui/empty-state.js';

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
  root.querySelectorAll(".haui-color-popover.open").forEach(el => el.classList.remove("open"));
  const pop = btn.closest(".haui-field").querySelector(".haui-color-popover");
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

/** The row being dragged: its list and index. Drag data is unreadable during dragover. */
let draggedItem = null;

/**
 * Render a single item list row with type icon, primary/secondary text,
 * override badge, and action buttons.
 *
 * @param {object} host - Lit host element
 * @param {object} item - the item config
 * @param {object} actions - { onEdit, onRemove? }
 * @param {{ list: string, index: number, onMove: (from: number, to: number) => void }|null} drag -
 *   makes the row draggable within its list; `onMove` gets the dragged row's index and its new one
 */
export function renderItemListRow(host, item, actions, drag = null) {
  const type = detectItemType(item?.item);
  const icon = (item && item.icon) || ITEM_TYPE_ICONS[type] || 'mdi:circle-outline';
  const typeLabel = itemTypeShort()[type] || t('Item');
  const secondary = itemSecondaryText(item);
  // An entity without a name of its own goes by its Home Assistant name, as on the panel.
  const entityName = !item?.name && type === ITEM_TYPE.ENTITY_ID
    ? host?.hass?.states?.[secondary]?.attributes?.friendly_name
    : '';
  const primary = entityName || itemPrimaryText(item);
  // The entity id below already tells an entity apart; other kinds name theirs.
  const showTypeChip = type !== ITEM_TYPE.ENTITY_ID && Boolean(item?.name);
  const parseItemColor = (val) =>
    val && !(typeof val === 'object' && !Array.isArray(val))
      ? parseRgbListToHex(val)
      : '';
  const itemColor = parseItemColor(item?.color);
  const itemBackColor = parseItemColor(item?.back_color);
  const iconStyle = [
    itemBackColor && `--haui-item-row-icon-background:${itemBackColor}`,
    itemColor && `--haui-item-row-icon-color:${itemColor}`,
  ].filter(Boolean).join(';');
  const clearDrop = (row) => row.classList.remove('is-drop-before', 'is-drop-after');
  // A row takes a drop only from another row of its own list.
  const takesDrop = () => draggedItem && draggedItem.list === drag.list && draggedItem.index !== drag.index;
  const startDrag = drag ? (event) => {
    draggedItem = { list: drag.list, index: drag.index };
    // Firefox starts a drag only once it carries data.
    event.dataTransfer?.setData('text/plain', String(drag.index));
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
    event.currentTarget.classList.add('is-dragging');
  } : null;
  const endDrag = drag ? (event) => {
    draggedItem = null;
    event.currentTarget.classList.remove('is-dragging');
  } : null;
  // Without preventDefault on dragover the browser never fires drop on the row.
  const allowDrop = drag ? (event) => {
    if (!takesDrop()) return;
    event.preventDefault();
    const after = dropsAfter(event);
    event.currentTarget.classList.toggle('is-drop-before', !after);
    event.currentTarget.classList.toggle('is-drop-after', after);
  } : null;
  const leaveDrop = drag ? (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) clearDrop(event.currentTarget);
  } : null;
  const acceptDrop = drag ? (event) => {
    if (!takesDrop()) return;
    event.preventDefault();
    clearDrop(event.currentTarget);
    const from = draggedItem.index;
    const slot = drag.index + (dropsAfter(event) ? 1 : 0);
    // Taking the dragged row out first moves every later slot up by one.
    const to = from < slot ? slot - 1 : slot;
    if (to !== from) drag.onMove(from, to);
  } : null;
  const gripLabel = drag ? t('Drag to reorder {name}').replace('{name}', primary) : '';
  // The whole row opens the item; the narrow sidebar keeps its width for the name.
  return html`
    <div class="haui-item-list-row" draggable=${drag ? 'true' : nothing}
      @dragstart=${startDrag ?? nothing} @dragend=${endDrag ?? nothing}
      @dragover=${allowDrop ?? nothing} @dragleave=${leaveDrop ?? nothing} @drop=${acceptDrop ?? nothing}>
      ${drag
        ? html`<span class="haui-item-row-grip" role="img" aria-label=${gripLabel} title=${gripLabel}>
            <ha-icon icon="mdi:drag" aria-hidden="true"></ha-icon>
          </span>`
        : ''}
      <button type="button" class="haui-item-row-main" title=${t("Edit")} @click=${actions.onEdit}>
        <span class="haui-item-row-icon" style=${iconStyle || nothing}>
          <ha-icon icon=${icon}></ha-icon>
        </span>
        <span class="haui-item-row-text">
          <span class="haui-item-row-primary">
            <span class="haui-item-row-name">${primary}</span>
            ${showTypeChip ? badge(typeLabel, 'neutral', 'haui-item-row-chip') : ''}
          </span>
          ${secondary
            ? html`<span class="haui-item-row-secondary">${secondary}</span>`
            : ''}
        </span>
        <ha-icon class="haui-item-row-edit" icon="mdi:pencil-outline"></ha-icon>
      </button>
      ${actions.onRemove
        ? html`<ha-icon-button class="haui-item-row-remove" label=${t("Remove")} title=${t("Remove")}
            @click=${actions.onRemove}
          ><ha-icon icon="mdi:delete-outline"></ha-icon></ha-icon-button>`
        : ''}
    </div>
  `;
}

/* ── haui-item-list-items / list-entities field ───────────────────────────────── */

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
    <div class="haui-field" id=${id}>
      <label title=${opt.description}>${opt.label}</label>
      ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}

      <div class="haui-item-list">
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
                return picker({
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
                class="haui-input"
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
        ? html`<div class="haui-item-list-limit">${t("Maximum {max} items").replace("{max}", max)}</div>`
        : addButton({
          label: t("Add"),
          onClick: () => {
            const seed = choices
              ? (Array.isArray(choices[0]) ? choices[0][0] : choices[0].value)
              : "";
            mutate((arr) => { arr.push(seed); });
          },
        })}
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
    <div class="haui-field" id=${id}>
      <label title=${opt.description}>${opt.label}</label>
      ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}

      <div class="haui-item-list">
        ${entities.length === 0 && editingIndex !== -1
          ? emptyState({ message: t('No items yet. Click "+ Add Item" below.'), iconName: null, className: 'haui-empty-state-inset' })
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
            },
            {
              list: opt.key,
              index: i,
              onMove: (from, to) => {
                const list = host._itemListData[opt.key];
                // The item open in the inline form keeps its form when rows move around it.
                const edited = isEditing ? list[editingIndex] : undefined;
                list.splice(to, 0, ...list.splice(from, 1));
                if (edited !== undefined) {
                  host._editingItem = { ...host._editingItem, index: list.indexOf(edited) };
                }
                host.requestUpdate();
              },
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
              return html`<div class="haui-item-list-limit">${t("Maximum {max} items").replace("{max}", max)}</div>`;
            }
            return addButton({
              label: t("Add Item"),
              onClick: () => {
                host._editingItem = {
                  optKey: opt.key,
                  index: -1,
                  config: {},
                  domain,
                };
                host._editingItemType = "entity_id";
                host.requestUpdate();
              },
            });
          })()}
    </div>
  `;
}

function renderItemColorEditor(host, { id, label, hint, value, getValue, setValue }) {
  const colorHex = parseRgbListToHex(value);
  const hasTemplate = formatFieldValue(value).includes("{{");
  const applyColor = (hex) => {
    const nextValue = hexToColorMatching(hex, getValue());
    saveColor(hex);
    setValue(nextValue);
  };
  const closePopover = () => host.renderRoot?.querySelectorAll(".haui-color-popover.open")
    .forEach((element) => element.classList.remove("open"));

  return html`
    <div class="haui-field">
      <label for=${id} title=${hint}>${label}</label>
      <div class="haui-field-row">
        <div class="input-preview-wrap">
          <div class="haui-color-swatch haui-color-editor-swatch input-preview"
            style=${`--haui-color-swatch:${colorHex || "#888"}`}
            title=${colorHex || t("no color")}
            @click=${(event) => event.currentTarget.querySelector("input[type=color]")?.click()}
          >
            <input type="color" .value=${colorHex || "#000000"}
              @input=${(event) => applyColor(event.target.value)}
            />
          </div>
          <input
            id=${id}
            class="haui-input"
            .value=${colorFieldText(value)}
            @input=${(event) => {
              const raw = event.target.value;
              if (host.api) scheduleTemplateRender(host.api, raw, `tp-${id}`, event.target);
              setValue(parseFieldValue(raw));
            }}
            @focus=${(event) => {
              if (host.api && String(event.target.value || "").includes("{{")) {
                scheduleTemplateRender(host.api, event.target.value, `tp-${id}`, event.target);
              }
            }}
          />
        </div>
        <ha-icon-button class="haui-color-picker-btn" @click=${toggleColorPopover} title=${t("Presets")}>
          <ha-icon icon="mdi:palette-swatch-outline"></ha-icon>
        </ha-icon-button>
      </div>
      <div class="haui-color-popover" @click=${(event) => event.stopPropagation()}>
        ${!hasTemplate ? renderColorPresets(colorHex, (hex) => {
          applyColor(hex);
          closePopover();
        }) : ""}
      </div>
      ${hint ? html`<div class="haui-field-hint">${hint}</div>` : ""}
      <div class="haui-template-preview" ?hidden=${!hasTemplate}>
        <span id=${`tp-${id}`}>${hasTemplate ? "..." : ""}</span>
      </div>
    </div>`;
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
        <div class="haui-checkbox-wrap">
          <div class="haui-checkbox-row">
            ${renderToggle(id, val, setVal)}
            <label for=${id} title=${opt.description}>${opt.label}</label>
          </div>
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "int":
      return html`
        <div class="haui-field">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          ${renderNumberInput(id, val, (raw) => setVal(parseInt(raw, 10) || 0), { step: "1" })}
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "color":
      return renderItemColorEditor(host, {
        id,
        label: opt.label,
        hint: opt.description,
        value: val,
        getValue: () => host._editingItem?.config?.[opt.key],
        setValue: setVal,
      });

    case "select":
      return html`
        <div class="haui-field">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          ${renderSelect(id, val, opt.choices || [], setVal)}
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "str":
    default:
      return html`
        <div class="haui-field">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          <input
            id=${id}
            class="haui-input"
            .value=${String(val != null ? val : "")}
            @input=${(e) => {
              if (host.api) scheduleTemplateRender(host.api, e.target.value, `tp-${id}`, e.target);
              setVal(e.target.value);
            }}
            @focus=${(e) => { if (host.api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.api, e.target.value, `tp-${id}`, e.target); }}
          />
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
          ${host.hass
            ? html`
                <div class="haui-template-preview" ?hidden=${!(String(val).includes("{{"))}>
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
    return renderItemColorEditor(host, {
      id: `item-${f}`,
      label,
      hint,
      value: ee.config?.[f],
      getValue: () => host._editingItem?.config?.[f],
      setValue: (value) => {
        host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: value } };
        setTimeout(() => host.requestUpdate(), 0);
      },
    });
  }
  if (f === 'icon') {
    const rawIcon = ee.config?.[f];
    const displayStr = formatFieldValue(rawIcon) || "";
    const showDictPreview = rawIcon != null && typeof rawIcon === "object" && !Array.isArray(rawIcon);
    const dictPreviewText = showDictPreview
      ? t("State-keyed: {value}").replace("{value}", Object.entries(rawIcon).map(([k, v]) => `${k} → ${v}`).join(", "))
      : "";
    return html`
      <div class="haui-field">
        <label for="item-${f}" title=${hint}>${label}</label>
        ${renderIconPicker(`item-${f}`, displayStr, host.api, (newVal) => {
          host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: parseFieldValue(newVal) } };
          setTimeout(() => host.requestUpdate(), 0);
        })}
        <div class="haui-state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
      </div>`;
  }
  const rawVal = ee.config?.[f];
  const displayStr = formatFieldValue(rawVal);
  const showDictPreview = rawVal != null && typeof rawVal === "object" && !Array.isArray(rawVal);
  const dictPreviewText = showDictPreview
    ? t("State-keyed: {value}").replace("{value}", Object.entries(rawVal).map(([k, v]) => `${k} → ${v}`).join(", "))
    : "";
  const hasTpl = displayStr.includes("{{");
  return html`
    <div class="haui-field">
      <label for="item-${f}" title=${hint}>${label}</label>
      <input id="item-${f}" .value=${displayStr} class="haui-input"
        @input=${(e) => {
          const raw = e.target.value;
          if (host.api) scheduleTemplateRender(host.api, raw, `tp-item-${f}`, e.target);
          host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: parseFieldValue(raw) } };
          setTimeout(() => host.requestUpdate(), 0);
        }}
        @focus=${(e) => { if (host.api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.api, e.target.value, `tp-item-${f}`, e.target); }}
      />
      ${host.hass
        ? html`<div class="haui-template-preview" ?hidden=${!hasTpl}>
            <span id="tp-item-${f}">${hasTpl ? "..." : ""}</span>
          </div>`
        : ""}
      <div class="haui-state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
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
    <div class="haui-item-edit-inline" id="${uid}">
      <div class="haui-field">
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

      <div class="haui-field">
        ${(() => {
          const labels = itemLabels();
          const info = labels[itemType] || labels.entity_id;
          if (itemType === ITEM_TYPE.SKIP) return "";
          if (itemType === ITEM_TYPE.ENTITY_ID) {
            return renderEntityPicker({
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
            return html`
              <label for="item-entity">${info.label}</label>
              ${renderSelect(
                "item-entity",
                itemValue,
                panelTargetOptions(host.devicePanels, host.systemPanels, itemValue),
                (v) => {
                  host._editingItem = {
                    ...host._editingItem,
                    config: { ...host._editingItem.config, item: v },
                  };
                },
                { placeholder: t("Choose a panel") },
              )}
            `;
          }
          return html`
            <label for="item-entity" title=${`${info.label} — ${t("enter an entity ID, panel key, service name, or custom text")}`}>${info.label}</label>
            <input
              id="item-entity"
              class="haui-input"
              .value=${itemValue}
              placeholder=${info.placeholder}
              @input=${(e) => {
                if (host.api) scheduleTemplateRender(host.api, e.target.value, `tp-item-entity`, e.target);
                host._editingItem = {
                  ...host._editingItem,
                  config: { ...host._editingItem.config, item: e.target.value },
                };
                setTimeout(() => host.requestUpdate(), 0);
              }}
              @focus=${(e) => { if (host.api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.api, e.target.value, `tp-item-entity`, e.target); }}
            />
            ${host.hass
              ? html`<div class="haui-template-preview" ?hidden=${!(String(itemValue).includes("{{"))}>
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
        class="haui-collapsible-title"
        @click=${(e) => {
          const toggle = e.currentTarget;
          const arrow = toggle.querySelector(".haui-collapsible-icon");
          const section = toggle.nextElementSibling;
          if (arrow) arrow.classList.toggle("is-open");
          if (section) section.classList.toggle("is-open");
        }}
      >
        <ha-icon icon="mdi:chevron-right" class="haui-collapsible-icon"></ha-icon>
        ${t("Advanced")}
      </div>
      <div class="haui-item-advanced-section">
        ${ENTITY_OVERRIDE_FIELDS.filter(f => f !== 'service_data' && f !== 'name' && f !== 'icon' && f !== 'color').map(
          (f) => {
            const fieldLabels = {
              value: t("Value"),
              state: t("State"),
              popup_key: t("Popup key"),
            };
            const hints = {
              value: t("A display value or Home Assistant template that overrides what is shown for this item on the panel. Supports typed values (integers, floats, JSON arrays/objects)."),
              state: t("An attribute name (string) or JSON array for nested attribute access that overrides the entity state used for display logic."),
              popup_key: t("The key of a popup panel configuration that opens when this item is tapped. Leave empty to use the default popup behavior."),
            };
            const typedFields = new Set(["value"]);
            const isTyped = typedFields.has(f);
            const rawVal = ee.config?.[f];
            const displayStr = formatFieldValue(rawVal);
            const showDictPreview = rawVal != null && typeof rawVal === "object" && !Array.isArray(rawVal);
            const dictPreviewText = showDictPreview
              ? t("State-keyed: {value}").replace("{value}", Object.entries(rawVal).map(([k, v]) => `${k} → ${v}`).join(", "))
              : "";
            return html`
              <div class="haui-field">
                <label for="item-${f}" title=${hints[f]}>${fieldLabels[f]}</label>
                <input
                  id="item-${f}"
                  class="haui-input"
                  .value=${displayStr}
                  @input=${(e) => {
                    const raw = e.target.value;
                    if (host.api) scheduleTemplateRender(host.api, raw, `tp-item-${f}`, e.target);
                    host._editingItem = {
                      ...host._editingItem,
                      config: { ...host._editingItem.config, [f]: isTyped ? parseFieldValue(raw) : raw },
                    };
                    setTimeout(() => host.requestUpdate(), 0);
                  }}
                  @focus=${(e) => { if (host.api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.api, e.target.value, `tp-item-${f}`, e.target); }}
                />
                ${host.hass
                  ? html`<div class="haui-template-preview" ?hidden=${!displayStr.includes("{{")}>
                      <span id="tp-item-${f}">${displayStr.includes("{{") ? "..." : ""}</span>
                    </div>`
                  : ""}
                <div class="haui-state-keyed-preview" ?hidden=${!showDictPreview}>${dictPreviewText}</div>
              </div>
            `;
          }
        )}
        ${host._editingItemType === ITEM_TYPE.ACTION
          ? html`
            <div class="haui-field">
              <label for="item-service_data" title=${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts.")}>${t("Service data")}</label>
              <textarea
                id="item-service_data"
                class="haui-w-full haui-item-service-data"
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
              <div class="haui-field-hint">${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts. Example: {\\\"vacuum_repeat\\\": 2}")}</div>
            </div>`
          : ""}
        ${(() => {
          if (!descriptor?.item_options?.length) return "";
          return descriptor.item_options.map((opt) =>
            renderItemOptionField(host, opt, ee.config?.[opt.key])
          );
        })()}
      </div>

      <div class="haui-item-edit-actions">
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
            for (const { key: f } of desc.item_options) {
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
          ${isAdd ? t("Add") : t("Apply")}
        </ha-button>
      </div>
    </div>
  `;
}