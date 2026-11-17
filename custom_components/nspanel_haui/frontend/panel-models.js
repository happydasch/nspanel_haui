/**
 * NSPanel HAUI - the Device screen's panel view models.
 *
 * Prepares the Panels view's list and side card for `views/panel-list.js` and
 * `ui/panel-info.js`: grouped rows with hub-rendered previews, role markers,
 * move state and menu closures, and the selected panel or the list overview.
 * The shell keeps thin wrappers; each function takes the editor element
 * (`host`) as its first parameter.
 */
import { html } from './lit-import.js';
import { t } from './localize.js';
import { isPortraitModel } from './constants.js';
import * as Crud from './crud.js';
import { groupPanels, panelRoleMarkers } from './panel-utils.js';
import { panelHasOptionErrors } from './option-rules.js';
import { buildPreviewContext } from './previews/context.js';
import { previewRenderKey } from './previews/previewer.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';
import { overlayAnchor } from './ui/popover.js';
import { idlePanelKeys } from './ui/panel-pills.js';
import { writePanelPreviewFolded } from './editor-preferences.js';

/* ── panel helpers ────────────────────────────────────────────────────────── */

/** The selected device's panels. @param {any} host */
export function devicePanels(host) {
  return host._panels.devices?.[host._selectedDevice]?.panels || [];
}

/** @param {any} host @param {string} groupId */
export function togglePanelGroup(host, groupId) {
  host._collapsedPanelGroups = host._collapsedPanelGroups.includes(groupId)
    ? host._collapsedPanelGroups.filter((id) => id !== groupId)
    : [...host._collapsedPanelGroups, groupId];
}

/* ── panel list ───────────────────────────────────────────────────────────── */

/**
 * Prepare the Device workspace's panel groups for `views/panel-list.js`.
 *
 * Every entry carries its hub-rendered preview, role markers, move state and
 * menu closures, so the view only renders and reports back through the model's
 * callbacks.
 *
 * @param {any} host - the editor element
 * @param {any} device - the routed device state (`{ name, panels, config }`)
 * @param {any} status - that device's status payload
 */
