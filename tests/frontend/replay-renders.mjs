// Replay hub card renders in the browser's Nextion simulator.
//
// Usage: node tests/frontend/replay-renders.mjs <orientation> <renders.json> [--themed-colors]
//
// renders.json maps a name to the hub's `{page, before, commands}`; it is
// written by tests/test_card_renders.py. Exits 1 when a render's page is not in
// the layout or the replay raises a warning the bare page load does not: the
// hub sent something the simulator cannot run, so its card would be wrong.
// With --themed-colors the renders come from a device whose `background`,
// `header_background`, `component_background` and `component_pressed` differ
// from the HMI's colours, so a visible widget still drawn in its page's HMI
// colour (`bco`, or `bco2` when pressed), still pressed in the HMI's pressed
// colour, or a visible slider, progress bar or toggle still on its own HMI
// `bco` (track, empty part, off state), did not follow the theme. The page must
// also load in the theme: right after the page switch, before the page's
// commands, no solid page or visible widget may show the HMI's background or
// header colour — the theme the hub sends ahead of the page switch is painted
// by the page's Preinitialize code, so no colour change is visible.
import './dom-shim.mjs';

import { readFileSync } from 'node:fs';

import { buildPreviewDisplay } from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';

const [orientation, rendersPath, ...flags] = process.argv.slice(2);
const themedColors = flags.includes('--themed-colors');
const layout = JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${orientation}.json`, import.meta.url),
  'utf8',
));
const renders = JSON.parse(readFileSync(rendersPath, 'utf8'));
const TYPE_PAGE = 121;
const CONTROL_TYPES = new Set([1, 53, 106]); // slider, dual-state button, progress bar
const STA_SOLID = 1;
// Pressed greys the TFTs compile into `bco2`: the default `component_pressed`, and
// the lighter grey some buttons kept from before the 0.4 dark theme.
const HMI_PRESSED = new Set([12678, 29582]);
const HMI_HEADER_BACKGROUND = 6339;

const failures = [];
for (const [name, render] of Object.entries(renders)) {
  const bare = [];
  buildPreviewDisplay(layout, render.page, { onWarn: (message) => bare.push(message) });
  const warnings = [];
  const display = buildPreviewDisplay(layout, render.page, {
    render,
    onWarn: (message) => warnings.push(message),
  });
  if (display.page?.id !== render.page) {
    failures.push(`${name}: page ${render.page} is not in the ${orientation} layout`);
  }
  const added = warnings.filter((message) => !bare.includes(message));
  if (added.length) failures.push(`${name}: ${added.join(' | ')}`);
  for (const expected of render.expected || []) {
    const component = display.component(expected.component);
    if (!component) {
      failures.push(`${name}: expected component ${expected.component} is missing`);
      continue;
    }
    if (expected.visible !== undefined && component.hidden === expected.visible) {
      failures.push(`${name}: ${expected.component} visibility is ${!component.hidden}`);
    }
    if (expected.textIncludes && !String(component.attrs.txt || '').includes(expected.textIncludes)) {
      failures.push(`${name}: ${expected.component} text does not include ${expected.textIncludes}`);
    }
  }
  if (themedColors) {
    const hmi = new Map(layout.pages[render.page].components.map((c) => [c.name, c.attrs]));
    const page = layout.pages[render.page].components.find((c) => c.type === TYPE_PAGE).attrs;
    if (page.sta === STA_SOLID) {
      const loaded = buildPreviewDisplay(layout, render.page, { render: { ...render, commands: [] } });
      const hmiColours = new Set([page.bco, HMI_HEADER_BACKGROUND]);
      const flashing = [...loaded.components.values()].filter((comp) => (
        comp.type === TYPE_PAGE
          ? comp.attrs.bco === page.bco
          : !comp.hidden && comp.attrs.sta === STA_SOLID && hmiColours.has(comp.attrs.bco)
      ));
      if (flashing.length) {
        failures.push(`${name}: loads in the HMI colours on ${flashing.map((c) => c.name).join(', ')}`);
      }
    }
    const visible = [...display.components.values()].filter(
      (comp) => comp.type !== TYPE_PAGE && !comp.hidden,
    );
    const unthemed = visible.filter((comp) => (
      page.sta === STA_SOLID && comp.attrs.sta === STA_SOLID
      && (comp.attrs.bco === page.bco || comp.attrs.bco2 === page.bco)
    ));
    if (unthemed.length) {
      failures.push(`${name}: keeps the HMI background on ${unthemed.map((c) => c.name).join(', ')}`);
    }
    const pressed = visible.filter((comp) => (
      page.sta === STA_SOLID && comp.attrs.sta === STA_SOLID && HMI_PRESSED.has(comp.attrs.bco2)
    ));
    if (pressed.length) {
      failures.push(`${name}: keeps the HMI pressed colour on ${pressed.map((c) => c.name).join(', ')}`);
    }
    const controls = visible.filter((comp) => (
      CONTROL_TYPES.has(comp.type) && hmi.get(comp.name).bco !== page.bco
      && comp.attrs.bco === hmi.get(comp.name).bco
    ));
    if (controls.length) {
      failures.push(`${name}: keeps the HMI control background on ${controls.map((c) => c.name).join(', ')}`);
    }
  }
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`${Object.keys(renders).length} ${orientation} renders replay cleanly`);
