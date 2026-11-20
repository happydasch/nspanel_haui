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
import { groupPanels, panelName, panelRoleMarkers } from './panel-utils.js';
import { resolveHomeKey, resolveIdleKeys, resolvePanelRoles, unknownPanelRef } from './panel-roles.js';
import { panelHasOptionErrors } from './option-rules.js';
import { buildPreviewContext } from './previews/context.js';
import { previewRenderKey } from './previews/previewer.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';
import { overlayAnchor } from './ui/popover.js';
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
  // The roles the hub plays: Home falls back to the first navigation panel while
  // none is configured (or the configured one is gone), and a key that names no
  // panel is not part of the idle carousel.
  const roleConfig = {
    homePanel: resolveHomeKey(panels, config, systemPanels),
    idleKeys: resolveIdleKeys(panels, config, systemPanels),
  };
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
  const nameOf = (panel) => panelName(panel, host._panelTypes) || t('Unnamed panel');
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
      // The rows just created — a setup's pages, or an added panel — say so for a moment.
      isNew: (host._newPanelKeys || []).includes(panel.key),
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
    // A device without panels gets one device-wide start instead of three
    // empty groups; a search keeps listing what matches it.
    setup: !query && panels.length === 0
      ? {
        title: t('This device has no panels yet'),
        actionLabel: t('Set up this device'),
        action: () => host._openQuickStart(host._selectedDevice),
      }
      : null,
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
  /** The name a role's panel is shown by: its panel's name, else its system label. */
  const labelOf = (panelKey) => {
    const entry = panels.find((panelEntry) => panelEntry.key === panelKey);
    if (entry) return panelName(entry, host._panelTypes) || t('Unnamed panel');
    return systemPanels.find((systemEntry) => systemEntry.key === panelKey)?.label || '';
  };
  if (!panel) {
    const roles = resolvePanelRoles(panels, config, systemPanels);
    /**
     * What a role's tile names and selects. Both roles answer alike: the panels
     * the device plays for the role, or - while the configured keys name none -
     * the first unknown key, so the tile says what is wrong instead of claiming
     * the role is unset. A tile selects only a panel the device has, and Home's
     * fallback to the first navigation panel shows only while nothing at all is
     * configured for it.
     *
     * @param {import('./panel-roles.js').PanelRole} role
     */
    const roleTile = (role) => {
      // While nothing is configured for a role, Home names the panel the device
      // opens instead; once something is configured, a stale key is reported.
      const keys = role.keys.length || role.missing.length
        ? role.keys
        : [role.fallback].filter(Boolean);
      const names = keys.map(labelOf);
      return {
        panelKey: names.length ? keys[0] : '',
        value: names.length > 1
          ? t('{name} and {count} more')
            .replace('{name}', names[0]).replace('{count}', String(names.length - 1))
          : names[0] || (role.missing.length ? unknownPanelRef(role.missing[0]) : ''),
      };
    };
    const home = roleTile(roles.home);
    const idle = roleTile(roles.idle);
    return {
      kind: 'overview',
      navigationCount: grouped.navigation.length,
      hiddenCount: grouped.hidden.length,
      popupCount: grouped.popups.length,
      homePanel: home.value,
      homePanelKey: home.panelKey,
      idlePanels: idle.value,
      idlePanelKey: idle.panelKey,
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
  // A popup override is not part of the device's page cycle, so it takes no role.
  // A role toggle says whether the panel is *configured* for it, not whether the
  // device plays it: pressing it on the panel Home falls back to assigns the role,
  // where a pressed state would clear an assignment the device never had.
  const roles = systemEntry ? [] : [
    {
      key: 'home',
      label: t('Home panel'),
      iconName: 'home',
      active: panel.key === config.home_panel,
      onToggle: () => host._togglePanelRole(panel.key, 'home'),
    },
    {
      key: 'idle',
      label: t('Idle panel'),
      iconName: 'sleep',
      active: resolveIdleKeys(panels, config, systemPanels).includes(panel.key),
      onToggle: () => host._togglePanelRole(panel.key, 'idle'),
    },
  ];
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
    roles,
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
