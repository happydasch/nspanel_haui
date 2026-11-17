/**
 * NSPanel HAUI - the Device screen.
 *
 * Renders the device rail, workspace, lead card and side stack, and owns the
 * screen's own UI state: the preview state the workspace reports, the side
 * cards' expansion, the diagnostics copy and the sidebar titles. Every
 * function takes the editor element (`host`) as its first parameter; the shell
 * keeps thin wrappers.
 */
import { html, nothing } from './lit-import.js';
import { t } from './localize.js';
import { isPortraitModel } from './constants.js';
import { deviceBrightness, hasUpdateAvailable } from './device-status.js';
import { groupPanels } from './panel-utils.js';
import { buildPreviewContext } from './previews/context.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';
import { renderDeviceView } from './views/device.js';
import { panelCatalog } from './views/panel-catalog.js';
import { renderPanelList } from './views/panel-list.js';
import { renderTitleHeader, renderFooter } from './toolbar.js';
import { panelActions, themeLabel, updatesSummary } from './ui/panel-manager.js';
import { panelSideCard } from './ui/panel-info.js';
import { deviceActions } from './ui/device-actions.js';
import { deviceDetails } from './ui/device-details.js';
import { diagnosticsReport } from './ui/device-diagnostics.js';
import { button } from './ui/button.js';
import { emptyState } from './ui/empty-state.js';
import { idlePanelKeys } from './ui/panel-pills.js';
import * as Crud from './crud.js';
import * as Toast from './toast.js';
import { copyText } from './dom-helpers.js';
import { writeSideCards } from './editor-preferences.js';
import { isSidebarOverlayKind } from './store/store.js';
import { settingsSection } from './device-settings-sections.js';

/* ── sidebar titles ───────────────────────────────────────────────────────── */

/** The sidebar strip's title for the panel editor: a new panel, or an existing one. @param {any} host */
export function panelEditorLabel(host) {
  const editing = host._editingPanel;
  const system = (host._panels?.system_panels || []).some((entry) => entry.key === editing?.data?.key);
  // A system panel's first edit has no index yet, but it is not a new panel.
  return editing && editing.index < 0 && !system ? t('Add Panel') : t('Edit Panel');
}

/**
 * The modal sidebar's title for a sidebar overlay kind. The device settings
 * name the group they show, or "Device settings" on their tile grid.
 * @param {any} host
 * @param {string|undefined} kind
 */
export function sidebarLabel(host, kind) {
  /** @type {Record<string, () => string>} */
  const labels = {
    'device-settings': () => (host._deviceSettingsSection
      ? settingsSection(host._deviceSettingsSection).label()
      : t('Device settings')),
    'panel-editor': () => host._panelEditorLabel(),
    'panel-catalog': () => t('Add panel'),
    updates: () => t('Updates'),
    theme: () => t('Theme'),
    logs: () => t('Logs'),
  };
  const label = kind ? labels[kind] : undefined;
  if (!label) throw new Error(`Unknown sidebar kind: ${kind}`);
  return label();
}

/* ── preview state and side cards ────────────────────────────────────────── */

/** Keep the Device header in step with the preview session it cannot see. @param {any} host @param {any} event */
export function onPreviewState(host, event) {
  const detail = event.detail || {};
  const previous = host.__previewState;
  host.__previewState = detail;
  host._store.actions.setPreviewIdle(Boolean(detail.idle));
  if (detail.mode && detail.mode !== host._store.getState().ui.preview.mode) {
    host._store.actions.setPreviewMode(detail.mode);
  }
  if (!previous || previous.idle !== detail.idle || previous.ready !== detail.ready
      || previous.canInteract !== detail.canInteract || previous.mode !== detail.mode
      || previous.sandboxChanged !== detail.sandboxChanged) {
    host.requestUpdate();
  }
}

/** Ask the hub to redraw the device display. @param {any} host @param {string} name */
export async function redrawDisplay(host, name) {
  if (!name || !host.entryId) return;
  try {
    await host.api.devices.refreshDisplay(host.entryId, name);
    host._showToast(t('Display refreshed for "{name}"').replace('{name}', name), 'success');
  } catch (error) {
    host._showToast(error.message || t('Failed to refresh display'), 'error');
  }
}

/** @param {any} host */
function persistSideCards(host) {
  writeSideCards({
    detailsExpanded: host._detailsExpanded,
    diagnosticsExpanded: host._diagnosticsExpanded,
    panelCardsExpanded: host._panelCardsExpanded,
  });
}

/** Toggle the Connection & device card, closing the other side areas when it opens. @param {any} host */
export function toggleDetails(host) {
  host._detailsExpanded = !host._detailsExpanded;
  if (host._detailsExpanded) {
    host._diagnosticsExpanded = false;
    host._panelCardsExpanded = [];
  }
  persistSideCards(host);
}

