/**
 * NSPanel HAUI - panel grid view rendering.
 *
 * An alternative to panel-table.js that displays panels as visual cards
 * in a CSS Grid layout.  Every function takes the Lit element instance
 * (`host`) as its first parameter.
 */
import { html } from './lit-import.js';
import { renderPanelGroups, renderPanelDropdown, buildPanelDropdownItems } from './panel-table.js';
import { renderPanelPreview } from './panel-previews.js';
import { renderBadges, getPanelMoveState, getSystemPanelKeys } from './panel-utils.js';
import { renderCardChrome, renderCardActions } from './panel-card.js';
import { t } from './localize.js';

/**
 * Render a single panel card for the grid view.
 * Shows icon, title, key, badges, and a more-actions dropdown.
 */
function renderPanelCard(host, p, panels, isNavPanel) {
  const { pIdx, canMoveUp, canMoveDown } = getPanelMoveState(p, panels, isNavPanel, getSystemPanelKeys(host));
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
  const hasIdleBtn = p.show_idle_button ?? dc.show_idle_button ?? false;
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

  // Right button auto-assignment (mirrors Python FunctionButtonMixin +
  // the grid/row pagination override):
  //   - pagination claims right_sec in navigation, right_pri otherwise
  //   - nav prev/next or non-nav close fill the remaining primary slot
  //   - notifications then take a free right slot; when both right slots
  //     are taken (pagination in navigation), they override the idle/sleep
  //     button on the home panel instead (left_sec)
  const paginationBtn = hasPagination
    ? { icon: 'mdi:chevron-double-down', accent: true }
    : '';
  let rightPri = showInNav ? 'mdi:chevron-right' : 'mdi:close';
  let rightSec = '';
  if (showInNav) {
    rightSec = paginationBtn;
  } else if (paginationBtn) {
    rightPri = paginationBtn;
  }
  // left_sec: not-home+home_btn → HOME, home+idle_btn → IDLE (notification is on right_sec)
  let leftSec = '';
  if (!isHome && hasHomeBtn) {
    leftSec = 'mdi:home-outline';
  } else if (isHome && hasIdleBtn) {
    leftSec = 'mdi:sleep';
  }
  if (hasNotifBtn) {
    const notifBtn = { icon: 'mdi:email-outline', accent: true };
    if (!rightSec) {
      rightSec = notifBtn;
    } else if (!rightPri) {
      rightPri = notifBtn;
    } else if (leftSec === 'mdi:sleep') {
      // Both right slots are claimed — notifications override the sleep button.
      leftSec = notifBtn;
    }
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
 * Main entry point: render the panel grid view (same groups as the list view,
 * with each group's cards laid out in a CSS Grid).
 */
export function renderPanelGrid(host) {
  return renderPanelGroups(
    host, renderPanelCard, (cards) => html`<div class="pg-grid">${cards}</div>`
  );
}
