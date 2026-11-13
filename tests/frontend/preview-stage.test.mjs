import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { byRole, byText } from './support/queries.mjs';
import { render } from './support/render.mjs';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';

test('preview stage presents the no-panel state and its next step', () => {
  const root = render(previewStage({ state: 'no-panel' }));
  assert.ok(root.querySelector('[aria-label="Panel preview"]'));
  assert.ok(byText(root, 'No panel to preview'));
  assert.ok(byText(root, 'Add a panel or assign a home panel to see a preview'));
});

test('preview stage shows its supplied screen and hardware content', () => {
  const screen = document.createElement('div');
  screen.textContent = 'Display content';
  const button = document.createElement('button');
  button.textContent = 'Hardware control';
  const root = render(previewStage({ screen, hardware: button }));
  assert.ok(byText(root, 'Display content'));
  assert.ok(byRole(root, 'button', { name: 'Hardware control' }));
  assert.equal(root.querySelector('[aria-label="Panel preview"]').getAttribute('aria-busy'), 'false');
});

test('preview stage announces startup and preview errors', () => {
  const loading = render(previewStage({ state: 'loading' }));
  assert.equal(loading.querySelector('[aria-live="polite"]')?.textContent.trim(), 'Starting the live preview…');
  assert.equal(loading.querySelector('[aria-label="Panel preview"]').getAttribute('aria-busy'), 'true');

  const failed = render(previewStage({ state: 'error', error: 'Hub unavailable' }));
  assert.equal(byRole(failed, 'alert')?.textContent.trim(), 'Hub unavailable');
});