/** Toggle Diagnostics, closing the other side areas when it opens. @param {any} host */
export function toggleDiagnostics(host) {
  host._diagnosticsExpanded = !host._diagnosticsExpanded;
  if (host._diagnosticsExpanded) {
    host._detailsExpanded = false;
    host._panelCardsExpanded = [];
  }
  persistSideCards(host);
}

/** Toggle a device side-stack card, closing other side areas when it opens.
 * @param {any} host @param {string} card */
export function togglePanelCard(host, card) {
  const expanded = host._panelCardsExpanded.includes(card);
  host._panelCardsExpanded = expanded
    ? host._panelCardsExpanded.filter((entry) => entry !== card)
    : [card];
  if (!expanded) {
    host._detailsExpanded = false;
    host._diagnosticsExpanded = false;
  }
  persistSideCards(host);
  if (card === 'theme' && !expanded && host._themesError) {
    host._loadThemeLibrary(host.entryId, true);
  }
}

/** Copy a plain-text diagnostics report for a bug report.
 * @param {any} host @param {string} name @param {any} status */
export async function copyDiagnostics(host, name, status) {
  try {
    await copyText(diagnosticsReport(name, status));
    host._showToast(t('Diagnostics report copied'), 'success');
  } catch (error) {
    host._showToast(error.message || t('Failed to copy the report'), 'error');
  }
}

/**
 * Toggle idle in the preview, explaining when the device has no idle panels.
 * @param {any} host
 * @param {any} config
 * @param {{ idle?: boolean }} previewState
 */
export function onPreviewIdle(host, config, previewState) {
  if (!previewState?.idle && !idlePanelKeys(config?.idle_panel, config?.idle_panel_extra).length) {
    host._showToast(t('No idle panels are configured'), 'error');
    return;
  }
  host._callPreviewWorkspace('idleTimeout');
}

/** Call a preview-workspace action of the header or the Diagnostics card.
 * @param {any} host @param {string} method @param {...any} args */
export function callPreviewWorkspace(host, method, ...args) {
  const element = host.renderRoot?.querySelector('nspanel-preview-workspace');
  const action = element?.[method];
  if (typeof action !== 'function') return;
  action.apply(element, args);
}

/* ── screen ──────────────────────────────────────────────────────────────── */

