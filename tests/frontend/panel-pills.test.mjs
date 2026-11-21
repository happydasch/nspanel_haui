import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { panelPills } from '../../custom_components/nspanel_haui/frontend/ui/panel-pills.js';

/** Flatten a Lit TemplateResult tree to text. */
function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (value?.strings) return value.strings.reduce((text, part, index) => text + part + flatten(value.values[index]), '');
  if (value == null) return '';
  if (typeof value === 'symbol') return '';
  return String(value);
}

/** Every template of a tree that renders `text`, innermost first. */
function templatesShowing(template, text, found = []) {
  if (!template?.strings) return found;
  for (const value of template.values) {
    for (const entry of Array.isArray(value) ? value : [value]) templatesShowing(entry, text, found);
  }
  if (flatten(template).includes(text)) found.push(template);
  return found;
}

/** The click handler of the innermost button inside the pill that renders `text`. */
function removeOf(view, text) {
  for (const template of templatesShowing(view, text)) {
    const index = template.strings.findIndex((part) => part.trimEnd().endsWith('@click='));
    if (index >= 0) return template.values[index];
  }
  throw new Error(`no remove button for ${text}`);
}

const PANELS = [
  { key: 'lights', type: 'grid', title: 'Lights' },
  { key: 'clock', type: 'grid', title: 'Clock' },
];

test('a listed panel pill shows its name, and a stale key stays listed as unknown', () => {
  const text = flatten(panelPills({
    id: 'dc-idle-panels', panels: PANELS, keys: ['clock', 'gone'], onChange: () => {},
  }));
  assert.match(text, /Clock/);
  // The stale reference is neither dropped nor shown as a bare key.
  assert.match(text, /Unknown key "gone"/);
  assert.doesNotMatch(text, /<span>gone<\/span>/);
});

test('removing an unknown key still removes the real key it names', () => {
  const changes = [];
  const view = panelPills({
    id: 'dc-idle-panels', panels: PANELS, keys: ['clock', 'gone'], onChange: (keys) => changes.push(keys),
  });
  removeOf(view, 'Unknown key "gone"')();
  assert.deepEqual(changes, [['clock']]);
});

test('the add list offers the panels the list does not hold yet', () => {
  const text = flatten(panelPills({
    id: 'dc-home-panel', panels: PANELS, keys: ['clock'], single: true, onChange: () => {},
  }));
  assert.match(text, /Lights/);
  assert.match(text, /dc-home-panel/);
});
