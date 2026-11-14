import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { DEVICE_CONFIG_DEFAULTS } from '../../custom_components/nspanel_haui/frontend/constants.js';
import { render } from './support/render.mjs';

/** A settings instance without Lit's update cycle, rendered on demand. */
function settings(props = {}) {
  const dlg = document.createElement('nspanel-device-settings');
  Object.assign(dlg, { requestUpdate() {}, dispatchEvent() { return true; } }, props);
  return dlg;
}

test('an empty brightness field names the brightness the panel uses', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, brightness: null, brightness_dim: null };
  const root = render(settings({
    config, _deviceConfigForm: config, deviceBrightness: { full: 62, dimmed: 15 },
  }).render());

  assert.equal(root.querySelector('#dc-brightness').placeholder, 'Panel: 62');
  assert.equal(root.querySelector('#dc-brightness_dim').placeholder, 'Panel: 15');
});

test('a brightness field without a panel reading has no placeholder', () => {
  const config = { ...DEVICE_CONFIG_DEFAULTS, brightness: 80, brightness_dim: null };
  const root = render(settings({ config, _deviceConfigForm: config }).render());

  assert.equal(root.querySelector('#dc-brightness').value, '80');
  assert.equal(root.querySelector('#dc-brightness_dim').placeholder, '');
});
