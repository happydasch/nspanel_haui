import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

// The queue lives in the store; the removed frontend/notifications.js wrapper
// only forwarded these calls.
const subscribeNotifications = (host) => host.store.actions.subscribeNotifications();
const stopNotificationSubscription = (host) => host.store.actions.stopNotifications();
const loadNotifications = async (host) => { await host.store.actions.loadNotifications(); };
const dismissNotification = async (host, notification) => {
  if (!notification) return;
  await host.store.actions.dismissNotification(notification.device, notification.id);
};
import { jsonResponse, makeHost } from './fake-host.mjs';

const panels = { devices: { kitchen: { config: {}, panels: [] } } };

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  if (Array.isArray(value.strings) && Array.isArray(value.values)) {
    return value.strings.map((part, index) => `${part}${flatten(value.values[index] ?? '')}`).join('');
  }
  return '';
}

test('notification centre renders a dismissible popover and an empty state', () => {
  const closed = notificationsView({ open: false, notifications: [], onDismiss() {}, onClose() {} });
  assert.equal(typeof closed, 'symbol');
  const item = { id: '42', device: 'kitchen', title: 'Doorbell', message: 'Front door', persistent: true };
  const opened = flatten(notificationsView({ open: true, notifications: [item], onDismiss() {}, onClose() {} }));
  assert.match(opened, /haui-notification-popover/);
  assert.match(opened, /Doorbell/);
  assert.match(opened, /Front door/);
  assert.match(opened, /Persistent/);
  assert.match(flatten(notificationsView({ open: true, notifications: [], onDismiss() {}, onClose() {} })), /No notifications queued/);
});

import { notificationsView } from '../../custom_components/nspanel_haui/frontend/views/notifications.js';


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
  host.store.setState((state) => ({ ...state, notifications: [notification] }));

  await dismissNotification(host, notification);

  assert.deepEqual(host._notifications, []);
  assert.equal(host.urls[0], '/api/nspanel_haui/notifications/entry1?device=kitchen&id=42');
});

test('live notification events add and remove inbox entries', async () => {
  let callback;
  let unsubscribed = false;
  const host = makeHost(panels, () => { throw new Error('no fetch'); });
  host.hass.connection = {
    subscribeEvents(handler, eventType) {
      assert.equal(eventType, 'nspanel_haui.notification');
      callback = handler;
      return Promise.resolve(() => { unsubscribed = true; });
    },
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
