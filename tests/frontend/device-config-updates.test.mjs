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
  const tpl = dlg.render();
  const start = tpl.strings.findIndex((s) => s.includes(`id="${id}"`));
  const binding = (name) => tpl.values[start + tpl.strings.slice(start).findIndex((s) => s.trimEnd().endsWith(name))];
  return { placeholder: binding('placeholder='), value: binding('.value='), onInput: binding('@input=') };
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
