import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { panelSideCard } from '../../custom_components/nspanel_haui/frontend/ui/panel-info.js';

function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join('');
  if (value?.strings) return value.strings.reduce((text, part, index) => text + part + flatten(value.values[index]), '');
  if (value == null) return '';
  if (typeof value === 'symbol') return '';
  return String(value);
}

/** Every template of a tree whose values include `label`, innermost first. */
function templatesWith(template, label, found = []) {
  if (!template?.strings) return found;
  for (const value of template.values) {
    for (const entry of Array.isArray(value) ? value : [value]) templatesWith(entry, label, found);
  }
  if (template.values.includes(label)) found.push(template);
  return found;
}

/** The click handler of the button that renders `label`. */
function clickOf(card, label) {
  const [button] = templatesWith(card, label);
  return button.values[button.strings.findIndex((part) => part.includes('@click='))];
}

test("the selected panel's card shows its render, type, key, group and the row's actions", () => {
  const calls = [];
  const card = panelSideCard({
    kind: 'panel',
    iconName: 'mdi:lightbulb-group',
    title: 'Kitchen lights',
    subtitle: 'Grid',
    description: 'A grid of entities.',
    preview: html`<nspanel-simulator-frame></nspanel-simulator-frame>`,
    portrait: true,
    facts: [
      ['Type', 'Grid'],
      ['Key', html`<code class="haui-panel-info-key">kitchen_lights</code>`],
      ['Group', 'Navigation'],
      ['Items', '4'],
    ],
    actions: [
      { label: 'Edit', iconName: 'edit', variant: 'primary', onClick: () => calls.push('edit') },
      { label: 'Duplicate', iconName: 'mdi:content-copy', onClick: () => calls.push('duplicate') },
      { label: 'Delete', iconName: 'delete', danger: true, onClick: () => calls.push('delete') },
    ],
    onClose: () => calls.push('close'),
  });
  const text = flatten(card);
  assert.match(text, /haui-panel-info/);
  assert.match(text, /haui-panel-info-icon/);
  assert.match(text, /Kitchen lights/);
  assert.match(text, /Grid/);
  assert.match(text, /A grid of entities\./);
  // The hub's render of the page, in the device's orientation.
  assert.match(text, /haui-panel-info-preview portrait/);
  assert.match(text, /nspanel-simulator-frame/);
  assert.match(text, /haui-panel-info-facts/);
  assert.match(text, /kitchen_lights/);
  assert.match(text, /Navigation/);
  assert.match(text, /4/);
  assert.match(text, /haui-button-danger/);
  clickOf(card, 'Edit')();
  clickOf(card, 'Duplicate')();
  clickOf(card, 'Delete')();
  clickOf(card, 'Close')();
  assert.deepEqual(calls, ['edit', 'duplicate', 'delete', 'close']);
});

test('the overview counts each group, names the home and idle panels, and says how rows work', () => {
  const text = flatten(panelSideCard({
    kind: 'overview', navigationCount: 3, hiddenCount: 1, popupCount: 2,
    homePanel: 'Lights', idlePanels: 'Clock and 1 more',
  }));
  assert.match(text, /About panels/);
  assert.match(text, /Select a panel in the list to see its details\./);
  assert.match(text, /haui-panels-overview-groups/);
  assert.match(text, /data-group=navigation/);
  assert.match(text, /data-group=hidden/);
  assert.match(text, /data-group=popups/);
  assert.match(text, /Navigation/);
  assert.match(text, /Hidden/);
  assert.match(text, /Popups/);
  // Each group row carries its count as the chip.
  assert.match(text, /<strong>3<\/strong>/);
  assert.match(text, /<strong>1<\/strong>/);
  assert.match(text, /<strong>2<\/strong>/);
  // The two ends of the device's cycle.
  assert.match(text, /haui-panels-overview-roles/);
  assert.match(text, /data-role=home/);
  assert.match(text, /data-role=idle/);
  assert.match(text, /Home panel/);
  assert.match(text, /Idle panel/);
  assert.match(text, /Lights/);
  assert.match(text, /Clock and 1 more/);
  assert.match(text, /haui-panels-overview-hints/);
  assert.match(text, /Drag a panel to reorder it, or drop it in the other group\./);
  assert.match(text, /The row menu duplicates, hides and deletes a panel\./);
  assert.doesNotMatch(text, /haui-panel-info-preview|haui-panel-info-key|haui-button/);
});

