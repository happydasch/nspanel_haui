// @ts-check
import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

function editor() {
  const instance = Object.create(NSPanelEditor.prototype);
  instance.toasts = [];
  instance.previewCalls = [];
  instance._showToast = (message, kind) => instance.toasts.push([message, kind]);
  instance._callPreviewWorkspace = (...args) => instance.previewCalls.push(args);
  return instance;
}

test('the preview Idle control explains when no idle panel is configured', () => {
  const instance = editor();

  instance._onPreviewIdle({}, { idle: false });

  assert.deepEqual(instance.toasts, [['No idle panels are configured', 'error']]);
  assert.deepEqual(instance.previewCalls, []);
});

test('the preview Idle control still toggles configured or currently active idle panels', () => {
  const instance = editor();

  instance._onPreviewIdle({ idle_panel: 'clock_0' }, { idle: false });
  instance._onPreviewIdle({}, { idle: true });

  assert.deepEqual(instance.toasts, []);
  assert.deepEqual(instance.previewCalls, [['idleTimeout'], ['idleTimeout']]);
});
