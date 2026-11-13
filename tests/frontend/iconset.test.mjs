import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { flush } from './support/render.mjs';

const HAUi_ICON = 'haui:home-assistant';

function makeIcon(icon, legacy) {
  const element = document.createElement('ha-icon');
  let value = icon;
  element.assignments = [];
  element._legacy = legacy;
  Object.defineProperty(element, 'icon', {
    configurable: true,
    get: () => value,
    set: (next) => {
      element.assignments.push(next);
      value = next;
    },
  });
  return element;
}

const broken = makeIcon(HAUi_ICON, true);
const healthy = makeIcon(HAUi_ICON, false);
const otherSet = makeIcon('mdi:home', false);
const shadowHost = document.createElement('div');
const shadowRoot = shadowHost.attachShadow({ mode: 'open' });
const brokenInShadow = makeIcon(HAUi_ICON, true);
document.body.append(broken, healthy, otherSet, shadowHost);
shadowRoot.append(brokenInShadow);

await import('../../custom_components/nspanel_haui/frontend/iconset.js');

test('registers the custom icon set', async () => {
  const set = window.customIcons.haui;
  assert.ok(set);
  assert.match((await set.getIcon('home-assistant')).path, /^M/);
  assert.deepEqual(await set.getIcon('missing'), {});
  assert.match((await window.customIconsets.haui('home-assistant')).path, /^M/);
});

test('repairs existing legacy icons in the document and shadow roots', () => {
  assert.deepEqual(broken.assignments, [undefined, HAUi_ICON]);
  assert.deepEqual(brokenInShadow.assignments, [undefined, HAUi_ICON]);
  assert.deepEqual(healthy.assignments, []);
  assert.deepEqual(otherSet.assignments, []);
});

test('repairs icons added later to the document and shadow roots', async () => {
  const late = makeIcon(HAUi_ICON, true);
  const lateInShadow = makeIcon(HAUi_ICON, true);
  document.body.append(late);
  shadowRoot.append(lateInShadow);
  await flush();
  assert.deepEqual(late.assignments, [undefined, HAUi_ICON]);
  assert.deepEqual(lateInShadow.assignments, [undefined, HAUi_ICON]);
});

test('repairs legacy icons when Home Assistant announces that its panel is ready', () => {
  broken.assignments.length = 0;
  broken._legacy = true;
  window.dispatchEvent(new Event('hass-panel-ready'));
  assert.deepEqual(broken.assignments, [undefined, HAUi_ICON]);
});
