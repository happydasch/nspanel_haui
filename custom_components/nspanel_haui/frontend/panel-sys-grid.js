/**
 * NSPanel HAUI - Editor - System panel grid card rendering.
 *
 * Renders system panels as grid cards (read-only, no edit/actions).
 * Uses the registered panel preview renderers by type, same as user panels.
 */
import { html } from './lit-import.js';
import { renderBadges } from './panel-utils.js';
import { renderPanelPreview } from './panel-previews.js';
import { isSysPanelEditable, renderPanelDropdown } from './panel-table.js';
import { renderCardChrome, renderCardActions } from './panel-card.js';
import { tDesc } from './localize.js';

/**
 * Build the dropdown items for a system panel card.
 * @param {import("lit").LitElement} host
 * @param {object} sp - system panel entry
 * @param {boolean} hasOverride
 * @returns {Array}
 */
function buildSysPanelDropdownItems(host, sp, hasOverride) {
  const items = [];
  if (hasOverride) {
    items.push({
      icon: 'mdi:restore',
      label: host._t('Reset to default'),
      action: () => host._resetSysPanelOverride(sp.key),
    });
    items.push('divider');
  }
  items.push({
    icon: 'mdi:pencil-outline',
    label: host._t('Edit'),
    action: () => host._openSysPanelEdit(sp),
  });
  return items;
}

/**
 * Render a single system panel as a grid card.
 * Shows an action dropdown for editable panels and an "Edited" badge
 * when the system panel has been overridden by a user panel.
 * @param {import("lit").LitElement} host
 * @param {object} sp - system panel entry { type, key, label, description, icon, has_header }
 * @returns {import("lit").TemplateResult}
 */
export function renderSystemPanelCard(host, sp) {
  const dc = host._deviceConfig || {};
  const editable = isSysPanelEditable(sp);
  const hasOverride = editable && host._devicePanels().some(p => p.key === sp.key);
  const badges = renderBadges(sp, dc, hasOverride);
  const onClickSysCard = editable ? () => host._openSysPanelEdit(sp) : undefined;

  // Use registered preview renderer — system panel entries have
  // the same 'type' field as user panels (e.g. 'system', 'popup_light')
  const previewResult = renderPanelPreview(host, sp, -1, sp);

  // For system panel previews — match Python backend logic:
  // popup panels get close+up, navigation panels get prev/next
  const sysIsPopup = sp.can_show_popup;
  const sysLeftPri = sysIsPopup ? 'mdi:chevron-up' : 'mdi:chevron-left';
  const sysRightPri = sysIsPopup ? 'mdi:close' : 'mdi:chevron-right';
  const headerButtons = { left: [sysLeftPri, ''], right: ['', sysRightPri] };

  const actions = editable
    ? renderCardActions(host, sp.key, (close) =>
        renderPanelDropdown(host, -1, buildSysPanelDropdownItems(host, sp, hasOverride), close)
      )
    : '';

  return html`
    <div class="pg-card pg-sys-card">
      ${renderCardChrome({
        icon: sp.icon,
        title: tDesc(sp, 'label'),
        key: sp.key,
        badges,
        hasHeader: sp.has_header !== false,
        headerButtons,
        preview: previewResult,
        description: tDesc(sp, 'description'),
        onClick: onClickSysCard,
        actions,
      })}
    </div>
  `;
}
