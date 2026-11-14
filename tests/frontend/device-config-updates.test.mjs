import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { DEFAULT_FIRMWARE_MANIFEST_URL, DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';

/** A dialog instance without Lit's constructor (which needs a real DOM). */
function dialog(fields) {
  // The view always gets a complete config; a test names only the fields it is about.
  const form = { gestures: DEVICE_CONFIG_DEFAULTS.gestures, ...fields };
  const dlg = document.createElement('nspanel-device-settings');
  Object.assign(dlg, { requestUpdate() {}, config: form, _deviceConfigForm: form, devicePanels: [], systemPanels: [], hass: null });
  return dlg;
}

/** An Updates sidebar with an isolated update-settings draft. */
function updatesSidebar(fields) {
  const update = { ...(fields.update || {}) };
  const UpdatesSidebar = customElements.get('nspanel-updates-sidebar');
  return Object.assign(document.createElement('nspanel-updates-sidebar'), {
    open: true,
    deviceName: 'kitchen',
    entryId: 'entry1',
    config: { update },
    deviceStatus: {
      integration_version: '0.5.0',
      device_info: { tft_version: '1.2.3', tft_required_version: '1.2.3' },
      update: { enabled: true, state: 'idle' },
    },
    _settingsInitial: { ...update },
    _settingsDraft: { ...update },
    _settingsDevice: 'kitchen',
    _events: [],
    _emit(name, detail) { this._events.push([name, detail]); },
    _picker: null,
    requestUpdate() {},
    ...fields,
  });
}

/** The click handlers of the rendered segmented control, in DOM order. */
function segmentedHandlers(dlg) {
  const handlers = [];
  const walk = (value) => {
    if (Array.isArray(value)) { value.forEach(walk); return; }
    if (!value?.strings) return;
    const isOption = value.strings.some((part) => part.trimEnd().endsWith('@click=')) &&
      value.values.some((item) => typeof item === 'string' && item.startsWith('haui-segmented-option'));
    if (isOption) {
      handlers.push(value.values[value.strings.findIndex((part) => part.trimEnd().endsWith('@click='))]);
      return;
    }
    value.values.forEach(walk);
  };
  walk(dlg.render());
  return handlers;
}

/** The placeholder, value and @input handler bound to the input with ``id``. */
function field(dlg, id) {
  const findBinding = (tpl, marker) => {
    for (let i = 0; i < tpl.strings.length; i++) {
      const idMatch = tpl.strings[i].includes(`id="${id}"`) ||
        (tpl.strings[i].includes("id=") && tpl.values[i] === id);
      if (!idMatch) continue;
      for (let j = i; j < tpl.strings.length; j++) {
        if (tpl.strings[j].trimEnd().endsWith(marker)) return tpl.values[j];
      }
    }
    // A list (schedule entries) is an array of templates.
    for (const value of tpl.values.flat()) {
      if (value?.strings && value?.values) {
        const result = findBinding(value, marker);
        if (result !== undefined) return result;
      }
    }
    return undefined;
  };
  const tpl = dlg.render();
  return {
    placeholder: findBinding(tpl, 'placeholder='),
    value: findBinding(tpl, '.value='),
    onInput: findBinding(tpl, '@input='),
  };
}

function eventHandler(dlg, id, eventName) {
  const findBinding = (tpl) => {
    for (let i = 0; i < tpl.strings.length; i++) {
      const idMatch = tpl.strings[i].includes(`id="${id}"`) ||
        (tpl.strings[i].includes("id=") && tpl.values[i] === id);
      if (!idMatch) continue;
      for (let j = i; j < tpl.strings.length; j++) {
        if (tpl.strings[j].trimEnd().endsWith(`${eventName}=`)) return tpl.values[j];
      }
    }
    // A list (schedule entries) is an array of templates.
    for (const value of tpl.values.flat()) {
      if (value?.strings && value?.values) {
        const result = findBinding(value);
        if (result !== undefined) return result;
      }
    }
    return undefined;
  };
  return findBinding(dlg.render());
}

function includesTemplateContent(value, content) {
  if (typeof value === 'string') return value.includes(content);
  if (Array.isArray(value)) return value.some((item) => includesTemplateContent(item, content));
  if (!value?.strings) return false;
  return value.strings.some((part) => part.includes(content)) ||
    value.values.some((item) => includesTemplateContent(item, content));
}

function findTemplateWithClass(value, className) {
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findTemplateWithClass(item, className);
      if (found) return found;
    }
    return null;
  }
  if (!value?.strings) return null;
  if (value.strings.some((part) => part.includes(className))) return value;
  for (const item of value.values) {
    const found = findTemplateWithClass(item, className);
    if (found) return found;
  }
  return null;
}

