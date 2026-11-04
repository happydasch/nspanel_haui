/**
 * NSPanel HAUI - System panel grid card rendering.
 *
 * Renders system panels as grid cards; only the popups can be edited, the
 * other system panels are shown read-only. The preview is the hub's render of
 * the device's configured panel, as for user panels.
 */
import { html } from './lit-import.js';
import { renderBadges } from './panel-utils.js';
import { renderPanelPreview } from './panel-previews.js';
import { renderPanelDropdown } from './panel-table.js';
import { renderCardChrome, renderCardActions } from './panel-card.js';
import { t } from './localize.js';

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
      label: t('Reset to default'),
      action: () => host._resetSysPanelOverride(sp.key),
    });
    items.push('divider');
  }
  items.push({
    icon: 'mdi:pencil-outline',
    label: t('Edit'),
    action: () => host._openSysPanelEdit(sp),
  });
  return items;
}

/**
 * Render a single system panel as a grid card.
 * An editable (popup) card shows an action dropdown and an "Edited" badge
 * when it has been overridden by a user panel; the others have no actions.
 * @param {import("lit").LitElement} host
 * @param {object} sp - system panel entry { type, key, label, description, icon, editable }
 * @returns {import("lit").TemplateResult}
 */
export function renderSystemPanelCard(host, sp) {
  const dc = host._deviceConfig || {};
  const hasOverride = sp.editable && host._devicePanels().some(p => p.key === sp.key);
  const badges = renderBadges(sp, dc, hasOverride);

  const actions = sp.editable
    ? renderCardActions(host, sp.key, (close) =>
      renderPanelDropdown(host, -1, buildSysPanelDropdownItems(host, sp, hasOverride), close)
    )
    : '';

  return html`
    <div class="pg-card ${sp.editable ? '' : 'pg-card-readonly'}">
      ${renderCardChrome({
        icon: sp.icon,
        title: sp.label,
        key: sp.key,
        badges,
        preview: renderPanelPreview(host, sp, -1, sp),
        description: sp.description,
        onClick: sp.editable ? () => host._openSysPanelEdit(sp) : undefined,
        actions,
      })}
    </div>
  `;
}
