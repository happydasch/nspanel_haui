import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  DATE_FORMAT_OPTIONS,
  DEVICE_CONFIG_DEFAULTS,
  DISPLAY_MODEL_OPTIONS,
  LOG_LEVEL_OPTIONS,
  TIME_FORMAT_OPTIONS,
} from '../../custom_components/nspanel_haui/frontend/constants.js';

test('the display model dropdown offers the two effective layouts', () => {
  // A US panel mounted landscape is functionally the default landscape layout
  // and is no longer offered separately (see frontend/constants.js).
  assert.deepEqual(
    DISPLAY_MODEL_OPTIONS.map((o) => o.value),
    ['eu', 'us'],
  );
  // The portrait US model maps to the portrait TFT.
  assert.ok(DISPLAY_MODEL_OPTIONS.some((o) => o.value === 'us'));
});

test('time and date format presets include US 12-hour and US date forms', () => {
  assert.ok(
    TIME_FORMAT_OPTIONS.some((o) => o.value === '%I:%M %p'),
    'US 12-hour AM/PM preset',
  );
  assert.ok(TIME_FORMAT_OPTIONS.some((o) => o.value === '%H:%M'));
  assert.ok(DATE_FORMAT_OPTIONS.some((o) => o.value === '%m/%d/%Y'), 'US numeric date');
  assert.ok(DATE_FORMAT_OPTIONS.some((o) => o.value === '%B %d, %Y'), 'US long date');
  // Empty value = inherit hub default
  assert.equal(TIME_FORMAT_OPTIONS[0].value, '');
  assert.equal(DATE_FORMAT_OPTIONS[0].value, '');
});

test('device config defaults carry the new keys', () => {
  assert.equal(DEVICE_CONFIG_DEFAULTS.display_model, 'eu');
  assert.equal(DEVICE_CONFIG_DEFAULTS.time_format, '');
  assert.equal(DEVICE_CONFIG_DEFAULTS.date_format, '');
  assert.equal(DEVICE_CONFIG_DEFAULTS.idle_panel_extra, '');
  assert.equal(DEVICE_CONFIG_DEFAULTS.stale_data_seconds, 0);
  assert.equal(DEVICE_CONFIG_DEFAULTS.log_level, 'INFO');
  assert.deepEqual(
    LOG_LEVEL_OPTIONS.map((o) => o.value),
    ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
  );
  assert.equal(DEVICE_CONFIG_DEFAULTS.use_sleep_schedule, false);
  assert.equal(DEVICE_CONFIG_DEFAULTS.sleep_schedule_start, '');
  assert.equal(DEVICE_CONFIG_DEFAULTS.sleep_schedule_end, '');
});
