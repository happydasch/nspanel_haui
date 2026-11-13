// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { surface } from './surface.js';
import { button, iconButton } from './button.js';
import { icon } from './icon.js';

/**
 * @typedef {Object} PanelInfoAction
 * @property {string} label
 * @property {string} iconName
 * @property {string} [variant] - a shared button variant; outline by default
 * @property {boolean} [danger] - drawn in the error colour (Delete)
 * @property {() => void} onClick
 *
 * @typedef {Object} PanelInfo
 * @property {'panel'} kind
 * @property {string} iconName
 * @property {string} title
 * @property {string} subtitle
 * @property {string} description
 * @property {unknown} [preview] - the hub's render of the panel
 * @property {boolean} [portrait]
 * @property {Array<[string, unknown]>} facts - label and value of one fact
 * @property {PanelInfoAction[]} actions
 * @property {() => void} onClose - clears the selected panel
 * @property {boolean} [previewExpanded] - false folds the render to a thumbnail
 * @property {() => void} [onTogglePreview] - folds or unfolds the render; without it the render stays as it is
 *
 * @typedef {Object} PanelsOverview
 * @property {'overview'} kind
 * @property {number} navigationCount
 * @property {number} hiddenCount
 * @property {number} popupCount
 * @property {string} [homePanel] - the panel the device opens as home
 * @property {string} [homePanelKey] - the home panel's key in the list
 * @property {string} [idlePanels] - the panel (or panels) it shows while idle
 * @property {string} [idlePanelKey] - the first idle panel's key in the list
 * @property {(key: string) => void} [onSelectPanel] - selects a role's panel in the list
 */

/**
 * The panel's render and its description. Open, the render takes the card's width
 * with the description under it; folded, the render is a thumbnail with the
 * description beside it, so the card takes less room. The render itself is the
 * toggle: a click on it folds or unfolds it.
 *
 * @param {{ preview?: unknown, portrait?: boolean, description?: string,
 *   expanded?: boolean, onToggle?: (() => void)|null }} options
 */
function previewBlock({ preview = nothing, portrait = false, description = '', expanded = true, onToggle = null }) {
  const size = `${portrait ? ' is-portrait' : ''}${expanded ? '' : ' is-small'}`;
  const label = expanded ? t('Show the panel preview small') : t('Show the panel preview large');
  const render = preview === nothing
    ? nothing
    : onToggle
      ? html`<button type="button" class=${'haui-panel-info-preview is-toggle' + size}
          aria-expanded=${expanded ? 'true' : 'false'} aria-label=${label} title=${label}
          @click=${onToggle}>${preview}<span class="haui-panel-info-preview-toggle">${icon(expanded ? 'chevron-up' : 'chevron-down')}</span></button>`
      : html`<div class=${'haui-panel-info-preview' + size}>${preview}</div>`;
  if (render === nothing && !description) return nothing;
  return html`<div class=${'haui-panel-info-preview-block' + (expanded ? '' : ' is-folded')}>${render}${description
    ? html`<p class="haui-panel-info-description">${description}</p>`
    : nothing}</div>`;
}

/**
 * The Panels view's card for the selected panel: the panel as the display draws
 * it, its type with the type's icon and the type's description, the facts that
 * decide how it behaves, and the actions its row's menu offers.
 *
 * @param {PanelInfo} model
 */
function selectedPanel({
  iconName, title, subtitle, description, preview, portrait = false, facts, actions = [],
  previewExpanded = true, onTogglePreview = null, onClose,
}) {
  return surface({
    className: 'haui-panel-info',
    leading: html`<span class="haui-panel-info-icon">${icon(iconName)}</span>`,
    title,
    subtitle,
    actions: iconButton({ label: t('Close'), iconName: 'close', onClick: onClose, className: 'haui-panel-info-close' }),
    body: html`
      ${previewBlock({
        preview, portrait, description, expanded: previewExpanded, onToggle: onTogglePreview,
      })}
      <dl class="haui-panel-info-facts">
        ${facts.map(([label, value]) => html`<div><dt>${label}</dt><dd>${value}</dd></div>`)}
      </dl>
      ${actions.length ? html`<div class="haui-card-actions">
        ${actions.map((action) => button({
          label: action.label,
          iconName: action.iconName,
          variant: action.variant || 'outline',
          className: action.danger ? 'haui-button-danger' : '',
          onClick: action.onClick,
        }))}
      </div>` : nothing}`,
  });
}

