/**
 * NSPanel HAUI - Editor - panel list rendering.
 *
 * Extracted from haui-editor.js render() method.  Every function takes the Lit
 * element instance (`host`) as its first parameter.
 */
import { html } from './lit-import.js';
import { renderDeviceSelector, renderDeviceInfoStrip } from './toolbar.js';

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
 * Build badge icons for home/sleep/wakeup panel designations.
 */
function renderBadges(p, dc) {
  const badges = [];
  if (!p.key) return badges;
  if (p.key === dc.home_panel) badges.push(html`<span class="pl-badge" title="Home panel"><ha-icon icon="mdi:home-outline"></ha-icon></span>`);
  if (p.key === dc.sleep_panel) badges.push(html`<span class="pl-badge" title="Sleep panel"><ha-icon icon="mdi:weather-night"></ha-icon></span>`);
  if (p.key === dc.wakeup_panel) badges.push(html`<span class="pl-badge" title="Wakeup panel"><ha-icon icon="mdi:weather-sunny"></ha-icon></span>`);
  return badges;
}

/**
 * Build dropdown menu items for a panel row.
 * @returns {Array<{icon:string, label:string, action:Function, disabled?:boolean, danger?:boolean}|'divider'>}
 */
function buildPanelDropdownItems(host, p, pIdx, canMoveUp, canMoveDown) {
  const dc = host._deviceConfig;
  const items = [];

  items.push(
    { icon: 'mdi:arrow-up', label: 'Move Up', disabled: !canMoveUp, action: () => host._moveUp(p.key) },
    { icon: 'mdi:arrow-down', label: 'Move Down', disabled: !canMoveDown, action: () => host._moveDown(p.key) },
  );
  items.push('divider');

  items.push({
    icon: p.show_in_navigation !== false ? 'mdi:eye-off-outline' : 'mdi:eye-outline',
    label: p.show_in_navigation !== false ? 'Non-Navigation' : 'Navigation',
    action: () => host._toggleNavVisibility(p.key),
  });
  items.push('divider');

  if (p.key && dc) {
    for (const [field, icon, labelSet, labelUnset] of [
      ['home_panel', 'mdi:home-outline', 'Set Home', 'Unset Home'],
      ['sleep_panel', 'mdi:weather-night', 'Set Sleep', 'Unset Sleep'],
      ['wakeup_panel', 'mdi:weather-sunny', 'Set Wakeup', 'Unset Wakeup'],
    ]) {
      if (dc[field] === p.key) {
        items.push({ icon: 'mdi:cancel', label: labelUnset, action: () => host._setSpecialPanel(field, '') });
      } else {
        items.push({ icon, label: labelSet, action: () => host._setSpecialPanel(field, p.key) });
      }
    }
  }

  items.push('divider');
  items.push({ icon: 'mdi:delete', label: 'Delete', danger: true, action: () => host._confirmDelete(pIdx) });

  return items;
}

/**
 * Render the dropdown menu for a panel row.
 * @param {import("lit").html} _html  (unused, for lit-html context)
 */
function renderPanelDropdown(host, pIdx, items) {
  return html`
    <div class="pl-dropdown">
      ${items.map(item => item === 'divider'
        ? html`<div class="pl-dropdown-divider"></div>`
        : html`<button class="pl-dropdown-item${item.danger ? ' danger' : ''}"
                ?disabled=${item.disabled}
                @click=${() => { host._actionsMenuIndex = null; item.action(); }}>
            <ha-icon icon=${item.icon}></ha-icon> ${item.label}
          </button>`
      )}
    </div>`;
}

function renderPanelRow(host, p, panels, isNavPanel) {
  const pIdx = panels.indexOf(p);
  const navPanels = panels.filter(pp => pp.show_in_navigation !== false);
  const hiddenPanels = panels.filter(pp => pp.show_in_navigation === false);
  const navIdx = navPanels.indexOf(p);
  const hiddenIdx = hiddenPanels.indexOf(p);
  const canMoveUp = isNavPanel ? navIdx > 0 : hiddenIdx > 0;
  const canMoveDown = isNavPanel ? (navIdx >= 0 && navIdx < navPanels.length - 1) : (hiddenIdx >= 0 && hiddenIdx < hiddenPanels.length - 1);
  const dc = host._deviceConfig || {};
  const pt = host._panelTypes.find(d => d.type_key === p.type);
  const badges = renderBadges(p, dc);

  return html`
    <div class="pl-row">
      <span class="pl-type">${pt ? html`<ha-icon icon=${pt.icon}></ha-icon>` : ""}</span>
      <span class="pl-title">${p.title || html`<span class="pl-unnamed">Unnamed</span>`}</span>
      <span class="pl-spacer"></span>
      <span class="pl-key">${p.key || '-'}</span>
      ${badges.length ? html`<span class="pl-badges">${badges}</span>` : ''}
      <div class="pl-actions">
        <ha-icon-button title="Move Up" class="pl-move-btn" ?disabled=${!canMoveUp} @click=${() => host._moveUp(p.key)}>
          <ha-icon icon="mdi:arrow-up"></ha-icon>
        </ha-icon-button>
        <ha-icon-button title="Move Down" class="pl-move-btn" ?disabled=${!canMoveDown} @click=${() => host._moveDown(p.key)}>
          <ha-icon icon="mdi:arrow-down"></ha-icon>
        </ha-icon-button>
        <ha-icon-button title="Edit" @click=${() => host._openEdit(pIdx)}>
          <ha-icon icon="mdi:pencil"></ha-icon>
        </ha-icon-button>
        <div class="pl-more" data-pidx=${pIdx}>
          <ha-icon-button
            title="More"
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
            ? renderPanelDropdown(host, pIdx, buildPanelDropdownItems(host, p, pIdx, canMoveUp, canMoveDown))
            : ''}
        </div>
      </div>
    </div>
  `;
}

