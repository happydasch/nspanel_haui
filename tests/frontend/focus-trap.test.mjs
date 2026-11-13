import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { trapTab } from '../../custom_components/nspanel_haui/frontend/ui/focus-trap.js';

function focusable(name) {
  return { name, focused: false, matches: () => true, focus() { this.focused = true; } };
}

/** An element that takes no focus itself and holds its controls in a shadow root. */
function shadowHost(elements) {
  return { matches: () => false, shadowRoot: { querySelectorAll: () => elements } };
}

function rootWith(elements, active) {
  return {
    ownerDocument: { activeElement: active },
    getRootNode() { return { activeElement: active }; },
    querySelectorAll() { return elements; },
    focus() { this.focused = true; },
  };
}

function keyEvent(key, shiftKey = false) {
  return { key, shiftKey, prevented: false, preventDefault() { this.prevented = true; } };
}

test('Tab wraps from the last sidebar control to the first', () => {
  const first = focusable('first');
  const last = focusable('last');
  const root = rootWith([first, last], last);
  const event = keyEvent('Tab');
  assert.equal(trapTab(event, root), true);
  assert.equal(event.prevented, true);
  assert.equal(first.focused, true);
});

test('Shift+Tab wraps from the first or sidebar container to the last control', () => {
  const first = focusable('first');
  const last = focusable('last');
  const root = rootWith([first, last], first);
  const event = keyEvent('Tab', true);
  trapTab(event, root);
  assert.equal(last.focused, true);
});

test('controls in the shadow root of the sidebar form are part of the trap', () => {
  const close = focusable('close');
  const field = focusable('field');
  const save = focusable('save');
  const collapsed = { ...focusable('collapsed'), checkVisibility: () => false };
  const elements = [close, shadowHost([field, collapsed, save])];

  // From a form field Shift+Tab is the browser's: the field is not the first control.
  const back = keyEvent('Tab', true);
  assert.equal(trapTab(back, rootWith(elements, save)), false);
  assert.equal(back.prevented, false);

  // The last reachable control wraps to the first; a control in a closed section is skipped.
  const forward = keyEvent('Tab');
  assert.equal(trapTab(forward, rootWith(elements, save)), true);
  assert.equal(close.focused, true);
  assert.equal(collapsed.focused, false);
});

test('non-Tab keys are left to the active control', () => {
  const root = rootWith([focusable('first')], null);
  const event = keyEvent('Escape');
  assert.equal(trapTab(event, root), false);
  assert.equal(event.prevented, false);
});

test('an empty sidebar remains keyboard focusable', () => {
  const root = rootWith([], null);
  const event = keyEvent('Tab');
  assert.equal(trapTab(event, root), true);
  assert.equal(root.focused, true);
});

test('a wheel turn stays inside the modal sidebar unless a scrollable part takes it', async () => {
  const { keepWheelInside } = await import('../../custom_components/nspanel_haui/frontend/ui/sidebar.js');
  const sidebar = {};
  const turn = (path) => {
    const event = { prevented: false, currentTarget: sidebar, composedPath: () => [...path, sidebar], preventDefault() { this.prevented = true; } };
    keepWheelInside(event);
    return event.prevented;
  };
  const previous = globalThis.getComputedStyle;
  globalThis.getComputedStyle = (element) => ({ overflowY: element.overflowY });
  try {
    // Over the strip or the footer nothing scrolls: the page behind must not move.
    assert.equal(turn([{ scrollHeight: 40, clientHeight: 40, overflowY: 'visible' }]), true);
    // Over the form the form scrolls.
    assert.equal(turn([{ scrollHeight: 900, clientHeight: 400, overflowY: 'auto' }]), false);
    // Tall content that does not scroll itself does not count.
    assert.equal(turn([{ scrollHeight: 900, clientHeight: 400, overflowY: 'visible' }]), true);
  } finally {
    globalThis.getComputedStyle = previous;
  }
});
