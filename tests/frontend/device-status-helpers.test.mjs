import { test } from 'node:test';
import assert from 'node:assert/strict';

import { deviceBrightness, deviceConnectionState, hasUpdateAvailable } from '../../custom_components/nspanel_haui/frontend/device-status.js';

test('update availability is true when either firmware or TFT is offered', () => {
  assert.equal(hasUpdateAvailable({ firmware_update_available: true }), true);
  assert.equal(hasUpdateAvailable({ tft_update_available: true }), true);
  assert.equal(hasUpdateAvailable({ firmware_update_available: false, tft_update_available: false }), false);
  assert.equal(hasUpdateAvailable(null), false);
});

test('connection state maps missing, disconnected and connected status consistently', () => {
  assert.deepEqual(deviceConnectionState(null), {
    connected: false,
    tone: 'unknown',
    label: 'Status unavailable',
  });
  assert.deepEqual(deviceConnectionState({ connected: false }), {
    connected: false,
    tone: 'offline',
    label: 'Disconnected',
  });
  assert.deepEqual(deviceConnectionState({ connected: true }), {
    connected: true,
    tone: 'online',
    label: 'Connected',
  });
});

test('the device brightness comes from the panel\'s own number entities', () => {
  const status = {
    device_info: {
      brightness_entity_id: 'number.panel_brightness_full',
      brightness_dim_entity_id: 'number.panel_brightness_dimmed',
    },
  };
  const hass = {
    states: {
      'number.panel_brightness_full': { state: '62' },
      'number.panel_brightness_dimmed': { state: '15' },
    },
  };

  assert.deepEqual(deviceBrightness(status, hass), { full: 62, dimmed: 15 });
});

test('an unreadable brightness entity is null, not an invented value', () => {
  const status = {
    device_info: {
      brightness_entity_id: 'number.panel_brightness_full',
      brightness_dim_entity_id: 'number.panel_brightness_dimmed',
    },
  };
  const hass = {
    states: {
      'number.panel_brightness_full': { state: 'unavailable' },
      'number.panel_brightness_dimmed': { state: 'unknown' },
    },
  };

  assert.deepEqual(deviceBrightness(status, hass), { full: null, dimmed: null });
  // No status yet (the editor still loading) and no ids at all.
  assert.deepEqual(deviceBrightness(null, null), { full: null, dimmed: null });
  assert.deepEqual(deviceBrightness({}, hass), { full: null, dimmed: null });
});
