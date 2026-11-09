import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { renderToast } from '../../custom_components/nspanel_haui/frontend/toast.js';

test('renders toasts as top-layer popovers above dialogs and other popovers', async () => {
  let showPopoverCalls = 0;
  const element = {
    matches(selector) {
      assert.equal(selector, ':popover-open');
      return false;
    },
    showPopover() {
      showPopoverCalls += 1;
    },
  };
  const host = {
    _toast: { message: 'Saved', type: 'success' },
    updateComplete: Promise.resolve(),
    renderRoot: {
      querySelector(selector) {
        assert.equal(selector, '.toast[popover]');
        return element;
      },
    },
  };

  const template = renderToast(host);
  assert.match(template.strings.join(''), /popover="manual"/);
  await host.updateComplete;
  await Promise.resolve();
  assert.equal(showPopoverCalls, 1);
});

test('does not try to open a toast after it has been cleared', () => {
  const host = { _toast: null };
  assert.equal(renderToast(host), '');
});
