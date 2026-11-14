import { render as renderLit } from '../../../custom_components/nspanel_haui/frontend/vendor/lit/index.js';

/** Render a Lit template into a real happy-dom container. */
export function render(template, container = document.createElement('div')) {
  renderLit(template, container);
  return container;
}

/** Construct and mount a registered custom element, then wait for its first Lit update. */
export async function mount(tag, props = {}, parent = document.body) {
  const element = document.createElement(tag);
  Object.assign(element, props);
  parent.append(element);
  if (element.updateComplete) await element.updateComplete;
  await settle();
  if (element.updateComplete) await element.updateComplete;
  return element;
}

export async function settle() {
  await Promise.resolve();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await Promise.resolve();
}

export async function flush(count = 2) {
  for (let i = 0; i < count; i += 1) await settle();
}
