import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  dismissNotification,
  loadNotifications,
  stopNotificationSubscription,
  subscribeNotifications,
} from '../../custom_components/nspanel_haui/frontend/notifications.js';
import { jsonResponse, makeHost } from './fake-host.mjs';

const panels = { devices: { kitchen: { config: {}, panels: [] } } };

test('the notifications inbox dialog is registered', async () => {
  const { NotificationsDialog } = await import(
    '../../custom_components/nspanel_haui/frontend/dialogs/notifications.js'
  );
  assert.equal(NotificationsDialog.name, 'NotificationsDialog');
  assert.equal(customElements.get('nspanel-dialog-notifications'), NotificationsDialog);
});

test('the notification inbox loads the current server queue', async () => {
  const notification = { id: '42', device: 'kitchen', title: 'Doorbell' };
  const host = makeHost(panels, (method, path) => {
    assert.equal(method, 'GET');
    assert.equal(path, '/api/nspanel_haui/notifications/entry1');
    return jsonResponse([notification]);
  });

  await loadNotifications(host);

  assert.deepEqual(host._notifications, [notification]);
});

test('a dismissed notification is removed through the backend API', async () => {
  const notification = { id: '42', device: 'kitchen', title: 'Doorbell' };
  const host = makeHost(panels, (method, path, options) => {
    assert.equal(method, 'DELETE');
    assert.equal(path, '/api/nspanel_haui/notifications/entry1');
    assert.equal(options.method, 'DELETE');
    return jsonResponse({ status: 'ok' });
  });
  host._notifications = [notification];

  await dismissNotification(host, notification);

  assert.deepEqual(host._notifications, []);
  assert.equal(host.urls[0], '/api/nspanel_haui/notifications/entry1?device=kitchen&id=42');
});

test('live notification events add and remove inbox entries', async () => {
  let callback;
  let unsubscribed = false;
  const host = {
    hass: {
      connection: {
        subscribeEvents(handler, eventType) {
          assert.equal(eventType, 'nspanel_haui.notification');
          callback = handler;
          return Promise.resolve(() => { unsubscribed = true; });
        },
      },
    },
    _notifications: [],
  };

  subscribeNotifications(host);
  await Promise.resolve();
  callback({ data: { id: '42', device: 'kitchen', state: 'added', title: 'Doorbell' } });
  assert.equal(host._notifications.length, 1);
  callback({ data: { id: '42', device: 'kitchen', state: 'added', title: 'Updated' } });
  assert.equal(host._notifications.length, 1);
  assert.equal(host._notifications[0].title, 'Updated');
  callback({ data: { id: '42', device: 'kitchen', state: 'removed' } });
  assert.deepEqual(host._notifications, []);

  stopNotificationSubscription(host);
  assert.equal(unsubscribed, true);
});
