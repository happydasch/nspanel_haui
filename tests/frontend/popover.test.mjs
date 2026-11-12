// @ts-check
import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  anchorElement,
  focusAnchor,
  menuItem,
  menuSeparator,
  overlayAnchor,
  placeOpenPopovers,
  placePopover,
  popover,
  popoverSurface,
} from '../../custom_components/nspanel_haui/frontend/ui/popover.js';
import { isAnchoredOverlayKind } from '../../custom_components/nspanel_haui/frontend/store/store.js';

const source = (template) => `${template.strings.join(' ')} ${template.values.map((value) => {
  if (Array.isArray(value)) return value.map((nested) => nested?.strings ? source(nested) : String(nested ?? '')).join(' ');
  return value?.strings ? source(value) : String(value ?? '');
}).join(' ')}`;

/** A fake element with a viewport rect and an inline style map. */
function element({ left = 0, top = 0, width = 100, height = 30, dataset = {}, style = {} } = {}) {
  return {
    dataset,
    style: {
      ...style,
      removeProperty(name) { delete this[name]; },
    },
    offsetWidth: width,
    offsetHeight: height,
    getBoundingClientRect: () => ({ left, top, right: left + width, bottom: top + height, width, height }),
    focus() { this.focused = true; },
  };
}

test('popover anchors pair a trigger with its surface', () => {
  assert.equal(overlayAnchor('notification-centre'), 'notification-centre');
  assert.equal(overlayAnchor('panel-menu', 'kitchen'), 'panel-menu:kitchen');
  assert.equal(isAnchoredOverlayKind('notification-centre'), true);
  assert.equal(isAnchoredOverlayKind('device-settings'), false);
  const trigger = element();
  const root = { querySelector: (selector) => (selector.includes('notification-centre') ? trigger : null) };
  assert.equal(anchorElement(root, 'notification-centre'), trigger);
  assert.equal(anchorElement(root, null), null);
  focusAnchor(root, 'notification-centre');
  assert.equal(trigger.focused, true);
  const surface = element();
  assert.equal(popoverSurface({ querySelector: () => surface }), surface);
});

test('the menu primitive keeps menu roles and skips a closed popover', () => {
  assert.equal(typeof popover({ open: false, id: 'x', label: 'Actions', content: '' }), 'symbol');
  const markup = source(popover({
    open: true,
    id: 'haui-header-actions-menu',
    label: 'Device actions',
    role: 'menu',
    anchorKey: 'notification-centre',
    content: [menuItem({ label: 'Settings', iconName: 'settings' }), menuSeparator()],
  }));
  assert.match(markup, /haui-popover/);
  assert.match(markup, /role=/);
  assert.ok(markup.includes('menu'));
  assert.ok(markup.includes('Device actions'));
  assert.ok(markup.includes('notification-centre'));
  assert.match(markup, /\bmenuitem\b/);
  assert.match(markup, /haui-menu-separator/);
  // A checkable item is a menuitemcheckbox, the only role aria-checked belongs to.
  const checkable = source(menuItem({ label: 'Show entities', checked: true }));
  assert.match(checkable, /\bmenuitemcheckbox\b/);
  assert.match(checkable, /aria-checked=/);
  assert.match(checkable, /\btrue\b/);
});

test('a placed popover sits under its trigger and clamps into the viewport', () => {
  const trigger = element({ left: 900, top: 40, width: 40, height: 32 });
  const panel = element({ width: 240, height: 200 });
  placePopover(panel, trigger, { align: 'end', win: { innerWidth: 1000, innerHeight: 700 } });
  assert.equal(panel.style.top, '78px');
  assert.equal(panel.style.left, '700px');
});

test('a popover without room below flips above its trigger', () => {
  const trigger = element({ left: 40, top: 600, width: 40, height: 32 });
  const panel = element({ width: 240, height: 200 });
  placePopover(panel, trigger, { align: 'end', win: { innerWidth: 1000, innerHeight: 700 } });
  assert.equal(panel.style.top, '394px');
});

test('narrow widths drop the inline placement so the sheet rule applies', () => {
  // What a wide placement leaves behind before the window narrows.
  const panel = element({
    dataset: { popoverAnchor: 'notification-centre' },
    style: { top: '10px', left: '20px', right: 'auto', bottom: 'auto' },
  });
  placeOpenPopovers({ querySelectorAll: () => [panel], querySelector: () => null }, { innerWidth: 480 });
  assert.equal(panel.style.top, undefined);
  assert.equal(panel.style.left, undefined);
  assert.equal(panel.style.right, undefined);
  assert.equal(panel.style.bottom, undefined);
});

test('a static popover keeps its own placement', () => {
  const panel = element({
    dataset: { popoverAnchor: 'notification-centre', popoverStatic: 'true' },
    style: { top: '64px', left: 'auto' },
  });
  placeOpenPopovers({ querySelectorAll: () => [panel], querySelector: () => null }, { innerWidth: 1200 });
  assert.equal(panel.style.top, '64px');
});


test('arrow, Home and End keys move through the enabled items of a menu', async () => {
  const { menuKeydown, focusMenu } = await import('../../custom_components/nspanel_haui/frontend/ui/popover.js');
  const focused = [];
  const items = ['Edit', 'Rename', 'Delete'].map((label) => ({ label, focus() { focused.push(label); root.activeElement = this; } }));
  const root = { activeElement: null };
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
  // Other keys stay with the page (Escape is the shell's).
  assert.equal(press('a'), false);
});
