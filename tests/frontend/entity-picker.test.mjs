import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderEntityPicker } from '../../custom_components/nspanel_haui/frontend/haui-entity.js';
import { createDropdownKeyboardController } from '../../custom_components/nspanel_haui/frontend/dom-helpers.js';

/** Flatten a Lit TemplateResult into its markup and text, for assertions. */
function markup(value) {
  if (value == null || typeof value === 'function') return '';
  if (Array.isArray(value)) return value.map(markup).join('');
  if (value.strings) {
    return value.strings.map((s, i) => s + (i < value.values.length ? markup(value.values[i]) : '')).join('');
  }
  return String(value);
}

const HASS = {
  states: {
    'light.a': { attributes: { friendly_name: 'Light A' } },
    'switch.b': { attributes: {} },
  },
};

test('the entity picker exposes combobox and listbox semantics', () => {
  const out = markup(renderEntityPicker({ id: 'ent', value: '', label: 'Entity', hass: HASS }));

  assert.match(out, /role="combobox"/);
  assert.match(out, /aria-haspopup="listbox"/);
  assert.match(out, /aria-expanded="false"/);
  assert.match(out, /aria-autocomplete="list"/);
  assert.match(out, /aria-controls=ent-dropdown/);
  assert.match(out, /id=ent-dropdown/);
  assert.match(out, /role="listbox"/);
  assert.match(out, /aria-labelledby=ent-label/);
  assert.match(out, /role="option"/);
  assert.match(out, /id=ent-dropdown-opt-0/);
  assert.match(out, /id=ent-dropdown-opt-1/);
});

/** Just enough element for the dropdown keyboard controller. */
class FakeEl {
  constructor(cls = '') {
    this.className = cls;
    this.attributes = {};
    this.style = {};
    this.hidden = false;
    this.id = '';
    this._classes = new Set();
    this.classList = {
      add: (c) => this._classes.add(c),
      remove: (c) => this._classes.delete(c),
      contains: (c) => this._classes.has(c),
      toggle: (c, on) => (on ? this._classes.add(c) : this._classes.delete(c)),
    };
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  scrollIntoView() { this.scrolled = true; }
}

function option(id, display) {
  const el = new FakeEl('entity-dropdown-item');
  el.id = id;
  el.style.display = display;
  return el;
}

function fakePicker(items) {
  const dropdown = new FakeEl('entity-dropdown');
  dropdown.style.display = '';
  dropdown.querySelectorAll = () => items;
  const input = new FakeEl('entity-picker-input');
  const wrap = new FakeEl('entity-picker-wrap');
  wrap.querySelector = (sel) => (sel === '.entity-dropdown' ? dropdown : null);
  return { wrap, input };
}

test('arrow keys highlight and select the visible option, not a hidden one', () => {
  const hiddenA = option('opt-a', 'none');
  const hiddenB = option('opt-b', 'none');
  const visible = option('opt-c', '');
  const { wrap, input } = fakePicker([hiddenA, hiddenB, visible]);

  let selected = null;
  const handler = createDropdownKeyboardController({
    getWrap: () => wrap,
    onSelect: (visibleItems, idx) => { selected = visibleItems[idx].id; },
    onDismiss: () => {},
  });

  handler({ key: 'ArrowDown', preventDefault() {}, target: input });

  assert.equal(visible.classList.contains('active'), true);
  assert.equal(hiddenA.classList.contains('active'), false);
  assert.equal(hiddenB.classList.contains('active'), false);
  assert.equal(input.getAttribute('aria-activedescendant'), 'opt-c');
  assert.equal(visible.scrolled, true);

  handler({ key: 'Enter', preventDefault() {}, target: input });
  assert.equal(selected, 'opt-c');
});
