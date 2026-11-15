import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { updateStateLabel, updateSummary } from'../../custom_components/nspanel_haui/frontend/dialogs/updates.js';
import { render } from './support/render.mjs';

function element(props = {}) {
  const UpdatesSidebar = customElements.get('nspanel-updates-sidebar');
  return Object.assign(document.createElement('nspanel-updates-sidebar'), {
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

test('the Updates sidebar combines update status and installed versions in one compact card', () => {
  const view = flatten(element().render());
  const root = render(element().render());
  const overview = root.querySelector('.haui-update-overview');
  assert.match(view, /haui-update-sidebar/);
  assert.ok(overview);
  assert.ok(overview.querySelector('.haui-update-summary'));
  assert.ok(overview.querySelector('.haui-update-versions'));
  assert.equal(root.querySelectorAll('.haui-update-overview').length, 1);
  // The sidebar frame carries the title and the close control.
  assert.doesNotMatch(view, /haui-popover|mdi:close/);
  assert.match(view, /0\.5\.0/);
  assert.match(view, /1\.2\.3/);
  assert.match(view, /1\.2\.4/);
  assert.match(view, /Check for updates/);
  assert.equal((view.match(/>\s*Install\s*</g) || []).length, 2);
  assert.doesNotMatch(view, /Install update/);
  assert.match(view, /haui-update-status-warning/);
  assert.match(view, /A display update is ready to install\./);
  assert.doesNotMatch(view, />idle</);
});

test('the integration version ends the check row, also with updates off', () => {
  const versions = (props) => {
    const overview = render(element(props).render()).querySelector('.haui-update-overview');
    const checkRow = overview.querySelector('.haui-update-check-action');
    return {
      list: overview.querySelector('.haui-update-versions').textContent,
      checkRow: checkRow.textContent,
      checkButton: Boolean(checkRow.querySelector('ha-button')),
    };
  };
  const on = versions();
  assert.doesNotMatch(on.list, /Integration|0\.5\.0/);
  assert.match(on.checkRow, /Check for updates[\s\S]*Integration\s*0\.5\.0/);
  const off = versions({
    deviceStatus: { integration_version: '0.5.0', device_info: {}, update: { enabled: false } },
  });
  assert.equal(off.checkButton, false);
  assert.match(off.checkRow, /Integration\s*0\.5\.0/);
});

test('an offered update shows as the version, with the version it updates to', () => {
  const firmwareRow = (update) => {
    const root = render(element({
      deviceStatus: {
        integration_version: '0.5.0',
        device_info: { yaml_version: '0.5.0', tft_version: '1.2.3' },
        update: { enabled: true, state: 'idle', firmware_update_version: '0.5.1', ...update },
      },
    }).render());
    const row = root.querySelector('.haui-update-versions .haui-update-version');
    return { text: row.textContent, badges: [...row.querySelectorAll('.haui-badge')].map((b) => b.textContent) };
  };
  const offered = firmwareRow({ firmware_update_available: true });
  assert.deepEqual(offered.badges.map((text) => text.replace(/\s+/g, '')), ['0.5.0→0.5.1']);
  assert.doesNotMatch(offered.text, /Update available|Latest release/);
  const current = firmwareRow({ firmware_update_available: false });
  assert.deepEqual(current.badges, []);
  assert.match(current.text, /Latest release: 0\.5\.1[\s\S]*0\.5\.0/);
});

test('the actions keep their full names where a narrow card shortens their labels', () => {
  const overview = render(element().render()).querySelector('.haui-update-overview');
  const checkRow = overview.querySelector('.haui-update-check-action');
  assert.equal(checkRow.querySelector('ha-button').getAttribute('aria-label'), 'Check for updates');
  assert.equal(checkRow.querySelector('.haui-update-integration').getAttribute('title'), 'Integration');
  assert.deepEqual(
    [...overview.querySelectorAll('.haui-update-versions ha-button')].map((b) => b.getAttribute('aria-label')),
    ['Install Firmware (YAML)', 'Install Display (TFT)'],
  );
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
    assert.equal(view._checkError, 'offline');
});

function settingsSidebar(update) {
  const sidebar = element({ config: { update } });
  sidebar._saved = [];
  sidebar._emit = (name, detail) => sidebar._saved.push([name, detail]);
  sidebar.willUpdate(new Map([['config', undefined]]));
  return sidebar;
}

test('the master switch sits in the settings heading and hides the rest while off', () => {
  const on = render(settingsSidebar({ enabled: true }).render());
  const toggle = on.querySelector('#update-enabled');
  assert.ok(on.querySelector('.haui-update-header').contains(toggle));
  assert.equal(toggle.getAttribute('aria-label'), 'Enable updates');

  const off = render(settingsSidebar({ enabled: false }).render());
  assert.ok(off.querySelector('.haui-update-header #update-enabled'));
  assert.equal(off.querySelector('#update-channel'), null);
  assert.match(off.querySelector('.haui-update-settings').textContent, /Updates are disabled for this device\./);
});

test('the settings lead with the three decisions and fold the rest away', () => {
  const root = render(settingsSidebar({ enabled: true }).render());
  const advanced = root.querySelector('details.haui-update-advanced');

  assert.equal(advanced.open, false);
  for (const id of ['update-enabled', 'update-channel', 'update-firmware-auto', 'update-interval']) {
    const control = root.querySelector(`#${id}`);
    assert.ok(control, `${id} is shown`);
    assert.equal(advanced.contains(control), false, `${id} is a main setting`);
  }
  // Where versions come from and how often to look, then whether a find installs by itself.
  assert.deepEqual(
    [...root.querySelectorAll('#update-firmware-auto, #update-channel, #update-interval')].map((c) => c.id),
    ['update-channel', 'update-interval', 'update-firmware-auto'],
  );
  for (const id of ['update-firmware-manifest-url', 'update-check-on-connect', 'update-tft-auto',
    'update-max-attempts', 'update-retry-interval']) {
    assert.ok(advanced.querySelector(`#${id}`), `${id} is an advanced setting`);
  }
});

test('a new version waits for the user or installs automatically', () => {
  const sidebar = settingsSidebar({ enabled: true });
  const root = render(sidebar.render());

  const automatic = root.querySelector('#update-firmware-auto');
  assert.equal(automatic.checked, false);
  assert.equal(root.querySelector('#update-install-delay'), null, 'no wait while nothing installs by itself');
  automatic.checked = true;
  automatic.dispatchEvent(new Event('change', { bubbles: true }));

  assert.deepEqual(sidebar._saved, [['save-update-settings', { update: { enabled: true, firmware_auto_update: true } }]]);
  assert.equal(render(sidebar.render()).querySelector('#update-install-delay option[selected]').value, '600');
});

test('the check interval is one list that can also turn checks off', () => {
  const sidebar = settingsSidebar({ enabled: true, update_interval: 5400 });
  const select = render(sidebar.render()).querySelector('#update-interval');

  assert.equal(select.querySelector('option[selected]').value, '5400', 'a stored odd interval stays selectable');
  select.value = '0';
  select.dispatchEvent(new Event('change', { bubbles: true }));

  assert.equal(sidebar._saved.at(-1)[1].update.update_interval, 0);
  assert.equal(render(sidebar.render()).querySelector('#update-interval option[selected]').textContent.trim(), 'Never');
});

test('a manifest URL opens Advanced, where it overrides the channel', () => {
  const root = render(settingsSidebar({ enabled: true, firmware_manifest_url: 'http://ha.local/m.json' }).render());

  assert.equal(root.querySelector('details.haui-update-advanced').open, true);
  assert.equal(root.querySelector('#update-firmware-manifest-url').value, 'http://ha.local/m.json');
});

test('the retry settings show only while something installs by itself', () => {
  const byHand = render(settingsSidebar({ enabled: true, auto_install: false }).render());
  assert.equal(byHand.querySelector('#update-max-attempts'), null);
  assert.equal(byHand.querySelector('#update-retry-interval'), null);

  const sidebar = settingsSidebar({ enabled: true, max_attempts: 3 });
  const attempts = render(sidebar.render()).querySelector('#update-max-attempts');
  attempts.value = '5';
  attempts.dispatchEvent(new Event('input', { bubbles: true }));
  sidebar._saveSettings();

  assert.equal(sidebar._saved.at(-1)[1].update.max_attempts, 5);
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
