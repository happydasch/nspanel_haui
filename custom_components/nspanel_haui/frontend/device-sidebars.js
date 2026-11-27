/**
 * NSPanel HAUI - the Device screen's sidebars.
 *
 * The Backups, Updates and Logs sidebars: what they show, how they open and
 * close, and the update settings save queue. Every function takes the editor
 * element (`host`) as its first parameter; the shell keeps thin wrappers.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import { clone } from './constants.js';
import { eventsByTime } from './ui/event-list.js';
import { copyText } from './dom-helpers.js';
import * as Crud from './crud.js';
import * as DeviceEvents from './device-events.js';

/* ── updates sidebar ─────────────────────────────────────────────────────── */

/** The Updates sidebar's body: the device's updates and its update settings. @param {any} host @param {string} name */
export function renderUpdates(host, name) {
  const state = host._store.getState();
  const device = state.devices.byName[name];
  return html`<nspanel-updates-sidebar
    .hass=${host.hass} .api=${host.api} .open=${true}
    .deviceStatus=${device.status} .statusError=${state.hub.statusError}
    .deviceName=${name} .entryId=${host.entryId}
    .config=${device.config}
    @dialog-closed=${() => host._closeUpdates()}
    @update-check=${() => host._store.actions.pollSelectedStatus()}
    @save-update-settings=${(event) => host._saveUpdateSettings(event)}
    @update-tft=${(event) => host._installThenRefresh(DeviceEvents.installTft(host, event))}
    @update-firmware=${(event) => host._installThenRefresh(DeviceEvents.installFirmware(host, event))}
    @repair-display=${() => askRepairDisplay(host, name)}
    @update-control=${(event) => host._controlUpdate(name, event.detail)}
  ></nspanel-updates-sidebar>`;
}

/**
 * Ask before repairing: the two uploads blank the display for several minutes.
 * @param {any} host @param {string} name
 */
export function askRepairDisplay(host, name) {
  host._repairDisplayTarget = name;
  host.requestUpdate();
}

/** What the repair rewrites, so nobody starts it for a display that works. */
export function repairDisplayParams() {
  return {
    title: t('Repair the display?'),
    message: t('The hub installs the release\'s small repair TFT and then the TFT this firmware needs, so the panel cannot be used for several minutes. Use it when the display stays blank or an update cannot finish.'),
    confirmText: t('Repair display'),
    cancelText: t('Cancel'),
    confirmVariant: 'brand',
  };
}

/** @param {any} host */
export async function confirmRepairDisplay(host) {
  const name = host._repairDisplayTarget;
  host._repairDisplayTarget = null;
  if (!name) return;
  await installThenRefresh(host, DeviceEvents.repairDisplay(host, { detail: { name } }));
}

/** @param {any} host */
export function cancelRepairDisplay(host) {
  host._repairDisplayTarget = null;
  host.requestUpdate();
}

/**
 * Read the status as soon as an install request is answered, so the sidebar
 * shows the install running (and stops offering it) without waiting for the
 * next poll.
 * @param {any} host
 * @param {Promise<unknown>} request
 */
export async function installThenRefresh(host, request) {
  await request;
  await host._store.actions.pollSelectedStatus();
}

/** Open the Updates sidebar on the device's screen. @param {any} host @param {string} deviceName */
export function openUpdates(host, deviceName) {
  host._captureSidebarFocus();
  host._store.actions.pushOverlay({ kind: 'updates', anchorKey: 'updates', subject: deviceName, draft: null });
}

/**
 * Start, put off or skip the device's scheduled firmware install, then read
 * its status again so the sidebar shows the result.
 * @param {any} host
 * @param {string} name
 * @param {{ action: 'install_now'|'defer'|'skip', seconds?: number }} detail
 */
export async function controlUpdate(host, name, detail) {
  if (await host._store.actions.controlUpdate(name, detail.action, detail.seconds)) {
    await host._store.actions.pollSelectedStatus();
  }
}