function renderSystemPanelRow(host, sp) {
  const dc = host._deviceConfig || {};
  const badges = renderBadges(sp, dc);

  return html`
    <div class="pl-row pl-sys-row">
      <span class="pl-type"><ha-icon icon=${sp.icon}></ha-icon></span>
      <span class="pl-title">${sp.label}</span>
      <span class="pl-spacer"></span>
      <span class="pl-key">${sp.key || '-'}</span>
      ${html`<span class="pl-badges">${badges}</span>`}
      <span class="pl-actions"></span>
    </div>
  `;
}

export function renderPanelTable(host) {
  const devices = Object.keys(host._panels.devices || {});
  const panels = host._selectedDevice
    ? (host._panels.devices[host._selectedDevice] && host._panels.devices[host._selectedDevice].panels) || []
    : [];

  // No device selected
  if (!host._selectedDevice) {
    if (devices.length === 0) {
      return renderEmptyCard("No devices found");
    }
    return html`
      <div class="device-selector-bar">
        ${renderDeviceSelector(host)}
      </div>
      <p style="padding:16px;">Select a device to edit its panels.</p>
    `;
  }

  const navPanels = panels.filter(p => p.show_in_navigation !== false);
  const hiddenPanels = panels.filter(p => p.show_in_navigation === false);

  return html`
    <div class="panel-list-header">
      <ha-icon-button
        title="Add Panel"
        label="Add Panel"
        @click=${() => host._openAdd()}
      >
        <ha-icon icon="mdi:plus"></ha-icon>
      </ha-icon-button>
      <div class="device-selector-inline">
        ${renderDeviceSelector(host)}
      </div>
      <div class="pl-more">
        <ha-icon-button
          title="Device actions"
          label="Device actions"
          @click=${() => host._toggleHeaderMenu()}
        >
          <ha-icon icon="mdi:dots-vertical"></ha-icon>
        </ha-icon-button>
        ${host._actionsMenuIndex === '__header__' ? html`
          <div class="pl-dropdown">
            <button class="pl-dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => { host._showDeviceInfo = true; host._actionsMenuIndex = null; host.requestUpdate(); }}>
              <ha-icon icon="mdi:information-outline"></ha-icon>
              Info
            </button>
            <button class="pl-dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderSettings()}>
              <ha-icon icon="mdi:cog-outline"></ha-icon>
              Settings
            </button>
            <div class="pl-dropdown-divider"></div>
            <button class="pl-dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderImportYaml()}>
              <ha-icon icon="mdi:file-import"></ha-icon>
              Import YAML
            </button>
            <button class="pl-dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderExportYaml()}>
              <ha-icon icon="mdi:file-export"></ha-icon>
              Export YAML
            </button>
            <div class="pl-dropdown-divider"></div>
            <button class="pl-dropdown-item"
                    @click=${() => { host._showLogs = true; host._actionsMenuIndex = null; host.requestUpdate(); }}>
              <ha-icon icon="mdi:file-document-outline"></ha-icon>
              Logs
            </button>
          </div>
        ` : ""}
      </div>
    </div>
    ${panels.length === 0
      ? renderEmptyCard('No panels configured yet.')
      : html`
        <div class="panel-group">
          <div class="group-title">Navigation (${navPanels.length} panels)</div>
          ${navPanels.map(p => renderPanelRow(host, p, panels, true))}
        </div>
        <div class="panel-group">
          <div class="group-title">Non-Navigation (${hiddenPanels.length} panels)</div>
          ${hiddenPanels.map(p => renderPanelRow(host, p, panels, false))}
        </div>
      `}
    <div class="card-footer">
      ${renderDeviceInfoStrip(host)}
    </div>
  `;
}

/**
 * Render system panels section (outside the card, no borders).
 */
export function renderSystemPanels(host) {
  if (!host._panels?.system_panels?.length) return "";
  return html`
    <details class="panel-group" ?open=${host.__systemPanelsOpen}
      @toggle=${(e) => { host.__systemPanelsOpen = e.target.open; }}>
      <summary class="group-title" style="cursor:pointer;">
        System Panels (${host._panels.system_panels.length} panels)
      </summary>
      ${host._panels.system_panels.map(sp => renderSystemPanelRow(host, sp))}
    </details>
  `;
}
