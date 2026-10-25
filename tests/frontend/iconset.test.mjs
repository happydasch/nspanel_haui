import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

/**
 * iconset.js runs on import: it registers the "haui" icon set and repairs
 * <ha-icon> elements that already resolved a "haui:" icon to the legacy
 * <iron-icon> fallback (the async add_extra_js_url import can lose the race
 * against the boot-time sidebar render). These fakes model the DOM surface it
 * touches.
 */

const HAUi_ICON = 'haui:home-assistant';

/** Fake <ha-icon> with an .icon property that logs every assignment. */
function makeIcon(icon, legacy) {
  let value = icon;
  const element = { _legacy: legacy, assignments: [] };
  Object.defineProperty(element, 'icon', {
    get: () => value,
    set: (next) => {
      element.assignments.push(next);
      value = next;
    },
  });
  return element;
}

const broken = makeIcon(HAUi_ICON, true); // lost the race: fell back to iron-icon
const healthy = makeIcon(HAUi_ICON, false); // resolved before this module ran
const otherSet = makeIcon('mdi:home', false); // not a haui icon
const brokenInShadow = makeIcon(HAUi_ICON, true); // sidebar renders in shadow DOM

const shadowHost = {
  shadowRoot: {
    querySelectorAll: (selector) =>
      selector === 'ha-icon' ? [brokenInShadow] : [],
  },
};

const eventHandlers = new Map();

globalThis.document = {
  querySelectorAll: (selector) => {
    if (selector === 'ha-icon') return [broken, healthy, otherSet];
    return [shadowHost];
  },
};
globalThis.addEventListener = (type, handler) => {
  eventHandlers.set(type, handler);
};

// Import last (dynamically, since import is hoisted): the module executes all
// of the above on load.
await import('../../custom_components/nspanel_haui/frontend/iconset.js');

test('registers the icon set on window.customIcons', async () => {
  const set = globalThis.window.customIcons['haui'];
  assert.ok(set, 'haui icon set is registered');
  const icon = await set.getIcon('home-assistant');
  assert.match(icon.path, /^M/, 'icon exposes SVG path data');
  assert.deepEqual(await set.getIcon('missing'), {});
});

test('registers the icon set on window.customIconsets', async () => {
  const icon = await globalThis.window.customIconsets['haui']('home-assistant');
  assert.match(icon.path, /^M/, 'icon exposes SVG path data');
});

test('repairs haui icons that fell back to the legacy icon', () => {
  assert.deepEqual(broken.assignments, [undefined, HAUi_ICON]);
  assert.deepEqual(brokenInShadow.assignments, [undefined, HAUi_ICON]);
  assert.deepEqual(healthy.assignments, []);
  assert.deepEqual(otherSet.assignments, []);
});

test('repairs again when a panel becomes ready', () => {
  broken.assignments.length = 0;
  const onPanelReady = eventHandlers.get('hass-panel-ready');
  assert.ok(onPanelReady, 'listens for hass-panel-ready');
  onPanelReady();
  assert.deepEqual(broken.assignments, [undefined, HAUi_ICON]);
});