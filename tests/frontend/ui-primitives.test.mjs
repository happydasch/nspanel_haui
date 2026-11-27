import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { button, iconButton } from '../../custom_components/nspanel_haui/frontend/ui/button.js';
import { badge, countBadge, statusDot } from '../../custom_components/nspanel_haui/frontend/ui/badge.js';
import { segmented } from '../../custom_components/nspanel_haui/frontend/ui/segmented.js';
import { choiceList } from '../../custom_components/nspanel_haui/frontend/ui/choice-list.js';
import { searchField } from '../../custom_components/nspanel_haui/frontend/ui/search-field.js';
import { emptyState } from '../../custom_components/nspanel_haui/frontend/ui/empty-state.js';
import { popover, menuItem } from '../../custom_components/nspanel_haui/frontend/ui/popover.js';
import { valueTile } from '../../custom_components/nspanel_haui/frontend/ui/info-tile.js';
import { settingsTile } from '../../custom_components/nspanel_haui/frontend/ui/settings-tile.js';
import { panelRoleMarker } from '../../custom_components/nspanel_haui/frontend/ui/panel-role.js';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { render } from './support/render.mjs';
import { accessibleName, byRole, byText } from './support/queries.mjs';
import { assertAccessibleName, assertRole } from './support/a11y.mjs';
test('a search field has an accessible name and reports input and keyboard events', () => {
  const queries = [];
  const keys = [];
  const root = render(searchField({
    label: 'Search panels', value: 'light', className: 'demo',
    onInput: (value) => queries.push(value), onKeyDown: (event) => keys.push(event.key),
  }));
  const input = root.querySelector('input[type="search"]');
  assert.equal(accessibleName(input), 'Search panels');
  assert.equal(input.value, 'light');
  input.value = 'weather';
  input.dispatchEvent(new Event('input'));
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
  assert.deepEqual(queries, ['weather']);
  assert.deepEqual(keys, ['Escape']);
});


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

test('a menu trigger says it opens a menu, and names the menu only while it is open', async () => {
  const { sortHandle } = await import('../../custom_components/nspanel_haui/frontend/ui/sort-handle.js');
  const closed = byRole(render(iconButton({
    label: 'Actions', iconName: 'more', hasPopup: 'menu', expanded: false,
  })), 'button', { name: 'Actions' });
  assert.equal(closed.getAttribute('aria-haspopup'), 'menu');
  assert.equal(closed.getAttribute('aria-expanded'), 'false');
  assert.equal(closed.getAttribute('aria-controls'), null);
  // A grip only works by dragging, so a screen reader does not announce it; a finger needs the
  // mark that `ui/drag-handle.js` hangs a touch drag on.
  const grip = render(sortHandle({ label: 'Drag to reorder Kitchen' })).querySelector('.haui-sort-handle');
  assert.equal(grip.getAttribute('aria-hidden'), 'true');
  assert.equal(grip.hasAttribute('data-drag-handle'), true);
});

test('a button detail is shown after the label and is part of its name', () => {
  const root = render(button({ label: 'Schedule', iconName: 'clock', detail: '2 entries' }));
  const schedule = byRole(root, 'button', { name: 'Schedule 2 entries' });
  assert.ok(schedule);
  assert.ok(byText(schedule, '2 entries'));
  assert.equal(byRole(render(button({ label: 'Save' })), 'button', { name: 'Save' }).textContent.trim(), 'Save');
});

test('a toggling button carries its state in aria-pressed, not only in its fill', () => {
  const pressed = byRole(render(button({ label: 'Home panel', pressed: true, variant: 'primary' })), 'button', { name: 'Home panel' });
  assert.equal(pressed.getAttribute('aria-pressed'), 'true');
  assert.ok(pressed.classList.contains('haui-button-primary'));
  const released = byRole(render(button({ label: 'Idle panel', pressed: false })), 'button', { name: 'Idle panel' });
  assert.equal(released.getAttribute('aria-pressed'), 'false');
  // A plain action button is not a toggle.
  assert.equal(byRole(render(button({ label: 'Save' })), 'button', { name: 'Save' }).getAttribute('aria-pressed'), null);
});

test('badges and status dots preserve visible status and accessible names', () => {
  const root = render([badge('Update available', 'warning'), statusDot('offline', 'Disconnected')]);
  assert.ok(byText(root, 'Update available'));
  const dot = byRole(root, 'img', { name: 'Disconnected' });
  assertRole(dot, 'img');
  assertAccessibleName(dot, 'Disconnected');
});

