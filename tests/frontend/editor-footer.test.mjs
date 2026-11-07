import { test } from 'node:test';
import assert from 'node:assert/strict';

await import('./dom-shim.mjs');
const { getEditorVersion, isPrereleaseVersion } = await import(
  '../../custom_components/nspanel_haui/frontend/toolbar.js'
);

test('editor footer version is read from the registered frontend asset URL', () => {
  assert.equal(
    getEditorVersion('http://homeassistant.local/nspanel_haui_frontend/0.4.5.dev31-0123456789ab/toolbar.js'),
    '0.4.5.dev31',
  );
  assert.equal(
    getEditorVersion('http://homeassistant.local/nspanel_haui_frontend/0.4.5-0123456789ab/toolbar.js'),
    '0.4.5',
  );
  assert.equal(getEditorVersion('http://homeassistant.local/frontend/toolbar.js'), null);
});

test('editor footer marks PEP 440 prerelease versions as development builds', () => {
  for (const version of [
    '0.4.5.dev31',
    '1.0.0a1',
    '1.0.0alpha1',
    '1.0.0b2',
    '1.0.0c1',
    '1.0.0preview1',
    '1.0.0rc1',
  ]) {
    assert.equal(isPrereleaseVersion(version), true, version);
  }
  for (const version of ['0.4.5', '0.4.5.post1', '0.4.5+local', '0.4.5+local.dev1']) {
    assert.equal(isPrereleaseVersion(version), false, version);
  }
});
