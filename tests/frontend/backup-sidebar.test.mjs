import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { makeHost } from './fake-host.mjs';

test('the Backups sidebar offers Export and Import, each in a card of its own', async () => {
  const sidebar = document.createElement('nspanel-backup-sidebar');
  Object.assign(sidebar, { open: true });
  const emitted = [];
  sidebar.addEventListener('backup-export', () => emitted.push('export'));
  sidebar.addEventListener('backup-import', () => emitted.push('import'));
  document.body.append(sidebar);
  await sidebar.updateComplete;

  const [exportCard, importCard] = sidebar.shadowRoot.querySelectorAll('.haui-backup-sidebar > section');
  assert.match(exportCard.textContent, /Export/);
  assert.match(exportCard.textContent, /Save this device’s settings and panels to a YAML file/);
  assert.match(importCard.textContent, /Import/);
  assert.match(importCard.textContent, /Restore a YAML backup on this hub, replacing the settings and panels/);
  // Import is the destructive one: it says so before it is run.
  assert.match(importCard.textContent, /no undo/);

  exportCard.querySelector('button').click();
  importCard.querySelector('button').click();
  assert.deepEqual(emitted, ['export', 'import']);
  sidebar.remove();
});

test('Backups opens and closes as a sidebar of the device screen', async () => {
  const editor = makeHost({ devices: { kitchen: { config: {}, panels: [] } } }, () => {
    throw new Error('opening the sidebar requests nothing');
  });
  Object.setPrototypeOf(editor, NSPanelEditor.prototype);
  editor._store = editor.store;
  editor.renderRoot = { querySelector: () => null, activeElement: null };
  const kinds = () => editor.store.getState().ui.overlays.map(({ kind, subject }) => [kind, subject]);

  editor._openBackups('kitchen');
  assert.deepEqual(kinds(), [['backups', 'kitchen']]);
  editor._closeSidebar();
  assert.deepEqual(kinds(), []);

  editor._openBackups('kitchen');
  editor._closeSidebarForRouteChange();
  assert.deepEqual(kinds(), []);
});
