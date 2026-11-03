import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { isPortraitModel } from '../../custom_components/nspanel_haui/frontend/constants.js';
import { renderPanelGrid } from '../../custom_components/nspanel_haui/frontend/panel-grid.js';
import { renderSystemPanelCard } from '../../custom_components/nspanel_haui/frontend/panel-sys-grid.js';
import { makeHost } from './fake-host.mjs';

/** Flatten a Lit TemplateResult tree to text, with functions shown as [fn]. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  if (typeof v === 'function') return '[fn]';
  return v == null ? '' : String(v);
}

function hostFor(displayModel, panels = [{ type: 'grid', key: 'grid_0', items: [] }]) {
  const host = makeHost({ devices: { kitchen: { config: {}, panels } } }, () => { throw new Error('no fetch'); });
  host._panelTypes = [{ type_key: 'grid', label: 'Grid', icon: 'mdi:view-grid', page_id: 9 }];
  host._deviceConfig = { display_model: displayModel };
  host.__navPanelsOpen = true;
  host.__hiddenPanelsOpen = false;
  return host;
}

test('the display model decides whether a device uses the portrait layout', () => {
  assert.equal(isPortraitModel('us'), true);
  assert.equal(isPortraitModel('US'), true);
  assert.equal(isPortraitModel('eu'), false);
  assert.equal(isPortraitModel(undefined), false);
});

test('portrait devices mount the simulator frame in portrait', () => {
  const out = flat(renderPanelGrid(hostFor('us')));
  assert.match(out, /pg-card-preview--portrait/);
  assert.match(out, /nspanel-simulator-frame[\s\S]*\.portrait=true/);
});

test('landscape devices mount the simulator frame without portrait', () => {
  const out = flat(renderPanelGrid(hostFor('eu')));
  assert.doesNotMatch(out, /pg-card-preview--portrait/);
  assert.match(out, /nspanel-simulator-frame/);
});

test('the simulator preview draws no duplicate fake header/footer chrome', () => {
  const out = flat(renderPanelGrid(hostFor('eu')));
  assert.doesNotMatch(out, /pg-card-preview-header|pg-card-preview-footer|pg-card-preview--with-header/);
});

test('system panel cards mount the simulator frame too', () => {
  const sp = { type: 'system', key: 'sys_system', label: 'System', has_header: true, page_id: 0 };
  const portrait = flat(renderSystemPanelCard(hostFor('us'), sp));
  assert.match(portrait, /pg-card-preview--portrait[\s\S]*nspanel-simulator-frame/);
  const landscape = flat(renderSystemPanelCard(hostFor('eu'), sp));
  assert.match(landscape, /nspanel-simulator-frame/);
});
