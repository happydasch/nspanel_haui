/**
 * NSPanel HAUI - notification queue helpers.
 *
 * The queue and its live subscription live in the store. These wrappers keep
 * the existing call sites (and the editor's `_` methods) working.
 */
export const NOTIFICATION_EVENT = 'nspanel_haui.notification';

export function subscribeNotifications(host) {
  host.store.actions.subscribeNotifications();
}

export function stopNotificationSubscription(host) {
  host.store.actions.stopNotifications();
}

export async function loadNotifications(host) {
  await host.store.actions.loadNotifications();
}

export async function dismissNotification(host, notification) {
  if (!notification) return;
  await host.store.actions.dismissNotification(notification.device, notification.id);
}
