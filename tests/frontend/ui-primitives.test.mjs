import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { button, iconButton } from '../../custom_components/nspanel_haui/frontend/ui/button.js';
import { badge, countBadge, statusDot } from '../../custom_components/nspanel_haui/frontend/ui/badge.js';
import { segmented } from '../../custom_components/nspanel_haui/frontend/ui/segmented.js';
import { emptyState } from '../../custom_components/nspanel_haui/frontend/ui/empty-state.js';
import { popover, menuItem } from '../../custom_components/nspanel_haui/frontend/ui/popover.js';
import { render } from './support/render.mjs';
import { byRole, byText } from './support/queries.mjs';
import { assertAccessibleName, assertRole } from './support/a11y.mjs';

test('button primitives expose native disabled and accessible icon-only behavior', () => {
  const root = render(button({ label: 'Save', busy: true }));
  const save = byRole(root, 'button', { name: 'Save' });
  assertAccessibleName(save, 'Save');
  assert.equal(save.disabled, true);
  assert.equal(save.getAttribute('aria-busy'), 'true');

  const activated = [];
  const activeRoot = render(button({ label: 'Apply', onClick: () => activated.push('applied') }));
  byRole(activeRoot, 'button', { name: 'Apply' }).dispatchEvent(new Event('click', { bubbles: true }));
  assert.deepEqual(activated, ['applied']);

  const closeRoot = render(iconButton({ label: 'Close panel', iconName: 'close', disabled: true }));
  const close = byRole(closeRoot, 'button', { name: 'Close panel' });
  assertAccessibleName(close, 'Close panel');
  assert.equal(close.disabled, true);
});

test('badges and status dots preserve visible status and accessible names', () => {
  const root = render([badge('Update available', 'warning'), statusDot('offline', 'Disconnected')]);
  assert.ok(byText(root, 'Update available'));
  const dot = byRole(root, 'img', { name: 'Disconnected' });
  assertRole(dot, 'img');
  assertAccessibleName(dot, 'Disconnected');
});

test('a count badge shows its number, keeps a tone and says what it counts', () => {
  const root = render([
    countBadge(3, { title: '3 items' }),
    countBadge(2, { tone: 'danger' }),
    countBadge(0, { tone: 'unknown' }),
  ]);
  const [items, errors, none] = root.querySelectorAll('.haui-badge-count');
  assert.equal(items.textContent, '3');
  assert.equal(items.getAttribute('title'), '3 items');
  assert.ok(errors.classList.contains('haui-badge-danger'));
  assert.equal(errors.hasAttribute('title'), false);
  assert.equal(none.textContent, '0');
  assert.ok(none.classList.contains('haui-badge-neutral'));
});

test('segmented controls report selection and invoke the chosen option', () => {
  const selected = [];
  const root = render(segmented({
    label: 'Workspace view',
    value: 'panels',
    options: [{ label: 'Preview', value: 'preview' }, { label: 'Panels', value: 'panels' }],
    onSelect: (value) => selected.push(value),
  }));
  const group = byRole(root, 'group', { name: 'Workspace view' });
  assert.ok(group);
  const panels = byRole(group, 'button', { name: 'Panels' });
  const preview = byRole(group, 'button', { name: 'Preview' });
  assert.equal(panels.getAttribute('aria-pressed'), 'true');
  assert.equal(preview.getAttribute('aria-pressed'), 'false');
  preview.dispatchEvent(new Event('click', { bubbles: true }));
  assert.deepEqual(selected, ['preview']);
});

test('empty states and menu items expose their content and semantic roles', () => {
  const empty = render(emptyState({ title: 'No devices', message: 'Add a device to begin' }));
  assert.ok(byText(empty, 'No devices'));
  assert.ok(byText(empty, 'Add a device to begin'));

  const menu = render([popover({ open: true, id: 'menu', label: 'Device actions', content: 'Actions' }), menuItem({ label: 'Remove', danger: true })]);
  assert.ok(byRole(menu, 'menuitem', { name: 'Remove' }));
});
