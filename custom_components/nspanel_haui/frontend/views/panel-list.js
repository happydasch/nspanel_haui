// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { panelRow } from '../ui/panel-row.js';
import { panelThumb } from '../ui/panel-thumb.js';
import { iconButton } from '../ui/button.js';
import { menuItem, menuSeparator, overlayAnchor, popover } from '../ui/popover.js';

/**
 * @typedef {Object} PanelListEntry
 * @property {string} key
 * @property {'user'|'popup'} kind
 * @property {boolean} [sortable] - whether the row's grip drags; every other grip is shown disabled
 * @property {string} title
 * @property {string} [typeLabel]
 * @property {number} [itemCount]
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
 * @param {{ groups: PanelListGroup[], portrait?: boolean, menuKey?: string|null, emptyMessage?: string,
 *   onToggleMenu?: (key: string) => void, onCloseMenu?: () => void,
 *   onDrop?: (move: {sourceKey: string, group: string, beforeKey: string|null}) => void }} model
 */
export function renderPanelList({
  groups = [], portrait = false, menuKey = null, emptyMessage = '',
  onToggleMenu = () => {}, onCloseMenu = () => {}, onDrop = () => {},
}) {
  return html`<section class="haui-panel-groups" aria-label=${t('Panels')}>
    ${groups.length || !emptyMessage ? nothing : html`<p class="haui-panel-empty">${emptyMessage}</p>`}
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
      <header class="haui-panel-group-heading">
        <strong id=${`haui-panel-group-${group.id}`}>${group.title}</strong>
        <span>${group.hint}</span>
      </header>
      <div class="haui-panel-list">
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
            onDrop: group.dropEnabled
              ? (sourceKey, after) => onDrop({
                sourceKey,
                group: group.id,
                beforeKey: after ? group.entries[position + 1]?.key ?? null : entry.key,
              })
              : null,
          });
        })}
        ${group.entries.length ? nothing : html`<p class="haui-panel-empty">${group.emptyMessage}</p>`}
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
      <ha-icon icon="mdi:drag" aria-hidden="true"></ha-icon>
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
    <ha-icon icon="mdi:drag" aria-hidden="true"></ha-icon>
  </span>`;
}