export function panelListModel(host, device, status) {
  const state = host._store.getState();
  const panels = device?.panels || [];
  const config = device?.config || {};
  const systemPanels = state.hub.systemPanels || [];
  const grouped = groupPanels(panels, systemPanels);
  const portrait = isPortraitModel(config.display_model);
  const systemKeys = new Set(systemPanels.map((entry) => entry.key).filter(Boolean));
  // The hub opens the first navigation panel as home while none is configured
  // (or the configured one is gone), so that panel carries the Home marker.
  const homeKnown = panels.some((panel) => panel.key === config.home_panel) || systemKeys.has(config.home_panel);
  const roleConfig = { ...config, home_panel: homeKnown ? config.home_panel : grouped.navigation[0]?.key };
  const context = buildPreviewContext(
    host.entryId,
    device?.name ?? host._selectedDevice,
    device,
    status,
    host.api,
    state.hub.themes,
  );
  // Every card shares this context: serialise it once, not once per card.
  const renderKey = previewRenderKey(context);
  const descriptorFor = (panel) => host._panelTypes.find((type) => type.type_key === panel.type);
  const nameOf = (panel) => panel.title || descriptorFor(panel)?.label || panel.key || t('Unnamed panel');
  // A panel moves to any other device of the hub, enabled or not.
  const otherDevices = state.devices.order
    .filter((name) => name !== context.device && state.devices.byName[name])
    .map((name) => ({ name, label: state.devices.byName[name].friendlyName || name }));
  const moveItems = (panel) => (otherDevices.length
    ? ['divider', {
      label: t('Move to…'),
      iconName: 'folder-move-outline',
      submenu: otherDevices.map((target) => ({
        label: target.label,
        onSelect: () => Crud.movePanelToDevice(host, panel.key, target.name),
      })),
    }]
    : []);

  /**
   * @param {Array} list
   * @param {boolean} isNavigation
   */
  const userEntries = (list, isNavigation) => list.map((panel) => {
    const index = panels.indexOf(panel);
    const descriptor = descriptorFor(panel);
    return {
      key: panel.key,
      kind: 'user',
      sortable: true,
      title: nameOf(panel),
      typeLabel: descriptor?.label || panel.type || '',
      itemCount: Array.isArray(panel.items) ? panel.items.length : 0,
      invalid: panelHasOptionErrors(descriptor, panel, { popup: false }),
      preview: renderSimulatorPreview(context, panel, index, renderKey),
      roles: panelRoleMarkers(panel.key, roleConfig),
      onEdit: () => host._openEdit(index),
      menu: [
        { label: t('Edit'), iconName: 'edit', onSelect: () => host._openEdit(index) },
        { label: t('Duplicate'), iconName: 'content-copy', onSelect: () => Crud.duplicatePanel(host, panel.key) },
        ...moveItems(panel),
        'divider',
        {
          label: isNavigation ? t('Hide from navigation') : t('Show in navigation'),
          iconName: isNavigation ? 'eye-off-outline' : 'eye-outline',
          onSelect: () => host._toggleNavVisibility(panel.key),
        },
        'divider',
        { label: t('Delete'), iconName: 'delete', danger: true, onSelect: () => host._confirmDelete(index) },
      ],
    };
  });

  /** @param {Array} list - the popups this device extends */
  const popupEntries = (list) => list.map((entry) => ({
    key: entry.key,
    kind: 'popup',
    title: entry.label || entry.key,
    typeLabel: t('Popup'),
    preview: renderSimulatorPreview(context, entry, -1, renderKey),
    roles: panelRoleMarkers(entry.key, roleConfig),
    onEdit: () => host._openSysPanelEdit(entry),
    menu: [
      { label: t('Edit'), iconName: 'edit', onSelect: () => host._openSysPanelEdit(entry) },
      'divider',
      { label: t('Reset to default'), iconName: 'restore', onSelect: () => host._resetSysPanelOverride(entry.key) },
    ],
  }));

  const count = (list) => String(list.length);
  // A search narrows every group to the rows that match; while it is active
  // the list is not a place to reorder, and groups without a match are left out.
  const query = (host._panelSearch || '').trim().toLocaleLowerCase();
  const matches = (entry) => `${entry.title} ${entry.key} ${entry.typeLabel || ''}`.toLocaleLowerCase().includes(query);
  const narrowed = (groups) => {
    const visibleGroups = query
      ? groups.map((group) => ({ ...group, dropEnabled: false, entries: group.entries.filter(matches) }))
        .filter((group) => group.entries.length)
      : groups;
    // Search results stay visible; clearing the query restores each group's collapsed state.
    return visibleGroups.map((group) => ({
      ...group,
      collapsed: !query && host._collapsedPanelGroups.includes(group.id),
    }));
  };
  return {
    emptyMessage: query ? t('No panels match this search.') : '',
    groups: narrowed([
      {
        id: 'navigation',
        title: grouped.navigation.length === 1
          ? t('Navigation (1 panel)')
          : t('Navigation ({count} panels)').replace('{count}', count(grouped.navigation)),
        hint: t('Drag to reorder or move between groups'),
        emptyMessage: t('Drop a panel here to show it in navigation.'),
        dropEnabled: true,
        entries: userEntries(grouped.navigation, true),
      },
      {
        id: 'hidden',
        title: grouped.hidden.length === 1
          ? t('Hidden (1 panel)')
          : t('Hidden ({count} panels)').replace('{count}', count(grouped.hidden)),
        hint: t('Reached from other panels, not the header'),
        emptyMessage: t('Drop a panel here to hide it from navigation.'),
        dropEnabled: true,
        entries: userEntries(grouped.hidden, false),
      },
      {
        id: 'popups',
        title: grouped.popups.length === 1
          ? t('Popups (1 panel)')
          : t('Popups ({count} panels)').replace('{count}', count(grouped.popups)),
        hint: t('Popups this device extends'),
        emptyMessage: t('Every popup is the built-in one. Extend one from Add panel.'),
        dropEnabled: false,
        entries: popupEntries(grouped.popups),
      },
    ]),
    portrait,
    menuKey: state.ui.overlays.at(-1)?.kind === 'panel-menu' ? state.ui.overlays.at(-1)?.subject : null,
    submenuKey: state.ui.overlays.at(-1)?.kind === 'panel-menu' ? host._panelSubmenuKey : null,
    selectedKey: host._selectedPanelKey,
    onToggleMenu: (key) => host._togglePanelMenu(key),
    onToggleSubmenu: (key) => host._togglePanelSubmenu(key),
    onCloseMenu: () => host._closePanelMenu(),
    onToggleGroup: (groupId) => host._togglePanelGroup(groupId),
    onSelect: (key) => host._togglePanelSelection(key),
    onDrop: (move) => Crud.movePanelToGroup(host, move.sourceKey, move.group, move.beforeKey),
  };
}

