import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderOptionField } from '../../custom_components/nspanel_haui/frontend/form-fields.js';

/** All functions (event handlers) in a Lit TemplateResult tree, in template order. */
function handlers(v, out = []) {
  if (Array.isArray(v)) v.forEach((x) => handlers(x, out));
  else if (v && v.values) v.values.forEach((x) => handlers(x, out));
  else if (typeof v === 'function') out.push(v);
  return out;
}

function host() {
  return { _editingPanel: { index: 0, data: { title: 'x' } }, updates: 0, requestUpdate() { this.updates++; } };
}

test('an int option stores the parsed number, an empty field unsets it', () => {
  const h = host();
  const [onInput] = handlers(renderOptionField(h, { key: 'timeout', kind: 'int' }, 5));
  onInput({ target: { value: '42' } });
  assert.deepEqual(h._editingPanel.data, { title: 'x', timeout: 42 });
  assert.equal(h.updates, 1);
  onInput({ target: { value: '' } });
  assert.equal(h._editingPanel.data.timeout, undefined);
  assert.equal(JSON.stringify(h._editingPanel.data), '{"title":"x"}');
});

test('a float option stores the parsed float', () => {
  const h = host();
  const [onInput] = handlers(renderOptionField(h, { key: 'ratio', kind: 'float' }, null));
  onInput({ target: { value: '1.5' } });
  assert.equal(h._editingPanel.data.ratio, 1.5);
});

test('a text option stores the raw text', () => {
  const h = host();
  const [onInput] = handlers(renderOptionField(h, { key: 'name', kind: 'str' }, 'a'));
  onInput({ target: { value: 'b' } });
  assert.equal(h._editingPanel.data.name, 'b');
});

test('a number field keeps what is being typed until the field is left', async () => {
  const { renderNumberInput } = await import('../../custom_components/nspanel_haui/frontend/form-fields.js');
  const { noChange } = await import('../../custom_components/nspanel_haui/frontend/lit-import.js');
  const input = { id: 'dc-timeout', value: '', isConnected: true };
  let stored = 10;
  const store = (raw) => { stored = raw === '' ? 0 : Number(raw); };
  const [onInput, onBlur] = handlers(renderNumberInput('dc-timeout', stored, store));

  // Emptying the field stores the minimum, but a render must not write "0" into the box.
  onInput({ target: input });
  assert.equal(stored, 0);
  assert.ok(renderNumberInput('dc-timeout', stored, store).values.includes(noChange));
  // Other number fields still follow their stored value.
  assert.ok(renderNumberInput('dc-other', 5, store).values.includes('5'));

  // Leaving the field hands it back to the stored value.
  onBlur();
  assert.ok(renderNumberInput('dc-timeout', stored, store).values.includes('0'));

  // A field that was removed while it was being typed in is not remembered.
  onInput({ target: input });
  input.isConnected = false;
  assert.ok(renderNumberInput('dc-timeout', stored, store).values.includes('0'));
});

import { colorFieldText } from '../../custom_components/nspanel_haui/frontend/form-fields.js';

test('colour fields show plain colours as #rrggbb and keep templates as written', () => {
  assert.equal(colorFieldText([251, 86, 7]), '#fb5607');
  assert.equal(colorFieldText('#00ff00'), '#00ff00');
  assert.equal(colorFieldText('{{ "red" }}'), '{{ "red" }}');
  assert.equal(colorFieldText(null), '');
});

const background = {
  key: 'background',
  kind: 'select',
  allow_template: true,
  choices: [{ value: 'dark', label: 'Dark Color' }, { value: 'modern', label: 'Modern' }],
};

test('a select that allows templates offers a template field for a non-choice value', () => {
  const h = host();
  const [, onTemplateInput] = handlers(renderOptionField(h, background, "{{ 'dark' }}"));
  onTemplateInput({ target: { value: "{{ 'modern' }}" } });
  assert.equal(h._editingPanel.data.background, "{{ 'modern' }}");
});

test('picking "Template…" clears the value so the template field shows', () => {
  const h = host();
  const [onSelect] = handlers(renderOptionField(h, background, 'dark'));
  onSelect({ target: { value: '__template__' } });
  assert.equal(h._editingPanel.data.background, '');
});
