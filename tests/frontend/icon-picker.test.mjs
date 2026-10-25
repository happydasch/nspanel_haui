import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  fillIconDropdown,
  matchIcons,
  renderIconPicker,
} from '../../custom_components/nspanel_haui/frontend/form-fields.js';
import { jsonResponse } from './fake-host.mjs';

/** Just enough of an element for the icon picker's dropdown code. */
class FakeElement {
  constructor(tag, className = '') {
    this.tagName = tag.toUpperCase();
    this.className = className;
    this.children = [];
    this.attributes = {};
    this.listeners = {};
    this.style = {};
    this.hidden = false;
    this.textContent = '';
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
  querySelectorAll(selector) {
    const cls = selector.replace(/^\./, '');
    const found = [];
    const walk = (el) => el.children.forEach((c) => {
      if (c.className.split(' ').includes(cls)) found.push(c);
      walk(c);
    });
    walk(this);
    return found;
  }
}
globalThis.document.createElement = (tag) => new FakeElement(tag);

function pickerWrap() {
  const wrap = new FakeElement('div', 'icon-picker-wrap');
  const input = new FakeElement('input', 'native-input icon-picker-input');
  input.id = 'fld-icon';
  input.value = '';
  wrap.append(input, new FakeElement('ha-icon', 'icon-preview'), new FakeElement('div', 'icon-dropdown'));
  return { wrap, input, dropdown: wrap.querySelector('.icon-dropdown') };
}

// "weather-sunny" sorts far past the first 200 names, which is where the old list ended.
const ICONS = [...Array.from({ length: 500 }, (_, i) => `aaa-${i}`), 'sunny-alert', 'weather-sunny'];

async function loadedIcons() {
  const hass = { async fetchWithAuth() { return jsonResponse(ICONS); } };
  renderIconPicker('fld-icon', '', hass, null);
  for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r));
  return hass;
}

test('the icon dropdown finds icons from the whole icon list', async () => {
  const hass = await loadedIcons();
  const { wrap, dropdown } = pickerWrap();

  fillIconDropdown(wrap, 'mdi:weather-sun', hass, null);

  const shown = dropdown.children.map((item) => item.getAttribute('data-icon'));
  assert.deepEqual(shown, ['weather-sunny']);
  assert.equal(dropdown.hidden, false);
});

test('picking an icon with the mouse reports and shows the choice', async () => {
  const hass = await loadedIcons();
  const { wrap, input, dropdown } = pickerWrap();
  const picked = [];

  fillIconDropdown(wrap, 'weather', hass, (v) => picked.push(v));
  const item = dropdown.children[0];
  item.listeners.mousedown.forEach((fn) => fn({ preventDefault() {}, currentTarget: item }));

  assert.deepEqual(picked, ['mdi:weather-sunny']);
  assert.equal(input.value, 'mdi:weather-sunny');
});

test('icon matches list names starting with the query first and are capped', () => {
  const icons = ['alarm-light', 'light', 'lightbulb', 'ceiling-light', 'light-switch'];

  assert.deepEqual(matchIcons(icons, 'light', 4), ['light', 'lightbulb', 'light-switch', 'alarm-light']);
});
