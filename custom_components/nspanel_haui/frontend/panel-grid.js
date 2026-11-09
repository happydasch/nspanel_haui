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

  const onClick = () => host._openEdit(pIdx);

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
        preview: renderPanelPreview(host, p, pIdx),
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
