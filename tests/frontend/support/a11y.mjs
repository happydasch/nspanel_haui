import assert from 'node:assert/strict';
import { accessibleName } from './queries.mjs';

export function assertAccessibleName(element, expected) {
  assert.ok(element, 'Expected an accessible control to exist');
  assert.equal(accessibleName(element), expected);
}
export function assertRole(element, role) {
  assert.ok(element, 'Expected an element to exist');
  assert.equal(element.getAttribute('role') || implicitRole(element), role);
}
export function assertFocusable(element) {
  assert.ok(element, 'Expected a focusable element to exist');
  element.focus();
  assert.equal(element.ownerDocument.activeElement, element);
}
export function assertNoNestedInteractive(root) {
  for (const parent of root.querySelectorAll('button,a,input,select,textarea,[role=button],[role=link]')) {
    assert.equal(parent.querySelector('button,a,input,select,textarea,[role=button],[role=link]'), null);
  }
}
export function assertFocusReturned(document, trigger) {
  assert.equal(document.activeElement, trigger);
}

function implicitRole(element) {
  if (element.matches('button')) return 'button';
  if (element.matches('a[href]')) return 'link';
  if (element.matches('input[type=checkbox]')) return 'checkbox';
  if (element.matches('input,textarea')) return 'textbox';
  if (element.matches('select')) return 'combobox';
  return null;
}
