// @ts-check
import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

/** An editor whose preview workspace and toasts are recorded. */
function editor() {
  const instance = document.createElement('nspanel-haui-editor');
  instance.toasts = [];
  instance.previewCalls = [];
  instance._showToast = (message, kind) => instance.toasts.push([message, kind]);
  instance._callPreviewWorkspace = (...args) => instance.previewCalls.push(args);
  return instance;
}

/** A device state whose panels are the given keys. */
function device(config, keys) {
  return { name: 'kitchen', config, panels: keys.map((key) => ({ key, type: 'grid', title: key })) };
}

test('the preview Idle control explains when no idle panel is configured', () => {
  const instance = editor();

  instance._onPreviewIdle(device({}, []), { idle: false });

  assert.deepEqual(instance.toasts, [['No idle panels are configured', 'error']]);
  assert.deepEqual(instance.previewCalls, []);
});

test('a configured idle panel the device no longer has does not count as one', () => {
  const instance = editor();

  instance._onPreviewIdle(device({ idle_panel: 'gone' }, ['clock']), { idle: false });

  assert.deepEqual(instance.toasts, [['No idle panels are configured', 'error']]);
  assert.deepEqual(instance.previewCalls, []);
});

test('the preview Idle control still toggles configured or currently active idle panels', () => {
  const instance = editor();

  instance._onPreviewIdle(device({ idle_panel: 'clock' }, ['clock']), { idle: false });
  instance._onPreviewIdle(device({}, []), { idle: true });

  assert.deepEqual(instance.toasts, []);
  assert.deepEqual(instance.previewCalls, [['idleTimeout'], ['idleTimeout']]);
});
