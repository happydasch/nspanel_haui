import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { stateRowsToMap, stateValues } from '../../custom_components/nspanel_haui/frontend/ui/state-values.js';
import { render } from './support/render.mjs';
import { byRole } from './support/queries.mjs';

/** Render the list for `rows`; every change re-renders it and is recorded. */
function mount(rows, states = []) {
  const container = document.createElement('div');
  const changes = [];
  const draw = (current) => render(stateValues({
    id: 'item-icon',
    label: 'Icon',
    rows: current,
    states,
    renderValue: (row, valueId, valueLabel, setValue) => html`<input id=${valueId} aria-label=${valueLabel}
      .value=${String(row.value ?? '')} @input=${(event) => setValue(event.target.value)} />`,
    onChange: (next) => { changes.push(next); draw(next); },
  }), container);
  draw(rows);
  return { container, changes };
}

function type(input, value) {
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

test('each state is a row of its state, its value and a remove button in a labelled list', () => {
  const { container } = mount(
    [{ state: 'on', value: 'mdi:lightbulb' }, { state: 'off', value: 'mdi:lightbulb-outline' }],
    [{ value: 'on', label: 'On' }, { value: 'off', label: 'Off' }],
  );
  const list = container.querySelector('ul[aria-label="Icon"]');
  assert.equal(list.querySelectorAll('li').length, 2);
  assert.equal(byRole(container, 'textbox', { name: 'Icon for state off' }).value, 'mdi:lightbulb-outline');
  assert.ok(byRole(container, 'button', { name: 'Remove state on' }));

  const stateField = container.querySelector('li input[aria-label="State"]');
  const suggestions = container.querySelector(`#${stateField.getAttribute('list')}`);
  assert.deepEqual([...suggestions.querySelectorAll('option')].map((option) => option.value), ['on', 'off']);
});

test('editing a state or its value, adding and removing a row report the new rows', () => {
  const { container, changes } = mount([{ state: 'on', value: 'mdi:a' }]);
  type(container.querySelector('li input[aria-label="State"]'), 'open');
  type(byRole(container, 'textbox', { name: 'Icon for state open' }), 'mdi:b');
  byRole(container, 'button', { name: '+ Add state' }).click();
  byRole(container, 'button', { name: 'Remove state open' }).click();

  assert.deepEqual(changes, [
    [{ state: 'open', value: 'mdi:a' }],
    [{ state: 'open', value: 'mdi:b' }],
    [{ state: 'open', value: 'mdi:b' }, { state: '', value: '' }],
    [{ state: '', value: '' }],
  ]);
});

test('a state listed twice is marked on the row that is not used', () => {
  const { container } = mount([{ state: 'on', value: 'mdi:a' }, { state: 'on', value: 'mdi:b' }]);
  const [first, second] = container.querySelectorAll('li input[aria-label="State"]');
  assert.equal(first.getAttribute('aria-invalid'), null);
  assert.equal(second.getAttribute('aria-invalid'), 'true');
  const warning = container.querySelector(`#${second.getAttribute('aria-describedby')}`);
  assert.match(warning.textContent, /listed above/);
});

test('the stored map keeps the first row of a state and drops rows without a state or a value', () => {
  assert.deepEqual(stateRowsToMap([
    { state: 'on', value: '#00ff00' },
    { state: 'on', value: '#ff0000' },
    { state: '', value: '#0000ff' },
    { state: 'off', value: '' },
    { state: 'unavailable', value: [255, 0, 0] },
  ]), { on: '#00ff00', unavailable: [255, 0, 0] });
});
