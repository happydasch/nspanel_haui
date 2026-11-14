import { LitElement, html, css } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { haStyle, editorContainerStyles, editorStyles } from '../../custom_components/nspanel_haui/frontend/styles.js';
import { previewStyles } from '../../custom_components/nspanel_haui/frontend/styles/preview-styles.js';
import { icon } from '../../custom_components/nspanel_haui/frontend/ui/icon.js';
import { button, iconButton, backButton } from '../../custom_components/nspanel_haui/frontend/ui/button.js';
import { badge, countBadge, statusDot } from '../../custom_components/nspanel_haui/frontend/ui/badge.js';
import { surface, sectionHeading } from '../../custom_components/nspanel_haui/frontend/ui/surface.js';
import { segmented } from '../../custom_components/nspanel_haui/frontend/ui/segmented.js';
import { sortHandle } from '../../custom_components/nspanel_haui/frontend/ui/sort-handle.js';
import { emptyState } from '../../custom_components/nspanel_haui/frontend/ui/empty-state.js';
import { menuItem, popover } from '../../custom_components/nspanel_haui/frontend/ui/popover.js';
import { relativeTime, uptimeLabel, versionLabel } from '../../custom_components/nspanel_haui/frontend/ui/format.js';
import { renderFooter } from '../../custom_components/nspanel_haui/frontend/toolbar.js';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';
import { sidebarFrame } from '../../custom_components/nspanel_haui/frontend/ui/sidebar.js';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { updateProgress } from '../../custom_components/nspanel_haui/frontend/ui/update-progress.js';
import { rolloutCard } from '../../custom_components/nspanel_haui/frontend/ui/rollout-card.js';

const noop = () => {};
const DIAGNOSTICS_DEMO = {
  name: 'kitchen',
  status: {
    connected: true,
    integration_version: '0.5.0',
    integration_version_mismatch: false,
    update: { state: 'installing', version: '0.5.0' },
    device_info: {
      ip: '192.0.2.10', ssid: 'HomeNet', rssi: -54, connection_uptime: 11_520, display_state: 'on',
      yaml_version: '0.5.0', tft_version: '0.5.0', last_disconnect_reason: 'heartbeat timeout',
      disconnected_since: new Date(Date.now() - 2 * 86_400_000).toISOString(),
    },
    logs: ['[2026-11-11T10:00:00+01:00] WARNING slow render', '[2026-11-11T10:00:01+01:00] INFO started'],
    idle_page: { state: 'pending', idle_in: 95 },
    connection_health: {
      drops_24h: 2,
      recent_drops: [
        { time: new Date(Date.now() - 3 * 3_600_000).toISOString(), reason: 'device reconnected' },
        { time: new Date(Date.now() - 9 * 3_600_000).toISOString(), reason: 'heartbeat timeout' },
      ],
      late_heartbeats_24h: 4,
      longest_heartbeat_gap: 9.2,
      heartbeat_interval: 5,
    },
    active_listeners: [
      { item_id: 'weather.home', attribute: 'temperature', callback_name: 'callback_weather' },
      { item_id: 'weather.home', attribute: 'pressure', callback_name: 'callback_weather' },
      { item_id: 'sensor.kitchen_temperature', attribute: null, callback_name: 'callback_inside_temp' },
      { item_id: 'light.kitchen', attribute: 'state', callback_name: 'on_state' },
    ],
    active_listener_count: 4,
    active_timers: [{ callback_name: 'tick', type: 'repeat', interval: 30 }],
    active_timer_count: 1,
  },
  // A Home Assistant stand-in for the watched entities: their states and its formatter.
  hass: {
    states: {
      'weather.home': { state: 'sunny', attributes: { friendly_name: 'Home weather' } },
      'sensor.kitchen_temperature': { state: 'unavailable', attributes: { friendly_name: 'Kitchen temperature' } },
    },
    formatEntityState: (stateObj) => (stateObj.state === 'sunny' ? 'Sunny' : 'Unavailable'),
  },
  onSettings: noop, onUpdates: noop, onLogs: noop, onCopyReport: noop, onToggleDiagnostics: noop,
};

