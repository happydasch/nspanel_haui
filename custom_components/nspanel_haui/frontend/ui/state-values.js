// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { addButton, iconButton } from './button.js';

/**
 * @typedef {{ state: string, value: unknown }} StateRow
 * @typedef {{ value: string, label?: string }} StateChoice
 */

/**
 * A value per state, as the hub reads it: the first row of a state wins, and a
 * row without a state or a value is not stored, so its state uses the default
 * like every state without a row.
 * @param {StateRow[]} rows
 * @returns {Record<string, unknown>}
 */
export function stateRowsToMap(rows) {
  /** @type {Record<string, unknown>} */
  const map = {};
  for (const { state, value } of rows) {
    if (state === '' || Object.hasOwn(map, state)) continue;
    map[state] = value;
  }
  for (const [state, value] of Object.entries(map)) {
    if (value === '' || value === null || value === undefined) delete map[state];
  }
  return map;
}

/**
 * One value for each state of an entity: a row per state (the state, its
 * value, a remove button), then the add row. The state field suggests
 * `states`; the value control is the caller's (`renderValue`), so a row edits
 * a name, an icon or a colour with the field it has outside the list.
 *
 * @param {{ id: string, label: string, labelledBy?: string, rows: StateRow[], states?: StateChoice[],
 *   renderValue: (row: StateRow, valueId: string, valueLabel: string, setValue: (value: unknown) => void) => unknown,
 *   onChange: (rows: StateRow[]) => void }} options
 */
export function stateValues({ id, label, labelledBy, rows, states = [], renderValue, onChange }) {
  const listId = `${id}-states`;
  const replace = (/** @type {number} */ index, /** @type {Partial<StateRow>} */ change) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, ...change } : row)));
  const row = (/** @type {StateRow} */ entry, /** @type {number} */ index) => {
    const stateId = `${id}-state-${index}`;
    const named = entry.state || t('new state');
    const listedAbove = entry.state !== '' && rows.slice(0, index).some((other) => other.state === entry.state);
    return html`<li class="haui-state-value">
      <input id=${stateId} class="haui-input haui-state-value-state" list=${listId}
        aria-label=${t('State')} placeholder=${t('State')} .value=${entry.state}
        aria-invalid=${listedAbove ? 'true' : nothing}
        aria-describedby=${listedAbove ? `${stateId}-warning` : nothing}
        @input=${(/** @type {Event} */ event) =>
          replace(index, { state: /** @type {HTMLInputElement} */ (event.target).value })} />
      <div class="haui-state-value-control">
        ${renderValue(entry, `${id}-value-${index}`,
          t('{field} for state {state}').replace('{field}', label).replace('{state}', named),
          (value) => replace(index, { value }))}
      </div>
      ${iconButton({
        label: t('Remove state {state}').replace('{state}', named),
        iconName: 'delete',
        onClick: () => onChange(rows.filter((_, i) => i !== index)),
      })}
      ${listedAbove
        ? html`<span class="haui-field-warning haui-state-value-warning" id=${`${stateId}-warning`}>
            ${t('This state is listed above. This row is not used.')}</span>`
        : nothing}
    </li>`;
  };
  return html`<div class="haui-state-values">
    <ul class="haui-state-value-list" role="list" aria-label=${labelledBy ? nothing : label}
      aria-labelledby=${labelledBy ?? nothing}>${rows.map(row)}</ul>
    <datalist id=${listId}>
      ${states.map((choice) => html`<option value=${choice.value} label=${choice.label || nothing}></option>`)}
    </datalist>
    ${addButton({
      label: t('Add state'),
      onClick: () => onChange([...rows, { state: '', value: '' }]),
    })}
  </div>`;
}
