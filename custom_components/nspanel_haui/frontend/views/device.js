// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { deviceRail } from '../ui/device-rail.js';
import { segmented } from '../ui/segmented.js';
import { icon } from '../ui/icon.js';
import { backButton } from '../ui/button.js';
import { modalSidebar } from '../ui/sidebar.js';

/**
 * The preview controls of the workspace header: the Live toggle (off is the
 * simulated preview) and idle. Device tools stay in the contextual side stack.
 * They report intent; the workspace follows it and answers with its session
 * state.
 *
 * @param {{ preview: {mode: string, idle: boolean, canInteract: boolean},
 *   onMode: (mode: string) => void, onIdle: () => void }} options
 */
export function previewControls({ preview, onMode, onIdle }) {
  const live = preview.mode === 'live';
  const toolButton = (key, iconName, label, pressed, onClick, extra = {}) => html`
    <button type="button"
      class=${`haui-preview-tool ${key === 'live' ? 'is-live' : ''} ${pressed ? 'is-active' : ''}`.trim()}
      aria-pressed=${String(pressed)}
      aria-label=${label} title=${extra.title || label}
      ?disabled=${extra.disabled === true}
      @click=${onClick}>${icon(iconName)}<span>${label}</span></button>`;
  return html`<div class="haui-preview-controls">
    ${toolButton('idle', 'sleep', t('Idle'), preview.idle, onIdle, { disabled: !preview.canInteract })}
    ${toolButton('live', 'activity', t('Live'), live, () => onMode(live ? 'simulated' : 'live'), {
      title: live
        ? t('Live: touches act on the connected panel. Press to return to the simulated preview.')
        : t('Show the connected panel live instead of the simulated preview'),
    })}
  </div>`;
}

/**
 * Device frame: the workspace changes view while the side column stays contextual.
 * The view's lead card (`leadContent`, its next actions) heads the side column,
 * followed by the view's own cards (`sideContent`): on Preview the device facts,
 * on Panels the selected panel (or the list's overview). The side column sticks to
 * the viewport. Once the layout is one column, the lead card moves above the
 * workspace and the side stack below it; keyboard focus still follows the markup:
 * lead card, side stack, then workspace.
 * A modal sidebar (settings, panel editor, catalog) opens over the page; the side
 * column stays in place underneath it.
 *
 * @param {{ devices: any[], selectedName: string, title?: string, onBack?: () => void,
 *   panelCount: number, panelView: string,
 *   workspace: unknown, leadContent?: unknown, sideContent?: unknown, sidebarContent?: unknown, preview?: any,
 *   sideLabel?: string,
 *   panelSearch?: { query: string, onQuery: (query: string) => void }|null, railCollapsed?: boolean,
 *   sidebarOpen?: boolean, sidebarLabel?: string, onCloseSide?: () => void, onSelectDevice: (name: string) => void,
 *   onSwitchView: (view: string) => void, onMode?: (mode: string) => void, onIdle?: () => void }} model
 */
export function renderDeviceView({
  devices, selectedName, title = selectedName, onBack, panelCount, panelView, workspace, leadContent = nothing, sideContent = nothing, sidebarContent = nothing, preview, panelSearch = null, railCollapsed = false,
  sideLabel = t('Device details'),
  sidebarOpen = false, sidebarLabel = t('Editor sidebar'), onCloseSide, onSelectDevice, onSwitchView,
  onMode = () => {}, onIdle = () => {},
}) {
  const isPreview = panelView !== 'panels';
  const live = isPreview && preview?.mode === 'live';
  return html`<main class="haui-dashboard-content haui-device-screen">
    <header class="haui-device-head">
      ${onBack ? backButton({ label: t('Show all devices'), onClick: onBack }) : nothing}
      <h1>${title}</h1>
      ${devices.length > 1 ? deviceRail({
        devices, selected: selectedName, collapsed: railCollapsed, onSelect: onSelectDevice,
      }) : nothing}
    </header>
    <div class="haui-device-layout">
      <div class="haui-device-side">
        ${leadContent !== nothing ? html`<div class="haui-device-lead">${leadContent}</div>` : nothing}
        <aside class="haui-device-side-stack" aria-label=${sideLabel}>${sideContent}</aside>
      </div>
      <section class=${`haui-device-workspace${live ? ' is-live' : ''}`} aria-label=${t('Device workspace')}>
        <header class="haui-workspace-header">
          ${segmented({
            label: t('Workspace view'),
            value: panelView,
            options: [
              { label: t('Device'), value: 'preview', icon: 'monitor', disabled: panelCount === 0 },
              { label: t('Panels'), value: 'panels', icon: 'view-dashboard-outline', count: panelCount },
            ],
            onSelect: onSwitchView,
          })}
          ${isPreview && preview
            ? previewControls({ preview, onMode, onIdle })
            : nothing}
          ${!isPreview && panelSearch ? html`<label class="haui-panel-search">
            ${icon('search')}
            <input type="search" .value=${panelSearch.query} placeholder=${t('Search panels')}
              aria-label=${t('Search panels')}
              @input=${(event) => panelSearch.onQuery(event.currentTarget.value)}>
          </label>` : nothing}
        </header>
        <div class=${`haui-workspace-body${isPreview ? ' is-preview' : ''}`}>${workspace}</div>
      </section>
      ${sidebarOpen ? modalSidebar({
        label: sidebarLabel, ariaLabel: t('Editor sidebar'), body: sidebarContent, onClose: () => onCloseSide?.(),
      }) : nothing}
    </div>
  </main>`;
}
