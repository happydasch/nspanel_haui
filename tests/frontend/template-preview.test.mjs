import './dom-shim.mjs';

import { test, mock } from 'node:test';
import assert from 'node:assert/strict';

import { scheduleTemplateRender } from '../../custom_components/nspanel_haui/frontend/form-fields.js';

/**
 * Fake HA connection: `render_template` behaves like HA's websocket command, which
 * acknowledges the subscription with an empty result and then pushes the rendered
 * text as an event (websocket_api/commands.py handle_render_template).
 */
function fakeHass(events) {
  const subs = [];
  return {
    subs,
    async callWS() { return null; },
    connection: {
      async subscribeMessage(callback, msg) {
        const sub = { msg, unsubscribed: 0 };
        subs.push(sub);
        queueMicrotask(() => events.forEach((ev) => callback(ev)));
        return () => { sub.unsubscribed += 1; };
      },
    },
  };
}

/** A preview <span> reachable from `contextEl` the way the editor's shadow root exposes it. */
function previewFixture() {
  const wrapper = { hidden: true };
  const span = { textContent: '', style: {}, closest: () => wrapper };
  const contextEl = { getRootNode: () => ({ querySelector: () => span }) };
  return { span, contextEl };
}

async function renderPreview(hass, template) {
  const { span, contextEl } = previewFixture();
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    scheduleTemplateRender(hass, template, 'tp-x', contextEl);
    mock.timers.tick(500);
  } finally {
    mock.timers.reset();
  }
  for (let i = 0; i < 10; i++) await new Promise((r) => setImmediate(r));
  return span;
}

test('the template preview shows the text HA renders', async () => {
  const hass = fakeHass([{ result: 'Kitchen is on', listeners: {} }]);

  const span = await renderPreview(hass, '{{ "Kitchen is " ~ states("light.kitchen") }}');

  assert.equal(span.textContent, 'Kitchen is on');
  assert.equal(hass.subs[0].msg.type, 'render_template');
});

test('the template preview subscription is closed after the first result', async () => {
  const hass = fakeHass([{ result: 'a', listeners: {} }]);

  await renderPreview(hass, '{{ "a" }}');

  assert.equal(hass.subs[0].unsubscribed, 1);
});

test('a template error is shown as an error, after warnings are skipped', async () => {
  const hass = fakeHass([
    { error: 'deprecated filter', level: 'WARNING' },
    { error: "'foo' is undefined", level: 'ERROR' },
  ]);

  const span = await renderPreview(hass, '{{ foo.bar }}');

  assert.equal(span.textContent, '(template error)');
  assert.equal(hass.subs[0].unsubscribed, 1);
});
