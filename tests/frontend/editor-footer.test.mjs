import { test } from 'node:test';
import assert from 'node:assert/strict';

await import('./dom-shim.mjs');
const { docsUrl, getEditorVersion, isPrereleaseVersion } = await import(
  '../../custom_components/nspanel_haui/frontend/toolbar.js'
);

test('frontend asset version is read from the registered frontend URL', () => {
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

test('PEP 440 prerelease versions are identified as development builds', () => {
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

test('documentation links prereleases to the dev docs and releases to stable docs', () => {
  assert.equal(docsUrl('0.4.5.dev31'), 'https://happydasch.github.io/nspanel_haui/dev/');
  assert.equal(docsUrl('1.0.0rc1'), 'https://happydasch.github.io/nspanel_haui/dev/');
  assert.equal(docsUrl('0.4.5'), 'https://happydasch.github.io/nspanel_haui/');
  assert.equal(docsUrl(null), 'https://happydasch.github.io/nspanel_haui/');
});

const { renderFooter } = await import('../../custom_components/nspanel_haui/frontend/toolbar.js');

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  if (Array.isArray(value.strings) && Array.isArray(value.values)) {
    return value.strings.map((part, index) => `${part}${flatten(value.values[index] ?? '')}`).join('');
  }
  return '';
}

test('persistent editor footer retains project links when no asset version is available', () => {
  const output = flatten(renderFooter({}));
  assert.match(output, /editor-footer/);
  assert.match(output, /GitHub/);
  assert.match(output, /Documentation/);
  assert.doesNotMatch(output, /footer-version-group/);
});
