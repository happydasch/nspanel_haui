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
  host._panelTypes = [{ type_key: 'grid', label: 'Grid', icon: 'mdi:view-grid' }];
  host._deviceConfig = { display_model: displayModel };
  host.__navPanelsOpen = true;
  host.__hiddenPanelsOpen = false;
  return host;
}

/** The simulated header bar of the first card (between the header and the screen markup). */
const headerOf = (out) => out.slice(out.indexOf('pg-card-preview-header'), out.indexOf('pg-card-preview-screen'));

test('the display model decides whether a device uses the portrait layout', () => {
  assert.equal(isPortraitModel('us'), true);
  assert.equal(isPortraitModel('US'), true);
  assert.equal(isPortraitModel('eu'), false);
  assert.equal(isPortraitModel(undefined), false);
});

test('portrait devices get the 320x480 frame with the function buttons in a bottom bar', () => {
  const out = flat(renderPanelGrid(hostFor('us')));
  assert.match(out, /pg-card-preview--portrait/);
  assert.doesNotMatch(headerOf(out), /pg-sim-btn-group/);
  const footer = out.slice(out.indexOf('pg-card-preview-footer'));
  assert.match(footer, /pg-sim-btn-group-left[\s\S]*mdi:chevron-left/);
  assert.match(footer, /pg-sim-btn-group-right[\s\S]*mdi:chevron-right/);
});

test('landscape devices keep the function buttons in the header', () => {
  const out = flat(renderPanelGrid(hostFor('eu')));
  assert.doesNotMatch(out, /pg-card-preview--portrait|pg-card-preview-footer/);
  assert.match(headerOf(out), /pg-sim-btn-group-left[\s\S]*mdi:chevron-left/);
});

test('system panel cards follow the device display model too', () => {
  const sp = { type: 'system', key: 'sys_system', label: 'System', has_header: true };
  const portrait = flat(renderSystemPanelCard(hostFor('us'), sp));
  assert.match(portrait, /pg-card-preview--portrait[\s\S]*pg-card-preview-footer/);
  const landscape = flat(renderSystemPanelCard(hostFor('eu'), sp));
  assert.doesNotMatch(landscape, /pg-card-preview--portrait/);
});
