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
  return html`<div class="card-content" style="text-align:center;padding:2rem;">
    <p>${message}</p>
  </div>`;
}



function renderPanelRow(host, p, panels, isNavPanel) {
  const pIdx = panels.indexOf(p);
  const navPanels = panels.filter(pp => pp.show_in_navigation !== false);
  const navIdx = navPanels.indexOf(p);
  const canMoveUp = isNavPanel && navIdx > 0;
  const canMoveDown = isNavPanel && navIdx >= 0 && navIdx < navPanels.length - 1;

  return html`
    <div class="panel-item">
      <span class="col-icons">${(() => {
        const dc = host._deviceConfig || {};
        const icons = [];
        if (p.key) {
          if (p.key === dc.home_panel) icons.push(html`<ha-icon icon="mdi:home-outline" title="Home panel"></ha-icon>`);
          if (p.key === dc.sleep_panel) icons.push(html`<ha-icon icon="mdi:weather-night" title="Sleep panel"></ha-icon>`);
          if (p.key === dc.wakeup_panel) icons.push(html`<ha-icon icon="mdi:weather-sunny" title="Wakeup panel"></ha-icon>`);
        }
        return icons.length ? icons : html`&nbsp;`;
      })()}</span>
      <span class="col-title type">${(() => {
        const pt = host._panelTypes.find(d => d.type_key === p.type);
        const label = pt ? pt.label : (p.type || "?");
        const displayTitle = p.title || "";
        return html`${displayTitle ? html`${displayTitle} — ` : ""}${label} <span class="col-key key">${p.key || "-"}</span>`;
      })()}</span>
      <div class="col-actions">
        ${isNavPanel ? html`
          <ha-icon-button
            title="Move up"
            ?disabled=${!canMoveUp}
            @click=${() => host._moveUp(p.key)}
          ><ha-icon icon="mdi:arrow-up"></ha-icon></ha-icon-button>
          <ha-icon-button
            title="Move down"
            ?disabled=${!canMoveDown}
            @click=${() => host._moveDown(p.key)}
          ><ha-icon icon="mdi:arrow-down"></ha-icon></ha-icon-button>
        ` : ''}
        <ha-icon-button
          title="Edit"
          @click=${() => host._openEdit(pIdx)}
        >
          <ha-icon icon="mdi:pencil"></ha-icon>
        </ha-icon-button>
        <div class="panel-more" data-pidx=${pIdx} style="position:relative;display:inline-block;">
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
          ${host._actionsMenuIndex === pIdx ? html`
            <div class="dropdown-menu">
              ${isNavPanel ? html`
                <button class="dropdown-item" ?disabled=${!canMoveUp}
                  @click=${() => { host._actionsMenuIndex = null; host._moveUp(p.key); }}>
                  <ha-icon icon="mdi:arrow-up"></ha-icon> Move Up
                </button>
                <button class="dropdown-item" ?disabled=${!canMoveDown}
                  @click=${() => { host._actionsMenuIndex = null; host._moveDown(p.key); }}>
                  <ha-icon icon="mdi:arrow-down"></ha-icon> Move Down
                </button>
                <div class="dropdown-divider"></div>
              ` : ''}

              <button class="dropdown-item"
                @click=${() => { host._actionsMenuIndex = null; host._toggleNavVisibility(p.key); }}>
                <ha-icon icon="${p.show_in_navigation !== false ? 'mdi:eye-off-outline' : 'mdi:eye-outline'}"></ha-icon>
                ${p.show_in_navigation !== false ? 'Non-Navigation' : 'Navigation'}
              </button>
              <div class="dropdown-divider"></div>

              ${p.key && host._deviceConfig && host._deviceConfig.home_panel !== p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('home_panel', p.key); }}>
                  <ha-icon icon="mdi:home-outline"></ha-icon> Set Home
                </button>
              ` : (p.key && host._deviceConfig && host._deviceConfig.home_panel === p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('home_panel', ''); }}>
                  <ha-icon icon="mdi:home-remove-outline"></ha-icon> Unset Home
                </button>
              ` : '')}
              ${p.key && host._deviceConfig && host._deviceConfig.sleep_panel !== p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('sleep_panel', p.key); }}>
                  <ha-icon icon="mdi:weather-night"></ha-icon> Set Sleep
                </button>
              ` : (p.key && host._deviceConfig && host._deviceConfig.sleep_panel === p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('sleep_panel', ''); }}>
                  <ha-icon icon="mdi:cancel"></ha-icon> Unset Sleep
                </button>
              ` : '')}
              ${p.key && host._deviceConfig && host._deviceConfig.wakeup_panel !== p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('wakeup_panel', p.key); }}>
                  <ha-icon icon="mdi:weather-sunny"></ha-icon> Set Wakeup
                </button>
              ` : (p.key && host._deviceConfig && host._deviceConfig.wakeup_panel === p.key ? html`
                <button class="dropdown-item"
                  @click=${() => { host._actionsMenuIndex = null; host._setSpecialPanel('wakeup_panel', ''); }}>
                  <ha-icon icon="mdi:cancel"></ha-icon> Unset Wakeup
                </button>
              ` : '')}

              <div class="dropdown-divider"></div>
              <button class="dropdown-item danger"
                @click=${() => { host._actionsMenuIndex = null; host._confirmDelete(pIdx); }}>
                <ha-icon icon="mdi:delete"></ha-icon> Delete
              </button>
            </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}



function renderSystemPanelRow(host, sp) {
  return html`
    <div class="panel-item system-panel-item">
      <span class="col-icons">
        <ha-icon icon="mdi:cog-outline" title="System panel"></ha-icon>
      </span>
      <span class="col-title type">
        ${sp.label}
        <span class="col-key key">${sp.key || "-"}</span>
      </span>
      <span class="col-actions"></span>
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
      <ha-icon-button
        title="Info"
        label="Info"
        @click=${() => { host._showDeviceInfo = true; host.requestUpdate(); }}
      >
        <ha-icon icon="mdi:information-outline"></ha-icon>
      </ha-icon-button>
      <div class="panel-more" style="position:relative;display:inline-block;">
        <ha-icon-button
          title="Device actions"
          label="Device actions"
          @click=${() => host._toggleHeaderMenu()}
        >
          <ha-icon icon="mdi:dots-vertical"></ha-icon>
        </ha-icon-button>
        ${host._actionsMenuIndex === '__header__' ? html`
          <div class="dropdown-menu">
            <button class="dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderSettings()}>
              <ha-icon icon="mdi:cog-outline"></ha-icon>
              Settings
            </button>
            <button class="dropdown-item"
                    @click=${() => { host._showLogs = true; host.requestUpdate(); }}>
              <ha-icon icon="mdi:file-document-outline"></ha-icon>
              Logs
            </button>
            <div class="dropdown-divider"></div>
            <button class="dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderImportYaml()}>
              <ha-icon icon="mdi:file-import"></ha-icon>
              Import YAML
            </button>
            <button class="dropdown-item${host._selectedDevice ? '' : ' disabled'}"
                    ?disabled=${!host._selectedDevice}
                    @click=${() => host._onHeaderExportYaml()}>
              <ha-icon icon="mdi:file-export"></ha-icon>
              Export YAML
            </button>
          </div>
        ` : ""}
      </div>
    </div>
    ${panels.length === 0
      ? renderEmptyCard('No panels configured yet.')
      : html`
        <div class="plain-panel-group">
          <div class="plain-group-title">Navigation (${navPanels.length} panels)</div>
          ${navPanels.map(p => renderPanelRow(host, p, panels, true))}
        </div>
        <div class="plain-panel-group">
          <div class="plain-group-title">Non-Navigation (${hiddenPanels.length} panels)</div>
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
    <details class="panel-group system-panel-group"
        @toggle=${(e) => { host.__systemPanelsOpen = e.target.open; }}>
      <summary class="plain-group-title">System Panels (${host._panels.system_panels.length})</summary>
      ${host._panels.system_panels.map(sp => renderSystemPanelRow(host, sp))}
    </details>
  `;
}


