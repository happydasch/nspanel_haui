import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/app/shell.js';
import { makeHost } from './fake-host.mjs';
import { mount, settle } from './support/render.mjs';
import { byRole } from './support/queries.mjs';

const OTHER_DEVICES = [{ name: 'office', label: 'Office' }];

/** Mount the sidebar with a fake device API, and collect the events it emits. */
async function openSidebar(api = { devices: { copy: async () => ({ devices: [] }) } }) {
  const sidebar = await mount('nspanel-backup-sidebar', {
    open: true,
    deviceName: 'kitchen',
    devices: OTHER_DEVICES,
    entryId: 'entry1',
    api,
  });
  const emitted = [];
  for (const name of ['backup-export', 'backup-import', 'backup-copied']) {
    sidebar.addEventListener(name, (event) => emitted.push([name, event.detail]));
  }
  return { sidebar, emitted };
}

/** The sidebar's two cards: the YAML file, then the copy. */
function cards(sidebar) {
  const found = [...sidebar.shadowRoot.querySelectorAll('.haui-backup-sidebar > section')];
  assert.equal(found.length, 2, 'the file and the copy stay two cards');
  return found;
}

/** A pick row's checkbox in the copy card; the row's hint makes the name a prefix match. */
function pick(card, name) {
  const box = byRole(card, 'checkbox', { name, exact: false });
  assert.ok(box, name + ' is offered');
  return box;
}

test('the backup file is one card with Export and Import as one pair', async () => {
  const { sidebar, emitted } = await openSidebar();
  const [fileCard, copyCard] = cards(sidebar);

  assert.match(fileCard.textContent, /Backup file/);
  const exportButton = byRole(fileCard, 'button', { name: 'Export' });
  const importButton = byRole(fileCard, 'button', { name: 'Import' });
  // Import is the destructive direction: the note it names says so before it is run.
  assert.equal(importButton.getAttribute('aria-describedby'), 'backup-import-hint');
  assert.match(fileCard.textContent, /no undo/);
  // The copy is its own card, not another row of the file's.
  assert.match(copyCard.textContent, /Copy to other devices/);
  assert.doesNotMatch(fileCard.textContent, /Copy to other devices/);
  exportButton.click();
  importButton.click();

  assert.deepEqual(emitted.map(([name]) => name), ['backup-export', 'backup-import']);
  sidebar.remove();
});

test('Select all picks every device, and Clear empties the pick again', async () => {
  const sidebar = await mount('nspanel-backup-sidebar', {
    open: true,
    deviceName: 'kitchen',
    devices: [{ name: 'office', label: 'Office' }, { name: 'bedroom', label: 'Bedroom' }],
    entryId: 'entry1',
    api: null,
  });
  const card = cards(sidebar)[1];
  const copyButton = () => byRole(card, 'button', { name: 'Copy' });
  assert.equal(copyButton().disabled, true);

  byRole(card, 'button', { name: 'Select all' }).click();
  await settle();
  assert.equal(pick(card, 'Office').checked, true);
  assert.equal(pick(card, 'Bedroom').checked, true);
  assert.equal(copyButton().disabled, false);

  byRole(card, 'button', { name: 'Clear' }).click();
  await settle();
  assert.equal(pick(card, 'Office').checked, false);
  assert.equal(pick(card, 'Bedroom').checked, false);
  assert.equal(copyButton().disabled, true);
  sidebar.remove();
});

test('a copy takes the picked sections to the picked devices', async () => {
  const calls = [];
  const api = {
    devices: {
      copy: async (...args) => {
        calls.push(args);
        return { devices: ['office'] };
      },
    },
  };
  const { sidebar, emitted } = await openSidebar(api);
  const card = cards(sidebar)[1];

  // Settings and panels are what makes a device look like this one; updates are not.
  assert.equal(pick(card, 'Device settings').checked, true);
  assert.equal(pick(card, 'Panels').checked, true);
  assert.equal(pick(card, 'Update settings').checked, false);
  // Nothing to copy onto yet.
  assert.equal(byRole(card, 'button', { name: 'Copy' }).disabled, true);

  pick(card, 'Office').click();
  await settle();
  assert.equal(byRole(card, 'button', { name: 'Copy' }).disabled, false);
  byRole(card, 'button', { name: 'Copy' }).click();
  await settle();
  await settle();

  assert.deepEqual(calls, [['entry1', 'kitchen', ['office'], ['settings', 'panels']]]);
  assert.deepEqual(emitted, [['backup-copied', { devices: ['office'] }]]);
  // The copy is done with those devices: another one has to pick them again.
  assert.equal(byRole(card, 'button', { name: 'Copy' }).disabled, true);
  sidebar.remove();
});

test('a section left unpicked is not sent, and an empty choice keeps Copy off', async () => {
  const calls = [];
  const api = {
    devices: {
      copy: async (...args) => {
        calls.push(args);
        return { devices: ['office'] };
      },
    },
  };
  const { sidebar } = await openSidebar(api);
  const card = cards(sidebar)[1];

  pick(card, 'Office').click();
  pick(card, 'Device settings').click();
  pick(card, 'Panels').click();
  await settle();
  assert.equal(byRole(card, 'button', { name: 'Copy' }).disabled, true);

  pick(card, 'Update settings').click();
  await settle();
  byRole(card, 'button', { name: 'Copy' }).click();
  await settle();
  await settle();

  assert.deepEqual(calls, [['entry1', 'kitchen', ['office'], ['update']]]);
  sidebar.remove();
});

test('a refused copy says why in the card', async () => {
  const api = {
    devices: {
      copy: async () => {
        throw new Error('Panel light_0: item must be a light');
      },
    },
  };
  const { sidebar, emitted } = await openSidebar(api);
  const card = cards(sidebar)[1];

  pick(card, 'Office').click();
  await settle();
  byRole(card, 'button', { name: 'Copy' }).click();
  await settle();
  await settle();

  assert.match(card.textContent, /Panel light_0: item must be a light/);
  assert.equal(emitted.length, 0);
  sidebar.remove();
});

test('a hub with no other device says so instead of offering a copy', async () => {
  const sidebar = await mount('nspanel-backup-sidebar', {
    open: true, deviceName: 'kitchen', devices: [], entryId: 'entry1', api: null,
  });
  const card = cards(sidebar)[1];

  assert.match(card.textContent, /no other device to copy to/);
  assert.equal(byRole(card, 'button', { name: 'Copy' }), null);
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
