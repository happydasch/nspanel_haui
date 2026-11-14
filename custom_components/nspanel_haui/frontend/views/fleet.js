// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { deviceCard } from '../ui/device-card.js';
import { deviceRow } from '../ui/device-row.js';
import { fleetBar, fleetSummary } from '../ui/fleet-summary.js';
import { eventList, latestEvents } from '../ui/event-list.js';
import { emptyState } from '../ui/empty-state.js';
import { button, iconButton } from '../ui/button.js';
import { sectionHeading } from '../ui/surface.js';
import { menuItem, menuSeparator, overlayAnchor, popover } from '../ui/popover.js';
import { hasUpdateAvailable } from '../device-status.js';
import { rolloutCard } from '../ui/rollout-card.js';

/** Where the carousel sits between its scroll extents. */
export function carouselEdgesFrom(carousel) {
  const max = Math.max(0, (carousel?.scrollWidth || 0) - (carousel?.clientWidth || 0));
  const left = Math.max(0, carousel?.scrollLeft || 0);
  return { atStart: left <= 1, atEnd: left >= max - 1 };
}

/**
 * Build Fleet from prepared store data; all changes are sent back as callbacks.
 * @param {{ devices: any[], events: any[], version: string, statusPending?: boolean,
 *   carousel?: {atStart: boolean, atEnd: boolean}, menu?: any,
 *   onCarouselScroll?: (edges: {atStart: boolean, atEnd: boolean}) => void,
 *   onMenu?: ((name: string, anchorKey: string) => void)|null, onCloseMenu?: () => void,
 *   onOpenDevice: (name: string) => void,
 *   onReorderDevices: (order: string[]) => void,
 *   discovered?: any[], scanning?: boolean, scanError?: string, statusError?: string|null, onScan?: () => void,
 *   onAddDevices?: (devices: any[]) => void,
 *   installable?: number, onInstallUpdates?: () => void,
 *   rollout?: any, onCancelRollout?: (device: string|null) => void,
 *   onOpenLogs?: () => void }} data
 */
