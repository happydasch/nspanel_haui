import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderPanelTable } from '../../custom_components/nspanel_haui/frontend/panel-table.js';
import { renderPanelGrid } from '../../custom_components/nspanel_haui/frontend/panel-grid.js';
import { makeHost } from './fake-host.mjs';

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

function hostFor(panels, extra = {}) {
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => { throw new Error('no fetch'); });
  host._panelTypes = [{ type_key: 'clock', label: 'Clock' }];
  host.__navPanelsOpen = true;
  host.__hiddenPanelsOpen = false;
  return Object.assign(host, extra);
}

const summaries = (out) => [...out.matchAll(/<summary class="group-title">([^<]*)<\/summary>/g)].map((m) => m[1]);
const open = (out) => [...out.matchAll(/<details class="panel-group" \?open=(\S*)/g)].map((m) => m[1]);

for (const [name, render] of [['table', renderPanelTable], ['grid', renderPanelGrid]]) {
  test(`${name} view lists navigation and non-navigation groups with counts`, () => {
    const host = hostFor([
      { type: 'clock', key: 'clock_0' },
      { type: 'clock', key: 'clock_1', show_in_navigation: false },
      { type: 'clock', key: 'clock_2' },
    ]);
    const out = flat(render(host));
    assert.deepEqual(summaries(out), ['Navigation (2 panels)', 'Non-Navigation (1 panels)']);
    assert.equal(open(out).length, 2);
  });

  test(`${name} view shows empty and no-device states`, () => {
    assert.match(flat(render(hostFor([]))), /No panels configured yet\./);
    const none = hostFor([{ type: 'clock', key: 'a' }], { _selectedDevice: null });
    assert.match(flat(render(none)), /Select a device to edit its panels\./);
    const empty = hostFor([]);
    empty._panels = { devices: {} };
    empty._selectedDevice = null;
    assert.match(flat(render(empty)), /No devices found/);
  });

  test(`${name} view persists the collapse state of a group`, () => {
    const host = hostFor([{ type: 'clock', key: 'a' }]);
    const stored = [];
    globalThis.localStorage = { setItem: (k, v) => stored.push([k, v]) };
    try {
      const tpl = render(host);
      const groups = tpl.values.find((v) => v && v.values && v.values.some((x) => typeof x === 'function'));
      const toggle = groups.values.find((x) => typeof x === 'function');
      toggle({ target: { open: true } });
    } finally {
      delete globalThis.localStorage;
    }
    assert.equal(host.__navPanelsOpen, true);
    assert.deepEqual(stored, [['haui_navPanelsOpen', true]]);
  });
}
