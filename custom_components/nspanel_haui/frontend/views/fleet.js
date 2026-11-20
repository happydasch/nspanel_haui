// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { deviceCard } from '../ui/device-card.js';
import { deviceSlots } from '../ui/device-slot.js';
import { deviceRow } from '../ui/device-row.js';
import { fleetBar, fleetSummary } from '../ui/fleet-summary.js';
import { eventList, eventsFrom, eventsInLast24Hours, latestEvents } from '../ui/event-list.js';
import { emptyState } from '../ui/empty-state.js';
import { button, iconButton } from '../ui/button.js';
import { sectionHeading } from '../ui/surface.js';
import { menuItem, menuSeparator, overlayAnchor, popover } from '../ui/popover.js';
import { hasUpdateAvailable } from '../device-status.js';
import { rolloutCard } from '../ui/rollout-card.js';

/** Where the carousel sits between its real-device scroll extents. */
export function carouselEdgesFrom(carousel) {
  const max = Math.max(0, (carousel?.scrollWidth || 0) - (carousel?.clientWidth || 0));
  const left = Math.max(0, carousel?.scrollLeft || 0);
  return { atStart: left <= 1, atEnd: left >= max - 1 };
}

/** The row's card gap and padding, as `fleet-styles.js` sets them. */
const CARD_GAP = 16;
const ROW_PADDING = 4;
const DEVICE_CARD_SELECTOR = '.haui-device-card:not(.haui-device-slot-card)';

/**
 * How many card-sized placeholders complete the visible row. A final slot may continue beyond its
 * right edge; ghosts are clipped without implying another real device or adding a fade.
 * @param {{ room: number, cardWidth: number }} size
 */
export function deviceSlotCount({ room, cardWidth }) {
  if (!(cardWidth > 0) || !(room > 0)) return 0;
  return Math.ceil((room + CARD_GAP) / (cardWidth + CARD_GAP));
}

/** No slots when there is no real card or the real device cards already scroll. */
const NO_SLOTS = Object.freeze({ room: 0, count: 0, width: 0, height: 0, left: 0, top: 0 });

/**
 * Measure decorative card outlines in the unused end of a row with no real devices to scroll to.
 * The overlay is clipped to the carousel viewport but never participates in its grid or scroll width.
 * @returns {{ room: number, count: number, width: number, height: number, left: number, top: number }}
 */
export function carouselSlots(carousel) {
  const cards = carousel ? [...carousel.querySelectorAll(DEVICE_CARD_SELECTOR)] : [];
  if (!cards.length || !carousel.clientWidth || carousel.scrollWidth > carousel.clientWidth + 1) {
    return NO_SLOTS;
  }
  const row = carousel.getBoundingClientRect();
  const first = cards[0].getBoundingClientRect();
  const last = cards[cards.length - 1].getBoundingClientRect();
  const room = row.left + carousel.clientWidth - ROW_PADDING - last.right - CARD_GAP;
  const count = deviceSlotCount({ room, cardWidth: first.width });
  if (!count) return NO_SLOTS;
  return {
    room: Math.round(room),
    count,
    width: Math.round(first.width),
    height: Math.round(first.height),
    left: Math.round(last.right - row.left + CARD_GAP),
    top: Math.round(first.top - row.top),
  };
}

/**
 * Scroll the carousel sideways until the card at `index` is centred; the page itself stays put.
 * A fresh `'auto'` jump places a restored selection before the row is painted.
 */
export function centerCard(carousel, index, behavior = 'smooth') {
  const card = carousel?.querySelectorAll(DEVICE_CARD_SELECTOR)[index];
  if (!carousel || !card) return;
  const view = carousel.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  carousel.scrollBy({ left: box.left + box.width / 2 - (view.left + view.width / 2), behavior });
}

/** Scroll the carousel sideways until the card at `index` is in view; the page itself stays put. */
function revealCard(from, index) {
  const carousel = from.closest('.haui-dashboard-content')?.querySelector('.haui-fleet-carousel');
  const card = carousel?.querySelectorAll(DEVICE_CARD_SELECTOR)[index];
  if (!carousel || !card) return;
  const view = carousel.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  if (box.left >= view.left && box.right <= view.right) return;
  centerCard(carousel, index);
}

