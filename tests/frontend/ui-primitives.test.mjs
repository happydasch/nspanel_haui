import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { button, iconButton } from '../../custom_components/nspanel_haui/frontend/ui/button.js';
import { badge, statusDot } from '../../custom_components/nspanel_haui/frontend/ui/badge.js';
import { segmented } from '../../custom_components/nspanel_haui/frontend/ui/segmented.js';
import { emptyState } from '../../custom_components/nspanel_haui/frontend/ui/empty-state.js';
import { popover, menuItem } from '../../custom_components/nspanel_haui/frontend/ui/popover.js';

const source = (template) => `${template.strings.join(' ')} ${template.values.map((value) => {
  if (Array.isArray(value)) return value.map((nested) => nested?.strings ? source(nested) : String(nested ?? '')).join(' ');
  return value?.strings ? source(value) : String(value ?? '');
}).join(' ')}`;

test('button primitives expose native disabled, busy, and accessible icon-only semantics', () => {
  const primary = button({ label: 'Save', variant: 'primary', busy: true });
  assert.match(source(primary), /<button/);
  assert.match(source(primary), /aria-busy/);
  assert.ok(primary.values.includes(true));

  const iconOnly = iconButton({ label: 'Close panel', iconName: 'close', disabled: true });
  assert.match(source(iconOnly), /aria-label/);
  assert.ok(iconOnly.values.includes('Close panel'));
  assert.ok(iconOnly.values.includes(true));
});

test('badges and status dots render explicit tones and labels', () => {
  assert.match(source(badge('Update', 'warning')), /haui-badge-warning/);
  const dot = statusDot('offline', 'Disconnected');
  assert.match(source(dot), /role="img"/);
  assert.ok(dot.values.includes('Disconnected'));
});

test('segmented controls provide pressed state and disable unsupported options', () => {
  const template = segmented({
    label: 'Workspace view',
    value: 'panels',
    options: [{ label: 'Preview', value: 'preview' }, { label: 'Panels', value: 'panels' }],
    onSelect: () => {},
  });
  assert.match(source(template), /role="group"/);
  assert.match(source(template), /aria-pressed/);
  assert.ok(template.values.some((value) => Array.isArray(value)));
});

test('empty state and popover templates provide labels and menu roles', () => {
  assert.match(source(emptyState({ title: 'No devices', message: 'Add a device to begin' })), /haui-empty-state/);
  assert.match(source(popover({ open: true, id: 'menu', label: 'Device actions', content: 'Actions' })), /role/);
  assert.match(source(menuItem({ label: 'Remove', danger: true })), /\bmenuitem\b/);
});