function templateText(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(templateText).join('');
  if (!value?.strings) return '';
  return value.strings.reduce((text, part, index) =>
    `${text}${part}${templateText(value.values[index])}`, '');
}

test('the firmware manifest URL is stored only while it overrides the default', () => {
  const dlg = updatesSidebar({ update: { firmware_auto_update: true } });
  const url = 'http://homeassistant.local:8123/local/nspanel/firmware-manifest.json';

  const empty = field(dlg, 'update-firmware-manifest-url');
  assert.equal(empty.placeholder, DEFAULT_FIRMWARE_MANIFEST_URL);
  assert.equal(empty.value, '');

  empty.onInput({ target: { value: ` ${url} ` } });
  assert.deepEqual(dlg._settingsDraft, { firmware_auto_update: true, firmware_manifest_url: url });
  assert.equal(field(dlg, 'update-firmware-manifest-url').value, url);

  field(dlg, 'update-firmware-manifest-url').onInput({ target: { value: '' } });
  const saved = JSON.parse(JSON.stringify(dlg._settingsDraft));
  assert.deepEqual(saved, { firmware_auto_update: true }, 'an empty field falls back to the default');
});

test('the master update toggle hides subordinate settings and preserves them', () => {
  const dlg = updatesSidebar({ update: { enabled: false, check_on_connect: false, update_interval: 7200 } });

  assert.equal(includesTemplateContent(dlg.render(), 'Enable updates'), true);
  assert.equal(field(dlg, 'update-enabled').value, undefined);
  assert.equal(includesTemplateContent(dlg.render(), 'Check for updates on connect'), false);

  eventHandler(dlg, 'update-enabled', '@change')({ target: { checked: true } });
  assert.equal(dlg._settingsDraft.enabled, true);
  assert.equal(dlg._settingsDraft.check_on_connect, false);
  assert.equal(dlg._settingsDraft.update_interval, 7200);
  assert.equal(includesTemplateContent(dlg.render(), 'Check for updates on connect'), true);

  eventHandler(dlg, 'update-enabled', '@change')({ target: { checked: false } });
  assert.equal(dlg._settingsDraft.enabled, false);
  assert.equal(dlg._settingsDraft.update_interval, 7200);
});

test('the firmware update channel selects the dev manifest and stores the channel', () => {
  const dlg = updatesSidebar({ update: { firmware_auto_update: true } });

  // The URL placeholder follows the channel; the segmented control stores it.
  assert.equal(field(dlg, 'update-firmware-manifest-url').placeholder, DEFAULT_FIRMWARE_MANIFEST_URL);

  const options = segmentedHandlers(dlg);
  options[1]();
  assert.equal(dlg._settingsDraft.firmware_update_channel, 'dev');
  // The dev channel has no fixed manifest URL to show.
  assert.equal(field(dlg, 'update-firmware-manifest-url').placeholder, '');
  // The URL stays empty: the channel decides, the store holds no URL.
  assert.equal(dlg._settingsDraft.firmware_manifest_url, undefined);

  segmentedHandlers(dlg)[0]();
  assert.equal(dlg._settingsDraft.firmware_update_channel, 'stable');
  assert.equal(field(dlg, 'update-firmware-manifest-url').placeholder, DEFAULT_FIRMWARE_MANIFEST_URL);
});

