import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderItemListField, renderItemListRow } from '../../custom_components/nspanel_haui/frontend/item-renderers.js';

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (value?.strings) return value.strings.reduce((text, part, index) => text + part + flatten(value.values[index]), '');
  return value == null ? '' : String(value);
}

/** Every item row template of a rendered field, in list order. */
function rowsOf(value) {
  if (Array.isArray(value)) return value.flatMap(rowsOf);
  if (!value?.strings) return [];
  if (value.strings[0].includes('item-list-row')) return [value];
  return value.values.flatMap(rowsOf);
}

const handler = (row, name) => row.values[row.strings.findIndex((part) => part.endsWith(`${name}=`))];

function dragEvent(clientY) {
  const prevented = [];
  return {
    clientY,
    prevented,
    preventDefault: () => prevented.push(true),
    dataTransfer: { setData() {} },
    currentTarget: {
      classList: { add() {}, remove() {}, toggle() {} },
      contains: () => false,
      getBoundingClientRect: () => ({ top: 0, height: 40 }),
    },
  };
}

function listHost(items, listKey = 'items') {
  return {
    _itemListData: { [listKey]: items.map((item) => ({ item })) },
    _editingItem: null,
    updates: 0,
    requestUpdate() { this.updates += 1; },
  };
}

const field = (host, key = 'items') => renderItemListField(host, { key, kind: 'item_list', label: 'Items' }, []);
const order = (host, key = 'items') => host._itemListData[key].map((entry) => entry.item);

/** Drag row `from` onto the upper (`after` false) or lower half of row `onto`. */
function drag(host, from, onto, after) {
  const rows = rowsOf(field(host));
  handler(rows[from], '@dragstart')(dragEvent(0));
  const over = dragEvent(after ? 30 : 10);
  handler(rows[onto], '@dragover')(over);
  handler(rows[onto], '@drop')(dragEvent(after ? 30 : 10));
  handler(rows[from], '@dragend')(dragEvent(0));
  return over;
}

test('an item list row is dragged by a grip and has no move buttons', () => {
  const output = flatten(field(listHost(['light.a', 'light.b'])));
  assert.match(output, /draggable=true/);
  assert.match(output, /item-row-grip/);
  assert.doesNotMatch(output, /Move up|Move down|chevron-up|chevron-down/);
});

test('a single item row is not draggable', () => {
  const row = renderItemListRow({}, { item: 'light.a' }, { onEdit() {} });
  assert.doesNotMatch(flatten(row), /item-row-grip|draggable=true/);
});

test('dropping a row on the lower half of another moves it after that row', () => {
  const host = listHost(['light.a', 'light.b', 'light.c']);
  const over = drag(host, 0, 2, true);
  assert.equal(over.prevented.length, 1);
  assert.deepEqual(order(host), ['light.b', 'light.c', 'light.a']);
  assert.equal(host.updates, 1);
});

test('dropping a row on the upper half of another moves it before that row', () => {
  const host = listHost(['light.a', 'light.b', 'light.c']);
  drag(host, 2, 0, false);
  assert.deepEqual(order(host), ['light.c', 'light.a', 'light.b']);
});

test('a drop that leaves the row where it is changes nothing', () => {
  const host = listHost(['light.a', 'light.b', 'light.c']);
  drag(host, 0, 1, false);
  drag(host, 1, 1, true);
  assert.deepEqual(order(host), ['light.a', 'light.b', 'light.c']);
  assert.equal(host.updates, 0);
});

test('a row takes no drop from another list', () => {
  const host = listHost(['light.a', 'light.b']);
  host._itemListData.extra = [{ item: 'switch.a' }, { item: 'switch.b' }];
  const source = rowsOf(field(host, 'extra'))[0];
  const target = rowsOf(field(host))[1];
  handler(source, '@dragstart')(dragEvent(0));
  const over = dragEvent(30);
  handler(target, '@dragover')(over);
  handler(target, '@drop')(dragEvent(30));
  handler(source, '@dragend')(dragEvent(0));
  assert.equal(over.prevented.length, 0);
  assert.deepEqual(order(host), ['light.a', 'light.b']);
  assert.deepEqual(order(host, 'extra'), ['switch.a', 'switch.b']);
});

test('the item open in the inline form follows a move around it', () => {
  const host = listHost(['light.a', 'light.b', 'light.c']);
  host._editingItem = { optKey: 'items', index: 1, config: { item: 'light.b' }, domain: '' };
  host._editingItemType = 'entity_id';
  // Row 1 is the form, so the rendered rows are items 0 and 2.
  const rows = rowsOf(field(host));
  handler(rows[1], '@dragstart')(dragEvent(0));
  handler(rows[0], '@drop')(dragEvent(10));
  assert.deepEqual(order(host), ['light.c', 'light.a', 'light.b']);
  assert.equal(host._editingItem.index, 2);
});
