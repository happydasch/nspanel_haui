import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { panelRow } from '../../custom_components/nspanel_haui/frontend/ui/panel-row.js';
import { panelThumb, zoomPlacement } from '../../custom_components/nspanel_haui/frontend/ui/panel-thumb.js';
import { panelRoleMarkers } from '../../custom_components/nspanel_haui/frontend/panel-utils.js';

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (value?.strings) return value.strings.reduce((text, part, index) => text + part + flatten(value.values[index]), '');
  return value == null ? '' : String(value);
}

/** The click handler of the row's title button. */
function titleClick(row) {
  const title = row.strings.findIndex((part) => part.includes('haui-panel-row-title'));
  const index = row.strings.findIndex((part, at) => at > title && part.trimEnd().endsWith('@click='));
  return row.values[index];
}

/** The click and key handlers of the row itself. */
function rowHandlers(row) {
  const at = (name) => row.values[row.strings.findIndex((part) => part.includes(`@${name}=`))];
  return { click: at('click'), keydown: at('keydown') };
}

test('panel row renders its title, key, item count and independent actions', () => {
  const edited = [];
  const row = panelRow({
    group: 'navigation', title: 'Kitchen light', key: 'kitchen_light', itemCount: 2,
    actions: { strings: ['<button>More</button>'], values: [] },
    onEdit: () => edited.push('kitchen_light'),
  });
  const output = flatten(row);
  assert.match(output, /haui-panel-row/);
  assert.match(output, /Kitchen light/);
  assert.match(output, /kitchen_light/);
  assert.match(output, /2 items/);
  assert.match(output, /More/);
  titleClick(row)();
  assert.deepEqual(edited, ['kitchen_light']);
});

test('a locked row explains why it cannot be edited', () => {
  const output = flatten(panelRow({ group: 'system', title: 'Settings', key: 'sys_settings', lockReason: 'Fixed system panel' }));
  assert.match(output, /Fixed system panel/);
});

const rowEvent = {
  clientY: 0,
  stopPropagation() {},
  currentTarget: {
    classList: { remove() {}, toggle() {} },
    getBoundingClientRect: () => ({ top: 0, height: 60 }),
  },
};

test('panel row drop delegates the source key without owning reorder state', () => {
  const moved = [];
  const row = panelRow({ group: 'navigation', key: 'target', title: 'Target', onDrop: (key) => moved.push(key) });
  const dropIndex = row.strings.findIndex((part) => part.includes('@drop='));
  const preventDefault = [];
  row.values[dropIndex]({
    ...rowEvent,
    preventDefault: () => preventDefault.push(true),
    dataTransfer: { getData: (type) => type === 'text/plain' ? 'source' : '' },
  });
  assert.deepEqual(preventDefault, [true]);
  assert.deepEqual(moved, ['source']);
});

test('panel thumbnail provides an accessible preview name', () => {
  const thumb = panelThumb({
    content: { strings: ['<nspanel-simulator-frame></nspanel-simulator-frame>'], values: [] },
    portrait: true,
    label: 'Kitchen light',
  });
  assert.equal(thumb.values[1], 'Preview of Kitchen light');
  assert.match(flatten(thumb), /nspanel-simulator-frame/);
});

test('the enlarged preview sits beside its thumbnail and stays inside the viewport', () => {
  const viewport = { width: 1200, height: 800 };
  assert.deepEqual(zoomPlacement({ top: 400, right: 172, width: 72, height: 51 }, viewport), {
    left: 184, top: 323.5, width: 288, height: 204,
  });
  // Near the bottom edge it moves up; on a phone it shrinks to the viewport.
  assert.equal(zoomPlacement({ top: 780, right: 172, width: 72, height: 51 }, viewport).top, 588);
  const phone = zoomPlacement({ top: 100, right: 150, width: 72, height: 51 }, { width: 280, height: 600 });
  assert.equal(phone.width, 264);
  assert.equal(phone.left, 8);
});

