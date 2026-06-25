/**
 * NSPanel HAUI - Editor - panel grid view rendering.
 *
 * An alternative to panel-table.js that displays panels as visual cards
 * in a CSS Grid layout.  Every function takes the Lit element instance
 * (`host`) as its first parameter.
 */
import { html } from './lit-import.js';
import { renderEmptyCard } from './panel-table.js';
import { renderPanelDropdown, buildPanelDropdownItems } from './panel-table.js';
import { renderPanelPreview } from './panel-previews.js';
import { renderBadges, getPanelMoveState, computeFilteredPanels, getSystemPanelKeys } from './panel-utils.js';
import { renderCardChrome, renderCardActions } from './panel-card.js';
import { t } from './localize.js';

/**
 * Render a single panel card for the grid view.
 * Shows icon, title, key, badges, and a more-actions dropdown.
 */
function renderPanelCard(host, p, panels, isNavPanel) {
  const { pIdx, canMoveUp, canMoveDown } = getPanelMoveState(p, panels, isNavPanel);
  const dc = host._deviceConfig || {};
  const pt = host._panelTypes.find(d => d.type_key === p.type);
  // For override panels (user panels with a system panel key), don't fall
  // back to the type label as title — the override has no title of its own
  // and the runtime falls back to the system panel's label instead.
  const isOverride = host._panels?.system_panels?.some(sp => sp.key === p.key);
  const badges = renderBadges(p, dc, isOverride);

  const previewResult = renderPanelPreview(host, p, pIdx, pt);
  const onClick = () => host._openEdit(pIdx);

  // Compute simulated header button icons based on panel/device config,
  // matching the Python FunctionButtonMixin._auto_assign_fncs() logic.
  const showInNav = p.show_in_navigation !== false;
  const isHome = !!(dc.home_panel && p.key === dc.home_panel);
  const hasHomeBtn = p.show_home_button ?? dc.show_home_button ?? false;
  const hasNotifBtn = p.show_notifications_button ?? dc.show_notifications_button ?? true;
  const hasSleepBtn = p.show_sleep_button ?? dc.show_sleep_button ?? false;
  // left_pri: nav → PREV, non-nav → UP
  let leftPri;
  if (showInNav) {
    leftPri = 'mdi:chevron-left';
  } else {
    leftPri = 'mdi:chevron-up';
  }
  // Pagination limit: grid shows 6 items/page, row shows 5.
  const PAGINATION_LIMITS = { grid: 6, row: 5 };
  const items = (p && p.items) || [];
  const paginationLimit = PAGINATION_LIMITS[p.type];
  const hasPagination = paginationLimit != null && items.length > paginationLimit;

  // Right button auto-assignment (mirrors Python FunctionButtonMixin + grid/row
  // overrides for pagination):
  //   - nav + pagination → NEXT on right_pri, pagination on right_sec
  //   - nav + no pagination → NEXT on right_pri
  //   - non-nav + pagination → CLOSE on right_pri, pagination on right_sec
  //   - non-nav + no pagination → CLOSE on right_pri (auto-assigned via _auto_assign_fncs)
  let rightPri, rightSec;
  if (showInNav) {
    rightPri = 'mdi:chevron-right';
    rightSec = hasPagination ? { icon: 'mdi:chevron-double-down', accent: true } : '';
  } else if (hasPagination) {
    rightPri = 'mdi:close';
    rightSec = { icon: 'mdi:chevron-double-down', accent: true };
  } else {
    rightPri = 'mdi:close';
    rightSec = '';
  }
  // left_sec: not-home+home_btn → HOME, home+notif → NOTIF, home+sleep → SLEEP
  let leftSec = '';
  if (!isHome && hasHomeBtn) {
    leftSec = 'mdi:home-outline';
  } else if (isHome && hasNotifBtn) {
    leftSec = 'mdi:email-outline';
  } else if (isHome && hasSleepBtn) {
    leftSec = 'mdi:sleep';
  }
  const headerButtons = { left: [leftPri, leftSec], right: [rightSec, rightPri] };
  // Preview renderers can override any of the 4 header button positions
  if (previewResult.headerButtonOverrides) {
    const o = previewResult.headerButtonOverrides;
    if (o.leftPri !== undefined) headerButtons.left[0] = o.leftPri;
    if (o.leftSec !== undefined) headerButtons.left[1] = o.leftSec;
    if (o.rightPri !== undefined) headerButtons.right[1] = o.rightPri;
    if (o.rightSec !== undefined) headerButtons.right[0] = o.rightSec;
  }

  const actions = renderCardActions(host, p.key, (close) =>
    renderPanelDropdown(host, pIdx, buildPanelDropdownItems(host, p, pIdx, canMoveUp, canMoveDown), close)
  );

  return html`
    <div class="pg-card">
      ${renderCardChrome({
        icon: pt?.icon,
        title: p.title,
        titleFallback: isOverride ? '' : (pt ? pt.label : t('Unnamed')),
        key: p.key,
        badges,
        hasHeader: pt ? pt.has_header !== false : true,
        headerButtons,
        preview: previewResult,
        description: pt ? pt.description : '',
        onClick,
        actions,
      })}
    </div>
  `;
}

/**
 * Main entry point: render the panel grid view.
 *
 * Mirrors the structure of renderPanelTable() from panel-table.js:
 * - No device selected → prompt (toolbar with selector is rendered by editor)
 * - Device selected → grid sections
 */
export function renderPanelGrid(host) {
  const devices = Object.keys(host._panels.devices || {});
  const panels = host._selectedDevice
    ? (host._panels.devices[host._selectedDevice] && host._panels.devices[host._selectedDevice].panels) || []
    : [];

  // No device selected
  if (!host._selectedDevice) {
    if (devices.length === 0) {
      return renderEmptyCard(t('No devices found'));
    }
    return html`
      <p class="no-device-selected">${t('Select a device to edit its panels.')}</p>
    `;
  }

  const sysPanelKeys = getSystemPanelKeys(host);
  const { navPanels, hiddenPanels } = computeFilteredPanels(panels, sysPanelKeys);
  const writeOpen = (key, v) => {
    try { localStorage.setItem(key, v); } catch (_e) { /* ignore */ }
  };

  return html`
    ${panels.length === 0
      ? renderEmptyCard(t('No panels configured yet.'))
      : html`
        <details class="panel-group" ?open=${host.__navPanelsOpen}
          @toggle=${(e) => { host.__navPanelsOpen = e.target.open; writeOpen('haui_navPanelsOpen', e.target.open); }}>
          <summary class="group-title">${t('Navigation')} (${navPanels.length} ${t('panels')})</summary>
          <div class="pg-grid">
            ${navPanels.map(p => renderPanelCard(host, p, panels, true))}
          </div>
        </details>
        <details class="panel-group" ?open=${host.__hiddenPanelsOpen}
          @toggle=${(e) => { host.__hiddenPanelsOpen = e.target.open; writeOpen('haui_hiddenPanelsOpen', e.target.open); }}>
          <summary class="group-title">${t('Non-Navigation')} (${hiddenPanels.length} ${t('panels')})</summary>
          <div class="pg-grid">
            ${hiddenPanels.map(p => renderPanelCard(host, p, panels, false))}
          </div>
        </details>
      `}
  `;
}
