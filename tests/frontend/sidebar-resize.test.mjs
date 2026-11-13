import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { modalSidebar } from '../../custom_components/nspanel_haui/frontend/ui/sidebar.js';
import { render } from './support/render.mjs';
import { byRole } from './support/queries.mjs';
import { assertAccessibleName } from './support/a11y.mjs';

test('the resize separator responds to keyboard limits, persists width, and resets', () => {
  const renderSidebar = () => render(modalSidebar({
    label: 'Logs', body: document.createTextNode('Lines'), onClose() {},
  }));
  const root = renderSidebar();
  const separator = byRole(root, 'separator', { name: 'Resize sidebar' });
  assert.ok(separator);
  assertAccessibleName(separator, 'Resize sidebar');

  const width = () => Number(separator.getAttribute('aria-valuenow'));
  const key = (name) => separator.dispatchEvent(new KeyboardEvent('keydown', {
    key: name, bubbles: true, cancelable: true,
  }));
  const initial = width();
  key('ArrowLeft');
  assert.ok(width() > initial);

  key('Home');
  const minimum = Number(separator.getAttribute('aria-valuemin'));
  assert.equal(width(), minimum);
  key('ArrowRight');
  assert.equal(width(), minimum);

  key('End');
  const maximum = Number(separator.getAttribute('aria-valuemax'));
  assert.equal(width(), maximum);
  assert.equal(localStorage.getItem('haui_sidebarWidth'), String(maximum));

  const reopened = renderSidebar();
  const reopenedSeparator = byRole(reopened, 'separator', { name: 'Resize sidebar' });
  assert.equal(Number(reopenedSeparator.getAttribute('aria-valuenow')), maximum);

  separator.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
  assert.equal(width(), initial);
});
