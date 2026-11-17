/**
 * NSPanel HAUI - the Fleet screen.
 *
 * Renders Fleet's regions (`views/fleet.js` and `ui/`) from the store and
 * owns the screen's own actions: the device scan, the device menu, the bulk
 * update rollout and the remove confirmation. Every function takes the editor
 * element (`host`) as its first parameter; the shell keeps thin wrappers.
 */
import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { hasUpdateAvailable } from './device-status.js';
import { renderTitleHeader, renderFooter } from './toolbar.js';
import { renderFleetView } from './views/fleet.js';
import { modalSidebar } from './ui/sidebar.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';
import { buildPreviewContext } from './previews/context.js';
import * as DeviceEvents from './device-events.js';
import * as Toast from './toast.js';

/* ── device discovery ────────────────────────────────────────────────────── */

/**
 * Look for HAUI devices the hub does not manage yet. Runs once the editor has
 * loaded and on request from Fleet; the result is what Fleet offers to add.
 * @param {any} host
 */
export async function scanDevices(host) {
  if (!host.entryId || host._scanning) return;
  host._scanning = true;
  host._scanError = '';
  try {
    const result = await host.api.devices.scan(host.entryId);
    host._discovered = result.devices || [];
  } catch (error) {
    host._scanError = error.message || t('Scan failed');
  }
  host._scanning = false;
}

/** Devices found by the scan that are not configured (anymore). @param {any} host */
export function discoveredDevices(host) {
  const known = host._store.getState().devices.byName;
  return (host._discovered || []).filter((device) => !known[device.name || device.friendly_name]);
}

/** @param {any} host @param {Array<any>} devices */
export async function addDevices(host, devices) {
  await DeviceEvents.addDevices(host, devices);
}

/* ── updates ──────────────────────────────────────────────────────────────── */

/** Connected devices with an offered update the hub may install. @param {any} host */
export function updatableDevices(host) {
  const state = host._store.getState();
  // A status that failed to refresh may describe a device that went offline.
  if (state.hub.statusError) return [];
  return state.devices.order.filter((name) => {
    const status = state.devices.byName[name].status;
    const update = status?.update;
    return status?.connected === true && update && update.enabled !== false
      && !update.firmware_installing
      && hasUpdateAvailable(update);
  });
}

/** The bulk update confirmation's copy. @param {any} host */
export function bulkUpdateParams(host) {
  return {
    title: t('Install all offered updates?'),
    message: t('Install the offered firmware and display updates on {count} device(s), one after the other? A display cannot be used while it updates, and a firmware update restarts the panel. The first failure stops the devices after it.')
      .replace('{count}', String(host._updatableDevices().length)),
    confirmText: t('Install'),
    cancelText: t('Cancel'),
    confirmVariant: 'brand',
  };
}

/**
 * Install what each device is offered, one device at a time on the hub: a
 * panel is offline while it updates, so they never all go at once.
 * @param {any} host
 */
export async function installOfferedUpdates(host) {
  host._confirmBulkUpdate = false;
  await host._store.actions.startRollout();
}

/* ── device removal ──────────────────────────────────────────────────────── */

/** The remove confirmation of Fleet's device menu. @param {any} host */
export function removeDeviceParams(host) {
  const name = host._removeTarget;
  if (!name) return null;
  return {
    title: t('Remove device?'),
    message: t('Remove {name} from the hub? Its settings and panels are deleted. This cannot be undone.')
      .replace('{name}', host._panels.devices?.[name]?.friendly_name || name),
    confirmText: t('Remove'),
    cancelText: t('Cancel'),
  };
}

/** @param {any} host */
export async function confirmRemoveDevice(host) {
  const name = host._removeTarget;
  host._removeTarget = null;
  if (!name) return;
  await DeviceEvents.removeDevice(host, name);
  // A removed device is discoverable again.
  host._scanDevices();
}

/* ── device menu ─────────────────────────────────────────────────────────── */

/** The Fleet device menu: the actions the overview can reach without a route change. @param {any} host */
export function deviceMenuModel(host) {
  const top = host._store.getState().ui.overlays.at(-1);
  if (top?.kind !== 'device-menu') return null;
  const name = top.subject;
  const enabled = host._store.getState().devices.byName[name]?.config.enabled !== false;
  const at = (action) => () => {
    host._selectDevice(name);
    action();
  };
  return {
    key: name,
    anchorKey: top.anchorKey,
    label: t('Actions for {name}').replace('{name}', host._panels.devices?.[name]?.friendly_name || name),
    items: [
      { label: t('View'), iconName: 'screen', onSelect: at(() => host._navigateToDevice(name)) },
      { label: t('Panels'), iconName: 'panels', onSelect: at(() => host._router?.navigate({ view: 'device', device: name, panelView: 'panels' })) },
      'divider',
      { label: t('Logs'), iconName: 'log', onSelect: at(() => host._openLogs(name)) },
      'divider',
      {
        label: enabled ? t('Disable') : t('Enable'),
        iconName: enabled ? 'close-circle-outline' : 'check-circle-outline',
        onSelect: () => DeviceEvents.toggleDevice(host, name),
      },
      { label: t('Remove'), iconName: 'delete', danger: true, onSelect: () => { host._removeTarget = name; } },
    ],
  };
}

