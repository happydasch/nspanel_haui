// Replay hub card renders in the browser's Nextion simulator.
//
// Usage: node tests/frontend/replay-renders.mjs <orientation> <renders.json>
//
// renders.json maps a name to the hub's `{page, before, commands}`; it is
// written by tests/test_card_renders.py. Exits 1 when a render's page is not in
// the layout or the replay raises a warning the bare page load does not: the
// hub sent something the simulator cannot run, so its card would be wrong.
import './dom-shim.mjs';

import { readFileSync } from 'node:fs';

import { buildPreviewDisplay } from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';

const [orientation, rendersPath] = process.argv.slice(2);
const layout = JSON.parse(readFileSync(
  new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${orientation}.json`, import.meta.url),
  'utf8',
));
const renders = JSON.parse(readFileSync(rendersPath, 'utf8'));

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
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`${Object.keys(renders).length} ${orientation} renders replay cleanly`);
