/**
 * NSPanel HAUI - Editor - Inline item (entity) editing.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { encodeItemValue } from './haui-item.js';
import { ENTITY_OVERRIDE_FIELDS } from './haui-entity.js';
import { formVal } from './dom-helpers.js';

export function saveItemEdit(host) {
  const ee = host._editingItem;
  if (!ee) return;
  const { optKey, index } = ee;

  const uid = `item-edit-${optKey}-${index}`;
  const inline = host.renderRoot.querySelector(`#${uid}`);
  if (!inline) return;

  const typeVal = host._editingItemType || inline.querySelector("#item-type")?.value || "entity_id";

  const inputVal = formVal(inline, "item-entity");
  const config = { item: encodeItemValue(inputVal, typeVal) };

  for (const f of ENTITY_OVERRIDE_FIELDS) {
    const fv = ee.config?.[f];
    if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
  }

  const savePt = host._editingPanelType || host._editingPanel?.data?.type;
  const panelTypes = host._panelTypes || host.panelTypes;
  const descriptor = (savePt && panelTypes)
    ? panelTypes.find(d => d.type_key === savePt) || null
    : null;
  if (descriptor?.item_options) {
    for (const f of descriptor.item_options) {
      const fv = ee.config?.[f];
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
}

export function cancelItemEdit(host) {
  host._editingItem = null;
  host._editingItemType = null;
  host.requestUpdate();
}