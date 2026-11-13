import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { render } from './support/render.mjs';

import { updatePolicyView } from '../../custom_components/nspanel_haui/frontend/views/update-policy.js';
import { updatePolicySummary } from '../../custom_components/nspanel_haui/frontend/ui/format.js';

const POLICY = {
  firmware_auto_update: false,
  auto_install: true,
  install_delay: 600,
  max_attempts: 3,
  retry_interval: 3600,
};

function view(options = {}) {
  return render(updatePolicyView({ policy: POLICY, dirty: false, onChange() {}, onSave() {}, ...options }));
}

test('the policy names every setting with its current value', () => {
  const root = view();

  assert.equal(root.querySelector('#policy-firmware-auto').checked, false);
  assert.equal(root.querySelector('#policy-tft-auto').checked, true);
  assert.equal(root.querySelector('#policy-install-delay option[selected]').value, '600');
  assert.equal(root.querySelector('#policy-max-attempts').value, '3');
  assert.equal(root.querySelector('#policy-retry-interval option[selected]').value, '3600');
  assert.match(root.textContent, /Install firmware updates automatically/);
  assert.match(root.textContent, /Failed attempts before it stops/);
});

test('a change reports the whole edited policy', () => {
  const changes = [];
  const root = view({ onChange: (policy) => changes.push(policy) });

  const toggle = root.querySelector('#policy-firmware-auto');
  toggle.checked = true;
  toggle.dispatchEvent(new Event('change', { bubbles: true }));

  assert.deepEqual(changes, [{ ...POLICY, firmware_auto_update: true }]);
});

test('save waits for a change and reports it', () => {
  const saved = [];
  const clean = view({ onSave: () => saved.push(true) });
  const save = (root) => [...root.querySelectorAll('button')].find((button) => /Save/.test(button.textContent));

  assert.equal(save(clean).disabled, true);
  const dirty = view({ dirty: true, onSave: () => saved.push(true) });
  save(dirty).click();
  assert.deepEqual(saved, [true]);
});

test('the policy summary reads as one line', () => {
  assert.equal(
    updatePolicySummary(POLICY),
    'Firmware: by hand · Display: automatic · 3 attempts, 1 hour apart',
  );
  assert.equal(
    updatePolicySummary({ ...POLICY, firmware_auto_update: true, max_attempts: 1, retry_interval: 86400 }),
    'Firmware: automatic, after 10 minutes · Display: automatic · 1 attempt',
  );
});
