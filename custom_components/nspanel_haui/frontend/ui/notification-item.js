// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { iconButton } from './button.js';
import { icon } from './icon.js';

/** Render one queued notification without owning its state or dismissal API. */
export function notificationItem(notification, onDismiss) {
  return html`<article class="haui-notification-item">
    <span class="haui-notification-icon" aria-hidden="true">
      ${notification.icon ? html`<ha-icon icon=${notification.icon}></ha-icon>` : icon('notification')}
    </span>
    <div class="haui-notification-content">
      <strong>${notification.title}</strong>
      ${notification.message ? html`<p>${notification.message}</p>` : ''}
      <div class="haui-notification-meta">
        <span>${notification.device}</span>
        ${notification.persistent ? html`<span>${t('Persistent')}</span>` : ''}
      </div>
    </div>
    ${iconButton({ label: t('Dismiss'), iconName: 'close', onClick: () => onDismiss(notification) })}
  </article>`;
}
