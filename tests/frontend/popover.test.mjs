import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  anchorElement,
  focusAnchor,
  menuItem,
  menuSeparator,
  overlayAnchor,
  popover,
  popoverSurface,
} from '../../custom_components/nspanel_haui/frontend/ui/popover.js';
import { isAnchoredOverlayKind } from '../../custom_components/nspanel_haui/frontend/store/store.js';
import { render } from './support/render.mjs';

test('popover anchors pair a trigger with its surface and restore focus', () => {
  assert.equal(overlayAnchor('notification-centre'), 'notification-centre');
  assert.equal(overlayAnchor('panel-menu', 'kitchen'), 'panel-menu:kitchen');
  assert.equal(isAnchoredOverlayKind('notification-centre'), true);
  assert.equal(isAnchoredOverlayKind('device-settings'), false);

  const root = document.createElement('div');
  const trigger = document.createElement('button');
  trigger.setAttribute('data-overlay-anchor', 'notification-centre');
  root.append(trigger);
  document.body.append(root);
  assert.equal(anchorElement(root, 'notification-centre'), trigger);
  assert.equal(anchorElement(root, null), null);
  focusAnchor(root, 'notification-centre');
  assert.equal(document.activeElement, trigger);

  const surface = document.createElement('div');
  assert.equal(popoverSurface({ querySelector: () => surface }), surface);
});

test('open popovers expose menu semantics and checkable menu items', () => {
  const root = render(popover({
    open: true,
    id: 'haui-header-actions-menu',
    label: 'Device actions',
    role: 'menu',
    anchorKey: 'notification-centre',
    content: [menuItem({ label: 'Settings', iconName: 'settings' }), menuSeparator()],
  }));
  const menu = root.querySelector('[role="menu"]');
  assert.ok(menu);
  assert.equal(menu.getAttribute('aria-label'), 'Device actions');
  assert.equal(menu.dataset.popoverAnchor, 'notification-centre');
  assert.ok(root.querySelector('[role="menuitem"]'));
  assert.ok(root.querySelector('[role="separator"]'));

  const checkable = render(menuItem({ label: 'Show entities', checked: true }));
  const item = checkable.querySelector('[role="menuitemcheckbox"]');
  assert.ok(item);
  assert.equal(item.getAttribute('aria-checked'), 'true');
});

test('a closed popover is omitted', () => {
  assert.equal(typeof popover({ open: false, id: 'x', label: 'Actions', content: '' }), 'symbol');
});

test('arrow, Home and End keys move through the enabled items of a menu', async () => {
  const { menuKeydown, focusMenu } = await import('../../custom_components/nspanel_haui/frontend/ui/popover.js');
  const focused = [];
  const root = { activeElement: null };
  const items = ['Edit', 'Rename', 'Delete'].map((label) => ({
    label,
    focus() { focused.push(label); root.activeElement = this; },
  }));
  const menu = {
    dataset: {},
    querySelectorAll: () => items,
    querySelector: () => items[0],
    getRootNode: () => root,
  };
  const press = (key) => {
    const event = { key, currentTarget: menu, prevented: false, preventDefault() { this.prevented = true; } };
    menuKeydown(event);
    return event.prevented;
  };
  focusMenu({ querySelector: () => menu });
  focusMenu({ querySelector: () => menu });
  assert.deepEqual(focused, ['Edit']);
  assert.equal(press('ArrowDown'), true);
  press('ArrowDown');
  press('ArrowDown');
  press('ArrowUp');
  press('Home');
  press('End');
  assert.deepEqual(focused, ['Edit', 'Rename', 'Delete', 'Edit', 'Delete', 'Edit', 'Delete']);
  assert.equal(press('a'), false);
});
