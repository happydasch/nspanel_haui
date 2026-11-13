import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  fillEntityDropdown,
  matchEntities,
  renderEntityPicker,
} from '../../custom_components/nspanel_haui/frontend/haui-entity.js';
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
  // The options are filled in when the dropdown opens, not rendered per entity.
  assert.doesNotMatch(out, /entity-dropdown-item/);
});

const entity = (entityId, name = entityId) => ({ entityId, name, search: `${entityId}\n${name}`.toLowerCase() });

test('entity matches follow the query and the domain, and are capped with the total kept', () => {
  const entities = [
    entity('light.desk', 'Desk'), entity('light.hall', 'Hall lamp'),
    entity('switch.lamp', 'Plug'), entity('switch.fan', 'Fan'),
  ];
  const ids = (found) => found.matches.map((match) => match.entityId);

  assert.deepEqual(ids(matchEntities(entities, '')), ['light.desk', 'light.hall', 'switch.lamp', 'switch.fan']);
  // The id or the friendly name may contain the query.
  assert.deepEqual(ids(matchEntities(entities, 'lamp')), ['light.hall', 'switch.lamp']);
  assert.deepEqual(ids(matchEntities(entities, 'lamp', 'switch')), ['switch.lamp']);

  const capped = matchEntities(entities, '', '__all', 3);
  assert.equal(capped.matches.length, 3);
  assert.equal(capped.total, 4);
});

test('the dropdown shows the matches as options and says how many it left out', () => {
  const created = [];
  const previous = globalThis.document.createElement;
  globalThis.document.createElement = () => {
    const el = new FakeEl();
    el.children = [];
    el.append = (...nodes) => el.children.push(...nodes);
    created.push(el);
    return el;
  };
  try {
    const dropdown = new FakeEl('entity-dropdown');
    dropdown.id = 'ent-dropdown';
    dropdown.replaceChildren = (...nodes) => { dropdown.children = nodes; };

    fillEntityDropdown(dropdown, { matches: [entity('light.a', 'Light A'), entity('switch.b')], total: 5 });

    const [first, second, more] = dropdown.children;
    assert.equal(dropdown.children.length, 3);
    assert.equal(first.id, 'ent-dropdown-opt-0');
    assert.equal(first.getAttribute('role'), 'option');
    assert.equal(first.getAttribute('data-entity-id'), 'light.a');
    assert.deepEqual(first.children.map((child) => child.textContent), ['Light A', 'light.a']);
    assert.equal(second.id, 'ent-dropdown-opt-1');
    // The note is not an option: the keyboard controller only walks the items.
    assert.equal(more.className, 'entity-dropdown-more');
    assert.match(more.textContent, /^3 more/);

    fillEntityDropdown(dropdown, { matches: [entity('light.a')], total: 1 });
    assert.equal(dropdown.children.length, 1);
  } finally {
    globalThis.document.createElement = previous;
  }
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
