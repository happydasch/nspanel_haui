import { test } from 'node:test';
import assert from 'node:assert/strict';

import { formatRoute, parseRoute, createRouter } from '../../custom_components/nspanel_haui/frontend/app/router.js';

test('parses fleet, device, panel-list, and panel-editor hashes', () => {
  assert.deepEqual(parseRoute(''), { view: 'fleet', device: null, panel: null, panelView: 'preview' });
  assert.deepEqual(parseRoute('#/device/Living%20Room'), {
    view: 'device', device: 'Living Room', panel: null, panelView: 'preview',
  });
  assert.deepEqual(parseRoute('#/device/kitchen/panels'), {
    view: 'device', device: 'kitchen', panel: null, panelView: 'panels',
  });
  assert.deepEqual(parseRoute('#/device/kitchen/panel/popup_notify'), {
    view: 'device', device: 'kitchen', panel: 'popup_notify', panelView: 'panels',
  });
});

test('canonical routes encode names and round-trip path separators', () => {
  const route = { view: 'device', device: 'Ground/Floor', panel: 'a/b', panelView: 'panels' };
  const hash = formatRoute(route);
  assert.equal(hash, '#/device/Ground%2FFloor/panel/a%2Fb');
  assert.deepEqual(parseRoute(hash), route);
});

test('malformed and unknown route shapes resolve to fleet', () => {
  for (const hash of ['#/', '#/other/x', '#/device/', '#/device/x/panel/', '#/device/%ZZ']) {
    assert.deepEqual(parseRoute(hash), { view: 'fleet', device: null, panel: null, panelView: 'preview' });
  }
});

test('router syncs URL navigation and removes history listeners on destroy', () => {
  const listeners = new Map();
  const calls = [];
  const win = {
    location: { hash: '#/', pathname: '/nspanel-haui', search: '?x=1' },
    history: {
      pushState: (_state, _title, url) => { calls.push(['push', url]); win.location.hash = url.slice(url.indexOf('#')); },
      replaceState: (_state, _title, url) => { calls.push(['replace', url]); win.location.hash = url.slice(url.indexOf('#')); },
    },
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name, callback) => { if (listeners.get(name) === callback) listeners.delete(name); },
  };
  const routes = [];
  const store = { actions: { setRoute: (route) => routes.push(route) } };
  const router = createRouter(store, win);

  router.navigate({ view: 'device', device: 'office', panel: null, panelView: 'preview' });
  router.navigate({ view: 'device', device: 'office', panel: null, panelView: 'panels' }, { replace: true });
  listeners.get('popstate')();
  assert.deepEqual(calls.map(([kind]) => kind), ['push', 'replace']);
  assert.deepEqual(routes.at(-1), { view: 'device', device: 'office', panel: null, panelView: 'panels' });

  router.destroy();
  assert.equal(listeners.size, 0);
});
