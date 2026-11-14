// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { iconButton } from '../ui/button.js';
import { popover, overlayAnchor } from '../ui/popover.js';
import { notificationItem } from '../ui/notification-item.js';
import { emptyState } from '../ui/empty-state.js';

/** Render the queued notification centre as one anchored overlay surface. */
export function notificationsView({ open, notifications, onDismiss, onClose }) {
  const body = notifications.length
    ? html`<div class="haui-notification-list">${notifications.map((notification) => notificationItem(notification, onDismiss))}</div>`
    : emptyState({ message: t('No notifications queued.'), iconName: null, className: 'haui-empty-state-compact' });
  return popover({
    open,
    id: 'haui-notification-centre',
    label: t('Notifications'),
    className: 'haui-notification-popover',
    anchorKey: overlayAnchor('notification-centre'),
    // The centre keeps its own top-right placement: the bell is the anchor for
    // focus and outside-click, not for geometry.
    staticPlacement: true,
    content: html`<header class="haui-notification-header">
      <h2>${t('Notifications')}</h2>
      ${iconButton({ label: t('Close'), iconName: 'close', onClick: onClose })}
    </header>${body}`,
  });
}
