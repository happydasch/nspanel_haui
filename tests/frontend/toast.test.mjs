import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderToast } from '../../custom_components/nspanel_haui/frontend/toast.js';
import { render, flush } from './support/render.mjs';
import { byText } from './support/queries.mjs';

test('rendered haui-toast exposes its message in the popover', async () => {
  const host = { _toast: { message: 'Saved', type: 'success' }, updateComplete: new Promise(() => {}) };
  const root = document.createElement('div');
  host.renderRoot = root;
  render(renderToast(host), root);
  await flush();

  const toastElement = byText(root, 'Saved');
  assert.ok(toastElement);
  assert.equal(toastElement.getAttribute('popover'), 'manual');
});
