import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { DEFAULT_FIRMWARE_MANIFEST_URL } from '../../custom_components/nspanel_haui/frontend/constants.js';

/** A dialog instance without Lit's constructor (which needs a real DOM). */
function dialog(form) {
  const dlg = Object.create(customElements.get('nspanel-dialog-device-config').prototype);
  Object.assign(dlg, { requestUpdate() {}, config: form, _deviceConfigForm: form, devicePanels: [], hass: null });
  return dlg;
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
    for (const value of tpl.values) {
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
    for (const value of tpl.values) {
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

test('the firmware manifest URL is stored only while it overrides the default', () => {
  const dlg = dialog({ update: { firmware_auto_update: true } });
  const url = 'http://homeassistant.local:8123/local/nspanel/firmware-manifest.json';

  const empty = field(dlg, 'dc-update-firmware_manifest_url');
  assert.equal(empty.placeholder, DEFAULT_FIRMWARE_MANIFEST_URL);
  assert.equal(empty.value, '');

  empty.onInput({ target: { value: ` ${url} ` } });
  assert.deepEqual(dlg._deviceConfigForm.update, { firmware_auto_update: true, firmware_manifest_url: url });
  assert.equal(field(dlg, 'dc-update-firmware_manifest_url').value, url);

  field(dlg, 'dc-update-firmware_manifest_url').onInput({ target: { value: '' } });
  const saved = JSON.parse(JSON.stringify(dlg._deviceConfigForm.update));
  assert.deepEqual(saved, { firmware_auto_update: true }, 'an empty field falls back to the default');
});

test('the master update toggle hides subordinate settings and preserves them', () => {
  const dlg = dialog({ update: { enabled: false, check_on_connect: false, update_interval: 7200 } });

  assert.equal(includesTemplateContent(dlg.render(), 'Enable updates'), true);
  assert.equal(field(dlg, 'dc-update-enabled').value, undefined);
  assert.equal(includesTemplateContent(dlg.render(), 'Check for updates on connect'), false);

  eventHandler(dlg, 'dc-update-enabled', '@change')({ target: { checked: true } });
  assert.equal(dlg._deviceConfigForm.update.enabled, true);
  assert.equal(dlg._deviceConfigForm.update.check_on_connect, false);
  assert.equal(dlg._deviceConfigForm.update.update_interval, 7200);
  assert.equal(includesTemplateContent(dlg.render(), 'Check for updates on connect'), true);

  eventHandler(dlg, 'dc-update-enabled', '@change')({ target: { checked: false } });
  assert.equal(dlg._deviceConfigForm.update.enabled, false);
  assert.equal(dlg._deviceConfigForm.update.update_interval, 7200);
});

test('periodic update toggle maps disabled to zero and enables an interval', () => {
  const dlg = dialog({ update: { update_interval: 5400 } });

  eventHandler(dlg, 'dc-update-periodic-checks', '@change')({ target: { checked: false } });
  assert.equal(dlg._deviceConfigForm.update.update_interval, 0);
  assert.equal(field(dlg, 'dc-update-update_interval').value, undefined);
  const disabledRender = dlg.render();
  assert.equal(includesTemplateContent(disabledRender, 'Update check interval (seconds)'), true);
  assert.equal(includesTemplateContent(disabledRender, 'How often to check GitHub for a newer release.'), true);

  eventHandler(dlg, 'dc-update-periodic-checks', '@change')({ target: { checked: true } });
  assert.equal(dlg._deviceConfigForm.update.update_interval, 3600);

  field(dlg, 'dc-update-update_interval').onInput({ target: { value: '7200' } });
  assert.equal(dlg._deviceConfigForm.update.update_interval, 7200);
});

test('the firmware update channel selects the dev manifest and stores the channel', () => {
  const dlg = dialog({ update: { firmware_auto_update: true } });

  // The URL placeholder follows the channel; the select stores its value.
  assert.equal(field(dlg, 'dc-update-firmware_manifest_url').placeholder, DEFAULT_FIRMWARE_MANIFEST_URL);

  const findChange = (tpl, id) => {
    for (let i = 0; i < tpl.strings.length; i++) {
      const idMatch = tpl.strings[i].includes(`id="${id}"`) ||
        (tpl.strings[i].includes("id=") && tpl.values[i] === id);
      if (!idMatch) continue;
      for (let j = i; j < tpl.strings.length; j++) {
        if (tpl.strings[j].trimEnd().endsWith('@change=')) return tpl.values[j];
      }
    }
    for (const value of tpl.values) {
      if (value?.strings && value?.values) {
        const result = findChange(value, id);
        if (result !== undefined) return result;
      }
    }
    return undefined;
  };

  findChange(dlg.render(), 'dc-update-firmware_update_channel')({ target: { value: 'dev' } });
  assert.equal(dlg._deviceConfigForm.update.firmware_update_channel, 'dev');
  // The dev channel has no fixed manifest URL to show.
  assert.equal(field(dlg, 'dc-update-firmware_manifest_url').placeholder, '');
  // The URL stays empty: the channel decides, the store holds no URL.
  assert.equal(dlg._deviceConfigForm.update.firmware_manifest_url, undefined);
});

test('Day/Night profile fields keep schedule, brightness, timeouts and idle target in the saved form', () => {
  const dlg = dialog({
    day_night_schedule_mode: 'fixed',
    day_night_start: '21:00',
    day_night_end: '07:00',
    day_brightness_full: null,
    day_brightness_dimmed: null,
    day_duration_dim: null,
    night_use_auto_dimming: true,
    night_timeout_dimming: 10,
    night_duration_dim: 2,
    night_brightness_full: 50,
    night_brightness_dimmed: 20,
    night_use_auto_page: true,
    night_timeout_page: 30,
    night_idle_panel: '',
    night_use_auto_display_off: true,
    night_timeout_display_off: 120,
  });

  field(dlg, 'dc-day_night_start').onInput({ target: { value: '22:30' } });
  field(dlg, 'dc-day_night_end').onInput({ target: { value: '06:15' } });
  field(dlg, 'dc-day_brightness_full').onInput({ target: { value: '62' } });
  field(dlg, 'dc-day_brightness_dimmed').onInput({ target: { value: '14' } });
  field(dlg, 'dc-day_duration_dim').onInput({ target: { value: '1.5' } });
  field(dlg, 'dc-night_timeout_dimming').onInput({ target: { value: '25' } });
  field(dlg, 'dc-night_duration_dim').onInput({ target: { value: '0.8' } });
  field(dlg, 'dc-night_brightness_full').onInput({ target: { value: '18' } });
  field(dlg, 'dc-night_brightness_dimmed').onInput({ target: { value: '3' } });
  field(dlg, 'dc-night_timeout_page').onInput({ target: { value: '45' } });
  field(dlg, 'dc-night_timeout_display_off').onInput({ target: { value: '240' } });

  const eventHandler = (id, eventName) => {
    const findBinding = (tpl) => {
      for (let i = 0; i < tpl.strings.length; i++) {
        const idMatch = tpl.strings[i].includes(`id="${id}"`) ||
          (tpl.strings[i].includes("id=") && tpl.values[i] === id);
        if (idMatch) {
          for (let j = i; j < tpl.strings.length; j++) {
            if (tpl.strings[j].trimEnd().endsWith(`${eventName}=`)) return tpl.values[j];
          }
        }
      }
      for (const value of tpl.values) {
        if (value?.strings && value?.values) {
          const result = findBinding(value);
          if (result !== undefined) return result;
        }
      }
      return undefined;
    };
    return findBinding(dlg.render());
  };
  eventHandler('dc-night_idle_panel', '@change')({ target: { value: 'night_clock' } });
  eventHandler('dc-night_use_auto_dimming', '@change')({ target: { checked: false } });

  assert.deepEqual(
    Object.fromEntries(Object.entries(dlg._deviceConfigForm).filter(([key]) => key.startsWith('day_') || key.startsWith('night_'))),
    {
      day_night_schedule_mode: 'fixed',
      day_night_start: '22:30',
      day_night_end: '06:15',
      day_brightness_full: 62,
      day_brightness_dimmed: 14,
      day_duration_dim: 1.5,
      night_use_auto_dimming: false,
      night_timeout_dimming: 25,
      night_duration_dim: 0.8,
      night_brightness_full: 18,
      night_brightness_dimmed: 3,
      night_use_auto_page: true,
      night_timeout_page: 45,
      night_idle_panel: 'night_clock',
      night_use_auto_display_off: true,
      night_timeout_display_off: 240,
    },
  );
});

test('solar schedule offsets accept signed minute adjustments', () => {
  const dlg = dialog({
    day_night_schedule_mode: 'sun',
    day_night_sunset_offset: 0,
    day_night_sunrise_offset: 0,
  });

  field(dlg, 'dc-day_night_sunset_offset').onInput({ target: { value: '-35' } });
  field(dlg, 'dc-day_night_sunrise_offset').onInput({ target: { value: '20' } });

  assert.equal(dlg._deviceConfigForm.day_night_sunset_offset, -35);
  assert.equal(dlg._deviceConfigForm.day_night_sunrise_offset, 20);
});