test('a status poll keeps unsaved update settings until a save lands', () => {
  const sidebar = updatesSidebar({ update: { enabled: true } });
  eventHandler(sidebar, 'update-enabled', '@change')({ target: { checked: false } });

  // The editor re-renders on every poll with a fresh config object.
  sidebar.willUpdate(new Set(['config', 'deviceStatus']));
  assert.equal(sidebar._settingsDraft.enabled, false);
  assert.equal(sidebar._settingsChanged(), true);

  // A save that landed brings the stored settings, which become the new baseline.
  sidebar.config = { update: { enabled: false } };
  sidebar.willUpdate(new Set(['config']));
  assert.deepEqual(sidebar._settingsDraft, { enabled: false });
  assert.equal(sidebar._settingsChanged(), false);
});

test('the Updates sidebar applies settings automatically and has no save footer', () => {
  const sidebar = updatesSidebar({ update: { enabled: true, check_on_connect: true } });

  eventHandler(sidebar, 'update-enabled', '@change')({ target: { checked: false } });

  assert.deepEqual(sidebar._events, [
    ['save-update-settings', { update: { enabled: false, check_on_connect: true } }],
  ]);
  assert.equal(includesTemplateContent(sidebar.render(), 'Discard'), false);
  assert.equal(includesTemplateContent(sidebar.render(), 'Save'), false);
});

test('update preferences live in the Updates sidebar instead of Device settings', () => {
  assert.equal(includesTemplateContent(dialog({}).render(), 'Enable updates'), false);
  const sidebar = updatesSidebar({ update: { enabled: true } });
  assert.equal(includesTemplateContent(sidebar.render(), 'Update settings'), true);
  assert.equal(includesTemplateContent(sidebar.render(), 'Update channel'), true);
});

test('update preferences remain available without a device status snapshot', () => {
  const sidebar = updatesSidebar({ update: { enabled: true }, deviceStatus: null });
  assert.equal(includesTemplateContent(sidebar.render(), 'Update settings'), true);
});

test('update settings auto-save after the user finishes typing', async () => {
  const sidebar = updatesSidebar({ update: { enabled: true } });
  const first = field(sidebar, 'update-firmware-manifest-url');
  first.onInput({ target: { value: 'http://ha.local/first.json' } });
  field(sidebar, 'update-firmware-manifest-url').onInput({ target: { value: 'http://ha.local/final.json' } });

  assert.deepEqual(sidebar._events, []);
  await new Promise((resolve) => setTimeout(resolve, 350));

  assert.deepEqual(sidebar._events, [[
    'save-update-settings',
    { update: { enabled: true, firmware_manifest_url: 'http://ha.local/final.json' } },
  ]]);
});
test('automatic update settings saves serialize and keep the latest change', async () => {
  const { NSPanelEditor } = await import('../../custom_components/nspanel_haui/frontend/app/shell.js');
  const saves = [];
  let currentConfig = { update: { enabled: true } };
  let finishFirstSave;
  let busy = false;
  const store = {
    getState: () => ({ hub: { saving: busy } }),
    selectors: {
      configFor: () => currentConfig,
      devicePanels: () => [],
    },
    actions: {
      async saveDeviceConfig(payload) {
        saves.push(payload.deviceConfig.update);
        busy = true;
        if (saves.length === 1) await new Promise((resolve) => { finishFirstSave = resolve; });
        currentConfig = payload.deviceConfig;
        busy = false;
        return true;
      },
      closeOverlay() {},
    },
  };
  const editor = Object.assign(document.createElement('nspanel-haui-editor'), {
    _selectedDevice: 'kitchen',
    _store: store,
    store,
    entryId: 'entry1',
  });

  const firstSave = editor._saveUpdateSettings({ detail: { update: { enabled: false } } });
  editor._saveUpdateSettings({ detail: { update: { enabled: false, auto_install: true } } });
  finishFirstSave();
  await firstSave;

  assert.deepEqual(saves, [
    { enabled: false },
    { enabled: false, auto_install: true },
  ]);
});


test('an emptied brightness is saved as unset', () => {
  const dlg = dialog({ brightness: 80, schedule: [] });

  field(dlg, 'dc-brightness').onInput({ target: { value: '' } });

  assert.equal(dlg._deviceConfigForm.brightness, null);
});
