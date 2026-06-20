/**
 * NSPanel HAUI - Editor - panel list rendering.
 *
 * Extracted from haui-editor.js render() method.  Every function takes the Lit
 * element instance (`host`) as its first parameter.
 */
import { html } from './lit-import.js';
import { renderBadges, computeFilteredPanels, getPanelMoveState, getSystemPanelKeys } from './panel-utils.js';
import { renderSystemPanelCard } from './panel-sys-grid.js';
import { POPUP_TO_USER_TYPE } from './constants.js';

/**
 * Render a consistent empty-state card for use across the editor.
 * @param {string} message - Message to display inside the card.
 * @returns {import("lit").TemplateResult}
 */
export function renderEmptyCard(message) {
  return html`<div class="card-content panel-table-empty">
    <p>${message}</p>
  </div>`;
}

/**
 * Build dropdown menu items for a panel row.
 * @returns {Array<{icon:string, label:string, action:Function, disabled?:boolean, danger?:boolean}|'divider'>}
 */
export function buildPanelDropdownItems(host, p, pIdx, canMoveUp, canMoveDown) {
  const dc = host._deviceConfig;
  const isSysOverride = !!(p.key && host._panels?.system_panels?.some(sp => sp.key === p.key));
  const items = [];

  items.push(
    { icon: 'mdi:pencil-outline', label: host._t('Edit'), action: () => host._openEdit(pIdx) }
  );

  items.push('divider');

  items.push(
    { icon: 'mdi:arrow-up', label: host._t('Move Up'), disabled: !canMoveUp, action: () => host._moveUp(p.key) },
    { icon: 'mdi:arrow-down', label: host._t('Move Down'), disabled: !canMoveDown, action: () => host._moveDown(p.key) },
  );
  items.push('divider');

  items.push({
    icon: p.show_in_navigation !== false ? 'mdi:eye-off-outline' : 'mdi:eye-outline',
    label: p.show_in_navigation !== false ? host._t('Non-Navigation') : host._t('Navigation'),
    action: () => host._toggleNavVisibility(p.key),
  });
  items.push('divider');

  if (p.key && dc) {
    for (const [field, icon, labelSet, labelUnset] of [
      ['home_panel', 'mdi:home-outline', host._t('Set Home'), host._t('Unset Home')],
      ['sleep_panel', 'mdi:weather-night', host._t('Set Sleep'), host._t('Unset Sleep')],
      ['wakeup_panel', 'mdi:weather-sunny', host._t('Set Wakeup'), host._t('Unset Wakeup')],
    ]) {
      if (dc[field] === p.key) {
        items.push({ icon: 'mdi:cancel', label: labelUnset, action: () => host._setSpecialPanel(field, '') });
      } else {
        items.push({ icon, label: labelSet, action: () => host._setSpecialPanel(field, p.key) });
      }
    }
  }

  items.push('divider');
  if (isSysOverride) {
    items.push({
      icon: 'mdi:restore',
      label: host._t('Reset to default'),
      action: () => host._resetSysPanelOverride(p.key),
    });
  } else {
    items.push({ icon: 'mdi:delete-outline', label: host._t('Delete'), danger: true, action: () => host._confirmDelete(pIdx) });
  }

  return items;
}

/**
 * Render the dropdown menu for a panel row.
 * @param {import("lit").html} _html  (unused, for lit-html context)
 */
export function renderPanelDropdown(host, pIdx, items, onClose) {
  return html`
    <div class="pl-dropdown">
      ${items.map(item => item === 'divider'
        ? html`<div class="pl-dropdown-divider"></div>`
        : html`<button class="pl-dropdown-item${item.danger ? ' danger' : ''}"
                ?disabled=${item.disabled}
                @click=${() => { if (onClose) onClose(); item.action(); }}>
            <ha-icon icon=${item.icon}></ha-icon> ${item.label}
          </button>`
      )}
    </div>`;
}

/**
 * Check if a system panel is editable (i.e. has a corresponding user-facing type).
 * @param {object} sysPanel - system panel entry
 * @returns {boolean}
 */
export function isSysPanelEditable(sysPanel) {
  return !!POPUP_TO_USER_TYPE[sysPanel.type];
}

function renderPanelRow(host, p, panels, isNavPanel) {
  const { pIdx, canMoveUp, canMoveDown } = getPanelMoveState(p, panels, isNavPanel);
  const dc = host._deviceConfig || {};
  const pt = host._panelTypes.find(d => d.type_key === p.type);
  // For override panels (user panels with a system panel key), don't fall
  // back to the type label as title — the override has no title of its own
  // and the runtime falls back to the system panel's label instead.
  const isOverride = host._panels?.system_panels?.some(sp => sp.key === p.key);
  const badges = renderBadges(p, dc, isOverride);

  return html`
    <div class="pl-row">
      <span class="pl-card-type-icon">${pt ? html`<ha-icon icon=${pt.icon}></ha-icon>` : ""}</span>
      <span class="pl-title">${p.title || (isOverride ? "" : html`<span class="pl-unnamed">${(pt && pt.label) || host._t('Unnamed')}</span>`)}</span>
      <div class="pl-meta">
        <span class="pl-key">${p.key || '-'}</span>
        ${badges.length ? html`<span class="pl-badges">${badges}</span>` : ''}
      </div>
      <div class="pl-actions">
        <ha-icon-button title=${host._t('Move Up')} class="pl-move-btn" ?disabled=${!canMoveUp} @click=${() => host._moveUp(p.key)}>
          <ha-icon icon="mdi:arrow-up"></ha-icon>
        </ha-icon-button>
        <ha-icon-button title=${host._t('Move Down')} class="pl-move-btn" ?disabled=${!canMoveDown} @click=${() => host._moveDown(p.key)}>
          <ha-icon icon="mdi:arrow-down"></ha-icon>
        </ha-icon-button>
        <ha-icon-button title=${host._t('Edit')} class="pl-edit-btn" @click=${() => host._openEdit(pIdx)}>
          <ha-icon icon="mdi:pencil-outline"></ha-icon>
        </ha-icon-button>
        <div class="pl-more" data-pidx=${pIdx}>
          <ha-icon-button
            title=${host._t('More')}
            class=${host._actionsMenuIndex === pIdx ? 'active' : ''}
            @click=${(e) => {
              e.stopPropagation();
              host._actionsMenuIndex = host._actionsMenuIndex === pIdx ? null : pIdx;
              host.requestUpdate();
            }}
          >
            <ha-icon icon="mdi:dots-vertical"></ha-icon>
          </ha-icon-button>
          ${host._actionsMenuIndex === pIdx
            ? renderPanelDropdown(host, pIdx, buildPanelDropdownItems(host, p, pIdx, canMoveUp, canMoveDown), () => { host._actionsMenuIndex = null; })
            : ''}
        </div>
      </div>
    </div>
  `;
}

