// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { panelRow } from '../ui/panel-row.js';
import { panelThumb } from '../ui/panel-thumb.js';
import { iconButton } from '../ui/button.js';
import { sectionHeading } from '../ui/surface.js';
import { emptyState } from '../ui/empty-state.js';
import { icon } from '../ui/icon.js';
import { menuItem, menuSeparator, overlayAnchor, popover } from '../ui/popover.js';

/**
 * @typedef {Object} PanelListEntry
 * @property {string} key
 * @property {'user'|'popup'} kind
 * @property {boolean} [sortable] - whether the row's grip drags; every other grip is shown disabled
 * @property {string} title
 * @property {string} [typeLabel]
 * @property {number} [itemCount]
 * @property {boolean} [invalid] - the saved panel breaks a rule of its type
 * @property {unknown} [preview]
 * @property {unknown[]} [roles]
 * @property {string} [lockReason]
 * @property {Array<{label: string, iconName?: string, danger?: boolean, disabled?: boolean, onSelect: () => void}|'divider'>} [menu]
 * @property {(() => void)|null} [onEdit]
 *
 * @typedef {Object} PanelListGroup
 * @property {string} id
 * @property {string} title
 * @property {string} hint
 * @property {string} emptyMessage
 * @property {boolean} dropEnabled
 * @property {boolean} [collapsed]
 * @property {PanelListEntry[]} entries
 */

/**
 * Render one entry's overflow menu through the shared anchored popover.
 *
 * @param {{ entry: PanelListEntry, open: boolean, onToggleMenu: (key: string) => void, onCloseMenu: () => void }} options
 */
function renderEntry({ entry, open, onToggleMenu, onCloseMenu }) {
  const anchorKey = overlayAnchor('panel-menu', entry.key);
  const items = entry.menu || [];
  const menu = open ? popover({
    open,
    id: `haui-panel-menu-${entry.key}`,
    label: t('Actions for {name}').replace('{name}', entry.title),
    role: 'menu',
    className: 'haui-panel-menu',
    anchorKey,
    content: items.map((item) => (item === 'divider'
      ? menuSeparator()
      : menuItem({
        label: item.label,
        iconName: item.iconName,
        danger: item.danger === true,
        disabled: item.disabled === true,
        onSelect: () => { onCloseMenu(); item.onSelect(); },
      }))),
  }) : nothing;
  return {
    anchorKey,
    menu,
    action: items.length
      ? iconButton({
        label: t('Actions for {name}').replace('{name}', entry.title),
        iconName: 'more',
        className: 'haui-row-action',
        anchorKey,
        onClick: () => onToggleMenu(entry.key),
        expanded: open,
        controls: `haui-panel-menu-${entry.key}`,
      })
      : nothing,
  };
}

/**
 * The Device workspace's four panel groups: navigation, hidden, popups, system.
 *
 * `selectedKey` marks the selected row and `onSelect` reports a row the user
 * picked; the caller decides what a selection means (the Panels view's side card
 * describes it).
 *
 * @param {{ groups: PanelListGroup[], portrait?: boolean, menuKey?: string|null, emptyMessage?: string,
 *   selectedKey?: string|null,
 *   onToggleMenu?: (key: string) => void, onCloseMenu?: () => void,
 *   onToggleGroup?: (groupId: string) => void, onSelect?: (key: string) => void,
 *   onDrop?: (move: {sourceKey: string, group: string, beforeKey: string|null}) => void }} model
 */
