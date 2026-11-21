import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  idlePanelConfig,
  idlePanelKeys,
  panelExists,
  resolveHomeKey,
  resolveIdleKeys,
  resolvePanelRoles,
  unknownPanelRef,
} from '../../custom_components/nspanel_haui/frontend/panel-roles.js';

const PANELS = [
  { key: 'lights', type: 'grid', title: 'Lights', show_in_navigation: true },
  { key: 'clock', type: 'grid', title: 'Clock', show_in_navigation: false },
  { key: 'weather', type: 'light', title: '', show_in_navigation: true },
];

test('the unified idle list composes and splits the existing string settings in order', () => {
  assert.deepEqual(idlePanelKeys('clock', 'weather, gone, clock'), ['clock', 'weather', 'gone']);
  assert.deepEqual(idlePanelConfig(['weather', 'gone', 'weather']), {
    idle_panel: 'weather', idle_panel_extra: 'gone',
  });
  assert.deepEqual(idlePanelConfig([]), { idle_panel: '', idle_panel_extra: '' });
});

test('a reference names a panel of the device or a system panel, else it is stale', () => {
  assert.equal(panelExists('lights', PANELS), true);
  assert.equal(panelExists('popup_notify', PANELS, [{ key: 'popup_notify' }]), true);
  assert.equal(panelExists('gone', PANELS), false);
  assert.equal(panelExists('', PANELS), false);
});

test('a stale reference keeps its real key under an unknown-key marker', () => {
  assert.equal(unknownPanelRef('gone'), 'Unknown key "gone"');
});

test('Home uses the configured panel, else the first navigation panel', () => {
  assert.equal(resolveHomeKey(PANELS, { home_panel: 'clock' }), 'clock');
  assert.equal(resolveHomeKey(PANELS, { home_panel: '' }), 'lights');
  // A hidden panel never becomes the fallback, and a device without panels has none.
  assert.equal(resolveHomeKey([{ key: 'clock', show_in_navigation: false }], {}), '');
  assert.equal(resolveHomeKey([], { home_panel: 'gone' }), '');
});

test('a popup override is not a home fallback', () => {
  const panels = [{ key: 'popup_light', type: 'light', show_in_navigation: true }];
  assert.equal(resolveHomeKey(panels, {}, [{ key: 'popup_light' }]), '');
});

test('a configured panel the device no longer has is not the home panel', () => {
  assert.equal(resolveHomeKey(PANELS, { home_panel: 'gone' }), 'lights');
  // A system page is a panel too, so naming one is not a stale reference.
  assert.equal(
    resolveHomeKey(PANELS, { home_panel: 'popup_notify' }, [{ key: 'popup_notify' }]),
    'popup_notify',
  );
});

test('the idle carousel is the configured keys that name a panel, in play order', () => {
  assert.deepEqual(
    resolveIdleKeys(PANELS, { idle_panel: 'gone', idle_panel_extra: 'weather, clock, gone2' }),
    ['weather', 'clock'],
  );
  // Only stale keys: the device plays nothing, so nothing is set.
  assert.deepEqual(resolveIdleKeys(PANELS, { idle_panel: 'gone' }), []);
  assert.deepEqual(resolveIdleKeys([], { idle_panel: 'clock' }), []);
});

test('both roles split their keys into the ones that name a panel and the ones that do not', () => {
  const { home, idle } = resolvePanelRoles(
    PANELS,
    { home_panel: 'gone', idle_panel: 'gone2', idle_panel_extra: 'weather, clock' },
  );
  // Home is the same kind of setting as the idle list: a stale key is reported,
  // never resolved to another panel.
  assert.deepEqual(home, { keys: [], missing: ['gone'], fallback: 'lights' });
  assert.deepEqual(idle, { keys: ['weather', 'clock'], missing: ['gone2'], fallback: '' });

  // While nothing is configured, Home names the panel the hub opens instead.
  assert.deepEqual(
    resolvePanelRoles(PANELS, {}).home,
    { keys: [], missing: [], fallback: 'lights' },
  );
});