test('the home and idle tiles select their panel rows', () => {
  const selected = [];
  const card = panelSideCard({
    kind: 'overview', navigationCount: 2, hiddenCount: 0, popupCount: 0,
    homePanel: 'Lights', homePanelKey: 'lights',
    idlePanels: 'Clock and 1 more', idlePanelKey: 'clock',
    onSelectPanel: (key) => selected.push(key),
  });
  const homeTile = templatesWith(card, 'Select Home panel: Lights')[0];
  const idleTile = templatesWith(card, 'Select Idle panel: Clock and 1 more')[0];
  assert.ok(homeTile.strings.join('').includes('haui-panels-overview-role-tile'));
  assert.ok(homeTile.strings.join('').includes('data-role='));
  assert.ok(idleTile.strings.join('').includes('haui-panels-overview-role-tile'));
  clickOf(card, 'Select Home panel: Lights')();
  clickOf(card, 'Select Idle panel: Clock and 1 more')();
  assert.deepEqual(selected, ['lights', 'clock']);
});

test('an unassigned home falls back to the first navigation panel, and an empty idle says so', () => {
  const text = flatten(panelSideCard({ kind: 'overview', navigationCount: 0, hiddenCount: 0, popupCount: 0 }));
  assert.match(text, /First navigation panel/);
  assert.match(text, /Not set/);
});

test('the preview folds to a thumbnail beside the description, and the card keeps its facts', () => {
  const toggles = [];
  const model = {
    kind: 'panel',
    iconName: 'grid',
    title: 'Lights',
    subtitle: 'Grid',
    description: 'A grid of entities.',
    preview: html`<nspanel-simulator-frame></nspanel-simulator-frame>`,
    facts: [['Type', 'Grid'], ['Key', 'lights']],
    actions: [{ label: 'Edit', iconName: 'edit', onClick: () => {} }],
    onTogglePreview: () => toggles.push(true),
    onClose: () => {},
  };

  const expanded = flatten(panelSideCard(model));
  assert.match(expanded, /haui-panel-info-preview-block/);
  assert.doesNotMatch(expanded, /is-folded|is-small/);
  // The render is the toggle, pointing up while the preview is large.
  assert.match(expanded, /haui-panel-info-preview is-toggle/);
  assert.match(expanded, /aria-expanded=true/);
  assert.match(expanded, /haui-panel-info-preview-toggle/);
  clickOf(panelSideCard(model), 'Show the panel preview small')();
  assert.deepEqual(toggles, [true]);

  const folded = flatten(panelSideCard({ ...model, previewExpanded: false }));
  assert.match(folded, /haui-panel-info-preview-block is-folded/);
  assert.match(folded, /haui-panel-info-preview is-toggle is-small/);
  assert.match(folded, /A grid of entities\./);
  assert.match(folded, /aria-expanded=false/);
  // Folding the render never takes the card's facts or actions with it.
  assert.match(folded, /haui-panel-info-facts/);
  assert.match(folded, /lights/);
  assert.match(folded, /haui-button/);
  clickOf(panelSideCard({ ...model, previewExpanded: false }), 'Show the panel preview large')();
  assert.deepEqual(toggles, [true, true]);
});

test('a card without a toggle keeps its render as it is', () => {
  const card = panelSideCard({
    kind: 'panel',
    iconName: 'grid',
    title: 'Lights',
    subtitle: 'Grid',
    description: 'A grid of entities.',
    preview: html`<nspanel-simulator-frame></nspanel-simulator-frame>`,
    facts: [['Type', 'Grid']],
    actions: [],
    onClose: () => {},
  });
  const text = flatten(card);
  assert.match(text, /haui-panel-info-preview/);
  assert.doesNotMatch(text, /haui-panel-info-preview is-toggle|haui-panel-info-preview-toggle/);
});

