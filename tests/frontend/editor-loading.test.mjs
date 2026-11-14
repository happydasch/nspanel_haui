import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { createStore } from '../../custom_components/nspanel_haui/frontend/store/store.js';
import { t } from '../../custom_components/nspanel_haui/frontend/localize.js';
import { jsonResponse } from './fake-host.mjs';

const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

/**
 * A fake backend: config_entries/get and /panel_types answer with `entries` and
 * `panelTypes` (a promise that never settles when omitted), translations with
 * `translations[lang]`. Every request is counted in `requests`.
 */
function backend({ entries, panelTypes, translations = {} } = {}) {
  const requests = [];
  const never = new Promise(() => {});
  return {
    requests,
    hass(language = 'en') {
      return {
        language,
        async callWS(msg) {
          requests.push(msg.type);
          return entries ?? never;
        },
        async fetchWithAuth(url) {
          const path = url.split('?')[0];
          requests.push(path);
          if (path === '/api/nspanel_haui/panel_types') return panelTypes ? panelTypes(url) : never;
          if (path === '/api/nspanel_haui/panel_templates') return jsonResponse([]);
          const lang = path.match(/translations\/(\w+)/)?.[1];
          if (lang) return jsonResponse(translations[lang] ?? {});
          throw new Error(`unexpected ${url}`);
        },
      };
    },
  };
}

/** The editor element without Lit's constructor, which needs a real DOM. */
function editor() {
  const ed = document.createElement('nspanel-haui-editor');
  Object.assign(ed, {
    entryId: null,
    _loading: true,
    _panelTypes: [],
    toasts: [],
    renders: 0,
    requestUpdate() { this.renders++; },
    _showToast(msg, kind) { this.toasts.push([kind, msg]); },
  });
  ed.api = createApiClient(() => ed.hass);
  ed._store = createStore({
    client: ed.api,
    storage: { read: (key, fallback) => fallback, write() {} },
    onToast: (message, kind) => ed.toasts.push([kind, message]),
  });
  ed._store.subscribe(() => ed._syncFromStore());
  ed._syncFromStore();
  return ed;
}

function pushHass(ed, hass) {
  ed.hass = hass;
  ed.updated(new Map([['hass', undefined]]));
}

test('a newer copy of the entry reloads the page instead of defining the editor again', async () => {
  // HA imports the entry again from a new URL after a restart that changed the frontend.
  const original = Object.getOwnPropertyDescriptor(globalThis, 'location');
  let reloads = 0;
  Object.defineProperty(globalThis, 'location', {
    configurable: true, value: { reload: () => { reloads += 1; } },
  });
  try {
    let loaded = false;
    import('../../custom_components/nspanel_haui/frontend/haui-editor.js?digest=newer')
      .then(() => { loaded = true; });
    await settle();
    assert.equal(reloads, 1);
    assert.equal(loaded, false);
    assert.equal(customElements.get('nspanel-haui-editor'), NSPanelEditor);
  } finally {
    if (original) Object.defineProperty(globalThis, 'location', original);
    else delete globalThis.location;
  }
});

test('loads still pending are not requested again on each hass update', async (t) => {
  // The backend never answers; the client's request timeout would keep the
  // process alive for its full duration, so run this test on mock timers.
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const be = backend();
  const ed = editor();

  for (let i = 0; i < 3; i++) pushHass(ed, be.hass());
  await settle();

  assert.equal(be.requests.filter((r) => r === 'config_entries/get').length, 1);
  assert.equal(be.requests.filter((r) => r === '/api/nspanel_haui/panel_types').length, 1);
});

test('a failed panel-type load is reported once, not retried on every hass update', async () => {
  const be = backend({ entries: [], panelTypes: () => jsonResponse({}, 500) });
  const ed = editor();

  pushHass(ed, be.hass());
  await settle();
  pushHass(ed, be.hass());
  pushHass(ed, be.hass());
  await settle();

  assert.equal(be.requests.filter((r) => r === '/api/nspanel_haui/panel_types').length, 1);
  assert.deepEqual(ed.toasts.map(([kind]) => kind), ['error']);
});

test('an unreadable integration list is reported as an error, not as "none configured"', async () => {
  const ed = editor();
  ed.hass = {
    language: 'en',
    async callWS() { throw new Error('Connection lost'); },
  };

  await ed._loadEntries();

  assert.equal(ed._entriesError, 'Connection lost');
  assert.equal(ed._loading, false);
  assert.deepEqual(ed.toasts, []);
});

test('a language change reloads translations and panel types and re-renders', async () => {
  const be = backend({
    entries: [],
    panelTypes: (url) => jsonResponse([{ type_key: 'clock', label: url.includes('language=de') ? 'Uhr' : 'Clock' }]),
    translations: { de: { Cancel: 'Abbrechen' } },
  });
  const ed = editor();
  pushHass(ed, be.hass('en'));
  await settle();

  pushHass(ed, be.hass('de'));
  const rendersBefore = ed.renders;
  await settle();

  assert.equal(t('Cancel'), 'Abbrechen');
  assert.equal(ed._panelTypes[0].label, 'Uhr');
  assert.ok(ed.renders > rendersBefore, 'the editor re-renders once translations arrive');
});
