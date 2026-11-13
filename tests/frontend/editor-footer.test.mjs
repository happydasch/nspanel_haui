import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { render } from './support/render.mjs';
import { byRole } from './support/queries.mjs';
import {
  docsUrl,
  getIntegrationVersion,
  isPrereleaseVersion,
  renderFooter,
} from '../../custom_components/nspanel_haui/frontend/toolbar.js';

test('frontend asset version is read from the registered frontend URL', () => {
  assert.equal(
    getIntegrationVersion('http://homeassistant.local/nspanel_haui_frontend/0.4.5.dev31-0123456789ab/toolbar.js'),
    '0.4.5.dev31',
  );
  assert.equal(
    getIntegrationVersion('http://homeassistant.local/nspanel_haui_frontend/0.4.5-0123456789ab/toolbar.js'),
    '0.4.5',
  );
  assert.equal(getIntegrationVersion('http://homeassistant.local/frontend/toolbar.js'), null);
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

test('the persistent footer keeps its external links when no version is available', () => {
  const root = render(renderFooter({}, null));
  const github = byRole(root, 'link', { name: 'GitHub' });
  const documentation = byRole(root, 'link', { name: 'Documentation' });

  assert.ok(github);
  assert.ok(documentation);
  assert.equal(github.href, 'https://github.com/happydasch/nspanel_haui');
  assert.equal(documentation.href, 'https://happydasch.github.io/nspanel_haui/');
  assert.equal(root.querySelectorAll('[title="Integration version"]').length, 0);
});

test('the footer shows version data and points prereleases at the development docs', () => {
  const root = render(renderFooter({}, '0.5.0.dev16'));
  const documentation = byRole(root, 'link', { name: 'Documentation' });

  assert.equal(root.querySelector('[title="Integration version"]')?.textContent, 'v0.5.0.dev16');
  assert.ok(root.querySelector('[title="Development prerelease"]'));
  assert.equal(documentation.href, 'https://happydasch.github.io/nspanel_haui/dev/');
});
