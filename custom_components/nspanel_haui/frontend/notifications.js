import { t } from './localize.js';

export const NOTIFICATION_EVENT = 'nspanel_haui.notification';

export function subscribeNotifications(host) {
  const connection = host.hass?.connection;
  if (!connection || host.__notificationConnection === connection) return;
  stopNotificationSubscription(host);
  host.__notificationConnection = connection;
  connection.subscribeEvents((event) => {
    const notification = event?.data;
    if (!notification?.id || !notification.device) return;
    const current = host._notifications || [];
    const key = `${notification.device}:${notification.id}`;
    const remaining = current.filter((item) => `${item.device}:${item.id}` !== key);
    host._notifications = notification.state === 'removed'
      ? remaining
      : [...remaining, notification];
  }, NOTIFICATION_EVENT).then((unsubscribe) => {
    if (host.__notificationConnection !== connection) unsubscribe();
    else host.__notificationUnsubscribe = unsubscribe;
  }).catch((error) => {
    console.error('Failed to subscribe to NSPanel HAUI notifications:', error);
  });
}

export function stopNotificationSubscription(host) {
  host.__notificationUnsubscribe?.();
  host.__notificationUnsubscribe = null;
  host.__notificationConnection = null;
}

export async function loadNotifications(host) {
  if (!host.entryId || !host.hass) return;
  try {
    const response = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/notifications/${host.entryId}`
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    host._notifications = await response.json();
  } catch (error) {
    console.error('Failed to load NSPanel HAUI notifications:', error);
    host._showToast(t('Failed to load notifications'), 'error');
  }
}

export async function dismissNotification(host, notification) {
  const query = new URLSearchParams({ device: notification.device, id: notification.id });
  try {
    const response = await host.hass.fetchWithAuth(
      `/api/nspanel_haui/notifications/${host.entryId}?${query}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    host._notifications = host._notifications.filter((item) =>
      item.device !== notification.device || item.id !== notification.id
    );
  } catch (error) {
    console.error('Failed to dismiss NSPanel HAUI notification:', error);
    host._showToast(t('Failed to dismiss notification'), 'error');
  }
}