/**
 * Build Fleet from prepared store data; all changes are sent back as callbacks.
 * @param {{ devices: any[], events: any[], version: string, statusPending?: boolean,
 *   carousel?: {atStart: boolean, atEnd: boolean}, menu?: any,
 *   slots?: {room: number, count: number, width: number, height: number, left: number, top: number},
 *   onCarouselScroll?: (edges: {atStart: boolean, atEnd: boolean}) => void,
 *   onMenu?: ((name: string, anchorKey: string) => void)|null, onCloseMenu?: () => void,
 *   onOpenDevice: (name: string) => void,
 *   onSetUpDevice?: (name: string) => void,
 *   selectedDevice?: string|null, onSelectDevice?: (name: string) => void,
 *   onReorderDevices: (order: string[]) => void,
 *   discovered?: any[], scanning?: boolean, scanError?: string, statusError?: string|null, onScan?: () => void,
 *   onAddDevices?: (devices: any[]) => void,
 *   installable?: number, onInstallUpdates?: () => void,
 *   rollout?: any, onCancelRollout?: (device: string|null) => void, onDismissRollout?: () => void,
 *   eventsSince?: number|null, onResetEvents?: () => void, onShowAllEvents?: () => void,
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
  const carouselEdges = data.carousel || { atStart: true, atEnd: data.slots?.count > 0 };
  const atStart = carouselEdges.atStart !== false;
  const atEnd = carouselEdges.atEnd === true;
  const scrollCarousel = (event, direction) => {
    const carousel = event.currentTarget.parentElement.querySelector('.haui-fleet-carousel');
    carousel?.scrollBy({ left: direction * Math.max(240, carousel.clientWidth * 0.8), behavior: 'smooth' });
  };
  const onCarouselScroll = (event) => data.onCarouselScroll?.(carouselEdgesFrom(event.currentTarget));
  const menu = data.menu || null;
  const discovered = data.discovered || [];
  // Cards and rows follow the same device order, so a row's index is its card's.
  const selectDevice = data.onSelectDevice ? (event, name, index) => {
    const selecting = data.selectedDevice !== name;
    data.onSelectDevice?.(name);
    if (selecting) revealCard(event.currentTarget, index);
  } : null;
  const cards = data.devices.map((item) => deviceCard({
    ...item,
    selected: item.name === data.selectedDevice,
    // A device that still needs its panels opens the quick start instead of a
    // page it does not have.
    onOpen: item.needsSetup
      ? () => data.onSetUpDevice?.(item.name)
      : () => data.onOpenDevice(item.name),
    onSelect: data.onSelectDevice ? () => data.onSelectDevice?.(item.name) : null,
    ...dragActions(item.name, '.haui-device-card'),
  }));
  const hasGhostCards = data.slots?.count > 0;
  const slots = hasGhostCards
    ? deviceSlots({ count: data.slots.count, left: data.slots.left, step: data.slots.width + CARD_GAP })
    : nothing;
  const slotStyle = hasGhostCards ? [
    `--haui-device-slots-top: ${data.slots.top}px`,
    `--haui-device-slot-width: ${data.slots.width}px`,
    `--haui-device-slot-height: ${data.slots.height}px`,
  ].join('; ') : nothing;
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
  // A selected device scopes Fleet's log surfaces to itself: its events here, and its
  // lines in the Logs sidebar, which the shell opens on the same device.
  const selected = data.selectedDevice
    ? data.devices.find(({ name }) => name === data.selectedDevice) || null
    : null;
  const events = data.selectedDevice
    ? data.events.filter((event) => event.device === data.selectedDevice)
    : data.events;
  // A reset starts the timeline at the moment it was pressed instead of the default 24 hours.
  const latest = latestEvents(
    data.eventsSince != null ? eventsFrom(events, data.eventsSince) : eventsInLast24Hours(events),
  );
  // The segments close the card, so the connection of every device reads at its foot without
  // repeating a column of the table.
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
    <div class="haui-device-table" role="table" aria-labelledby="haui-inventory-heading"
      aria-describedby=${selectDevice ? 'haui-inventory-select-hint' : nothing}>
      ${selectDevice ? html`<span class="haui-sr-only" id="haui-inventory-select-hint">${
        t('Enter or Space on a row selects its device.')}</span>` : nothing}
      <div class="haui-device-row haui-device-row-head" role="row">
        <span role="columnheader">${t('Device')}</span><span role="columnheader">${t('IP address')}</span>
        <span role="columnheader">${t('YAML')}</span><span role="columnheader">${t('TFT')}</span><span role="columnheader"><span class="haui-sr-only">${t('Actions')}</span></span>
      </div>
      ${data.devices.map((item, index) => deviceRow({
        ...item,
        menuOpen: menu?.key === item.name,
        selected: item.name === data.selectedDevice,
        onSelect: selectDevice ? (event) => selectDevice(event, item.name, index) : null,
        onMenu: data.onMenu ? () => data.onMenu(item.name, overlayAnchor('device-menu-row', item.name)) : null,
        onOpen: () => data.onOpenDevice(item.name),
        ...dragActions(item.name, '.haui-device-row'),
      }))}
    </div>
    <footer class="haui-inventory-footer">
      ${fleetBar({ devices: data.devices, total: data.devices.length, online })}
    </footer>
  </section>`;

  return html`<main class="haui-dashboard-content">
    <h1 class="haui-sr-only">${t('Dashboard')}</h1>
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
        <div class="haui-fleet-carousel${atStart ? '' : ' is-clipped-start'}${atEnd ? '' : ' has-right-fade'}" role="list" @scroll=${onCarouselScroll}>${cards}</div>
        ${hasGhostCards ? html`<div class="haui-device-slots has-right-fade" aria-hidden="true" style=${slotStyle}>${slots}</div>` : nothing}
      </div>`
        : emptyState({
          iconName: 'devices', title: t('No devices yet'), message: t('Add a device to get started'),
          action: data.onScan, actionLabel: data.scanning ? t('Scanning...') : t('Scan for devices'),
        })}
      ${data.scanError ? html`<p class="haui-fleet-scan-error" role="alert">${data.scanError}</p>` : nothing}
      ${data.statusError ? html`<p class="haui-fleet-scan-error" role="status">${
        t('Device status could not be refreshed: {error}').replace('{error}', data.statusError)}</p>` : nothing}
      ${discovered.length ? html`<section class="haui-discovered" aria-labelledby="haui-discovered-heading">
        <header>
          <div><h2 id="haui-discovered-heading">${t('Discovered Devices')}</h2>
            <p>${t('Devices found on your network that this hub does not manage yet.')}</p></div>
          ${discovered.length > 1 ? button({
            label: t('Add All'), iconName: 'plus', onClick: () => data.onAddDevices?.(discovered),
          }) : nothing}
        </header>
        <ul role="list">${discovered.map((found) => html`<li>
          <div><strong>${found.friendly_name || found.name}</strong>
            ${found.friendly_name && found.friendly_name !== found.name ? html`<span>${found.name}</span>` : nothing}</div>
          ${button({ label: t('Add'), iconName: 'plus', variant: 'primary', onClick: () => data.onAddDevices?.([found]) })}
        </li>`)}</ul>
      </section>` : nothing}
    </section>
    ${rolloutCard({
      rollout: data.rollout, devices: data.devices,
      onCancel: data.onCancelRollout, onDismiss: data.onDismissRollout,
    })}
    ${data.devices.length ? html`<div class="haui-fleet-grid">
      ${inventory}
      ${eventList({
        events: latest,
        deviceName: selected?.device?.friendlyName || null,
        since: data.eventsSince ?? null,
        onReset: data.onResetEvents,
        onShowWindow: data.onShowAllEvents,
        onOpenLogs: data.onOpenLogs,
      })}
    </div>` : ''}
    ${deviceMenu}
  </main>`;
}
