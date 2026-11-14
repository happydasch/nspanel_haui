import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  entityWarnings,
  optionErrors,
  optionValueErrors,
  panelHasOptionErrors,
} from '../../custom_components/nspanel_haui/frontend/option-rules.js';

// The cases the hub's rule engine runs too (tests/test_option_rules.py).
const CASES = JSON.parse(readFileSync(new URL('../fixtures/option_rules_cases.json', import.meta.url), 'utf8'));

/** The fixture's option, shaped like the panel types endpoint serialises it. */
const asServed = (option) => ({
  ...option,
  choices: (option.choices || []).map(([value, label]) => ({ value, label })),
});

for (const testCase of CASES) {
  test(`option rule: ${testCase.name}`, () => {
    const errors = optionValueErrors(asServed(testCase.option), testCase.value, { popup: testCase.popup });
    assert.deepEqual(errors.map((error) => [error.field, error.kind]), testCase.errors);
    for (const error of errors) assert.ok(error.message, testCase.name);
  });
}

const LIGHT = {
  type_key: 'light',
  options: [
    { key: 'item', kind: 'item', domain: 'light', required: true },
    { key: 'show_kelvin', kind: 'bool' },
  ],
};
const GRID = {
  type_key: 'grid',
  options: [{ key: 'items', kind: 'item_list', max_items: 2 }],
};

test('the editor keys errors by the field it renders', () => {
  const errors = optionErrors(LIGHT, { item: { item: 'sensor.x' } }, {}, { popup: false });

  assert.deepEqual([...errors.keys()], ['fld-item']);
  assert.equal(errors.get('fld-item').kind, 'domain');
  assert.match(errors.get('fld-item').message, /light/);
});

test('item lists in the editor state win over the saved panel', () => {
  const itemLists = { items: [{ item: 'light.a' }, { item: '' }] };

  const errors = optionErrors(GRID, { items: [{ item: 'light.a' }] }, itemLists, { popup: false });

  assert.deepEqual([...errors.keys()], ['fld-items-1']);
  assert.equal(errors.get('fld-items-1').kind, 'required');
});

test('a single item is read from its one-element editor list', () => {
  const errors = optionErrors(LIGHT, { item: { item: 'light.a' } }, { item: [{ item: '' }] }, { popup: false });

  assert.equal(errors.get('fld-item').kind, 'required');
});

test('entities Home Assistant does not know are warnings', () => {
  const states = { 'light.present': {} };
  const itemLists = { items: [{ item: 'light.present' }, { item: 'light.missing' }, { item: 'navigate:x' }] };

  const warnings = entityWarnings(GRID, {}, itemLists, states);

  assert.deepEqual([...warnings.keys()], ['fld-items-1']);
  assert.match(warnings.get('fld-items-1'), /light\.missing/);
});

test('no warnings without Home Assistant states', () => {
  assert.equal(entityWarnings(LIGHT, { item: { item: 'light.x' } }, {}, undefined).size, 0);
});

test('a stored panel is checked against its type', () => {
  assert.equal(panelHasOptionErrors(LIGHT, { item: { item: 'sensor.x' } }, { popup: false }), true);
  assert.equal(panelHasOptionErrors(LIGHT, { item: { item: 'light.a' } }, { popup: false }), false);
  assert.equal(panelHasOptionErrors(LIGHT, {}, { popup: true }), false);
  assert.equal(panelHasOptionErrors(undefined, {}, { popup: false }), false);
});