/* ── panel side card ──────────────────────────────────────────────────────── */

/**
 * The Panels view's side card: the selected panel, or what the list is about
 * while nothing is selected.
 *
 * @param {any} host - the editor element
 * @param {any} device - the routed device state (`{ name, panels, config }`)
 * @param {any} status - that device's status payload
 */
export function panelSideModel(host, device, status) {
  const state = host._store.getState();
  const panels = device?.panels || [];
  const config = device?.config || {};
  const systemPanels = state.hub.systemPanels || [];
  const grouped = groupPanels(panels, systemPanels);
  const descriptorFor = (panel) => host._panelTypes.find((type) => type.type_key === panel?.type);
  const key = host._selectedPanelKey;
  // Every listed row is either one of the device's panels or a popup it
  // replaces (stored among them), so the panel configs answer both.
  const panel = key ? panels.find((entry) => entry.key === key) : null;
  const titleOf = (panelKey) => {
    const entry = panelKey ? panels.find((panelEntry) => panelEntry.key === panelKey) : null;
    const system = panelKey ? systemPanels.find((systemEntry) => systemEntry.key === panelKey) : null;
    if (!entry && !system) return '';
    return entry?.title || descriptorFor(entry)?.label || entry?.key || system?.label || panelKey;
  };
  if (!panel) {
    // What the device opens at both ends of its idle cycle: the configured home
    // panel (or the hub's fallback to the first navigation panel) and the idle
    // page, whose panel comes from the ordered idle list.
    const idleKeys = idlePanelKeys(config.idle_panel, config.idle_panel_extra);
    const idleTitles = idleKeys.map(titleOf).filter(Boolean);
    const configuredHomeKey = config.home_panel || grouped.navigation[0]?.key || '';
    const homePanelKey = panels.some((entry) => entry.key === configuredHomeKey) ? configuredHomeKey : '';
    const idlePanelKey = idleKeys[0] && panels.some((entry) => entry.key === idleKeys[0])
      ? idleKeys[0]
      : '';
    return {
      kind: 'overview',
      navigationCount: grouped.navigation.length,
      hiddenCount: grouped.hidden.length,
      popupCount: grouped.popups.length,
      homePanel: titleOf(configuredHomeKey),
      homePanelKey,
      idlePanels: idleTitles.length > 1
        ? t('{name} and {count} more')
          .replace('{name}', idleTitles[0]).replace('{count}', String(idleTitles.length - 1))
        : idleTitles[0] || '',
      idlePanelKey: idleKeys[0] || '',
      onSelectPanel: (panelKey) => host._togglePanelSelection(panelKey),
    };
  }
  const descriptor = descriptorFor(panel);
  const systemEntry = systemPanels.find((entry) => entry.key === key);
  const index = panels.indexOf(panel);
  const facts = [
    [t('Type'), descriptor?.label || panel.type || ''],
    [t('Key'), html`<code class="haui-panel-info-key">${panel.key}</code>`],
    [t('Group'), systemEntry ? t('Popup') : panel.show_in_navigation === false ? t('Hidden') : t('Navigation')],
  ];
  if (Array.isArray(panel.items)) facts.push([t('Items'), String(panel.items.length)]);
  // The hub opens the first navigation panel as home while none is configured.
  const home = panel.key === (config.home_panel || grouped.navigation[0]?.key);
  const roles = [
    ...(home ? [t('Home panel')] : []),
    ...(panel.key === config.idle_panel ? [t('Idle panel')] : []),
  ];
  if (roles.length) facts.push([t('Role'), roles.join(' · ')]);
  const context = buildPreviewContext(
    host.entryId,
    device?.name ?? host._selectedDevice,
    device,
    status,
    host.api,
    state.hub.themes,
  );
  // A popup override is edited and reset; a panel of the device is edited,
  // duplicated and deleted, as its row's menu offers.
  const actions = systemEntry
    ? [
      { label: t('Edit'), iconName: 'edit', variant: 'primary', onClick: () => host._openSysPanelEdit(systemEntry) },
      { label: t('Reset to default'), iconName: 'restore', onClick: () => host._resetSysPanelOverride(panel.key) },
    ]
    : [
      { label: t('Edit'), iconName: 'edit', variant: 'primary', onClick: () => host._openEdit(index) },
      { label: t('Duplicate'), iconName: 'content-copy', onClick: () => Crud.duplicatePanel(host, panel.key) },
      { label: t('Delete'), iconName: 'delete', danger: true, onClick: () => host._confirmDelete(index) },
    ];
  return {
    kind: 'panel',
    iconName: descriptor?.icon || 'panels',
    title: panel.title || descriptor?.label || panel.key,
    subtitle: descriptor?.label || panel.type || '',
    description: descriptor?.description || '',
    preview: renderSimulatorPreview(context, panel, systemEntry ? -1 : index, previewRenderKey(context)),
    portrait: isPortraitModel(config.display_model),
    facts,
    actions,
    previewExpanded: !host._panelPreviewCollapsed,
    onTogglePreview: () => host._togglePanelPreview(),
    onClose: () => { host._selectedPanelKey = null; },
  };
}