/** The Device screen: workspace, lead card and side stack for the routed device. @param {any} host */
export function renderDeviceScreen(host) {
  const state = host._store.getState();
  const route = state.ui.route;
  const name = route.device;
  const device = name ? state.devices.byName[name] : null;
  if (!name || !device) return host._renderFleetScreen();
  const status = device.status;
  const railDevices = state.devices.order.map((deviceName) => {
    const entry = state.devices.byName[deviceName];
    return {
      name: deviceName,
      device: entry,
      status: entry.status,
      updates: hasUpdateAvailable(entry.status?.update),
    };
  });
  const preview = state.ui.preview;
  const previewState = host.__previewState || {};
  // Every open sidebar stays rendered and the topmost one is shown, so a nested
  // editor keeps the draft below it.
  const sidebarKinds = state.ui.overlays.map((overlay) => overlay.kind).filter(isSidebarOverlayKind);
  const sidebarKind = sidebarKinds.at(-1);
  const interactiveSession = html`<nspanel-preview-workspace class="haui-inline-live-preview"
    .hass=${host.hass} .active=${true} .entryId=${host.entryId} .device=${name}
    .mode=${preview.mode} .showEntities=${preview.showEntities}
    @preview-state=${(event) => host._onPreviewState(event)}
    @preview-notice=${(event) => host._showToast(event.detail.message, event.detail.type)}
  ></nspanel-preview-workspace>`;
  // Only the Panels view pays for the list: the Preview view renders on every
  // Home Assistant state change and would build every card for nothing.
  const workspace = route.panelView === 'panels'
    ? renderPanelList(host._panelListModel(device, status))
    : interactiveSession;
  // Every open sidebar stays rendered and the topmost one is shown, so a nested
  // editor keeps the draft below it.
  const panelEditor = sidebarKinds.includes('panel-editor') && host._editingPanel ? html`<nspanel-panel-editor
    .hass=${host.hass} .api=${host.api} .open=${true}
    .panel=${host._editingPanel} .panelTypes=${host._panelTypes}
    .themes=${{ ...host._builtinThemes, ...host._customThemes }}
    .devicePanels=${host._devicePanels()} .systemPanels=${host._panels?.system_panels || []}
    .saving=${host._saving} .error=${host._error} .entryId=${host.entryId}
    .serverErrors=${host._serverErrors || []}
    .dialogVersion=${host._dialogVersion}
    .previewContext=${buildPreviewContext(host.entryId, name, device, status, host.api, state.hub.themes)}
    @dialog-closed=${() => {
      host.__openedRoutePanel = null;
      host._closeEdit();
      if (state.ui.route.panel) host._router?.navigate({ view: 'device', device: name, panelView: 'panels' }, { replace: true });
    }} @dialog-save=${(event) => host._save(event)}
  ></nspanel-panel-editor>` : null;
  // The settings follow the stored config, so a save in a sidebar opened from
  // them (theme) reaches their form.
  const deviceSettings = html`<nspanel-device-settings
    .hass=${host.hass} .open=${true}
    .config=${device.config}
    .panels=${device.panels}
    .systemPanels=${state.hub.systemPanels || []}
    .builtinThemes=${host._builtinThemes}
    .customThemes=${host._customThemes}
    .deviceBrightness=${deviceBrightness(status, host.hass)}
    .section=${host._deviceSettingsSection}
    .saving=${host._saving}
    .api=${host.api} .entryId=${host.entryId}
    @dialog-closed=${() => host._closeDeviceConfig()}
    @dialog-save=${(event) => host._onDeviceConfigSave(event)}
    @section-change=${(event) => host._openDeviceSettingsSection(event.detail.section)}
  ></nspanel-device-settings>`;
  const catalog = () => panelCatalog({
    panelTypes: host._panelTypes,
    query: host._panelCatalogSearch,
    onQuery: (query) => { host._panelCatalogSearch = query; },
    compactPreviews: host._panelCatalogCompact,
    onPreviewSize: (compact) => host._chooseCatalogPreviewSize(compact),
    onSelect: (type) => host._openAdd(type),
    copies: host._panelTemplates(),
    onSelectCopy: (panel) => host._openAddFrom(panel),
    starters: state.hub.panelTemplates || [],
    onSelectStarter: (panel) => {
      host._panelCatalogOpen = false;
      Crud.openAddFromTemplate(host, panel);
    },
    popups: groupPanels(device.panels, state.hub.systemPanels || []).defaults,
    onSelectPopup: (entry) => host._openSysPanelFromCatalog(entry),
    preview: (panel, byKey = false) => renderSimulatorPreview(
      buildPreviewContext(host.entryId, name, device, status, host.api, state.hub.themes), panel, byKey ? -1 : 0),
    portrait: isPortraitModel(device.config.display_model),
  });
  const theme = () => html`<nspanel-theme-sidebar
    .hass=${host.hass} .api=${host.api} .open=${true}
    .entryId=${host.entryId}
    .themeId=${host._themeId || 'dark'}
    @dialog-closed=${() => host._closeThemeSidebar()} @dialog-save=${(event) => host._onThemeSave(event)}
  ></nspanel-theme-sidebar>`;
  /** @param {string} kind @param {() => unknown} content */
  const layer = (kind, content) => (sidebarKinds.includes(kind)
    ? html`<div class="haui-sidebar-layer" ?hidden=${kind !== sidebarKind}>${content()}</div>`
    : nothing);
  // The modal sidebar opens over the page; the side stack below it stays as it is.
  const sidebarContent = sidebarKind ? html`${layer('device-settings', () => deviceSettings)}${
    layer('panel-catalog', catalog)}${layer('panel-editor', () => panelEditor)}${
    layer('updates', () => host._renderUpdates(name))}${layer('theme', theme)}${
    layer('logs', () => host._renderLogs())}` : null;
  const leadContent = route.panelView === 'panels'
    ? panelActions({
        panels: device.panels,
        onAdd: () => host._openCatalog(),
        onSettings: () => host._openSettings(),
      })
    : deviceActions({
        status,
        onSettings: () => host._openSettings(),
        onUpdates: () => host._openUpdates(name),
        onAdd: () => host._openCatalog(),
      });
  const sideContent = route.panelView === 'panels'
    ? panelSideCard(host._panelSideModel(device, status))
    : deviceDetails({
          name,
          status,
          statusError: host._deviceStatusError,
          hass: host.hass,
          onLogs: () => host._openLogs(name),
          onUpdates: () => host._openUpdates(name),
          updatesDetail: updatesSummary(device.config),
          themeDetail: themeLabel(device.config.theme_id, host._builtinThemes, host._customThemes),
          onEditTheme: () => host._openTheme(device.config.theme_id),
          onCopyReport: () => host._copyDiagnostics(name, status),
          detailsExpanded: host._detailsExpanded,
          onToggleDetails: () => host._toggleDetails(),
          diagnosticsExpanded: host._diagnosticsExpanded,
          onToggleDiagnostics: () => host._toggleDiagnostics(),
          yamlExpanded: host._panelCardsExpanded.includes('yaml'),
          onToggleYaml: () => host._togglePanelCard('yaml'),
          onYamlImport: () => host._importYaml(),
          onYamlExport: () => host._exportYaml(),
          showEntities: preview.showEntities,
          onShowEntities: (show) => host._store.actions.setPreviewEntities(show),
          // Live already shows the device's page; only the simulated preview follows a click.
          onOpenPage: (previewState.mode || preview.mode) !== 'live' && previewState.ready && status?.current_panel
            ? () => host._callPreviewWorkspace(
              'openPanel', status.current_panel, status.idle_page?.state === 'active',
            )
            : null,
          previewTools: {
            live: (previewState.mode || preview.mode) === 'live',
            ready: Boolean(previewState.ready),
            canInteract: Boolean(previewState.canInteract),
            sandboxChanged: Boolean(previewState.sandboxChanged),
            onReset: () => host._callPreviewWorkspace('resetSession'),
            onRedraw: () => host._redrawDisplay(name),
          },
        });

  return html`<div class="haui-container">
    ${renderTitleHeader(host)}
    ${renderDeviceView({
      devices: railDevices,
      selectedName: name,
      title: device.friendlyName || name,
      onBack: () => host._navigateToFleet(),
      panelCount: device.panels.length,
      panelView: route.panelView,
      panelSearch: { query: host._panelSearch, onQuery: (value) => { host._panelSearch = value; } },
      railCollapsed: host._railCollapsed,
      workspace,
      leadContent,
      sideContent,
      sideLabel: route.panelView === 'panels' ? t('Panel details') : t('Device details'),
      sidebarContent,
      preview: {
        mode: previewState.mode || preview.mode,
        idle: Boolean(previewState.idle),
        canInteract: Boolean(previewState.canInteract),
      },
      sidebarOpen: Boolean(sidebarContent),
      sidebarLabel: sidebarKind ? host._sidebarLabel(sidebarKind) : undefined,
      // A settings group is one level below the tile grid: back returns to it.
      sidebarBack: sidebarKind === 'device-settings' && host._deviceSettingsSection
        ? {
          label: t('Back to device settings'),
          onBack: () => host._openDeviceSettingsSection(null),
        }
        : null,
      onCloseSide: () => host._closeSidebar(),
      onSelectDevice: (deviceName) => host._navigateToDevice(deviceName),
      onSwitchView: (panelView) => host._router?.navigate(
        { view: 'device', device: name, panelView }, { replace: true },
      ),
      onMode: (mode) => {
        host._store.actions.setPreviewMode(mode);
        // Also when the store already holds this mode: a Live session that failed
        // to start must still switch back to Simulated.
        host._callPreviewWorkspace('setLive', mode === 'live');
      },
      onIdle: () => host._onPreviewIdle(device.config, previewState),
    })}
    <nspanel-dialog-confirm
      .hass=${host.hass} .open=${host._deleteTarget !== null}
      .params=${host._deleteTarget !== null ? host._confirmDialogParams : null}
      @dialog-closed=${() => host._cancelDelete()} @dialog-confirmed=${() => host._doDelete()}
    ></nspanel-dialog-confirm>
    <nspanel-dialog-confirm
      .hass=${host.hass} .open=${host._tftInstallTarget !== null}
      .params=${host._tftInstallTarget !== null ? host._tftInstallParams : null}
      @dialog-closed=${() => host._cancelTftInstall()} @dialog-confirmed=${() => host._confirmTftInstall()}
    ></nspanel-dialog-confirm>
    ${host._renderNotificationsView()}
    ${host._toast ? Toast.renderToast(host) : ''}
    ${renderFooter(host)}
  </div>`;
}

/* ── loading ─────────────────────────────────────────────────────────────── */

/** The editor's loading screen, with its way out when Home Assistant's elements never arrive.
 * @param {any} host @param {string} message */
export function renderLoading(host, message) {
  return html`<div class="haui-container">
    ${renderTitleHeader(host)}
    <div class="haui-main-content">
      ${emptyState({ message, iconName: null, className: 'haui-empty-state-loading' })}
      ${host._haElementsSlow ? html`<div class="haui-loading-actions">
        ${button({ label: t('Continue anyway'), variant: 'outline', onClick: () => host._forceRenderWithoutHaElements() })}
        ${button({ label: t('Reload page'), variant: 'primary', onClick: () => host._reloadPage() })}
      </div>` : nothing}
    </div>
    ${renderFooter(host)}
  </div>`;
}