test('a panel role marker names the role it marks, and an unknown one draws nothing', () => {
  const names = ['home', 'idle', 'navigation', 'hidden']
    .map((role) => accessibleName(render(panelRoleMarker({ role })).firstElementChild));
  assert.deepEqual(names, ['Home panel', 'Idle panel', 'Navigation', 'Hidden']);
  // A further idle panel of the cycle names its place, and is the dimmed marker.
  const extra = render(panelRoleMarker({ role: 'idle', label: 'Idle panel 2', extra: true })).firstElementChild;
  assert.deepEqual([accessibleName(extra), extra.classList.contains('is-extra')], ['Idle panel 2', true]);
  assert.equal(render(panelRoleMarker({ role: 'unknown' })).firstElementChild, null);
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

test('a segment count takes its option tone, neutral without one', () => {
  const root = render(segmented({
    label: 'Log level',
    value: 'all',
    options: [{ label: 'All', value: 'all', count: 4 }, { label: 'Errors', value: 'error', count: 2, tone: 'danger' }],
  }));
  const [all, errors] = root.querySelectorAll('.haui-badge-count');
  assert.ok(all.classList.contains('haui-badge-neutral'));
  assert.ok(errors.classList.contains('haui-badge-danger'));
  assert.equal(errors.textContent, '2');
});

test('a choice list is one labelled group of rows, and reports every toggle by key', () => {
  const toggles = [];
  const root = render(choiceList({
    id: 'copy-parts',
    label: 'What to copy',
    badge: countBadge(1, { title: '1 part picked' }),
    actions: html`<button type="button">Select all</button>`,
    choices: [
      { key: 'settings', label: 'Device settings', hint: 'Language and screen', iconName: 'settings', checked: true },
      { key: 'panels', label: 'Panels', checked: false },
      { key: 'update', label: 'Update settings', hint: 'Channel and installs', checked: false, disabled: true },
    ],
    onToggle: (key, checked) => toggles.push([key, checked]),
  }));

  // The heading names the group, so a screen reader reads it once.
  const group = byRole(root, 'group', { name: 'What to copy' });
  assert.ok(group);
  assert.equal(root.querySelector('.haui-badge-count').textContent, '1');
  assert.ok(byRole(root, 'button', { name: 'Select all' }));

  // A row's hint is part of its name, so the name stays a prefix match.
  assert.equal(byRole(group, 'checkbox', { name: 'Device settings', exact: false }).checked, true);
  assert.equal(byRole(group, 'checkbox', { name: 'Panels', exact: false }).checked, false);
  assert.equal(byRole(group, 'checkbox', { name: 'Update settings', exact: false }).disabled, true);
  assert.ok(byRole(group, 'checkbox', { name: 'Panels', exact: false }).closest('.haui-choice').classList.contains('is-checked') === false);
  assert.ok(byRole(group, 'checkbox', { name: 'Device settings', exact: false }).closest('.haui-choice').classList.contains('is-checked'));

  const panels = byRole(group, 'checkbox', { name: 'Panels', exact: false });
  panels.checked = true;
  panels.dispatchEvent(new Event('change'));
  assert.deepEqual(toggles, [['panels', true]]);
});

test('a choice list with nothing to pick says so instead of drawing an empty group', () => {
  const root = render(choiceList({
    id: 'targets', label: 'To devices', choices: [], onToggle: () => {},
    emptyText: 'Pick at least one device to copy to.',
  }));
  assert.equal(byRole(root, 'group', { name: 'To devices' }), null);
  assert.equal(root.querySelector('.haui-choice'), null);
  assert.ok(byText(root, 'Pick at least one device to copy to.'));
});

test('empty states and menu items expose their content and semantic roles', () => {
  const empty = render(emptyState({ title: 'No devices', message: 'Add a device to begin' }));
  assert.ok(byText(empty, 'No devices'));
  assert.ok(byText(empty, 'Add a device to begin'));

  const menu = render([popover({ open: true, id: 'menu', label: 'Device actions', content: 'Actions' }), menuItem({ label: 'Remove', danger: true })]);
  assert.ok(byRole(menu, 'menuitem', { name: 'Remove' }));
});

test('a value tile pairs its label with its value and detail, and offers no control', () => {
  const root = render(html`<dl>${valueTile({ label: 'Brightness', value: '80%', detail: 'Dimmed: 15%', iconName: 'brightness' })}${
    valueTile({ label: 'Notification sound', value: 'Off', muted: true })}</dl>`);
  const terms = [...root.querySelectorAll('dt')];
  assert.deepEqual(terms.map((term) => term.textContent.trim()), ['Brightness', 'Notification sound']);
  assert.deepEqual([...terms[0].parentElement.querySelectorAll('dd')].map((value) => value.textContent.trim()),
    ['80%', 'Dimmed: 15%']);
  assert.equal(terms[0].querySelector('ha-icon').getAttribute('aria-hidden'), 'true');
  assert.equal(root.querySelector('button'), null);
});

test('a settings tile is one button naming its group and what the group holds', () => {
  const opened = [];
  const root = render([
    settingsTile({
      key: 'schedule', iconName: 'clock', label: 'Schedule', summary: '3 entries',
      onClick: () => opened.push('schedule'),
    }),
    settingsTile({ key: 'advanced', iconName: 'tuneVariant', label: 'Advanced',
      onClick: () => opened.push('advanced') }),
  ]);
  const tiles = [...root.querySelectorAll('[data-settings-tile]')];
  assert.deepEqual(tiles.map((tile) => tile.dataset.settingsTile), ['schedule', 'advanced']);

  // The accessible name is the group plus its value line, on the button itself.
  const schedule = byRole(root, 'button', { name: 'Schedule', exact: false });
  assert.ok(schedule);
  assert.equal(accessibleName(schedule).replace(/\s+/g, ' ').trim(), 'Schedule 3 entries');
  schedule.dispatchEvent(new Event('click', { bubbles: true }));
  assert.deepEqual(opened, ['schedule']);

  // No nested control: the whole tile is the button.
  assert.equal(root.querySelector('button button, button a, button [role="button"]'), null);
});