export function renderPanelList({
  groups = [], portrait = false, menuKey = null, emptyMessage = '', selectedKey = null,
  onToggleMenu = () => {}, onCloseMenu = () => {}, onToggleGroup = () => {},
  onSelect = () => {}, onDrop = () => {},
}) {
  return html`<section class="haui-panel-groups" aria-label=${t('Panels')}>
    ${groups.length || !emptyMessage ? nothing : emptyState({ message: emptyMessage, iconName: null, className: 'haui-empty-state-compact' })}
    ${groups.map((group) => html`<section class="haui-panel-group" data-panel-group=${group.id}
      aria-labelledby=${`haui-panel-group-${group.id}`}
      @dragover=${group.dropEnabled ? overGroup : nothing}
      @dragleave=${group.dropEnabled ? leaveGroup : nothing}
      @drop=${group.dropEnabled ? (event) => {
        // A drop on the heading or below the rows moves the panel to the group's end.
        event.preventDefault();
        event.currentTarget.classList.remove('is-drop-target');
        const sourceKey = event.dataTransfer?.getData('text/plain');
        if (sourceKey) onDrop({ sourceKey, group: group.id, beforeKey: null });
      } : nothing}>
      <header>
        ${sectionHeading({
          title: group.title,
          titleId: `haui-panel-group-${group.id}`,
          className: 'haui-panel-group-heading',
          leading: iconButton({
            label: group.collapsed ? t('Show more') : t('Show less'),
            iconName: group.collapsed ? 'chevronRight' : 'chevron-down',
            className: 'haui-panel-group-toggle',
            expanded: group.collapsed !== true,
            controls: `haui-panel-list-${group.id}`,
            onClick: () => onToggleGroup(group.id),
          }),
          badge: html`<span>${group.hint}</span>`,
        })}
      </header>
      <div class="haui-panel-list" id=${`haui-panel-list-${group.id}`} ?hidden=${group.collapsed === true}>
        ${group.entries.map((entry, position) => {
          const { menu, action } = renderEntry({
            entry, open: menuKey === entry.key, onToggleMenu, onCloseMenu,
          });
          return panelRow({
            key: entry.key,
            group: group.id,
            title: entry.title,
            typeLabel: entry.typeLabel,
            itemCount: entry.itemCount,
            invalid: entry.invalid === true,
            selected: selectedKey === entry.key,
            thumbnail: panelThumb({
              content: entry.preview,
              portrait,
              label: entry.title,
              roles: entry.roles,
            }),
            lockReason: entry.lockReason,
            menu,
            actions: html`${entry.onEdit ? iconButton({
              label: t('Edit {name}').replace('{name}', entry.title),
              iconName: 'edit',
              className: 'haui-row-action',
              onClick: entry.onEdit,
            }) : nothing}${action}`,
            handle: sortHandleFor(entry),
            onEdit: entry.onEdit,
            onSelect: () => onSelect(entry.key),
            onDrop: group.dropEnabled
              ? (sourceKey, after) => onDrop({
                sourceKey,
                group: group.id,
                beforeKey: after ? group.entries[position + 1]?.key ?? null : entry.key,
              })
              : null,
          });
        })}
        ${group.entries.length ? nothing : emptyState({ message: group.emptyMessage, iconName: null, className: 'haui-empty-state-compact' })}
      </div>
    </section>`)}
  </section>`;
}

/** Mark the group a dragged panel would be appended to. */
function overGroup(event) {
  event.preventDefault();
  event.currentTarget.classList.add('is-drop-target');
}

function leaveGroup(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) event.currentTarget.classList.remove('is-drop-target');
}

/**
 * Drag grip of a panel row. Only a sortable entry's grip drags, so rows that
 * keep their place still line up.
 *
 * @param {PanelListEntry} entry
 */
function sortHandleFor(entry) {
  if (!entry.sortable) {
    const label = t('{name} cannot be reordered').replace('{name}', entry.title);
    return html`<span class="haui-panel-handle is-disabled" role="img" aria-label=${label} title=${label}>
      ${icon('grip')}
    </span>`;
  }
  const label = t('Drag to reorder {name}').replace('{name}', entry.title);
  return html`<span class="haui-panel-handle" draggable="true" role="img" aria-label=${label} title=${label}
    @dragstart=${(event) => {
      const row = event.currentTarget.closest('.haui-panel-row');
      event.dataTransfer?.setData('text/plain', entry.key);
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
      // Drag the whole row, not only the grip.
      if (row) event.dataTransfer?.setDragImage?.(row, 12, 12);
      row?.classList.add('is-dragging');
    }}
    @dragend=${(event) => event.currentTarget.closest('.haui-panel-row')?.classList.remove('is-dragging')}>
    ${icon('grip')}
  </span>`;
}
