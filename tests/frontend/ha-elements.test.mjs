import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { NSPanelEditor } from '../../custom_components/nspanel_haui/frontend/haui-editor.js';

const settle = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

/** Flatten a Lit TemplateResult into its markup and text, for assertions. */
function markup(value) {
  if (value == null || typeof value === 'function') return '';
  if (Array.isArray(value)) return value.map(markup).join('');
  if (value.strings) {
    return value.strings.map((s, i) => s + (i < value.values.length ? markup(value.values[i]) : '')).join('');
  }
  return String(value);
}

/** The editor element without Lit's constructor, which needs a real DOM. */
function loadedEditor() {
  const ed = Object.create(NSPanelEditor.prototype);
  Object.assign(ed, {
    entryId: 'entry1',
    _loading: false,
    _panels: { devices: {} },
    _panelTypes: [],
    _selectedDevice: null,
    _deviceConfig: null,
    _viewMode: 'grid',
    _toast: null,
    _deleteTarget: null,
    requestUpdate() {},
  });
  return ed;
}

// HA defines these when it loads its more-info dialog, which can be after the
// editor first renders.
const HA_ELEMENTS = ['ha-dialog', 'ha-dialog-footer', 'ha-card', 'ha-alert'];

// Runs first: the elements are still undefined in this process.
test('the editor names HA elements that do not load instead of waiting silently', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const ed = loadedEditor();
  ed._waitForHaElements();

  t.mock.timers.tick(15000);

  const out = markup(ed.render());
  assert.match(out, /ha-dialog-footer/);
  assert.doesNotMatch(out, /<nspanel-dialog-edit-panel/);
});

// Elements stay undefined for the rest of this process until a later test
// defines them, so this test must run before "waits for HA elements".
test('the slow loading screen offers a way out instead of a dead end', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const ed = loadedEditor();
  ed._waitForHaElements();
  t.mock.timers.tick(15000);

  const waiting = markup(ed.render());
  assert.match(waiting, /Continue anyway/);
  assert.match(waiting, /Reload page/);

  ed._forceRenderWithoutHaElements();
  const forced = markup(ed.render());
  assert.match(forced, /<nspanel-dialog-edit-panel/);
  assert.doesNotMatch(forced, /Continue anyway/);
});

test('the editor waits for HA elements, then renders once they are defined', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const ed = loadedEditor();
  ed._waitForHaElements();

  assert.doesNotMatch(markup(ed.render()), /<ha-dialog/);

  for (const tag of HA_ELEMENTS) customElements.define(tag, class {});
  await settle();

  assert.match(markup(ed.render()), /<nspanel-dialog-edit-panel/);
});

// A failed config-entry load must not be mistaken for "no integration set up".
test('an unreadable integration list renders the error instead of the empty state', () => {
  const ed = loadedEditor();
  ed._haElementsReady = true;
  ed.entryId = null;
  ed._entriesError = 'Connection lost';

  const out = markup(ed.render());
  assert.match(out, /Connection lost/);
  assert.doesNotMatch(out, /No NSPanel HAUI integration configured/);
});
