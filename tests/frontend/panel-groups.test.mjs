import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderPanelList } from '../../custom_components/nspanel_haui/frontend/views/panel-list.js';
import { groupPanels } from '../../custom_components/nspanel_haui/frontend/panel-utils.js';

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

/** @param {string} id @param {Array} entries */
function group(id, entries, extra = {}) {
  return {
    id,
    title: `${id} (${entries.length} panels)`,
    hint: `${id} hint`,
    emptyMessage: `drop into ${id}`,
    dropEnabled: id === 'navigation' || id === 'hidden',
    entries,
    ...extra,
  };
}

const userEntry = (key, extra = {}) => ({
  key,
  kind: 'user',
  sortable: true,
  title: key,
  typeLabel: 'Clock',
  itemCount: 2,
  preview: { strings: ['<nspanel-simulator-frame></nspanel-simulator-frame>'], values: [] },
  roles: [],
  onEdit: () => {},
  menu: [{ label: 'Edit', onSelect: () => {} }],
  ...extra,
});

test('the groups render a band header and rows, without visible drop zones', () => {
  const out = flat(renderPanelList({
    groups: [
      group('navigation', [userEntry('clock_0')]),
      group('hidden', [userEntry('clock_hidden')]),
      group('popups', [{ key: 'popup_notify', kind: 'popup', title: 'Notification', onEdit: () => {}, menu: [] }]),
    ],
  }));
  assert.match(out, /navigation \(1 panels\)/);
  assert.match(out, /hidden \(1 panels\)/);
  assert.match(out, /popups \(1 panels\)/);
  assert.match(out, /haui-panel-thumb/);
  assert.match(out, /nspanel-simulator-frame/);
  assert.doesNotMatch(out, /haui-panel-dropzone/);
  assert.doesNotMatch(out, /drop into/);
});

test('every row has a grip, which drags only when its entry is sortable', () => {
  const out = flat(renderPanelList({
    groups: [
      group('navigation', [userEntry('clock_0')]),
      group('popups', [{ key: 'popup_notify', kind: 'popup', title: 'Notification', onEdit: () => {}, menu: [] }]),
    ],
  }));
  const grips = out.match(/<span class="haui-panel-handle[^>]*>/g) ?? [];
  assert.equal(grips.length, 2);
  assert.match(grips[0], /draggable="true"/);
  assert.doesNotMatch(grips[0], /is-disabled/);
  assert.doesNotMatch(grips[1], /draggable/);
  assert.match(grips[1], /is-disabled/);
  assert.match(grips[1], /Notification cannot be reordered/);
});

test('an empty group shows its message', () => {
  const out = flat(renderPanelList({
    groups: [group('popups', []), group('navigation', [])],
  }));
  assert.match(out, /haui-panel-empty/);
  assert.match(out, /drop into navigation/);
  assert.match(out, /drop into popups/);
});

test('an open panel menu renders from the model, not a local shell flag', () => {
  const closed = flat(renderPanelList({ groups: [group('navigation', [userEntry('clock_0')])] }));
  assert.doesNotMatch(closed, /haui-menu-item/);
  const opened = flat(renderPanelList({
    groups: [group('navigation', [userEntry('clock_0')])], menuKey: 'clock_0',
  }));
  assert.match(opened, /\bmenuitem\b/);
  assert.match(opened, /panel-menu:clock_0/);
});

/** The handler bound to `attribute` on the first template whose strings carry `marker`. */
function handler(template, marker, attribute) {
  if (!template?.strings) return null;
  const index = template.strings.findIndex((part) => part.endsWith(`${attribute}=`));
  if (template.strings.join('').includes(marker) && index >= 0) return template.values[index];
  for (const value of template.values.flat()) {
    const found = handler(value, marker, attribute);
    if (found) return found;
  }
  return null;
}

const dropEvent = (sourceKey, { top = 0, height = 60, clientY = 0 } = {}) => ({
  clientY,
  preventDefault() {},
  stopPropagation() {},
  dataTransfer: { getData: () => sourceKey },
  currentTarget: {
    classList: { add() {}, remove() {}, toggle() {} },
    contains: () => false,
    getBoundingClientRect: () => ({ top, height }),
  },
});

test('a drop on a row lands before or after it; a drop on the group lands at its end', () => {
  const moves = [];
  const list = renderPanelList({
    groups: [group('navigation', [userEntry('clock_0'), userEntry('clock_1')]), group('popups', [])],
    onDrop: (move) => moves.push(move),
  });
  const out = flat(list);
  assert.match(out, /data-panel-group=navigation/);
  assert.match(out, /data-panel-key=clock_0/);

  const rowDrop = handler(list, 'haui-panel-row"', '@drop');
  rowDrop(dropEvent('clock_1', { clientY: 10 }));
  rowDrop(dropEvent('clock_x', { clientY: 50 }));
  handler(list, 'haui-panel-group"', '@drop')(dropEvent('clock_0'));
  assert.deepEqual(moves, [
    { sourceKey: 'clock_1', group: 'navigation', beforeKey: 'clock_0' },
    { sourceKey: 'clock_x', group: 'navigation', beforeKey: 'clock_1' },
    { sourceKey: 'clock_0', group: 'navigation', beforeKey: null },
  ]);
});

test('groupPanels lists replaced popups, offers the rest and leaves fixed system panels out', () => {
  const panels = [
    { key: 'clock_0', show_in_navigation: true },
    { key: 'clock_1', show_in_navigation: false },
    { key: 'popup_light', type: 'light' },
  ];
  const systemPanels = [
    { key: 'popup_light', editable: true },
    { key: 'popup_cover', editable: true },
    { key: 'sys_settings', editable: false },
  ];
  const grouped = groupPanels(panels, systemPanels);
  assert.deepEqual(grouped.navigation.map((panel) => panel.key), ['clock_0']);
  assert.deepEqual(grouped.hidden.map((panel) => panel.key), ['clock_1']);
  assert.deepEqual(grouped.popups.map((entry) => entry.key), ['popup_light']);
  assert.deepEqual(grouped.defaults.map((entry) => entry.key), ['popup_cover']);
  assert.equal('system' in grouped, false);
});