class UiPrimitivesPreview extends LitElement {
  static styles = [haStyle, editorContainerStyles, editorStyles, previewStyles, css`
    :host { min-height: 100vh; background: var(--primary-background-color, #f5f5f5); }
    .gallery { width: min(100% - 32px, 1200px); margin: 0 auto; padding: 24px 0; }
    .gallery > h1 { margin: 0 0 6px; font-size: 24px; }
    .gallery > p { margin: 0 0 24px; color: var(--secondary-text-color); }
    .gallery-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap: 16px; align-items: start; }
    .gallery-card { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--divider-color); border-radius: 12px; background: var(--card-background-color); }
    .gallery-card h2 { margin: 0; font-size: 16px; }
    .gallery-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
    .gallery-stack { display: grid; gap: 12px; }
    .gallery-card .haui-surface { margin: 0; }
  `];

  render() {
    return html`<main class="gallery">
      <h1>NSPanel HAUI · Primitive preview</h1>
      <p>Test-only page. It uses the shipped Lit renderers and editor styles; focus controls or resize the browser to inspect states.</p>
      <div class="gallery-grid">
        <section class="gallery-card"><h2>Icons and buttons</h2>
          <div class="gallery-row">${icon('home')}${button({ label: 'Primary', iconName: 'check', variant: 'primary' })}${button({ label: 'Quiet', variant: 'quiet' })}${backButton({ label: 'Back', onClick: () => {} })}${iconButton({ label: 'Close', iconName: 'close' })}${iconButton({ label: 'Disabled', iconName: 'more', disabled: true })}</div>
          <div class="gallery-row">${button({ label: 'Saving', busy: true })}${button({ label: 'Unavailable', disabled: true })}${button({ label: 'Schedule', iconName: 'clock', detail: '2 entries' })}</div>
        </section>
        <section class="gallery-card"><h2>Badges and connection</h2>
          <div class="gallery-row">${['neutral', 'primary', 'success', 'warning', 'danger'].map((tone) => badge(tone, tone))}</div>
          <div class="gallery-row">${countBadge(12)}${countBadge(3, { tone: 'warning' })}${countBadge(1, { tone: 'danger' })}${countBadge(4, { title: '4 items' })}</div>
          <div class="gallery-row">${statusDot('online', 'Online')}${statusDot('offline', 'Offline')}${statusDot('stale', 'Stale')}${statusDot('unknown', 'Unknown')}</div>
        </section>
        <section class="gallery-card"><h2>Surfaces</h2>
          <div class="gallery-stack">${surface({ title: 'Plain surface', subtitle: 'Header, subtitle and body', body: 'Example content' })}${surface({ title: 'Gradient', variant: 'gradient', body: 'Summary surface' })}${surface({ title: 'Flush', variant: 'flush', body: 'Table content' })}</div>
          ${sectionHeading({ title: 'Section heading', subtitle: 'Optional subtitle', badge: countBadge(2) })}
        </section>
        <section class="gallery-card"><h2>Segmented control</h2>
          ${segmented({ label: 'Workspace view', value: 'preview', options: [{ label: 'Preview', value: 'preview' }, { label: 'Panels', value: 'panels', count: 3 }, { label: 'Errors', value: 'errors', count: 2, tone: 'danger' }, { label: 'Disabled', value: 'disabled', disabled: true }], onSelect() {} })}
        </section>
        <section class="gallery-card"><h2>Sorting</h2>
          ${sortHandle({ label: 'Kitchen device', onMoveUp() {}, onMoveDown() {} })}
          <p>Drag the handle or use its labelled move-up and move-down buttons.</p>
        </section>
        <section class="gallery-card"><h2>Empty state</h2>
          ${emptyState({ iconName: 'devices', title: 'No devices', message: 'Add a device to get started', actionLabel: 'Add device', action() {} })}
        </section>
        <section class="gallery-card"><h2>Popover and menu items</h2>
          ${popover({ open: true, id: 'preview-menu', label: 'Device actions', role: 'menu', content: html`${menuItem({ label: 'Configure', iconName: 'settings', onSelect() {} })}${menuItem({ label: 'Remove', iconName: 'close', danger: true, onSelect() {} })}${menuItem({ label: 'Unavailable', disabled: true, onSelect() {} })}` })}
        </section>
        <section class="gallery-card"><h2>Format helpers</h2>
          <p>${versionLabel('0.5.0')} · ${uptimeLabel(3 * 86400 + 3600)} · ${relativeTime(new Date(Date.now() - 60000).toISOString())}</p>
        </section>
        <section class="gallery-card"><h2>Preview stage</h2>
          <div class="gallery-stack">
            ${previewStage({ screen: html`<div style="width:200px;height:140px;background:#111"></div>`, state: 'ready' })}
            ${previewStage({ state: 'loading' })}
            ${previewStage({ state: 'no-panel' })}
            ${previewStage({ state: 'error', error: 'Session closed' })}
          </div>
        </section>
        <section class="gallery-card"><h2>Sidebar frame</h2>
          ${sidebarFrame({ label: 'Panel editor', body: html`<p style="padding:12px">Scrollable body</p>`, onClose() {} })}
        </section>
        <section class="gallery-card"><h2>Device details collapsed, diagnostics simple with issues</h2>
          ${deviceDetails({ ...DIAGNOSTICS_DEMO, detailsExpanded: false, status: {
            ...DIAGNOSTICS_DEMO.status,
            integration_version_mismatch: true,
            device_info: { ...DIAGNOSTICS_DEMO.status.device_info, tft_version: '0.4.9', tft_required_version: '0.5.0' },
          } })}
        </section>
        <section class="gallery-card"><h2>Device details and diagnostics expanded</h2>
          ${deviceDetails({ ...DIAGNOSTICS_DEMO, diagnosticsExpanded: true })}
        </section>
        <section class="gallery-card"><h2>Update progress: transferring, past its estimate, failed</h2>
          ${updateProgress({ label: 'Display update', progress: {
            phase: 'transferring', started_at: new Date(Date.now() - 300000).toISOString(),
            phase_started_at: new Date(Date.now() - 240000).toISOString(), expected_seconds: 900 } })}
          ${updateProgress({ label: 'Firmware update', progress: {
            phase: 'verifying', started_at: new Date(Date.now() - 400000).toISOString(),
            phase_started_at: new Date(Date.now() - 20000).toISOString(), expected_seconds: 180 } })}
          ${updateProgress({ label: 'Display update', progress: {
            phase: 'failed', started_at: null, phase_started_at: new Date().toISOString(), expected_seconds: 900 } })}
        </section>
        <section class="gallery-card"><h2>Update rollout: running, stopped</h2>
          ${rolloutCard({
            devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { update: { firmware_progress: {
              phase: 'transferring', started_at: new Date(Date.now() - 60000).toISOString(),
              phase_started_at: new Date(Date.now() - 50000).toISOString(), expected_seconds: 180 } } } }],
            rollout: { id: 1, state: 'running', devices: [
              { name: 'kitchen', kind: 'firmware', state: 'installing', error: null },
              { name: 'office', kind: 'tft', state: 'queued', error: null },
            ] },
            onCancel() {},
          })}
          ${rolloutCard({ devices: [], rollout: { id: 2, state: 'stopped', devices: [
            { name: 'kitchen', kind: 'firmware', state: 'failed', error: 'The panel did not reboot.' },
            { name: 'office', kind: 'tft', state: 'not_started', error: null },
          ] } })}
        </section>
        <section class="gallery-card"><h2>Persistent editor footer</h2>${renderFooter({})}</section>
      </div>
    </main>`;
  }
}

customElements.define('nspanel-ui-primitives-preview', UiPrimitivesPreview);