/** @param {any} host @param {string} name @param {string} anchorKey */
export function toggleDeviceMenu(host, name, anchorKey) {
  host._toggleAnchoredPopover('device-menu', anchorKey, name);
}

/* ── screen ──────────────────────────────────────────────────────────────── */

/** Fleet's screen: the carousel, its summary, the inventory and latest events. @param {any} host */
export function renderFleetScreen(host) {
  const state = host._store.getState();
  const devices = state.devices.order.map((name) => {
    const device = state.devices.byName[name];
    const status = device.status;
    const configuredKey = device.config.home_panel;
    const configuredIndex = device.panels.findIndex((panel) => panel.key === configuredKey);
    const fallbackIndex = device.panels.findIndex((panel) => panel.show_in_navigation !== false);
    const panelIndex = configuredIndex >= 0 ? configuredIndex : fallbackIndex;
    const panel = panelIndex >= 0
      ? device.panels[panelIndex]
      : state.hub.systemPanels.find((entry) => entry.key === configuredKey);
    const context = buildPreviewContext(state.hub.entryId, name, device, status, host.api, state.hub.themes);
    return {
      name,
      device,
      status,
      disabled: device.config.enabled === false,
      updates: hasUpdateAvailable(status?.update),
      preview: panel ? renderSimulatorPreview(context, panel, panelIndex < 0 ? -1 : panelIndex) : null,
    };
  });
  const events = devices.flatMap(({ name, status }) => (status?.logs || []).map((line) => ({
    device: name,
    deviceName: state.devices.byName[name].friendlyName,
    line,
  })));
  const versions = [...new Set(devices.map(({ status }) => status?.integration_version).filter(Boolean))];
  const hubVersion = versions.length === 1 ? versions[0] : versions.length > 1 ? t('Mixed versions') : t('Unknown');
  // Logs is Fleet's one sidebar.
  const logsOpen = host._isOverlayOpen('logs');
  return html`<div class="haui-container">
    ${renderTitleHeader(host)}
    ${renderFleetView({
      devices,
      events,
      version: hubVersion,
      statusPending: devices.some(({ status }) => !status),
      carousel: host.__carousel || { atStart: true, atEnd: false },
      slots: host.__carouselSlots,
      onCarouselScroll: (edges) => host._setCarouselEdges(edges),
      menu: host._deviceMenuModel(),
      onMenu: (name, anchorKey) => host._toggleDeviceMenu(name, anchorKey),
      onCloseMenu: () => host._closeAnchoredPopover('device-menu'),
      onOpenDevice: (name) => host._navigateToDevice(name),
      selectedDevice: host._fleetSelection,
      onSelectDevice: (name) => { host._fleetSelection = host._fleetSelection === name ? null : name; },
      // Reset starts the timeline at the moment it was pressed instead of the default 24 hours.
      // Hub log lines carry whole seconds, so the window starts at the second: a line written
      // right after the press is still inside it.
      eventsSince: host._fleetEventsSince,
      onResetEvents: () => { host._fleetEventsSince = Math.floor(Date.now() / 1000) * 1000; },
      onShowAllEvents: () => { host._fleetEventsSince = null; },
      onReorderDevices: (order) => host._store.actions.reorderDevices(order),
      discovered: host._discoveredDevices(),
      scanning: host._scanning,
      scanError: host._scanError,
      statusError: state.hub.statusError,
      installable: host._updatableDevices().length,
      onInstallUpdates: () => { host._confirmBulkUpdate = true; },
      onScan: () => host._scanDevices(),
      onAddDevices: (found) => host._addDevices(found),
      // Logs follows Fleet's selection; no selection lists every device's lines.
      onOpenLogs: () => host._openLogs(host._fleetSelection),
      rollout: state.hub.rollout,
      onCancelRollout: (device) => host._store.actions.cancelRollout(device),
      onDismissRollout: () => host._store.actions.dismissRollout(),
    })}
    ${host._renderNotificationsView()}
    <nspanel-dialog-confirm
      .hass=${host.hass} .open=${host._removeTarget !== null}
      .params=${host._removeDeviceParams}
      @dialog-closed=${() => { host._removeTarget = null; }}
      @dialog-confirmed=${() => host._confirmRemoveDevice()}
    ></nspanel-dialog-confirm>
    <nspanel-dialog-confirm
      .hass=${host.hass} .open=${host._confirmBulkUpdate === true}
      .params=${host._confirmBulkUpdate ? host._bulkUpdateParams : null}
      @dialog-closed=${() => { host._confirmBulkUpdate = false; }}
      @dialog-confirmed=${() => host._installOfferedUpdates()}
    ></nspanel-dialog-confirm>
    ${logsOpen ? modalSidebar({
      label: t('Logs'),
      body: host._renderLogs(),
      onClose: () => host._closeLogs(),
    }) : nothing}
    ${host._toast ? Toast.renderToast(host) : ''}
    ${renderFooter(host)}
  </div>`;
}