test('a thumbnail enlarges on mouse hover and toggles on tap or key press', () => {
  const listeners = new Map();
  const target = {
    addEventListener: (type, listener) => listeners.set(type, listener),
    removeEventListener: (type) => listeners.delete(type),
  };
  globalThis.window = { innerWidth: 1200, innerHeight: 800, ...target };
  globalThis.document = target;
  const classes = new Set();
  const view = {
    style: {},
    getBoundingClientRect: () => ({ left: 20, top: 10 }),
    removeAttribute() { this.style = {}; },
  };
  const attributes = {};
  const element = {
    classList: {
      add: (name) => classes.add(name), remove: (name) => classes.delete(name), contains: (name) => classes.has(name),
    },
    setAttribute: (name, value) => { attributes[name] = value; },
    querySelector: () => view,
    getBoundingClientRect: () => ({ top: 400, right: 172, width: 72, height: 51 }),
  };
  const thumb = panelThumb({ content: '', label: 'Kitchen light' });
  const handler = (name) => thumb.values[thumb.strings.findIndex((part) => part.trimEnd().endsWith(`@${name}=`))];

  handler('pointerenter')({ pointerType: 'touch', currentTarget: element });
  assert.equal(classes.has('is-zoomed'), false);
  handler('pointerenter')({ pointerType: 'mouse', currentTarget: element });
  assert.equal(classes.has('is-zoomed'), true);
  assert.equal(attributes['aria-expanded'], 'true');
  handler('click')({ pointerType: 'mouse', currentTarget: element });
  assert.equal(classes.has('is-zoomed'), true);
  handler('pointerleave')({ pointerType: 'mouse', currentTarget: element });
  assert.equal(classes.has('is-zoomed'), false);
  assert.equal(listeners.size, 0);

  handler('click')({ pointerType: 'touch', currentTarget: element });
  assert.equal(classes.has('is-zoomed'), true);
  listeners.get('pointerdown')({ type: 'pointerdown', composedPath: () => [element] });
  assert.equal(classes.has('is-zoomed'), true);
  listeners.get('pointerdown')({ type: 'pointerdown', composedPath: () => [] });
  assert.equal(classes.has('is-zoomed'), false);

  handler('click')({ pointerType: '', currentTarget: element });
  listeners.get('scroll')({ type: 'scroll' });
  assert.equal(classes.has('is-zoomed'), false);
  assert.equal(attributes['aria-expanded'], 'false');
});

test('home and idle markers follow the device role assignments', () => {
  const home = panelRoleMarkers('kitchen', { home_panel: 'kitchen', idle_panel: 'clock_0' });
  const idle = panelRoleMarkers('clock_0', { home_panel: 'kitchen', idle_panel: 'clock_0' });
  assert.equal(home.length, 1);
  assert.match(flatten(home[0]), /aria-label=Home panel/);
  assert.equal(idle.length, 1);
  assert.match(flatten(idle[0]), /aria-label=Idle panel/);
  assert.equal(panelRoleMarkers('other', { home_panel: 'kitchen', idle_panel: 'clock_0' }).length, 0);
});

test('a row that takes drops allows them on dragover; a locked row does not', () => {
  const dragOverOf = (row) => row.values[row.strings.findIndex((part) => part.includes('@dragover=')) ];
  const prevented = [];
  dragOverOf(panelRow({ group: 'navigation', key: 'target', title: 'Target', onDrop() {} }))({
    ...rowEvent,
    preventDefault: () => prevented.push(true),
  });
  assert.deepEqual(prevented, [true]);
  assert.notEqual(typeof dragOverOf(panelRow({ group: 'system', key: 'sys', title: 'System' })), 'function');
});

test('a row selects itself on a click outside its controls, and marks the selection', () => {
  const selected = [];
  const row = panelRow({ group: 'navigation', key: 'kitchen', title: 'Kitchen', onSelect: () => selected.push('kitchen') });
  const { click } = rowHandlers(row);
  click({ target: { closest: () => null } });
  assert.deepEqual(selected, ['kitchen']);
  // The title, the row actions and the overlaid menu keep their own click.
  click({ target: { closest: (selector) => selector.includes('button') ? {} : null } });
  assert.deepEqual(selected, ['kitchen']);

  const chosen = flatten(panelRow({ group: 'navigation', key: 'kitchen', title: 'Kitchen', selected: true, onSelect() {} }));
  assert.match(chosen, /haui-panel-row is-selected/);
  assert.match(chosen, /aria-current=true/);
  const plain = flatten(panelRow({ group: 'navigation', key: 'kitchen', title: 'Kitchen', onSelect() {} }));
  assert.doesNotMatch(plain, /is-selected|aria-current=true/);
});

test('a selectable row answers Enter and Space, and only a selectable one is in the tab order', () => {
  const selected = [];
  const row = panelRow({ group: 'navigation', key: 'kitchen', title: 'Kitchen', onSelect: () => selected.push('kitchen') });
  const { keydown } = rowHandlers(row);
  const prevented = [];
  keydown({ key: 'Enter', preventDefault: () => prevented.push(true) });
  keydown({ key: ' ', preventDefault: () => prevented.push(true) });
  keydown({ key: 'Tab', preventDefault: () => prevented.push(true) });
  assert.deepEqual(selected, ['kitchen', 'kitchen']);
  assert.deepEqual(prevented, [true, true]);
  assert.match(flatten(row), /tabindex=0/);
  assert.match(flatten(panelRow({ group: 'system', key: 'sys', title: 'System' })), /tabindex=Symbol\(lit-nothing\)/);
});

test('a panel whose saved settings break a rule says so in text', () => {
  const output = flatten(panelRow({ group: 'navigation', title: 'Lamp', key: 'light_0', invalid: true }));

  assert.match(output, /haui-badge-warning/);
  assert.match(output, /Check settings/);
  assert.doesNotMatch(flatten(panelRow({ group: 'navigation', title: 'Lamp', key: 'light_0' })), /Check settings/);
});
