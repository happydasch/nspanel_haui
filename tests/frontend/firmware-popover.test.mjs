import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { updateStateLabel, updateSummary } from'../../custom_components/nspanel_haui/frontend/dialogs/firmware.js';

function element(props = {}) {
  const FirmwarePopover = customElements.get('nspanel-firmware-popover');
  return Object.assign(Object.create(FirmwarePopover.prototype), {
    open: true,
    deviceName: 'kitchen',
    entryId: 'entry1',
    deviceStatus: {
      haui_version: '0.5.0',
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
