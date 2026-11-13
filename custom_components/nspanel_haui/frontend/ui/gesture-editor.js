// @ts-check
import { html, nothing } from '../lit-import.js';
import { GESTURE_ACTIONS, GESTURE_NAMES } from '../constants.js';
import { renderNumberInput, renderSelect } from '../form-fields.js';
import { panelTargetOptions } from '../haui-item.js';
import { t } from '../localize.js';
import { entryList } from './entry-list.js';
import { icon } from './icon.js';
import { sortHandle } from './sort-handle.js';

/** The gesture "Add gesture" starts with: it does nothing until it has swipes and an action. */
export const NEW_GESTURE = { swipes: [], action: '', timeframe: 3 };

/** A swipe's name, e.g. "Swipe left". @param {string} swipe */
export function swipeLabel(swipe) {
  return {
    swipe_left: t('Swipe left'),
    swipe_right: t('Swipe right'),
    swipe_up: t('Swipe up'),
    swipe_down: t('Swipe down'),
  }[swipe];
}

/** A gesture's swipes in order, e.g. "Swipe left → Swipe right". */
export function gestureSwipesLabel(gesture) {
  return gesture.swipes.length ? gesture.swipes.map(swipeLabel).join(' → ') : t('No swipes');
}

/**
 * What a gesture does: a step through the panels, or the name of the panel it opens.
 * @param {string} action @param {any[]} panels @param {any[]} systemPanels
 */
export function gestureActionLabel(action, panels = [], systemPanels = []) {
  if (!action) return t('No action');
  if (action === 'next_panel') return t('Next panel');
  if (action === 'prev_panel') return t('Previous panel');
  const panel = panels.find((candidate) => candidate.key === action);
  if (panel) return panel.title || panel.key;
  return systemPanels.find((candidate) => candidate.key === action)?.label || action;
}

/** A folded Gestures card's gestures, or that no swipe does anything. */
export function gestureSummary(gestures = [], panels = [], systemPanels = []) {
  return gestures.length
    ? gestures.map((gesture) => `${gestureSwipesLabel(gesture)}: ${
      gestureActionLabel(gesture.action, panels, systemPanels)}`).join(' · ')
    : t('No gestures: swipes do nothing.');
}

/**
 * Render the gestures of the Panels side stack as an `entryList`, like the
 * schedule: each gesture folds to its swipes and its action; only
 * `expandedEntryIndex` (the gesture just added) opens by state.
 *
 * @param {{ gestures?: any[], panels?: any[], systemPanels?: any[], idPrefix?: string,
 *   expandedEntryIndex?: number|null, onChange: (gestures: any[]) => void,
 *   onAdd?: (gestures: any[]) => void, onEntryToggle?: (index: number, open: boolean) => void }} options
 */