/**
 * What the panel list is about while no panel is selected: how many panels each
 * group holds, which panel the device opens as home and while idle, and how the
 * rows are worked with.
 *
 * @param {PanelsOverview} model
 */
function panelsOverview({
  navigationCount, hiddenCount, popupCount, homePanel = '', homePanelKey = '',
  idlePanels = '', idlePanelKey = '', onSelectPanel,
}) {
  const groups = [
    { key: 'navigation', iconName: 'panels', label: t('Navigation'), count: navigationCount },
    { key: 'hidden', iconName: 'mdi:eye-off-outline', label: t('Hidden'), count: hiddenCount },
    { key: 'popups', iconName: 'mdi:window-restore', label: t('Popups'), count: popupCount },
  ];
  // The two ends of the device's cycle: where it returns, and what it shows while idle.
  const roles = [
    {
      key: 'home', iconName: 'home', label: t('Home panel'), value: homePanel || t('First navigation panel'),
      panelKey: homePanelKey,
    },
    {
      key: 'idle', iconName: 'sleep', label: t('Idle panel'), value: idlePanels || t('Not set'),
      panelKey: idlePanelKey,
    },
  ];
  const hints = [
    {
      key: 'order',
      iconName: 'grip',
      text: t('Drag a panel to reorder it, or drop it in the other group.'),
    },
    {
      key: 'menu',
      iconName: 'more',
      text: t('The row menu duplicates, hides and deletes a panel.'),
    },
  ];
  return surface({
    className: 'haui-panel-info haui-panels-overview',
    leading: html`<span class="haui-panel-info-icon">${icon('panels')}</span>`,
    title: t('About panels'),
    subtitle: t('Select a panel in the list to see its details.'),
    body: html`
      <ul class="haui-panels-overview-groups">
        ${groups.map((group) => html`<li data-group=${group.key}>
          ${icon(group.iconName)}<span>${group.label}</span><strong>${String(group.count)}</strong>
        </li>`)}
      </ul>
      <div class="haui-panels-overview-roles">
        ${roles.map((role) => {
          const label = t('Select {role}: {name}')
            .replace('{role}', role.label).replace('{name}', role.value);
          return html`<button type="button" data-role=${role.key}
            class="haui-panels-overview-role-tile"
            aria-label=${label} title=${label}
            ?disabled=${!role.panelKey || !onSelectPanel}
            @click=${role.panelKey && onSelectPanel ? () => onSelectPanel(role.panelKey) : null}>
            <span class="haui-panels-overview-role-heading">
              <span class=${`haui-panel-role haui-panels-overview-role-icon haui-panel-role-${role.key}`}>${icon(role.iconName)}</span>
              <span class="haui-panels-overview-role-label">${role.label}</span>
            </span>
            <span class="haui-panels-overview-role-value">${role.value}</span>
          </button>`;
        })}
      </div>
      <ul class="haui-panels-overview-hints">
        ${hints.map((hint) => html`<li data-hint=${hint.key}>${icon(hint.iconName)}<span>${hint.text}</span></li>`)}
      </ul>`,
  });
}

/**
 * The side card of the Panels view: the selected panel, or the general overview
 * of the list while nothing is selected.
 *
 * @param {PanelInfo|PanelsOverview} model
 */
export function panelSideCard(model) {
  return model.kind === 'panel' ? selectedPanel(model) : panelsOverview(model);
}