/* ── selection and panel menus ────────────────────────────────────────────── */

/** Select a panel row; picking the selected row again clears the selection.
 * @param {any} host @param {string} key */
export function togglePanelSelection(host, key) {
  host._selectedPanelKey = host._selectedPanelKey === key ? null : key;
}

/** Fold or unfold the selected panel's render; the choice is remembered per browser.
 * @param {any} host */
export function togglePanelPreview(host) {
  host._panelPreviewCollapsed = !host._panelPreviewCollapsed;
  writePanelPreviewFolded(host._panelPreviewCollapsed);
}

/** @param {any} host @param {string} key */
export function togglePanelMenu(host, key) {
  host._panelSubmenuKey = null;
  const top = host._store.getState().ui.overlays.at(-1);
  if (top?.kind === 'panel-menu' && top.subject === key) {
    host._closePanelMenu();
    return;
  }
  host._store.actions.pushOverlay({
    kind: 'panel-menu',
    anchorKey: overlayAnchor('panel-menu', key),
    subject: key,
    draft: null,
  });
}

/** @param {any} host @param {string} key */
export function togglePanelSubmenu(host, key) {
  const opening = host._panelSubmenuKey !== key;
  host._panelSubmenuKey = opening ? key : null;
  if (opening && host.updateComplete) {
    void host.updateComplete.then(() => {
      host.renderRoot?.querySelector(`#haui-panel-submenu-${key} [role="menuitem"]`)?.focus();
    });
  }
}

/** @param {any} host @param {boolean} [restoreFocus] */
export function closePanelMenu(host, restoreFocus = true) {
  host._closeAnchoredPopover('panel-menu', restoreFocus);
}