/** @param {any} host @param {any} event */
export async function saveUpdateSettings(host, event) {
  const update = event.detail?.update;
  const deviceName = host._selectedDevice;
  if (!update || !deviceName) return;
  host.__pendingUpdateSettings = { deviceName, update: clone(update) };
  if (host.__savingUpdateSettings) return;

  host.__savingUpdateSettings = true;
  try {
    while (host.__pendingUpdateSettings) {
      const pending = host.__pendingUpdateSettings;
      host.__pendingUpdateSettings = null;
      while (host._store.getState().hub.saving) {
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
      const config = host._store.selectors.configFor(pending.deviceName);
      if (!config) continue;
      await Crud.saveDeviceConfig(
        host,
        { ...config, update: pending.update },
        '',
        pending.deviceName,
      );
    }
  } finally {
    host.__savingUpdateSettings = false;
  }
}

/** @param {any} host */
export function closeUpdates(host) {
  host._store.actions.closeOverlay('updates', 'updates');
  host._restoreSidebarFocus();
}

/* ── backups sidebar ─────────────────────────────────────────────────────── */

/** Open the Backups sidebar: the device's YAML file and a copy onto other devices. @param {any} host @param {string} deviceName */
export function openBackups(host, deviceName) {
  host._captureSidebarFocus();
  host._store.actions.pushOverlay({ kind: 'backups', anchorKey: 'backups', subject: deviceName, draft: null });
}

/**
 * The Backups sidebar's body: the device's YAML file, then a copy of what it
 * holds onto the hub's other devices.
 * @param {any} host
 * @param {string} name
 */
export function renderBackups(host, name) {
  const state = host._store.getState();
  const devices = state.devices.order
    .filter((entry) => entry !== name)
    .map((entry) => ({ name: entry, label: state.devices.byName[entry].friendlyName }));
  return html`<nspanel-backup-sidebar .open=${true}
    .api=${host.api} .entryId=${host.entryId} .deviceName=${name} .devices=${devices}
    .sourceLabel=${state.devices.byName[name].friendlyName}
    @backup-export=${() => host._exportYaml()}
    @backup-import=${() => host._importYaml()}
    @backup-copied=${(event) => host._onBackupCopied(event.detail)}
  ></nspanel-backup-sidebar>`;
}

/** @param {any} host */
export function closeBackups(host) {
  host._store.actions.closeOverlay('backups', 'backups');
  host._restoreSidebarFocus();
}

/* ── logs sidebar ────────────────────────────────────────────────────────── */

/**
 * Open the Logs sidebar on the screen shown, with one device selected or
 * every device (`null`, Fleet's Latest events).
 * @param {any} host
 * @param {string|null} deviceName
 */
export function openLogs(host, deviceName) {
  host._captureSidebarFocus();
  host._store.actions.pushOverlay({ kind: 'logs', anchorKey: 'logs', subject: deviceName, draft: null });
}

/** @param {any} host */
export function closeLogs(host) {
  host._store.actions.closeOverlay('logs', 'logs');
  host._restoreSidebarFocus();
}

/** The Logs sidebar's device selection changed; '' is every device.
 * @param {any} host @param {string} deviceName */
export function selectLogsDevice(host, deviceName) {
  host._store.actions.pushOverlay({ kind: 'logs', anchorKey: 'logs', subject: deviceName || null, draft: null });
}

/** Every device's lines and the device selector; the overlay's subject is the selected device.
 * @param {any} host */
export function renderLogs(host) {
  const state = host._store.getState();
  const selected = state.ui.overlays.find((overlay) => overlay.kind === 'logs')?.subject || '';
  const devices = state.devices.order.map((name) => ({ name, label: state.devices.byName[name].friendlyName }));
  const logs = eventsByTime(devices.flatMap(({ name, label }) => (
    state.devices.byName[name].status?.logs || []).map((line) => ({ line, device: name, deviceName: label }))));
  return html`<nspanel-logs-sidebar .open=${true} .logs=${logs} .devices=${devices} .device=${selected}
    @device-selected=${(event) => host._selectLogsDevice(event.detail.device)}
    @copy-logs=${(event) => host._copyLogs(event.detail.text)}></nspanel-logs-sidebar>`;
}

/** @param {any} host @param {string} text */
export async function copyLogs(host, text) {
  try {
    await copyText(text);
    host._showToast(t('Logs copied'), 'success');
  } catch (error) {
    host._showToast(error.message || t('Failed to copy the logs'), 'error');
  }
}
