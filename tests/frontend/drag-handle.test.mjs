import './support/browser.mjs';

import { beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { resetBrowser } from './support/browser.mjs';
import { render } from './support/render.mjs';
import { renderPanelList } from '../../custom_components/nspanel_haui/frontend/views/panel-list.js';
import { renderItemListField } from '../../custom_components/nspanel_haui/frontend/item-renderers.js';

beforeEach(resetBrowser);

/** The Panels view's navigation group with two user panels. */
function navigationGroup() {
  const entry = (key) => ({ key, kind: 'user', sortable: true, title: key, onEdit: () => {} });
  return [{
    id: 'navigation',
    title: 'Navigation',
    hint: '2 panels',
    emptyMessage: 'No panels',
    dropEnabled: true,
    entries: [entry('kitchen'), entry('hall')],
  }];
}

/** That group rendered into the document, reporting every drop. */
function panelList(drops) {
  const container = render(renderPanelList({ groups: navigationGroup(), onDrop: (move) => drops.push(move) }));
  document.body.append(container);
  return container;
}

const rowOf = (container, key) => container.querySelector(`[data-panel-key="${key}"]`);
const gripOf = (container, key) => rowOf(container, key).querySelector('[data-drag-handle]');

/** A press on the grip: a finger reports pointer events and starts no drag of its own. */
function pointer(type, { x = 0, y = 0, kind = 'touch' } = {}) {
  return new PointerEvent(type, {
    bubbles: true,
    cancelable: true,
    clientX: x,
    clientY: y,
    pointerId: 7,
    pointerType: kind,
    isPrimary: true,
    button: 0,
  });
}

/** Aim the browser's hit test at one element, as a finger resting over it would. */
function over(element) {
  const previous = document.elementFromPoint;
  document.elementFromPoint = () => element;
  return () => {
    document.elementFromPoint = previous;
  };
}

/** Press a grip and carry it to `to`; the returned function lets go there. */
function fingerDrag(grip, { from = { x: 10, y: 10 }, to = { x: 10, y: 40 }, kind = 'touch' } = {}) {
  grip.dispatchEvent(pointer('pointerdown', { ...from, kind }));
  document.dispatchEvent(pointer('pointermove', { ...to, kind }));
  return () => document.dispatchEvent(pointer('pointerup', { ...to, kind }));
}

test('a finger drag of a panel grip drops the row on the one it is released over', () => {
  const drops = [];
  const container = panelList(drops);
  const kitchen = rowOf(container, 'kitchen');
  const hall = rowOf(container, 'hall');
  const restoreHit = over(hall);
  const release = fingerDrag(gripOf(container, 'kitchen'));

  assert.equal(kitchen.classList.contains('is-dragging'), true);
  assert.equal(hall.classList.contains('is-drop-after'), true);

  release();
  restoreHit();
  assert.deepEqual(drops, [{ sourceKey: 'kitchen', group: 'navigation', beforeKey: null }]);
  assert.equal(kitchen.classList.contains('is-dragging'), false);
  assert.equal(hall.classList.contains('is-drop-after'), false);
});

test('a finger released over the upper half of a row drops the panel before it', () => {
  const drops = [];
  const container = panelList(drops);
  const restoreHit = over(rowOf(container, 'hall'));
  // Row halves come from the row's box; a release above its middle lands before it.
  const release = fingerDrag(gripOf(container, 'kitchen'), { from: { x: 10, y: 40 }, to: { x: 10, y: 0 } });
  release();
  restoreHit();
  assert.deepEqual(drops, [{ sourceKey: 'kitchen', group: 'navigation', beforeKey: 'hall' }]);
});

test('a finger that leaves a row clears its marker and marks the group it is over', () => {
  const drops = [];
  const container = panelList(drops);
  const hall = rowOf(container, 'hall');
  const group = container.querySelector('.haui-panel-group');
  const restoreHit = over(hall);
  const grip = gripOf(container, 'kitchen');
  grip.dispatchEvent(pointer('pointerdown', { x: 10, y: 10 }));
  document.dispatchEvent(pointer('pointermove', { x: 10, y: 40 }));
  assert.equal(hall.classList.contains('is-drop-after'), true);

  document.elementFromPoint = () => group;
  document.dispatchEvent(pointer('pointermove', { x: 10, y: 44 }));
  assert.equal(hall.classList.contains('is-drop-after'), false);
  assert.equal(group.classList.contains('is-drop-target'), true);

  document.dispatchEvent(pointer('pointerup', { x: 10, y: 44 }));
  restoreHit();
  assert.deepEqual(drops, [{ sourceKey: 'kitchen', group: 'navigation', beforeKey: null }]);
  assert.equal(group.classList.contains('is-drop-target'), false);
});

test('a tap on a grip moves nothing', () => {
  const drops = [];
  const container = panelList(drops);
  const kitchen = rowOf(container, 'kitchen');
  const grip = gripOf(container, 'kitchen');
  grip.dispatchEvent(pointer('pointerdown', { x: 10, y: 10 }));
  document.dispatchEvent(pointer('pointermove', { x: 11, y: 13 }));
  document.dispatchEvent(pointer('pointerup', { x: 11, y: 13 }));

  assert.deepEqual(drops, []);
  assert.equal(kitchen.classList.contains('is-dragging'), false);
});

test('a mouse on a grip is left to the browser own drag', () => {
  const drops = [];
  const container = panelList(drops);
  const kitchen = rowOf(container, 'kitchen');
  const hall = rowOf(container, 'hall');
  const restoreHit = over(hall);
  const release = fingerDrag(gripOf(container, 'kitchen'), { kind: 'mouse' });
  release();
  restoreHit();

  assert.deepEqual(drops, []);
  assert.equal(kitchen.classList.contains('is-dragging'), false);
  assert.equal(hall.classList.contains('is-drop-after'), false);
});

test('the click a touch ends with after a drag does not reach the row it landed on', () => {
  const drops = [];
  const container = panelList(drops);
  const hall = rowOf(container, 'hall');
  const restoreHit = over(hall);
  const release = fingerDrag(gripOf(container, 'kitchen'));
  release();

  let clicked = 0;
  const onClick = () => { clicked += 1; };
  hall.addEventListener('click', onClick);
  hall.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  hall.removeEventListener('click', onClick);
  restoreHit();

  assert.deepEqual(drops, [{ sourceKey: 'kitchen', group: 'navigation', beforeKey: null }]);
  assert.equal(clicked, 0);
});

test('a drop finds the row inside the shadow root the editor renders into', () => {
  const drops = [];
  const host = document.createElement('nspanel-test-editor');
  const shadow = host.attachShadow({ mode: 'open' });
  document.body.append(host);
  const container = render(renderPanelList({ groups: navigationGroup(), onDrop: (move) => drops.push(move) }));
  shadow.append(container);
  const restoreHit = over(host);
  // The document's hit test stops at the host; the open root names the row inside.
  const rowHit = () => rowOf(container, 'hall');
  shadow.elementFromPoint = rowHit;

  const release = fingerDrag(gripOf(container, 'kitchen'));
  release();
  delete shadow.elementFromPoint;
  restoreHit();

  assert.deepEqual(drops, [{ sourceKey: 'kitchen', group: 'navigation', beforeKey: null }]);
});
test('a fresh press after a drag lets its own click through', () => {
  const drops = [];
  const container = panelList(drops);
  const hall = rowOf(container, 'hall');
  const restoreHit = over(hall);
  const release = fingerDrag(gripOf(container, 'kitchen'));
  release();

  // A press of its own means the click the drag would have ended with never came.
  document.dispatchEvent(pointer('pointerdown', { x: 10, y: 40 }));
  let clicked = 0;
  const onClick = () => { clicked += 1; };
  hall.addEventListener('click', onClick);
  hall.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  hall.removeEventListener('click', onClick);
  restoreHit();

  assert.equal(clicked, 1);
});

/** The panel editor's settings sidebar: its item list as the form renders it. */
function settingsList(items) {
  const host = {
    _itemListData: { items: items.map((item) => ({ item })) },
    _editingItem: null,
    updates: 0,
    requestUpdate() { this.updates += 1; },
  };
  const container = render(renderItemListField(host, { key: 'items', kind: 'item_list', label: 'Items' }, []));
  document.body.append(container);
  // The form re-renders through this host; the rows already in the document stay for the drop.
  return { container, host, rows: [...container.querySelectorAll('.haui-item-list-row')] };
}

test('a finger drag of a settings grip reorders the rows of the panel edit sidebar', () => {
  const { host, rows } = settingsList(['light.a', 'light.b', 'light.c']);
  const restoreHit = over(rows[2]);
  const release = fingerDrag(rows[0].querySelector('[data-drag-handle]'));
  assert.equal(rows[0].classList.contains('is-dragging'), true);
  assert.equal(rows[2].classList.contains('is-drop-after'), true);

  release();
  restoreHit();

  assert.deepEqual(host._itemListData.items.map((entry) => entry.item), ['light.b', 'light.c', 'light.a']);
  assert.equal(host.updates, 1);
  assert.equal(rows[0].classList.contains('is-dragging'), false);
});

