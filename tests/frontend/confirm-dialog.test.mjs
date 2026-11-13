import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/haui-editor.js';
import { HauiDialog } from '../../custom_components/nspanel_haui/frontend/dialogs/haui-dialog.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';

import { hexToRgb565 } from '../../custom_components/nspanel_haui/frontend/color-utils.js';
import { openThemeSidebar, saveTheme } from '../../custom_components/nspanel_haui/frontend/theme-editor.js';
import { filterLogEntries, logEntries, logText } from '../../custom_components/nspanel_haui/frontend/dialogs/logs.js';

const DIALOGS = [
  'nspanel-panel-editor',
  'nspanel-dialog-confirm',
  'nspanel-device-settings',
  'nspanel-firmware-popover',
  'nspanel-logs-sidebar',
  'nspanel-theme-sidebar',
];

/** A dialog instance without Lit's constructor (which needs a real DOM), recording its events. */
function dialog(tag, props = {}) {
  const dlg = document.createElement(tag);
  const events = [];
  Object.assign(dlg, {
    api: createApiClient(() => dlg.hass), requestUpdate() {}, dispatchEvent(e) { events.push(e); return true; } }, props);
  return { dlg, events };
}

test('closing a dialog emits dialog-closed', () => {
  const { dlg, events } = dialog('nspanel-dialog-confirm');
  dlg._dispatchClose();
  assert.deepEqual(events.map((e) => e.type), ['dialog-closed']);
});
