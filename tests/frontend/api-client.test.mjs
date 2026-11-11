import { test } from 'node:test';
import assert from 'node:assert/strict';

import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

function hass({ language = 'en', fetchWithAuth, connection } = {}) {
  return {
    language,
    locale: { language },
    fetchWithAuth: fetchWithAuth || (async () => jsonResponse({})),
    callWS: async () => [],
    connection,
  };
}

test('entries.list keeps only the NSPanel HAUI config entries', async () => {
  const hassObject = hass({
    fetchWithAuth: async () => jsonResponse({}),
  });
  const api = createApiClient(() => hassObject);
  hassObject.callWS = async (message) => {
    assert.equal(message.type, 'config_entries/get');
    return [
      { entry_id: 'a', domain: 'nspanel_haui' },
      { entry_id: 'b', domain: 'other' },
    ];
  };

  assert.deepEqual(await api.entries.list(), [{ entry_id: 'a', domain: 'nspanel_haui' }]);
});

test('a server error message is surfaced and a non-JSON error falls back', async () => {
  const api = createApiClient(() => hass({
    fetchWithAuth: async () => jsonResponse({ message: 'Invalid panel config' }, 400),
  }));
  await assert.rejects(api.panels.save('entry1', { devices: {} }), /Invalid panel config/);

  const plain = createApiClient(() => hass({
    fetchWithAuth: async () => ({
      ok: false,
      status: 500,
      json: async () => { throw new Error('not json'); },
    }),
  }));
  await assert.rejects(plain.panels.load('entry1', 'en'), /HTTP 500/);
});

test('panels and status requests use the documented routes and query parameters', async () => {
  const seen = [];
  const api = createApiClient(() => hass({
    fetchWithAuth: async (url, options = {}) => {
      seen.push([options.method || 'GET', url]);
      if (url.includes('/status/')) return jsonResponse({ devices: { kitchen: {} } });
      return jsonResponse({ devices: {} });
    },
  }));

  await api.panels.load('entry1', 'de_DE');
  await api.panels.save('entry1', { devices: {} });
  await api.status.getAll('entry1');
  await api.status.get('entry1', 'kitchen');
  await api.devices.remove('entry1', 'kitchen');

  assert.deepEqual(seen, [
    ['GET', '/api/nspanel_haui/panels/entry1?language=de_DE'],
    ['POST', '/api/nspanel_haui/panels/entry1'],
    ['GET', '/api/nspanel_haui/status/entry1'],
    ['GET', '/api/nspanel_haui/status/entry1?device=kitchen'],
    ['DELETE', '/api/nspanel_haui/devices/entry1?name=kitchen'],
  ]);
});

test('status.getAll rejects an unfiltered response without a device map', async () => {
  const api = createApiClient(() => hass({
    fetchWithAuth: async () => jsonResponse({ connected: true }),
  }));
  await assert.rejects(api.status.getAll('entry1'), /Invalid device status response/);
});

test('notification dismissal encodes the device and id', async () => {
  let requested;
  const api = createApiClient(() => hass({
    fetchWithAuth: async (url) => { requested = url; return jsonResponse({ status: 'ok' }); },
  }));

  await api.notifications.dismiss('entry1', 'kitchen', '42');
  assert.equal(requested, '/api/nspanel_haui/notifications/entry1?device=kitchen&id=42');
});

test('a card render goes over the websocket with the panel or its key', async () => {
  const sent = [];
  const api = createApiClient(() => hass({
    connection: {
      sendMessagePromise: async (message) => { sent.push(message); return { page: 9 }; },
    },
  }));

  await api.preview.render('entry1', 'kitchen', { panel: { type: 'grid' } });
  await api.preview.render('entry1', 'kitchen', { key: 'popup_notify' });

  assert.deepEqual(sent, [
    { type: 'nspanel_haui/virtual_panel/render', entry_id: 'entry1', device: 'kitchen', panel: { type: 'grid' } },
    { type: 'nspanel_haui/virtual_panel/render', entry_id: 'entry1', device: 'kitchen', key: 'popup_notify' },
  ]);
});

test('YAML export returns the text and import posts it as YAML', async () => {
  const seen = [];
  const api = createApiClient(() => hass({
    fetchWithAuth: async (url, options = {}) => {
      seen.push([options.method || 'GET', url, options.body]);
      return {
        ok: true,
        status: 200,
        text: async () => 'views: []',
        json: async () => ({ device: 'kitchen' }),
      };
    },
  }));

  assert.equal(await api.yaml.export('entry1', 'kitchen'), 'views: []');
  await api.yaml.import('entry1', 'kitchen', 'views: []');
  assert.deepEqual(seen, [
    ['GET', '/api/nspanel_haui/yaml/entry1?device=kitchen', undefined],
    ['POST', '/api/nspanel_haui/yaml/entry1?device=kitchen', 'views: []'],
  ]);
});
