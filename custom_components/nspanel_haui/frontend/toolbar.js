/**
 * NSPanel HAUI - Editor - toolbar rendering.
 *
 * Renders the top toolbar: Add Panel button, device selector, device settings,
 * and a "More" dropdown.  Extracted from panel-table.js and combined with the
 * device bar previously rendered separately.
 */
import { html } from './lit-import.js';
import * as DeviceConfig from './device-config.js';
import {
  buildDeviceMap,
  getDeviceDisplayName,
  selectDevice,
  exportDeviceYaml,
  importDeviceYaml,
} from './device-manager.js';

/**
 * Render the Add Panel button - sits before the device selector.
 */
export function renderAddButton(host) {
  return html`
    <ha-icon-button title="Add Panel" @click=${() => host._openAdd()}>
      <ha-icon icon="mdi:plus"></ha-icon>
    </ha-icon-button>
  `;
}

/**
 * Render the action buttons (Cog, More) that go after the device selector.
 */
export function renderToolbarActions(host) {
  return html`
    <ha-icon-button title="Device settings" @click=${() => { DeviceConfig.openDeviceConfig(host); host.requestUpdate(); }}>
      <ha-icon icon="mdi:cog"></ha-icon>
    </ha-icon-button>

    <div class="toolbar-more" style="position:relative;display:inline-block;">
      <ha-icon-button title="More" class=${host._showToolbarMenu ? 'active' : ''} @click=${(e) => {
        e.stopPropagation();
        host._showToolbarMenu = !host._showToolbarMenu;
        host.requestUpdate();
      }}>
        <ha-icon icon="mdi:dots-vertical"></ha-icon>
      </ha-icon-button>
      ${host._showToolbarMenu ? html`
        <div class="dropdown-menu">
          <button class="dropdown-item" @click=${() => { host._showToolbarMenu = false; host._showDeviceInfo = true; host.requestUpdate(); }}>
            <ha-icon icon="mdi:information-outline"></ha-icon> Device Info
          </button>
          <button class="dropdown-item" @click=${() => { host._showToolbarMenu = false; host._showLogs = true; host.requestUpdate(); }}>
            <ha-icon icon="mdi:file-document-outline"></ha-icon> Device Logs
          </button>
          <button class="dropdown-item" @click=${() => { host._showToolbarMenu = false; importDeviceYaml(host); }}>
            <ha-icon icon="mdi:file-import"></ha-icon> Import YAML
          </button>
          <button class="dropdown-item" @click=${() => { host._showToolbarMenu = false; exportDeviceYaml(host); }}>
            <ha-icon icon="mdi:file-export"></ha-icon> Export YAML
          </button>
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * Render a device selector dropdown. Always shows as a dropdown so users
 * can see device names even when only one device exists.
 */
export function renderDeviceSelector(host) {
  if (!host._panels) return "";
  const deviceMap = buildDeviceMap(host);
  const displayNames = Object.keys(deviceMap);
  if (displayNames.length === 0) return "";
  const selected = host._selectedDevice;
  const selectedDisplayName = getDeviceDisplayName(host, selected);

  const options = displayNames.map((name) => {
    const devKey = deviceMap[name];
    const panelCount = (host._panels.devices[devKey]?.panels || []).length;
    const devConfig = (host._panels.devices[devKey]?.config) || {};
    const devEnabled = devConfig.enabled !== false;
    const suffix = devEnabled
      ? `\u00b7 ${panelCount} panel${panelCount !== 1 ? 's' : ''}`
      : `\u00b7 (disabled)`;
    return {
      value: name,
      label: `${name} ${suffix}`,
    };
  });

  return html`
    <ha-select
      class="toolbar-select"
      .value=${selectedDisplayName || ""}
      .options=${options}
      @selected=${(e) => selectDevice(host, e.detail.value)}
    ></ha-select>
  `;
}
