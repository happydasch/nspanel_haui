// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';
import { sortHandle } from './sort-handle.js';

/**
 * The panel keys of a comma-separated setting such as `idle_panel_extra`.
 *
 * @param {unknown} value
 * @returns {string[]}
 */
export function panelKeys(value) {
  return String(value ?? '').split(',').map((key) => key.trim()).filter(Boolean);
}

/**
 * The ordered idle-panel sequence shared by the primary and extra settings.
 * Runtime navigation deduplicates these keys, so the editor does too.
 *
 * @param {unknown} idlePanel
 * @param {unknown} idlePanelExtra
 * @returns {string[]}
 */
export function idlePanelKeys(idlePanel, idlePanelExtra) {
  return [...new Set([String(idlePanel ?? '').trim(), ...panelKeys(idlePanelExtra)].filter(Boolean))];
}

/**
 * Split an ordered idle-panel sequence into the existing persisted fields.
 *
 * @param {string[]} keys
 * @returns {{ idle_panel: string, idle_panel_extra: string }}
 */
export function idlePanelConfig(keys) {
  const unique = [...new Set(keys.map((key) => key.trim()).filter(Boolean))];
  return { idle_panel: unique[0] || '', idle_panel_extra: unique.slice(1).join(', ') };
}

/**
 * An ordered panel list as pills, each with a remove button; the last pill is
 * the select that adds a panel, or replaces the selected panel in `single`
 * mode. A panel is listed once, so `exclude` and the listed panels are not
 * offered again; a key without a panel stays listed under its key, so it can
 * be removed.
 *
 * @param {{ id: string, panels: any[], keys: string[], exclude?: string[], numbered?: boolean,
 *   reorderable?: boolean, single?: boolean, addLabel?: string, disabled?: boolean,
 *   onChange: (keys: string[]) => void }} data
 */
export function panelPills({
  id, panels, keys, exclude = [], numbered = false, reorderable = false, single = false,
  addLabel = t('Add panel'), disabled = false, onChange,
}) {
  const titleOf = (key) => panels.find((panel) => panel.key === key)?.title || key;
  const addable = panels.filter((panel) => panel.key && !exclude.includes(panel.key) && !keys.includes(panel.key));
  const canReorder = reorderable && !disabled;
  let draggedKey = '';
  const clearDrop = (row) => row.classList.remove('is-drop-before', 'is-drop-after');
  const move = (fromKey, targetIndex, after) => {
    const from = keys.indexOf(fromKey);
    const slot = targetIndex + (after ? 1 : 0);
    const to = from < slot ? slot - 1 : slot;
    if (from === -1 || to === from) return;
    const next = [...keys];
    const [key] = next.splice(from, 1);
    next.splice(to, 0, key);
    onChange(next);
  };
  return html`<ul class="haui-pill-list">
    ${keys.map((key, index) => {
      const title = titleOf(key);
      const startDrag = canReorder ? (event) => {
        draggedKey = key;
        event.dataTransfer?.setData('text/plain', key);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
        const row = event.currentTarget.closest('.haui-pill');
        if (row) event.dataTransfer?.setDragImage?.(row, 12, 12);
        row?.classList.add('is-dragging');
      } : undefined;
      const endDrag = canReorder ? (event) => {
        draggedKey = '';
        const row = event.currentTarget.closest('.haui-pill');
        row?.classList.remove('is-dragging');
        if (row) clearDrop(row);
      } : undefined;
      const allowDrop = canReorder ? (event) => {
        if (!draggedKey || draggedKey === key) return;
        event.preventDefault();
        const rect = event.currentTarget.getBoundingClientRect();
        const after = event.clientY > rect.top + rect.height / 2;
        event.currentTarget.classList.toggle('is-drop-before', !after);
        event.currentTarget.classList.toggle('is-drop-after', after);
      } : undefined;
      const leaveDrop = canReorder ? (event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) clearDrop(event.currentTarget);
      } : undefined;
      const acceptDrop = canReorder ? (event) => {
        if (!draggedKey || draggedKey === key) return;
        event.preventDefault();
        clearDrop(event.currentTarget);
        const rect = event.currentTarget.getBoundingClientRect();
        move(draggedKey, index, event.clientY > rect.top + rect.height / 2);
      } : undefined;
      const handle = canReorder ? sortHandle({
        label: t('Drag to reorder {name}').replace('{name}', title),
        onDragStart: startDrag,
        onDragEnd: endDrag,
      }) : nothing;
      return html`<li class="haui-pill" @dragover=${allowDrop ?? nothing}
        @dragleave=${leaveDrop ?? nothing} @drop=${acceptDrop ?? nothing}>
        ${handle}
        ${numbered ? html`<span class="haui-pill-order">${index + 1}.</span>` : nothing}
        <span>${title}</span>
        <button type="button" aria-label=${t('Remove {panel}').replace('{panel}', title)}
          title=${t('Remove')} ?disabled=${disabled}
          @click=${() => onChange(keys.filter((_, i) => i !== index))}>${icon('close')}</button>
      </li>`;
    })}
    ${addable.length ? html`<li><select id=${id} class="haui-select" ?disabled=${disabled}
      @change=${(event) => {
        const select = event.currentTarget;
        if (select.value) onChange(single ? [select.value] : [...keys, select.value]);
        // Lit reuses the option elements, so the pick has to be cleared by hand.
        select.value = '';
      }}>
      <option value="" selected>${addLabel}</option>
      ${addable.map((panel) => html`<option value=${panel.key}>${panel.title || panel.key}</option>`)}
    </select></li>` : nothing}
  </ul>`;
}
