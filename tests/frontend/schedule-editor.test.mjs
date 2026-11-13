import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { renderDeviceView, previewControls } from '../../custom_components/nspanel_haui/frontend/views/device.js';
import { deviceDetails } from '../../custom_components/nspanel_haui/frontend/ui/device-details.js';
import { panelActions, panelManager, deviceOptionPanel } from '../../custom_components/nspanel_haui/frontend/ui/panel-manager.js';
import { idlePanelConfig, idlePanelKeys } from '../../custom_components/nspanel_haui/frontend/ui/panel-pills.js';
import { deviceActions } from '../../custom_components/nspanel_haui/frontend/ui/device-actions.js';
import { panelCatalog } from '../../custom_components/nspanel_haui/frontend/views/panel-catalog.js';
import { previewStage } from '../../custom_components/nspanel_haui/frontend/ui/preview-stage.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';

function templateText(template) {
  return `${template?.strings?.join(' ') || ''} ${template?.values?.map((value) => {
    if (Array.isArray(value)) return value.map((entry) => entry?.strings ? templateText(entry) : String(entry ?? '')).join(' ');
    return value?.strings ? templateText(value) : String(value ?? '');
  }).join(' ') || ''}`;
}

function templatesMatching(template, marker, found = []) {
  if (!template?.strings) return found;
  if (template.strings.join('').includes(marker)) found.push(template);
  for (const value of template.values) {
    if (Array.isArray(value)) value.forEach((entry) => templatesMatching(entry, marker, found));
    else templatesMatching(value, marker, found);
  }
  return found;
}

/** The `placeholder=` value bound to the input with `id`. */
function placeholderFor(template, id) {
  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const index = template.strings.findIndex((part) => part.includes('placeholder='));
  if (idBound && index >= 0) return template.values[index];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = placeholderFor(entry, id);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

function eventBinding(template, id, eventName) {  if (!template?.strings) return undefined;
  const idBound = template.values.includes(id) || template.strings.some((part) => part.includes(`id="${id}"`));
  const eventIndex = template.strings.findIndex((part) => part.trimEnd().endsWith(`${eventName}=`));
  if (idBound && eventIndex >= 0) return template.values[eventIndex];
  for (const value of template.values) {
    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      const found = eventBinding(entry, id, eventName);
      if (found !== undefined) return found;
    }
  }
  return undefined;
}

function previewModel(extra = {}) {
  return {
    mode: 'simulated', idle: false, showEntities: false,
    ready: true, canInteract: true, ...extra,
  };
}

function deviceView(preview, callbacks = {}) {
  return renderDeviceView({
    devices: [{ name: 'kitchen', device: { friendlyName: 'Kitchen' }, status: { connected: true } }],
    selectedName: 'kitchen', panelCount: 2, panelView: 'preview',
    workspace: html`<p>Stage</p>`, sideContent: html`<p>Details</p>`,
    preview,
    onSelectDevice() {}, onSwitchView() {},
    ...callbacks,
  });
}

/** First template that renders a control carrying `marker` and `label`. */
/** First template that renders a control carrying `marker` and `label`. */
function controlWith(view, marker, label) {
  return templatesMatching(view, marker).find((entry) => templateText(entry).includes(label));
}

const click = (control) => control.values.find((value) => typeof value === 'function')();

function controls(preview, callbacks = {}) {
  return previewControls({
    preview,
    onMode: () => {},
    onIdle: () => {},
    ...callbacks,
  });
}

test('the Schedule button shows its entry count without opening the editor', () => {
  const folded = templateText(panelManager({
    panels: [], config: {
      brightness: 80,
      schedule: [
        { start: 'sunset', start_offset: -30, end: '22:00', sound: true, brightness: 40, display_off: false },
        { start: '22:00', end: 'sunrise', sound: false, brightness: 5, display_off: true, timeout_display_off: 30 },
      ],
    },
  }));
  assert.match(folded, /2 entries/);
  assert.doesNotMatch(folded, /panel-schedule_0_start_time/, 'the entries stay folded');

  const empty = templateText(panelManager({
    panels: [], config: { brightness: null, schedule: [] },
  }));
  assert.match(empty, /Nothing scheduled: the device settings apply all day\./);
  assert.doesNotMatch(empty, /entries</);
});