function renderSystemPanelRow(host, sp) {
  const dc = host._deviceConfig || {};
  const editable = isSysPanelEditable(sp);
  const hasOverride = editable && host._devicePanels().some(p => p.key === sp.key);
  const badges = renderBadges(sp, dc, hasOverride);

  return html`
    <div class="pl-row pl-sys-row">
      <span class="pl-card-type-icon"><ha-icon icon=${sp.icon}></ha-icon></span>
      <span class="pl-title">${sp.label}</span>
      <div class="pl-meta">
        <span class="pl-key">${sp.key || '-'}</span>
        ${badges.length ? html`<span class="pl-badges">${badges}</span>` : ''}
      </div>
      <span class="pl-actions">
        ${editable ? html`
          ${hasOverride ? html`
            <ha-icon-button title=${host._t('Reset to default')} @click=${() => host._resetSysPanelOverride(sp.key)}>
              <ha-icon icon="mdi:restore"></ha-icon>
            </ha-icon-button>
          ` : ''}
          <ha-icon-button title=${host._t('Edit System Panel')} @click=${() => host._openSysPanelEdit(sp)}>
            <ha-icon icon="mdi:pencil-outline"></ha-icon>
          </ha-icon-button>
        ` : ''}
      </span>
    </div>
  `;
}

/**
 * Main entry point: render the panel list (table) view.
 */

export function renderPanelTable(host) {
  const devices = Object.keys(host._panels.devices || {});
  const panels = host._selectedDevice
    ? (host._panels.devices[host._selectedDevice] && host._panels.devices[host._selectedDevice].panels) || []
    : [];

  // No device selected
  if (!host._selectedDevice) {
    if (devices.length === 0) {
      return renderEmptyCard(host._t('No devices found'));
    }
    return html`
      <p class="no-device-selected">${host._t('Select a device to edit its panels.')}</p>
    `;
  }

  const sysPanelKeys = getSystemPanelKeys(host);
  const { navPanels, hiddenPanels } = computeFilteredPanels(panels, sysPanelKeys);
  const writeOpen = (key, v) => {
    try { localStorage.setItem(key, v); } catch (_e) { /* ignore */ }
  };

  return html`
    ${panels.length === 0
      ? renderEmptyCard(host._t('No panels configured yet.'))
      : html`
        <details class="panel-group" ?open=${host.__navPanelsOpen}
          @toggle=${(e) => { host.__navPanelsOpen = e.target.open; writeOpen('haui_navPanelsOpen', e.target.open); }}>
          <summary class="group-title">${host._t('Navigation')} (${navPanels.length} ${host._t('panels')})</summary>
          ${navPanels.map(p => renderPanelRow(host, p, panels, true))}
        </details>
        <details class="panel-group" ?open=${host.__hiddenPanelsOpen}
          @toggle=${(e) => { host.__hiddenPanelsOpen = e.target.open; writeOpen('haui_hiddenPanelsOpen', e.target.open); }}>
          <summary class="group-title">${host._t('Non-Navigation')} (${hiddenPanels.length} ${host._t('panels')})</summary>
          ${hiddenPanels.map(p => renderPanelRow(host, p, panels, false))}
        </details>
      `}
  `;
}

/**
 * Render system panels section (outside the card, no borders).
 * @param {string} [viewMode] - 'grid' or 'list' (defaults to 'list')
 */
export function renderSystemPanels(host, viewMode) {
  if (!host._panels?.system_panels?.length) return "";
  const isGrid = viewMode === 'grid';
  const writeOpen = (v) => {
    try { localStorage.setItem('haui_systemPanelsOpen', v); } catch (_e) { /* ignore */ }
  };
  return html`
    <details class="panel-group" ?open=${host.__systemPanelsOpen}
      @toggle=${(e) => { host.__systemPanelsOpen = e.target.open; writeOpen(e.target.open); }}>
      <summary class="group-title">
        ${host._t('System Panels')} (${host._panels.system_panels.length} ${host._t('panels')})
      </summary>
      ${isGrid
        ? html`<div class="pg-grid">${host._panels.system_panels.map(sp => renderSystemPanelCard(host, sp))}</div>`
        : host._panels.system_panels.map(sp => renderSystemPanelRow(host, sp))}
    </details>
  `;
}
