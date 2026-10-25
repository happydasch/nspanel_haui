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

test('an int option stores the parsed number and keeps the other panel data', () => {
  const h = host();
  const [onInput] = handlers(renderOptionField(h, { key: 'timeout', kind: 'int' }, 5));
  onInput({ target: { value: '42' } });
  assert.deepEqual(h._editingPanel.data, { title: 'x', timeout: 42 });
  assert.equal(h.updates, 1);
  onInput({ target: { value: '' } });
  assert.equal(h._editingPanel.data.timeout, 0);
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
  choices: [{ value: 'dark', label: 'Dark' }, { value: 'modern', label: 'Modern' }],
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
