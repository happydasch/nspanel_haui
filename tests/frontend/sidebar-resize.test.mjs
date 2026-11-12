import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { html } from '../../custom_components/nspanel_haui/frontend/lit-import.js';
import { modalSidebar } from '../../custom_components/nspanel_haui/frontend/ui/sidebar.js';

function templatesMatching(template, marker, found = []) {
  if (!template?.strings) return found;
  if (template.strings.join('').includes(marker)) found.push(template);
  for (const value of template.values) {
    if (Array.isArray(value)) value.forEach((entry) => templatesMatching(entry, marker, found));
    else templatesMatching(value, marker, found);
  }
  return found;
}

/** The resize separator of a freshly rendered sidebar, and its handlers by event name. */
function renderHandle() {
  const view = modalSidebar({ label: 'Logs', body: html`<p>Lines</p>`, onClose() {} });
  const [sidebar] = templatesMatching(view, 'haui-modal-sidebar');
  const [handle] = templatesMatching(view, 'haui-sidebar-resize');
  const names = [...handle.strings.join('${}').matchAll(/@(\w+)=\$\{\}/g)].map((m) => m[1]);
  const handlers = Object.fromEntries(names.map((name, i) => [name, handle.values.filter((v) => typeof v === 'function')[i]]));
  return { sidebar, handle, handlers };
}

/** A separator element inside a sidebar element, enough for the handlers. */
function fakeHandle() {
  const style = new Map();
  const attributes = new Map();
  const sidebar = { style: { setProperty: (name, value) => style.set(name, value) } };
  return {
    style,
    attributes,
    element: {
      closest: (selector) => (selector === '.haui-modal-sidebar' ? sidebar : null),
      setAttribute: (name, value) => attributes.set(name, value),
    },
  };
}

test('every sidebar has a separator on its inner edge that keys resize, within limits', (t) => {
  globalThis.innerWidth = 1400;
  t.after(() => { delete globalThis.innerWidth; });
  const { sidebar, handle, handlers } = renderHandle();
  assert.match(handle.strings.join(''), /role="separator" aria-orientation="vertical"/);
  assert.ok(sidebar.values.includes('--haui-sidebar-width: 380px'));

  const target = fakeHandle();
  const key = (name) => handlers.keydown({ key: name, currentTarget: target.element, preventDefault() {} });
  key('ArrowLeft');
  assert.equal(target.style.get('--haui-sidebar-width'), '404px');
  assert.equal(target.attributes.get('aria-valuenow'), '404');
  key('Home');
  assert.equal(target.style.get('--haui-sidebar-width'), '320px');
  key('ArrowRight');
  assert.equal(target.style.get('--haui-sidebar-width'), '320px');
  // The page keeps a strip to click away beside the widest sidebar.
  key('End');
  assert.equal(target.style.get('--haui-sidebar-width'), '1280px');

  // The next sidebar opens at the width the last one was left at.
  assert.ok(renderHandle().sidebar.values.includes('--haui-sidebar-width: 1280px'));

  handlers.dblclick({ currentTarget: target.element });
  assert.equal(target.style.get('--haui-sidebar-width'), '380px');
});