test('the Schedule sidebar edits a draft and saves it explicitly', () => {
  const edits = [];
  const saves = [];
  const config = {
    brightness: 80,
    schedule: [{
      start: '22:00', end: '07:00', sound: true, brightness: 20,
      display_off: true, timeout_display_off: 30,
    }],
  };
  const view = deviceOptionPanel('schedule', {
    panels: [], config, scheduleDraft: { ...config, device: 'kitchen' }, onScheduleChange: (draft) => edits.push(draft),
    onScheduleSave: () => saves.push(true),
  });
  const text = templateText(view);
  assert.match(text, /Set display behavior by time of day/);
  assert.ok(text.indexOf('Set display behavior by time of day') < text.indexOf('panel-schedule-base-brightness'));
  assert.doesNotMatch(text, /YAML configuration/);
  assert.match(text, /panel-schedule-base-brightness/);
  assert.match(text, /panel-schedule_0_start_time/);

  const onInput = eventBinding(view, 'panel-schedule_0_start_time', '@input');
  onInput({ target: { value: '21:30' } });
  assert.equal(edits.at(-1).schedule[0].start, '21:30');
  assert.equal(edits.at(-1).brightness, 80);

  const save = controlWith(view, '<button', 'Save');
  click(save);
  assert.deepEqual(saves, [true]);
});

test('the schedule outside-brightness comes from the panel when the hub sets none', () => {
  const edits = [];
  const view = deviceOptionPanel('schedule', {
    panels: [],
    config: { brightness: null, brightness_dim: null, schedule: [] },
    deviceBrightness: { full: 62, dimmed: 15 },
    onScheduleChange: (draft) => edits.push(draft),
  });

  // The empty fields name the brightness the panel itself uses.
  assert.equal(placeholderFor(view, 'panel-schedule-base-brightness'), 'Panel: 62');
  assert.equal(placeholderFor(view, 'panel-schedule-base-brightness_dim'), 'Panel: 15');

  // A new entry takes the panel's full brightness, not an invented 100.
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(edits[0].brightness, 62);

  // A hub setting wins over the panel reading.
  eventBinding(deviceOptionPanel('schedule', {
    panels: [], config: { brightness: 40, schedule: [] }, deviceBrightness: { full: 62 }, onScheduleChange: (draft) => edits.push(draft),
  }), 'panel-schedule_add', '@click')();
  assert.equal(edits.at(-1).brightness, 40);
});

test('an entry inherit hint names the panel brightness when the hub sets none', () => {
  const view = deviceOptionPanel('schedule', {
    panels: [],
    config: {
      brightness: null,
      brightness_dim: null,
      timeout_dimming: 10,
      schedule: [{ start: '22:00', end: '07:00', sound: true, display_off: true, timeout_display_off: 30 }],
    },
    deviceBrightness: { full: 62, dimmed: 15 },
  });

  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness'), 'Inherit (62)');
  assert.equal(placeholderFor(view, 'panel-schedule_0_brightness_dim'), 'Inherit (15)');
});

test('adding the first inline Schedule entry sets the required outside brightness', () => {
  const edits = [];
  const view = deviceOptionPanel('schedule', {
    panels: [], config: { brightness: null, schedule: [] },
    onScheduleChange: (draft) => edits.push(draft),
  });
  eventBinding(view, 'panel-schedule_add', '@click')();
  assert.equal(edits[0].brightness, 100);  assert.deepEqual(edits[0].schedule, [{
    start: '22:00', start_offset: 0, end: '07:00', end_offset: 0,
    sound: true, brightness: 20, brightness_dim: null, display_off: true,
    timeout_dimming: null, timeout_display_off: 30, duration_dimming: null,
  }]);
});