export function renderFleetView(data) {
  const online = data.devices.filter(({ status }) => status?.connected === true).length;
  const updates = data.devices.filter(({ status }) => hasUpdateAvailable(status?.update)).length;
  const reorder = (fromName, targetName) => {
    if (!fromName || fromName === targetName) return;
    const order = data.devices.map(({ name }) => name);
    const from = order.indexOf(fromName);
    const target = order.indexOf(targetName);
    if (from < 0 || target < 0) return;
    order.splice(target, 0, order.splice(from, 1)[0]);
    data.onReorderDevices(order);
  };
  const dragActions = (name, selector) => ({
    onDragStart: (event) => {
      event.dataTransfer?.setData('text/plain', name);
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
      event.currentTarget.closest(selector)?.classList.add('is-dragging');
    },
    onDragEnd: (event) => event.currentTarget.closest(selector)?.classList.remove('is-dragging'),
    // The whole card or row takes the drop, not only its grip.
    onDragOver: (event) => {
      event.preventDefault();
      event.currentTarget.classList.add('is-drop-target');
    },
    onDragLeave: (event) => {
      if (event.currentTarget.contains(event.relatedTarget)) return;
      event.currentTarget.classList.remove('is-drop-target');
    },
    onDrop: (event) => {
      event.preventDefault();
      event.currentTarget.classList.remove('is-drop-target');
      reorder(event.dataTransfer?.getData('text/plain'), name);
    },
  });
  const carouselEdges = data.carousel || { atStart: true, atEnd: false };
  const atStart = carouselEdges.atStart !== false;
  const atEnd = carouselEdges.atEnd === true;
  const scrollCarousel = (event, direction) => {
    const carousel = event.currentTarget.parentElement.querySelector('.haui-fleet-carousel');
    carousel?.scrollBy({ left: direction * Math.max(240, carousel.clientWidth * 0.8), behavior: 'smooth' });
  };
  const onCarouselScroll = (event) => data.onCarouselScroll?.(carouselEdgesFrom(event.currentTarget));
  const menu = data.menu || null;
  const discovered = data.discovered || [];
  const cards = data.devices.map((item) => deviceCard({
    ...item,
    onSelect: () => data.onOpenDevice(item.name),
    ...dragActions(item.name, '.haui-device-card'),
  }));
  const deviceMenu = menu?.key
    ? popover({
      open: true,
      id: `haui-device-menu-${menu.key}`,
      label: menu.label,
      role: 'menu',
      className: 'haui-device-menu',
      anchorKey: menu.anchorKey,
      content: (menu.items || []).map((entry) => (entry === 'divider'
        ? menuSeparator()
        : menuItem({
          label: entry.label,
          iconName: entry.iconName,
          danger: entry.danger === true,
          onSelect: () => { data.onCloseMenu?.(); entry.onSelect(); },
        }))),
    })
    : nothing;
  const latest = latestEvents(data.events);
  const inventory = html`<section class="haui-device-inventory" aria-labelledby="haui-inventory-heading">
        <div class="haui-inventory-overview">
          ${fleetSummary({
            total: data.devices.length,
            online,
            updates,
            version: data.version,
            heading: sectionHeading({
              title: t('Device inventory'),
              className: 'haui-section-heading haui-fleet-inventory-heading',
              titleId: 'haui-inventory-heading',
            }),
            action: data.onInstallUpdates && data.installable ? button({
              label: t('Install updates ({count})').replace('{count}', String(data.installable)),
              iconName: 'download',
              variant: 'primary',
              className: 'haui-inventory-update',
              onClick: data.onInstallUpdates,
            }) : nothing,
            pending: data.statusPending === true,
          })}
        </div>
        ${fleetBar({ devices: data.devices, total: data.devices.length, online })}
        <div class="haui-device-table" role="table" aria-label=${t('Device inventory')}>
          <div class="haui-device-row haui-device-row-head" role="row">
            <span role="columnheader">${t('Device')}</span><span role="columnheader">${t('IP address')}</span>
            <span role="columnheader">${t('YAML')}</span><span role="columnheader">${t('TFT')}</span><span role="columnheader"></span>
          </div>
          ${data.devices.map((item) => deviceRow({
            ...item,
            menuOpen: menu?.key === item.name,
            onMenu: data.onMenu ? () => data.onMenu(item.name, overlayAnchor('device-menu-row', item.name)) : null,
            onOpen: () => data.onOpenDevice(item.name),
            ...dragActions(item.name, '.haui-device-row'),
          }))}
        </div>
      </section>`;

  return html`<main class="haui-dashboard-content">
    <section class="haui-fleet-carousel-region" aria-label=${t('Your devices')}>
      ${cards.length ? html`<div class="haui-fleet-carousel-wrap">
        ${cards.length > 1 ? html`
          ${iconButton({
            label: t('Scroll devices left'), iconName: 'chevronLeft',
            className: 'haui-carousel-arrow is-left', disabled: atStart,
            onClick: (event) => scrollCarousel(event, -1),
          })}
          ${iconButton({
            label: t('Scroll devices right'), iconName: 'chevronRight',
            className: 'haui-carousel-arrow is-right', disabled: atEnd,
            onClick: (event) => scrollCarousel(event, 1),
          })}
        ` : ''}
        <div class="haui-fleet-carousel" @scroll=${onCarouselScroll}>${cards}</div>
      </div>`
        : emptyState({
          iconName: 'devices', title: t('No devices yet'), message: t('Add a device to get started'),
          action: data.onScan, actionLabel: data.scanning ? t('Scanning...') : t('Scan for devices'),
        })}
      ${data.scanError ? html`<p class="haui-fleet-scan-error" role="alert">${data.scanError}</p>` : nothing}
      ${data.statusError ? html`<p class="haui-fleet-scan-error" role="alert">${
        t('Device status could not be refreshed: {error}').replace('{error}', data.statusError)}</p>` : nothing}
      ${discovered.length ? html`<section class="haui-discovered" aria-labelledby="haui-discovered-heading">
        <header>
          <div><h2 id="haui-discovered-heading">${t('Discovered Devices')}</h2>
            <p>${t('Devices found on your network that this hub does not manage yet.')}</p></div>
          ${discovered.length > 1 ? button({
            label: t('Add All'), iconName: 'plus', onClick: () => data.onAddDevices?.(discovered),
          }) : nothing}
        </header>
        <ul>${discovered.map((found) => html`<li>
          <div><strong>${found.friendly_name || found.name}</strong>
            ${found.friendly_name && found.friendly_name !== found.name ? html`<span>${found.name}</span>` : nothing}</div>
          ${button({ label: t('Add'), iconName: 'plus', variant: 'primary', onClick: () => data.onAddDevices?.([found]) })}
        </li>`)}</ul>
      </section>` : nothing}
    </section>
    ${rolloutCard({ rollout: data.rollout, devices: data.devices, onCancel: data.onCancelRollout })}
    ${data.devices.length ? html`<div class="haui-fleet-grid">
      ${inventory}
      ${eventList({ events: latest, onOpenLogs: data.onOpenLogs })}
    </div>` : ''}
    ${deviceMenu}
  </main>`;
}