export function gestureEditor({
  gestures = [], panels = [], systemPanels = [], idPrefix = 'panel-gesture', expandedEntryIndex = null,
  onChange, onAdd, onEntryToggle,
}) {
  // A popup opens with its caller's context (an entity, a notification), so a gesture cannot open one.
  const fixedSystemPanels = systemPanels.filter((panel) => !panel.editable);
  const update = (index, fields) => {
    const next = [...gestures];
    next[index] = { ...next[index], ...fields };
    onChange(next);
  };
  /** Whether a drag over this pill drops after it (in reading order) rather than before. */
  const dropsAfter = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return event.clientY > rect.bottom ||
      (event.clientY >= rect.top && event.clientY <= rect.bottom && event.clientX > rect.left + rect.width / 2);
  };
  const clearDrop = (row) => row.classList.remove('is-drop-before', 'is-drop-after');

  const swipeField = (gesture, index, id) => {
    const swipes = gesture.swipes;
    let draggedSwipe = -1;
    const moveSwipe = (from, target, after) => {
      const slot = target + (after ? 1 : 0);
      const to = from < slot ? slot - 1 : slot;
      if (from < 0 || to === from) return;
      const ordered = [...swipes];
      ordered.splice(to, 0, ordered.splice(from, 1)[0]);
      update(index, { swipes: ordered });
    };
    const pill = (swipe, swipeIndex) => {
      const label = swipeLabel(swipe);
      const handle = sortHandle({
        label: t('Drag to reorder {name}').replace('{name}', label),
        onDragStart: (event) => {
          draggedSwipe = swipeIndex;
          event.dataTransfer?.setData('text/plain', String(swipeIndex));
          if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
          const row = event.currentTarget.closest('.haui-pill');
          row?.classList.add('is-dragging');
          if (row) event.dataTransfer?.setDragImage?.(row, 12, 12);
        },
        onDragEnd: (event) => {
          draggedSwipe = -1;
          const row = event.currentTarget.closest('.haui-pill');
          row?.classList.remove('is-dragging');
          if (row) clearDrop(row);
        },
      });
      return html`<li class="haui-pill"
        @dragover=${(event) => {
          if (draggedSwipe < 0 || draggedSwipe === swipeIndex) return;
          event.preventDefault();
          const after = dropsAfter(event);
          event.currentTarget.classList.toggle('is-drop-before', !after);
          event.currentTarget.classList.toggle('is-drop-after', after);
        }}
        @dragleave=${(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) clearDrop(event.currentTarget);
        }}
        @drop=${(event) => {
          if (draggedSwipe < 0 || draggedSwipe === swipeIndex) return;
          event.preventDefault();
          clearDrop(event.currentTarget);
          moveSwipe(draggedSwipe, swipeIndex, dropsAfter(event));
        }}
      >
        ${handle}
        <span class="haui-pill-order">${swipeIndex + 1}.</span>
        <span>${label}</span>
        <button type="button" aria-label=${t('Remove swipe').concat(': ', label)} title=${t('Remove')}
          @click=${() => update(index, { swipes: swipes.filter((_, i) => i !== swipeIndex) })}
        >${icon('close')}</button>
      </li>`;
    };
    return html`<div class="haui-field">
      <span id=${id('swipes_label')} class="haui-gesture-swipes-label">${t('Swipes, in order')}</span>
      <ul class="haui-pill-list haui-gesture-swipes" aria-labelledby=${id('swipes_label')}>
        ${swipes.map(pill)}
        <li>
          <select id=${id('add_swipe')} class="haui-select" aria-label=${t('Add swipe')}
            @change=${(event) => {
              const select = event.currentTarget;
              if (select.value) update(index, { swipes: [...swipes, select.value] });
              select.value = '';
            }}>
            <option value="" selected>${t('Add swipe')}</option>
            ${GESTURE_NAMES.map((swipe) => html`<option value=${swipe}>${swipeLabel(swipe)}</option>`)}
          </select>
        </li>
      </ul>
      ${swipes.length > 1 ? html`<div class="haui-field-hint">${t('Drag swipes into order.')}</div>` : nothing}
    </div>`;
  };

  const body = (gesture, index) => {
    const id = (name) => `${idPrefix}_${index}_${name}`;
    const isStep = GESTURE_ACTIONS.includes(gesture.action);
    const actionOptions = [
      { value: '', label: t('- None -') },
      { value: 'next_panel', label: t('Next panel') },
      { value: 'prev_panel', label: t('Previous panel') },
      ...panelTargetOptions(panels, fixedSystemPanels, isStep ? '' : gesture.action),
    ];
    return html`
      ${swipeField(gesture, index, id)}
      <div class="haui-field-pair">
        <div class="haui-field">
          <label for=${id('action')}>${t('Action')}</label>
          ${renderSelect(id('action'), gesture.action, actionOptions, (action) => update(index, { action }))}
        </div>
        ${gesture.swipes.length > 1 ? html`<div class="haui-field">
          <label for=${id('timeframe')}>${t('Within (s)')}</label>
          ${renderNumberInput(id('timeframe'), gesture.timeframe, (raw) => {
            const value = parseInt(raw, 10);
            // An emptied box is unfinished typing: the gesture keeps its time limit until a number is typed.
            if (!Number.isNaN(value)) update(index, { timeframe: Math.max(1, Math.min(value, 60)) });
          }, { min: 1, max: 60 })}
        </div>` : nothing}
      </div>`;
  };
  return entryList({
    entries: gestures,
    className: 'haui-gesture-editor',
    addId: `${idPrefix}_add`,
    addLabel: t('Add gesture'),
    removeLabel: t('Remove gesture'),
    expandedIndex: expandedEntryIndex,
    onAdd: () => (onAdd || onChange)([...gestures, { ...NEW_GESTURE, swipes: [] }]),
    onRemove: (index) => onChange(gestures.filter((_, i) => i !== index)),
    onToggle: onEntryToggle,
    summary: gestureSwipesLabel,
    note: (gesture) => gestureActionLabel(gesture.action, panels, systemPanels),
    body,
  });
}
