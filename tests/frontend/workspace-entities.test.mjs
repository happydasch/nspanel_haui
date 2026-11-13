import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';

import '../../custom_components/nspanel_haui/frontend/views/panel-editor.js';
import '../../custom_components/nspanel_haui/frontend/views/workspace.js';

function collect(value, out = []) {
  if (typeof value === 'string') out.push(value);
  else if (Array.isArray(value)) value.forEach(v => collect(v, out));
  else if (value && typeof value === 'object') {
    if (Array.isArray(value.strings)) collect(value.strings, out);
    if (Array.isArray(value.values)) collect(value.values, out);
  }
  return out;
}

function renderText(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(renderText).join('');
  if (value && Array.isArray(value.strings) && Array.isArray(value.values)) {
    return value.strings.map((part, index) => `${part}${renderText(value.values[index])}`).join('');
  }
  return '';
}

function fakeHass() {
  const hass = {
    subscriptions: [],
    unsubscribed: 0,
    calls: [],
    connection: {
      async subscribeMessage(callback, message) {
        hass.subscriptions.push({ callback, message });
        return async () => { hass.unsubscribed++; };
      },
    },
    async callWS(message) { hass.calls.push(message); return null; },
  };
  return hass;
}

/** An inactive workspace instance without Lit's constructor (which needs a real DOM). */
function makeWorkspace(props = {}) {
  const Workspace = customElements.get('nspanel-preview-workspace');
  const workspace = document.createElement('nspanel-preview-workspace');
  const events = [];
  Object.assign(workspace, {
    requestUpdate() {},
    dispatchEvent(event) { events.push(event); return true; },
    events,
    entryId: 'entry1',
    device: 'kitchen',
    active: false,
    _session: null,
    _error: '',
    _stageWidth: 0,
    _pointerId: null,
    _resizeObserver: null,
    renderRoot: { querySelector: () => null },
    hass: fakeHass(),
  }, props);
  return { dlg: workspace };
}

const flush = () => new Promise(r => setTimeout(r, 0));

test('the reported state follows the session idle flag', async () => {
  const { dlg } = makeWorkspace({ active: true });
  const events = [];
  dlg.dispatchEvent = (event) => events.push(event.detail);
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg._session.idle = true;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, true);
  dlg._session.idle = false;
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, false);
  dlg._stopSession();
});

test('changing the open device option clears the preview entity selection', () => {
  const { dlg } = makeWorkspace({ optionSelection: 'theme' });
  dlg._hover = { entityId: 'light.lamp', x: 20, y: 20, width: 100, height: 100 };

  dlg.optionSelection = 'schedule';
  dlg.updated(new Map([['optionSelection', 'theme']]));

  assert.equal(dlg._hover, null);
});

function tooltipStyle(dlg) {
  return dlg._renderTooltip().values.slice(0, 2);
}

test('the reported state follows physical idle-state events', async () => {
  const { dlg } = makeWorkspace({ active: true });
  const events = [];
  dlg.dispatchEvent = (event) => events.push(event.detail);
  dlg.updated(new Map([['active', false]]));
  await flush();
  dlg.setLive(true);
  await flush();
  assert.equal(events.at(-1).idle, false);
  dlg._session._onMessage({
    type: 'physical',
    idle: true,
    display_state: 'off',
    connected: true,
  });
  dlg.updated(new Map());
  assert.equal(events.at(-1).idle, true);
  dlg._stopSession();
});

test('hovering a linked widget shows its entity; leaving or pressing hides it', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg.hass.states = { 'light.lamp': { attributes: { friendly_name: 'Lamp' } } };
  dlg.updated(new Map([['active', false]]));
  await flush();
  const session = dlg._session;
  session.display = {
    layout: { width: 480, height: 320, visible_width: 450 },
    components: new Map([['b', { id: 1, name: 'b', hidden: false, attrs: { x: 0, y: 0, w: 225, h: 160 } }]]),
    component: id => (id === 0 ? { name: 'grid' } : null),
  };
  session.entityMap = { b: 'light.lamp' };
  const rect = { left: 0, top: 0, width: 900, height: 640 };
  dlg.renderRoot = { querySelector: () => ({ getBoundingClientRect: () => rect }) };

  // Off by default: no tooltip until "Show entities" is switched on.
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover, null);
  dlg.showEntities = true;

  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover.entityId, 'light.lamp');
  const placement = tooltipStyle(dlg);
  assert.ok(placement.some((entry) => entry.startsWith('--vp-tooltip-left:')));
  assert.ok(placement.some((entry) => entry.startsWith('--vp-tooltip-top:')));
  const tip = collect(dlg._renderTooltip()).join(' ');
  assert.match(tip, /Lamp/);
  assert.match(tip, /light\.lamp/);

  // nothing linked there
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 800, clientY: 600 });
  assert.equal(dlg._hover, null);
  // touch input never shows it
  dlg._onPointerMove({ pointerId: 8, pointerType: 'touch', clientX: 100, clientY: 100 });
  assert.equal(dlg._hover, null);

  // switching it off hides a shown tooltip
  dlg._onPointerMove({ pointerId: 7, pointerType: 'mouse', clientX: 100, clientY: 100 });
  dlg.showEntities = false;
  dlg.updated(new Map([['showEntities', false]]));
  assert.equal(dlg._hover, null);
  dlg._stopSession();
});

test('near the right or bottom edge the tooltip chooses the available side', async () => {
  const { dlg } = makeWorkspace({ active: true });
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 600, width: 900, height: 640 };
  const corner = tooltipStyle(dlg);
  assert.ok(corner.some((entry) => entry.startsWith('--vp-tooltip-right:')));
  assert.ok(corner.some((entry) => entry.startsWith('--vp-tooltip-bottom:')));
  dlg._hover = { entityId: 'light.lamp', x: 800, y: 100, width: 900, height: 640 };
  assert.ok(tooltipStyle(dlg).some((entry) => entry.startsWith('--vp-tooltip-right:')));
});
