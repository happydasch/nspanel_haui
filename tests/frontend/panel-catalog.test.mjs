import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { byRole } from './support/queries.mjs';
import { render } from './support/render.mjs';
import { panelCatalog } from '../../custom_components/nspanel_haui/frontend/views/panel-catalog.js';

const category = (key, label) => ({ key, label, icon: 'mdi:' + key });

function catalog(options = {}) {
  return render(panelCatalog({ onQuery() {}, onSelect() {}, ...options }));
}

function choose(root, key) {
  const option = root.querySelector('[data-option="' + key + '"]');
  assert.ok(option, 'expected option ' + key);
  option.click();
}

test('panel search reports the entered query to its caller', () => {
  let searched;
  const root = catalog({
    panelTypes: [], query: 'light',
    onQuery: (value) => { searched = value; },
  });
  const search = byRole(root, 'textbox', { name: 'Search panels' });
  search.value = 'lights';
  search.dispatchEvent(new Event('input', { bubbles: true }));
  assert.equal(searched, 'lights');
});

test('the catalog toolbar labels its search by placeholder and introduces the sections', () => {
  const root = catalog({ panelTypes: [] });
  assert.equal(root.querySelector('.haui-panel-catalog-search-label'), null);
  const intro = root.querySelector('.haui-panel-catalog > .haui-config-section-intro');
  assert.ok(intro, 'the catalog shows its intro text');
  assert.match(intro.textContent, /panel type/);
});

test('panel catalog reports selected panel types and reuses preview inputs', () => {
  const selected = [];
  const previews = [];
  const types = [
    { type_key: 'grid', label: 'Grid', category: category('grouping', 'Grouping') },
    { type_key: 'clock', label: 'Clock', category: category('backgrounds', 'Backgrounds') },
  ];
  const root = catalog({
    panelTypes: types,
    onSelect: (type) => selected.push(type),
    preview: (panel) => { previews.push(panel); return 'preview:' + panel.type; },
  });
  assert.deepEqual([...root.querySelectorAll('[data-section]')].map((el) => el.dataset.section), [
    'grouping', 'backgrounds',
  ]);
  assert.equal(root.querySelector('[data-section="grouping"]').open, true);
  assert.equal(root.querySelector('[data-section="backgrounds"]').open, false);
  assert.equal(root.querySelectorAll('[data-option="grid"]').length, 1);
  assert.equal(root.querySelectorAll('[data-option="clock"]').length, 1);

  choose(root, 'grid');
  assert.deepEqual(selected, ['grid']);
  assert.equal(previews[0].type, 'grid');
});

test('preview layout controls report compact and large selections', () => {
  const selected = [];
  const root = catalog({
    panelTypes: [{ type_key: 'clock', label: 'Clock', category: category('backgrounds', 'Backgrounds') }],
    onPreviewSize: (compact) => selected.push(compact),
    preview: () => null,
  });
  const controls = root.querySelector('[role="group"][aria-label="Preview layout"]');
  const compact = [...controls.querySelectorAll('button')].find((button) => button.textContent.includes('Compact'));
  const large = [...controls.querySelectorAll('button')].find((button) => button.textContent.includes('Large'));
  assert.ok(compact);
  assert.ok(large);
  compact.click();
  large.click();
  assert.deepEqual(selected, [true, false]);
});

test('search opens matching categories and matches a category name', () => {
  const root = catalog({
    query: 'grouping',
    panelTypes: [
      { type_key: 'grid', label: 'Grid', category: category('grouping', 'Grouping') },
      { type_key: 'clock', label: 'Clock', category: category('backgrounds', 'Backgrounds') },
    ],
  });
  assert.equal(root.querySelectorAll('[data-option="grid"]').length, 1);
  assert.equal(root.querySelectorAll('[data-option="clock"]').length, 0);
  assert.equal(root.querySelector('[data-section="grouping"]').open, true);
});

test('popup and copied-panel options report the selected source', () => {
  const popup = { key: 'popup_cover', type: 'popup_cover', label: 'Cover', editable: true };
  const source = { type: 'grid', key: 'grid_0', title: 'Lights' };
  const selectedPopups = [];
  const selectedCopies = [];
  const root = catalog({
    panelTypes: [],
    popups: [popup],
    templates: [{
      id: 'kitchen:grid_0', device: 'kitchen', deviceLabel: 'Kitchen',
      label: 'Lights', detail: 'Grid', panel: source,
    }],
    onSelectPopup: (item) => selectedPopups.push(item),
    onSelectTemplate: (panel) => selectedCopies.push(panel),
  });
  assert.ok(root.querySelector('[data-section="popups"]'));
  assert.ok(root.querySelector('[data-section="copies"]'));
  choose(root, 'popup_cover');
  choose(root, 'kitchen:grid_0');
  assert.deepEqual(selectedPopups, [popup]);
  assert.deepEqual(selectedCopies, [source]);
});

test('copy list is grouped by device and filtered to matches', () => {
  const panel = (device, key, title) => ({
    id: device + ':' + key, device, deviceLabel: device, label: title, detail: 'Grid',
    panel: { type: 'grid', key, title },
  });
  const root = catalog({
    query: 'doors', panelTypes: [], templates: [
      panel('kitchen', 'grid_0', 'Lights'), panel('hall', 'grid_0', 'Doors'),
    ],
  });
  assert.equal(root.querySelectorAll('[data-option="hall:grid_0"]').length, 1);
  assert.equal(root.querySelectorAll('[data-option="kitchen:grid_0"]').length, 0);
  const groups = root.querySelectorAll('[data-device]');
  assert.equal(groups.length, 1);
  assert.equal(groups[0].dataset.device, 'hall');
  assert.equal(groups[0].open, true);
});
