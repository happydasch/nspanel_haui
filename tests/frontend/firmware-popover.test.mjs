import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { updateStateLabel, updateSummary } from'../../custom_components/nspanel_haui/frontend/dialogs/firmware.js';
import { render } from './support/render.mjs';

function element(props = {}) {
  const FirmwarePopover = customElements.get('nspanel-firmware-popover');
  return Object.assign(document.createElement('nspanel-firmware-popover'), {
    open: true,
    deviceName: 'kitchen',
    entryId: 'entry1',
    deviceStatus: {
      integration_version: '0.5.0',
      device_info: { tft_version: '1.2.3', tft_required_version: '1.2.4' },
      update: { enabled: true, state: 'idle', tft_update_available: true },
    },
    _picker: null,
    _actionBusy: false,
    ...props,
  });
}

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  if (Array.isArray(value.strings) && Array.isArray(value.values)) {
    return value.strings.map((part, index) => `${part}${flatten(value.values[index] ?? '')}`).join('');
  }
  return '';
}

test('the Updates sidebar shows current and required versions with available actions', () => {
  const view = flatten(element().render());
  assert.match(view, /haui-firmware-sidebar/);
  // The sidebar frame carries the title and the close control.
  assert.doesNotMatch(view, /haui-popover|mdi:close/);
  assert.match(view, /0\.5\.0/);
  assert.match(view, /1\.2\.3/);
  assert.match(view, /1\.2\.4/);
  assert.match(view, /Check for updates/);
  assert.equal((view.match(/>\s*Install\s*</g) || []).length, 2);
  assert.doesNotMatch(view, /Install update/);
  assert.match(view, /haui-firmware-status-warning/);
  assert.match(view, /A display update is ready to install\./);
  assert.doesNotMatch(view, />idle</);
});

test('the Updates sidebar leads with one status', () => {
  const summary = (update) => {
    const { tone, title, detail } = updateSummary({ enabled: true, state: 'idle', ...update });
    return [tone, title, detail];
  };
  assert.deepEqual(summary({}), ['success', 'Up to date', undefined]);
  assert.deepEqual(
    summary({ firmware_update_available: true, firmware_update_version: '0.5.1' }),
    ['warning', 'Update available', 'Firmware 0.5.1 is ready to install.'],
  );
  assert.deepEqual(
    summary({ firmware_update_reason: 'Built for another display' }),
    ['neutral', 'No update available', 'Built for another display'],
  );
  // A running install outranks a failure, a failure an offer.
  assert.deepEqual(
    summary({ firmware_installing: true, firmware_install_error: 'timeout' }),
    ['busy', 'Installing the firmware…', undefined],
  );
  assert.deepEqual(
    summary({ state: 'error', last_error: 'upload failed', tft_update_available: true }),
    ['danger', 'Display update failed', 'upload failed'],
  );
  assert.deepEqual(
    summary({ firmware_install_error: 'timeout', firmware_update_available: true }),
    ['danger', 'Firmware update failed', 'timeout'],
  );
  assert.deepEqual(summary({ enabled: false }), ['neutral', 'Updates are disabled for this device.', undefined]);
  assert.deepEqual(summary({ state: undefined }), ['neutral', 'Update status unavailable', undefined]);
});

test('every display update state the hub reports reads as words', () => {
  assert.equal(updateStateLabel('checking'), 'Checking for a display update…');
  assert.equal(updateStateLabel('installing'), 'Installing the display update…');
  assert.equal(updateStateLabel('done'), 'Display update installed');
  assert.equal(updateStateLabel('error'), 'Display update failed');
});

test('the Updates sidebar requests a fresh update check and reports completion', async () => {
  const calls = [];
  const events = [];
  const view = element({
    api: { updates: { async check(entryId, device) { calls.push([entryId, device]); } } },
    _emit(name) { events.push(name); },
  });
  await view._checkForUpdates();
  assert.deepEqual(calls, [['entry1', 'kitchen']]);
  assert.deepEqual(events, ['update-check']);
  assert.equal(view._actionBusy, false);
});

test('the Updates sidebar shows update check errors', async () => {
  const view = element({
    api: { updates: { async check() { throw new Error('offline'); } } },
    _emit() { assert.fail('failed update checks must not report success'); },
  });
  await view._checkForUpdates();
    assert.equal(view._popoverError, 'offline');
});

