import './support/browser.mjs';

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

import { render } from './support/render.mjs';
import { byLabel, byRole, byText } from './support/queries.mjs';
import { renderItemEditFields } from '../../custom_components/nspanel_haui/frontend/item-renderers.js';

/** Render a panel option into a container that re-renders on every requestUpdate. */
function mountOption(opt, data) {
  const container = document.createElement('div');
  const h = {
    _editingPanel: { index: 0, data },
    _openColorPresets: new Set(),
    requestUpdate() { render(renderOptionField(h, opt, h._editingPanel.data[opt.key]), container); },
  };
  h.requestUpdate();
  return { h, container };
}

const accent = { key: 'accent', kind: 'color', label: 'Accent', description: 'Accent of the panel.' };

test('a colour option is a labelled text field with a colour picker and hidden presets', () => {
  const { container } = mountOption(accent, { accent: [255, 120, 0] });
  assert.equal(byLabel(container, 'Accent').value, '#ff7800');
  assert.ok(byRole(container, 'textbox', { name: 'Pick color' }), 'the swatch opens the browser colour picker');
  const toggle = byRole(container, 'button', { name: 'Presets' });
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(container.querySelector(`#${toggle.getAttribute('aria-controls')}`).hidden, true);
});

test('the presets toggle shows preset colours, and a picked preset keeps the stored format', () => {
  const { h, container } = mountOption(accent, { accent: [255, 120, 0] });
  byRole(container, 'button', { name: 'Presets' }).click();
  const toggle = byRole(container, 'button', { name: 'Presets' });
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  assert.equal(container.querySelector(`#${toggle.getAttribute('aria-controls')}`).hidden, false);
  byRole(container, 'button', { name: '#F44336' }).click();
  assert.deepEqual(h._editingPanel.data.accent, [244, 67, 54]);
  assert.equal(byLabel(container, 'Accent').value, '#f44336');
});

test('typing in a colour option stores the parsed value', () => {
  const { h, container } = mountOption(accent, {});
  const input = byLabel(container, 'Accent');
  input.value = '[1, 2, 3]';
  input.dispatchEvent(new Event('input'));
  input.dispatchEvent(new Event('change'));
  assert.deepEqual(h._editingPanel.data.accent, [1, 2, 3]);
});

test('typing an RGB565 number keeps the typed text and stores the number on change', () => {
  const { h, container } = mountOption(accent, {});
  const input = byLabel(container, 'Accent');
  let typed = '';
  for (const key of '63488') {
    typed += key;
    input.value = typed;
    input.dispatchEvent(new Event('input'));
    assert.equal(input.value, typed);
  }
  input.dispatchEvent(new Event('change'));
  assert.equal(h._editingPanel.data.accent, 63488);
});

/** Render the inline item editor for one item of a panel with `itemOptions`. */
function mountItemEditor(itemOptions, config) {
  const container = document.createElement('div');
  const descriptor = { type_key: 'grid', item_options: itemOptions };
  const h = {
    _editingPanel: { index: 0, data: { type: 'grid' } },
    _editingItem: { optKey: 'entities', index: 0, config, domain: '' },
    _editingItemType: 'text',
    requestUpdate() { render(renderItemEditFields(h, descriptor), container); },
  };
  h.requestUpdate();
  return { h, container };
}

test('an item colour option uses the same colour field as a panel option', () => {
  const { h, container } = mountItemEditor(
    [{ key: 'back_color', kind: 'color', label: 'Background color', description: 'Background of the tile.' }],
    { item: 'Hello', back_color: '#00ff00' },
  );
  assert.equal(byLabel(container, 'Background color').value, '#00ff00');
  const toggles = [...container.querySelectorAll('button[aria-controls]')]
    .filter((button) => button.getAttribute('aria-label') === 'Presets');
  assert.equal(toggles.length, 2, 'the item colour and the item option colour each have presets');
  toggles[1].click();
  const presets = container.querySelector(`#${toggles[1].getAttribute('aria-controls')}`);
  byRole(presets, 'button', { name: '#2196F3' }).click();
  assert.equal(h._editingItem.config.back_color, '#2196F3');
});

test('the next item opens with its colour presets closed', () => {
  const { h, container } = mountItemEditor([], { item: 'Hello' });
  byRole(container, 'button', { name: 'Presets' }).click();
  assert.equal(byRole(container, 'button', { name: 'Presets' }).getAttribute('aria-expanded'), 'true');
  h._editingItem = { optKey: 'entities', index: 1, config: { item: 'World' }, domain: '' };
  h.requestUpdate();
  assert.equal(byRole(container, 'button', { name: 'Presets' }).getAttribute('aria-expanded'), 'false');
});

test('emptying an item number option unsets it instead of storing 0', () => {
  const { h, container } = mountItemEditor(
    [{ key: 'size', kind: 'int', label: 'Size', description: 'Tile size.' }],
    { item: 'Hello', size: 2 },
  );
  const input = byLabel(container, 'Size');
  input.value = '';
  input.dispatchEvent(new Event('input'));
  assert.equal(h._editingItem.config.size, undefined);
});

test('every item field shows its description', () => {
  const { container } = mountItemEditor([], { item: 'Hello' });
  const hints = [...container.querySelectorAll('.haui-field-hint')].map((hint) => hint.textContent);
  for (const start of ['Custom display name', 'An MDI icon name', 'A CSS hex color', 'A display value', 'An attribute name', 'The key of a popup']) {
    assert.ok(hints.some((hint) => hint.startsWith(start)), `missing hint: ${start}`);
  }
});

test('the advanced item fields fold behind a native disclosure', () => {
  const { container } = mountItemEditor([], { item: 'Hello' });
  const summary = byText(container, 'Advanced');
  assert.equal(summary.closest('summary')?.parentElement?.tagName, 'DETAILS');
});
