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
import {
  ENTITY_OVERRIDE_FIELDS, entityDisplayName, entityStateSuggestions, renderEntityPicker,
} from './haui-entity.js';
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
  fieldMessage,
  renderToggle,
  renderColorField,
  renderField,
} from './form-field-controls.js';
import { parseRgbListToHex } from './color-utils.js';
import { formVal } from './dom-helpers.js';
import { dropsAfter } from './ui/panel-row.js';
import { badge } from './ui/badge.js';
import { addButton } from './ui/button.js';
import { emptyState } from './ui/empty-state.js';
import { segmented } from './ui/segmented.js';
import { stateRowsToMap, stateValues } from './ui/state-values.js';
import { startHandleDrag } from './ui/drag-handle.js';

/* ── values per state ───────────────────────────────────────────────── */

/** A field given one value per state is a plain object of state → value. */
function isStateMap(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * The icon a row shows for its item: its own icon, the icon of the entity's
 * current state for icons per state; none for a template.
 */
function rowIcon(hass, item) {
  let value = item?.icon;
  if (isStateMap(value)) {
    const state = hass?.states?.[item.item]?.state;
    value = value[state] ?? Object.values(value)[0];
  }
  return typeof value === 'string' && value.includes(':') && !value.includes('{{') ? value : '';
}

/** The rows of an item field given per state, or null while it has one value. */
function stateRowsOf(ee, key) {
  if (ee.stateRows?.[key]) return ee.stateRows[key];
  const value = ee.config?.[key];
  return isStateMap(value) ? Object.entries(value).map(([state, v]) => ({ state, value: v })) : null;
}

/**
 * Store an item field's rows per state. The draft keeps the rows as typed, a
 * row without a state included; the item gets the map the hub reads.
 */
function setStateRows(host, key, rows) {
  const ee = host._editingItem;
  host._editingItem = {
    ...ee,
    stateRows: { ...ee.stateRows, [key]: rows },
    config: { ...ee.config, [key]: stateRowsToMap(rows) },
  };
  host.requestUpdate();
}

/** Give an item field one value again, for every state. */
function setSingleValue(host, key, value) {
  const { [key]: _rows, ...stateRows } = host._editingItem.stateRows ?? {};
  host._editingItem = {
    ...host._editingItem,
    stateRows,
    config: { ...host._editingItem.config, [key]: value },
  };
  host.requestUpdate();
}

/** A stored value: not empty, and not a value per state without any state. */
function hasValue(value) {
  if (value === null || value === undefined || value === '') return false;
  return !(isStateMap(value) && Object.keys(value).length === 0);
}

/**
 * An item field that takes one value or a value per state. `single` is its
 * control while it has one value; `rowValue` renders the value of one state.
 * Entity items offer the switch; another item keeps values it already has
 * per state editable, as it has no state to match them against.
 */
function renderPerStateField(host, ee, { key, label, hint, entityId, offered, single, rowValue }) {
  const id = `item-${key}`;
  const labelId = `${id}-label`;
  const rows = stateRowsOf(ee, key);
  const perState = rows !== null;
  const states = entityStateSuggestions(host.hass, entityId, ee.config?.state);
  const toRows = () => {
    const value = ee.config?.[key];
    // The value given so far becomes the current state's, the first state offered.
    setStateRows(host, key, [{ state: states[0]?.value ?? '', value: hasValue(value) ? value : '' }]);
  };
  const toSingle = () => {
    const filled = rows.filter((row) => hasValue(row.value));
    const kept = filled.find((row) => row.state === states[0]?.value) ?? filled[0];
    setSingleValue(host, key, kept?.value);
  };
  const mode = offered || perState
    ? html`<span class="haui-state-mode">${segmented({
        label: t('Values of {field}').replace('{field}', label),
        options: [{ value: 'one', label: t('One value') }, { value: 'state', label: t('Per state') }],
        value: perState ? 'state' : 'one',
        onSelect: (value) => {
          if (value === 'state' && !perState) toRows();
          if (value === 'one' && perState) toSingle();
        },
      })}</span>`
    : nothing;
  return html`
    <div class="haui-field">
      <div class="haui-field-label-row">
        <label id=${labelId} for=${perState ? nothing : id}>${label}</label>
        ${mode}
      </div>
      ${perState
        ? stateValues({
          id,
          label,
          labelledBy: labelId,
          rows,
          states,
          renderValue: rowValue,
          onChange: (next) => setStateRows(host, key, next),
        })
        : single}
      ${perState
        ? html`<div class="haui-field-hint is-persistent">${t('A state without a row uses the default.')}</div>`
        : nothing}
      ${hint ? html`<div class="haui-field-hint">${hint}</div>` : nothing}
    </div>
  `;
}

/** A text field that takes a template, with the template's result below it. */
function itemTextControl(host, { id, value, label, onInput }) {
  const text = formatFieldValue(value);
  const hasTpl = text.includes("{{");
  return html`
    <input id=${id} class="haui-input" aria-label=${label ?? nothing} .value=${text}
      @input=${(e) => {
        if (host.api) scheduleTemplateRender(host.api, e.target.value, `tp-${id}`, e.target);
        onInput(e.target.value);
      }}
      @focus=${(e) => { if (host.api && String(e.target.value || "").includes("{{")) scheduleTemplateRender(host.api, e.target.value, `tp-${id}`, e.target); }}
    />
    ${host.hass
      ? html`<div class="haui-template-preview" ?hidden=${!hasTpl}>
          <span id="tp-${id}">${hasTpl ? "..." : ""}</span>
        </div>`
      : ""}
  `;
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
  const icon = rowIcon(host?.hass, item) || ITEM_TYPE_ICONS[type] || 'mdi:circle-outline';
  const typeLabel = itemTypeShort()[type] || t('Item');
  const secondary = itemSecondaryText(item);
  // An entity without a name of its own goes by its Home Assistant name, as on the panel.
  const entityName = !item?.name && type === ITEM_TYPE.ENTITY_ID
    ? entityDisplayName(host?.hass, secondary)
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
        ? html`<span class="haui-item-row-grip" role="img" aria-label=${gripLabel} title=${gripLabel}
            data-drag-handle @pointerdown=${startHandleDrag}>
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
  // The API sends `choices: []` for an option that has none, so an empty list is no dropdown.
  const choices = Array.isArray(opt.choices) && opt.choices.length ? opt.choices : null;
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
      ${opt.description ? html`<div class="haui-field-hint is-persistent">${opt.description}</div>` : ""}

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
export function renderItemListField(host, opt, currentValue, feedback = {}) {
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
      ${opt.description ? html`<div class="haui-field-hint is-persistent">${opt.description}</div>` : ""}
      ${fieldMessage(id, feedback)}

      <div class="haui-item-list">
        ${entities.length === 0 && editingIndex !== -1
          ? emptyState({ message: t('No items yet. Click "+ Add Item" below.'), iconName: null, className: 'haui-empty-state-inset' })
          : ''}
        ${entities.map((item, i) => {
          if (editingIndex === i) {
            return renderItemEditFields(host);
          }
          const entryFeedback = feedback.entries?.get(i);
          return html`${renderItemListRow(
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
          )}${entryFeedback ? fieldMessage(`${id}-${i}`, entryFeedback) : nothing}`;
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

/** An item's colour field; its presets stay open while the item does. */
function itemColorControl(host, { id, value, label, setValue }) {
  // Kept on the item draft, so the next item opens with its presets closed.
  const openPresets = host._editingItem.openPresets ?? [];
  const presetsOpen = openPresets.includes(id);
  return renderColorField({
    id,
    value,
    label,
    api: host.api,
    onChange: setValue,
    presetsOpen,
    onTogglePresets: () => {
      host._editingItem = {
        ...host._editingItem,
        openPresets: presetsOpen ? openPresets.filter((key) => key !== id) : [...openPresets, id],
      };
      host.requestUpdate();
    },
  });
}

/** A colour that may be given per state: the item's own colour and its colour options. */
function renderItemColorField(host, ee, { key, label, hint, entityId, offered, setValue }) {
  return renderPerStateField(host, ee, {
    key,
    label,
    hint,
    entityId,
    offered,
    single: itemColorControl(host, { id: `item-${key}`, value: ee.config?.[key], setValue }),
    rowValue: (row, valueId, valueLabel, setRowValue) =>
      itemColorControl(host, { id: valueId, value: row.value, label: valueLabel, setValue: setRowValue }),
  });
}

/* ── per-item option field (mirrors renderOptionField for item configs) ─ */

/**
 * Render a single per-item override field, mirroring renderOptionField but
 * writing to host._editingItem.config instead of host._editingPanel.data.
 */
function renderItemOptionField(host, opt, currentValue, perState = {}) {
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
            <label for=${id} title=${opt.description}>${opt.label}</label>
            ${renderToggle(id, val, setVal)}
          </div>
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "int":
      // an empty field unsets the option, so the item uses the panel's value again
      return html`
        <div class="haui-field">
          <label for=${id} title=${opt.description}>${opt.label}</label>
          ${renderNumberInput(id, val, (raw) => setVal(raw === "" ? undefined : parseInt(raw, 10)), { step: "1" })}
          ${opt.description ? html`<div class="haui-field-hint">${opt.description}</div>` : ""}
        </div>
      `;

    case "color":
      return renderItemColorField(host, host._editingItem, {
        key: opt.key,
        label: opt.label,
        hint: opt.description,
        ...perState,
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

/* ── fields that take a value per state (name, icon, color, value) ──── */

/**
 * One of the item fields that take one value or a value per state. Name, icon
 * and colour sit above the Advanced fold, so users see them immediately.
 * `perState` says which entity the states belong to and whether to offer them.
 */
function renderStateField(host, ee, f, label, hint, perState) {
  // One value is stored typed, so a number stays a number.
  const setValue = (value) => {
    host._editingItem = { ...host._editingItem, config: { ...host._editingItem.config, [f]: value } };
    setTimeout(() => host.requestUpdate(), 0);
  };
  if (f === 'color') return renderItemColorField(host, ee, { key: f, label, hint, ...perState, setValue });
  const id = `item-${f}`;
  if (f === 'icon') {
    return renderPerStateField(host, ee, {
      key: f,
      label,
      hint,
      ...perState,
      single: renderIconPicker(id, formatFieldValue(ee.config?.[f]), host.api,
        (raw) => setValue(parseFieldValue(raw))),
      rowValue: (row, valueId, valueLabel, setRowValue) =>
        renderIconPicker(valueId, formatFieldValue(row.value), host.api, setRowValue, { label: valueLabel }),
    });
  }
  return renderPerStateField(host, ee, {
    key: f,
    label,
    hint,
    ...perState,
    single: itemTextControl(host, { id, value: ee.config?.[f], onInput: (raw) => setValue(parseFieldValue(raw)) }),
    rowValue: (row, valueId, valueLabel, setRowValue) =>
      itemTextControl(host, { id: valueId, value: row.value, label: valueLabel, onInput: setRowValue }),
  });
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
  // Only an entity has states; the per-state fields suggest the chosen entity's.
  const perState = {
    offered: itemType === ITEM_TYPE.ENTITY_ID,
    entityId: itemType === ITEM_TYPE.ENTITY_ID ? itemValue || '' : '',
  };

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
                // The per-state fields suggest the states of the chosen entity.
                host.requestUpdate();
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
            <label for="item-entity" title=${`${info.label} — ${t("enter an entity ID, panel key, action name, or custom text")}`}>${info.label}</label>
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
      ].map(fd => renderStateField(host, ee, fd.f, fd.label, fd.hint, perState))}
      <details class="haui-item-advanced">
        <summary class="haui-collapsible-title">
          <ha-icon icon="mdi:chevron-right" class="haui-collapsible-icon"></ha-icon>
          <span>${t("Advanced")}</span>
        </summary>
        <div class="haui-item-advanced-section">
          ${renderStateField(host, ee, 'value', t("Value"),
            t("A display value or Home Assistant template that overrides what is shown for this item on the panel. Supports typed values (integers, floats, JSON arrays/objects)."),
            perState)}
          ${[
            { f: 'state', label: t("State"), hint: t("An attribute name (string) or JSON array for nested attribute access that overrides the entity state used for display logic.") },
            { f: 'popup_key', label: t("Popup key"), hint: t("The key of a popup panel configuration that opens when this item is tapped. Leave empty to use the default popup behavior.") },
          ].map(({ f, label, hint }) => renderField({
            id: `item-${f}`,
            label,
            hint,
            control: html`<input
              id="item-${f}"
              class="haui-input"
              .value=${formatFieldValue(ee.config?.[f])}
              @input=${(e) => {
                host._editingItem = {
                  ...host._editingItem,
                  config: { ...host._editingItem.config, [f]: e.target.value },
                };
                setTimeout(() => host.requestUpdate(), 0);
              }}
            />`,
          }))}
          ${host._editingItemType === ITEM_TYPE.ACTION
            ? html`
              <div class="haui-field">
                <label for="item-service_data" title=${t("JSON object passed as service_data when calling the action. Keys are available as template variables in scripts.")}>${t("Action data")}</label>
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
              renderItemOptionField(host, opt, ee.config?.[opt.key], perState)
            );
          })()}
        </div>
      </details>

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
            if (hasValue(fv)) config[f] = fv;
          }
          const savePt = host._editingPanelType || host._editingPanel?.data?.type;
          const panelTypes = host._panelTypes || host.panelTypes;
          const desc = (savePt && panelTypes)
            ? panelTypes.find(d => d.type_key === savePt) || null
            : null;
          if (desc?.item_options) {
            for (const { key: f } of desc.item_options) {
              const fv = host._editingItem.config?.[f];
              if (hasValue(fv)) config[f] = fv;
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