const HUB_POLICY = {
  firmware_auto_update: true, auto_install: true, install_delay: 600, max_attempts: 3, retry_interval: 3600,
};

test('a device that follows the hub shows the hub policy and an override switch', () => {
  const view = flatten(element({ config: { update: { enabled: true } }, hubPolicy: HUB_POLICY }).render());

  assert.match(view, /Follows the hub policy/);
  assert.match(view, /Firmware: automatic, after 10 minutes/);
  assert.match(view, /Override the hub policy/);
  assert.doesNotMatch(view, /update-firmware-auto/);
});

test('a device that overrides the hub edits its own policy', () => {
  const config = { update: { enabled: true, policy_override: true, max_attempts: 2 } };
  const view = flatten(element({ config, hubPolicy: HUB_POLICY }).render());

  assert.doesNotMatch(view, /Follows the hub policy/);
  assert.match(view, /update-firmware-auto/);
  assert.match(view, /update-tft-auto/);
  assert.match(view, /update-max-attempts/);
  assert.match(view, /update-install-delay/);
  assert.match(view, /update-retry-interval/);
});

test('the status card says when the next automatic attempt follows', () => {
  const status = {
    integration_version: '0.5.0',
    device_info: { tft_version: '1.2.3' },
    update: {
      enabled: true, state: 'idle',
      firmware_auto: { attempts: 1, max_attempts: 3, next_attempt_at: '2026-11-13T14:05:00+00:00', stopped_reason: null },
      tft_auto: { attempts: 0, max_attempts: 3, next_attempt_at: null, stopped_reason: null },
    },
  };

  assert.match(flatten(element({ deviceStatus: status }).render()), /Attempt 1 of 3 failed/);
});

test('the status card says when the automatic install stopped', () => {
  const status = {
    integration_version: '0.5.0',
    device_info: { tft_version: '1.2.3' },
    update: {
      enabled: true, state: 'idle',
      firmware_auto: { attempts: 0, max_attempts: 3, next_attempt_at: null, stopped_reason: null },
      tft_auto: { attempts: 3, max_attempts: 3, next_attempt_at: null, stopped_reason: 'Automatic install of 0.5.1 stopped after 3 failed attempts.' },
    },
  };

  assert.match(flatten(element({ deviceStatus: status }).render()), /stopped after 3 failed attempts/);
});


function scheduledStatus(update = {}) {
  return {
    integration_version: '0.5.0',
    device_info: { tft_version: '1.2.3', yaml_version: '0.5.0' },
    update: {
      enabled: true, state: 'idle',
      firmware_update_available: true, firmware_update_version: '0.5.1',
      firmware_scheduled: { version: '0.5.1', starts_at: new Date(Date.now() + 600000).toISOString() },
      ...update,
    },
  };
}

test('a scheduled firmware install can start now, wait or be skipped', () => {
  const sidebar = element({ deviceStatus: scheduledStatus() });
  const events = [];
  sidebar._emit = (name, detail) => events.push([name, detail]);
  const root = render(sidebar.render());
  const card = root.querySelector('.haui-update-scheduled');
  const click = (text) => [...card.querySelectorAll('button')].find((button) => button.textContent.includes(text)).click();

  assert.match(card.textContent, /0\.5\.1/);
  click('Install now');
  click('In 1 hour');
  click('In 1 day');
  click('Skip this version');
  assert.deepEqual(events, [
    ['update-control', { action: 'install_now' }],
    ['update-control', { action: 'defer', seconds: 3600 }],
    ['update-control', { action: 'defer', seconds: 86400 }],
    ['update-control', { action: 'skip' }],
  ]);
});

test('an install in progress shows its steps', () => {
  const status = scheduledStatus({
    firmware_scheduled: null,
    tft_progress: {
      phase: 'transferring', started_at: new Date().toISOString(),
      phase_started_at: new Date().toISOString(), expected_seconds: 900,
    },
  });

  const root = render(element({ deviceStatus: status }).render());

  assert.ok(root.querySelector('[role="progressbar"]'));
  assert.match(root.textContent, /Transferring/);
});

test('a skipped firmware version is marked', () => {
  const status = scheduledStatus({ firmware_scheduled: null, firmware_skipped_version: '0.5.1' });

  assert.match(flatten(element({ deviceStatus: status }).render()), /Skipped/);
});
