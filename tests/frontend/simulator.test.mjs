import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  colorSubstitutions,
  devicePalette,
  itemColorRgb565,
} from '../../custom_components/nspanel_haui/frontend/previews/utils.js';
import {
  applyPreviewState,
  substituteColors,
  buildPreviewDisplay,
  loadPreviewState,
  previewStateFor,
  resolvePageId,
} from '../../custom_components/nspanel_haui/frontend/previews/previewer.js';
import {
  buildIconCharMap,
  loadIconMap,
  loadLayout,
  renderSimulatorScreen,
} from '../../custom_components/nspanel_haui/frontend/previews/simulator.js';

const ICON_MAP = JSON.parse(readFileSync(
  new URL('../../custom_components/nspanel_haui/frontend/virtual/icon_map.json', import.meta.url),
  'utf8',
));

function layout(orientation) {
  return JSON.parse(readFileSync(
    new URL(`../../custom_components/nspanel_haui/frontend/virtual/layout_${orientation}.json`, import.meta.url),
    'utf8',
  ));
}

/** Flatten a Lit TemplateResult tree to text. */
function flat(v) {
  if (Array.isArray(v)) return v.map(flat).join('');
  if (v && v.strings) return v.strings.reduce((a, s, i) => a + s + (i < v.values.length ? flat(v.values[i]) : ''), '');
  return v == null || typeof v === 'symbol' ? '' : String(v);
}

const BY_NAME = buildIconCharMap(ICON_MAP);
const byName = (d) => buildPreviewDisplay(layout('landscape'), d.page_id, {}, d, { seed: false }).page.name;

test('resolvePageId prefers the descriptor page_id', () => {
  assert.equal(resolvePageId({ type: 'grid' }, { type_key: 'grid', page_id: 9 }), 9);
  assert.equal(resolvePageId({ type: 'light' }, { type_key: 'light', page_id: 13 }), 13);
});

test('resolvePageId falls back to the static physical page map', () => {
  assert.equal(resolvePageId({ type: 'grid' }, null), 9);
  assert.equal(resolvePageId({ type: 'popup_unlock' }, null), 17);
  assert.equal(resolvePageId({ type: 'bogus' }, null), 0);
});

test('every physical page id maps onto a layout page in both orientations', () => {
  for (const orientation of ['landscape', 'portrait']) {
    const json = layout(orientation);
    for (const idStr of Object.keys(json.pages)) {
      const d = buildPreviewDisplay(json, Number(idStr), {}, null, { seed: false });
      assert.equal(d.page.id, Number(idStr), `${orientation} page ${idStr}`);
      const out = flat(renderSimulatorScreen(d, {
        scale: 0.5, iconName: () => null, pictureUrl: (id) => `p/${id}.webp`,
      }));
      assert.match(out, /vp-screen/);
    }
  }
});

test('panel descriptors cover every type key on the expected physical page (alias-aware)', () => {
  // popup aliases resolve to their physical page: popup_unlock shares alarm (17).
  assert.equal(resolvePageId({ type: 'popup_unlock' }, { type_key: 'popup_unlock', page_id: 17 }), 17);
  const viaDesc = [{ type: 'light', t: 13 }, { type: 'climate', t: 16 }, { type: 'media', t: 14 }];
  for (const { type, t } of viaDesc) {
    assert.equal(resolvePageId({ type }, { type_key: type, page_id: t }), t);
    const d = buildPreviewDisplay(layout('landscape'), t, {}, null, { seed: false });
    assert.equal(d.page.name, type);
  }
});

test('grid seeding populates item tiles from the panel config', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, {
    type: 'grid',
    title: 'Lights',
    items: [{ item: 'light.a', name: 'Lamp', icon: 'mdi:lightbulb' }],
  }, null, { byName: BY_NAME, host: {} });
  assert.equal(d.page.name, 'grid');
  assert.equal(d.component('g1Name').attrs.txt, 'Lamp');
  assert.ok(d.component('g1Icon').attrs.txt, 'item icon char written');
  assert.equal(d.component('g2Name').hidden, true, 'empty tile stays hidden');
});

test('a popup alarm alias seeds alarm page with the keypad visible', () => {
  const d = buildPreviewDisplay(layout('portrait'), 17, { type: 'popup_unlock' }, null, { byName: BY_NAME, host: {} });
  assert.equal(d.page.name, 'alarm');
  assert.equal(d.component('bKey1').hidden, false);
});

test('renderSimulatorScreen preserves the device aspect ratio and applies scale', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, {}, null, { seed: false });
  const out = flat(renderSimulatorScreen(d, { scale: 0.5, iconName: () => null, pictureUrl: (id) => `p/${id}.webp` }));
  assert.match(out, /vp-screen" style="width:450px;height:320px/);
  assert.match(out, /pg-sim-scaler" style="width:450px;height:320px;transform:scale\(0.5\)/);
  assert.match(out, /aspect-ratio:450\/320/);
});

test('loadLayout and loadIconMap use an injected loader and no session is created', () => {
  const loader = (url) => Promise.resolve({ url: String(url) });
  return Promise.all([
    loadLayout('landscape', loader).then((r) => assert.match(r.url, /layout_landscape\.json$/)),
    loadIconMap(loader).then((r) => assert.match(r.url, /icon_map\.json$/)),
  ]);
});

const PREVIEW_STATE = JSON.parse(readFileSync(
  new URL('../../custom_components/nspanel_haui/frontend/virtual/preview_state.json', import.meta.url),
  'utf8',
));

/** Number of visible widgets (id 0 is the page itself). */
const visibleCount = (d) => [...d.components.values()].filter((c) => c.id !== 0 && !c.hidden).length;

test('the hub snapshot is replayed so controls the HMI hides become visible', () => {
  // These pages hide their controls in the page's Preinitialize code and the
  // hub reveals them, so without the snapshot their previews looked blank.
  const controls = {
    18: ['bUp', 'bStop', 'bDown', 'hVertPos'],  // cover
    13: ['hBrightness'],                       // light
    12: ['bStart', 'bStop', 'bUp1', 'bDown1'],  // timer
    15: ['bAction', 'bHome'],                   // vacuum
  };
  for (const [pid, names] of Object.entries(controls)) {
    const blank = buildPreviewDisplay(layout('landscape'), pid, {}, null, { seed: false });
    const replayed = buildPreviewDisplay(layout('landscape'), pid, {}, null, {
      state: PREVIEW_STATE, host: {},
    });
    for (const name of names) {
      assert.equal(blank.component(name).hidden, true, `${name} starts hidden`);
      assert.equal(replayed.component(name).hidden, false, `${name} is revealed`);
    }
  }
});

test('the snapshot sets the widget colours, values and texts the hub sends', () => {
  const d = buildPreviewDisplay(layout('landscape'), 13, { type: 'light', title: 'Desk' }, null, {
    state: PREVIEW_STATE, host: {},
  });
  // Colours come from the hub's palette commands, not the HMI defaults.
  const paletteColor = PREVIEW_STATE['13'].commands
    .filter((c) => c.startsWith('tTitle.pco='))
    .at(-1)
    .split('=')[1];
  assert.equal(d.component('tTitle').attrs.pco, Number(paletteColor));
  // Sample light entity state from the snapshot (brightness 153 of 255).
  assert.ok(d.component('hBrightness').attrs.val > 0);
  // The panel's own title wins over the snapshot's sample title.
  assert.equal(d.component('tTitle').attrs.txt, 'Desk');
});

test('popup aliases replay their physical page and hide the base page mode bar', () => {
  const alarm = buildPreviewDisplay(layout('landscape'), 17, { type: 'alarm' }, null, {
    state: PREVIEW_STATE, host: {},
  });
  const unlock = buildPreviewDisplay(layout('landscape'), 17, { type: 'popup_unlock' }, null, {
    state: PREVIEW_STATE, host: {},
  });
  assert.equal(unlock.page.name, 'alarm');
  for (const name of ['b1Fnc', 'b2Fnc', 'b3Fnc', 'b4Fnc']) {
    assert.equal(unlock.component(name).hidden, true, `${name} hidden for the unlock popup`);
  }
  assert.ok(visibleCount(unlock) < visibleCount(alarm));
});

test('a page without snapshot falls back to representative seeding', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, {
    type: 'grid', items: [{ item: 'light.a', name: 'Lamp', icon: 'mdi:lightbulb' }],
  }, null, { host: {}, byName: BY_NAME, state: {} });
  assert.equal(d.component('g1Name').attrs.txt, 'Lamp');
});

test('configured climate, cover and light states overlay snapshots and fallback seeds', () => {
  const warnings = [];
  const host = {
    hass: {
      states: {
        'climate.office': {
          state: 'heat',
          attributes: {
            current_temperature: 20.5,
            temperature: 22,
            temperature_unit: '°C',
            hvac_modes: ['off', 'heat'],
          },
        },
        'cover.blind': {
          state: 'opening',
          attributes: { current_position: 40, supported_features: 15 },
        },
        'light.desk': {
          state: 'on',
          attributes: {
            brightness: 128,
            supported_color_modes: ['brightness', 'color_temp'],
            min_color_temp_kelvin: 200,
            max_color_temp_kelvin: 500,
            color_temp_kelvin: 320,
          },
        },
      },
    },
  };
  const build = (id, type, panel) => buildPreviewDisplay(
    layout('landscape'), id, { type, ...panel }, null,
    { state: {}, host, byName: BY_NAME, onWarn: (message) => warnings.push(message) },
  );

  const climate = build(16, 'climate', { item: 'climate.office' });
  assert.equal(climate.component('tTemp').attrs.txt, '20.5°C');
  assert.equal(climate.component('xSet').attrs.val, 220);
  assert.equal(climate.component('xSet1').hidden, true);
  assert.equal(climate.component('btMode2').attrs.val, 1);
  assert.equal(climate.component('btMode3').hidden, true);

  const cover = build(18, 'cover', { item: 'cover.blind' });
  assert.equal(cover.component('hVertPos').attrs.val, 40);
  assert.equal(cover.component('tInfo').attrs.txt, '40%');
  assert.equal(cover.component('bStop').hidden, false);

  const light = build(13, 'light', { item: 'light.desk' });
  assert.equal(light.component('hBrightness').attrs.val, 50);
  assert.equal(light.component('hBrightness').hidden, false);
  assert.equal(light.component('hColorTemp').hidden, true, 'only the default brightness control is active');
  assert.equal(light.component('tInfo').attrs.txt, '50%');
  assert.deepEqual(warnings, []);
});

test('weather options and configured sensors replace sample content', () => {
  const d = buildPreviewDisplay(layout('landscape'), 6, {
    type: 'weather',
    item: 'weather.home',
    inside_temp_item: 'sensor.inside',
    show_home_temp: true,
    show_weather: false,
    show_temp: false,
    forecast_type: '',
    info_items: [{ item: 'sensor.humidity', name: 'Humidity', icon: 'mdi:water-percent' }],
  }, null, {
    state: PREVIEW_STATE,
    byName: BY_NAME,
    host: {
      hass: {
        states: {
          'weather.home': {
            state: 'sunny',
            attributes: { temperature: 21, temperature_unit: '°C', pressure: 1012, pressure_unit: 'hPa' },
          },
          'sensor.inside': { state: '18' },
          'sensor.humidity': { state: '45' },
        },
      },
    },
  });
  assert.equal(d.component('tMainIcon').hidden, true);
  assert.equal(d.component('tMainText').hidden, true);
  assert.equal(d.component('tSubText').hidden, true);
  assert.equal(d.component('f1Name').hidden, true);
  assert.equal(d.component('d1Val').attrs.txt, '45');
  assert.equal(d.component('tMainText').attrs.txt, '18°C  21°C');
});

test('alarm options style the keypad and hide configured arm modes', () => {
  const d = buildPreviewDisplay(layout('landscape'), 17, {
    type: 'alarm',
    item: 'alarm_control_panel.home',
    keypad_font: 3,
    keypad_bg_color: '#ff0000',
    keypad_text_color: '#00ff00',
    hidden_arm_modes: ['away'],
    arm_button_color: '#0000ff',
  }, null, {
    state: PREVIEW_STATE,
    host: {
      hass: {
        states: {
          'alarm_control_panel.home': { state: 'disarmed', attributes: { supported_features: 7 } },
        },
      },
    },
  });
  assert.equal(d.component('bKey1').attrs.font, 3);
  assert.equal(d.component('bKey1').attrs.bco, 63488);
  assert.equal(d.component('bKey1').attrs.pco, 2016);
  assert.equal(d.component('tTitle').attrs.txt, 'disarmed');
  assert.equal(d.component('b1Fnc').attrs.txt, 'Home');
  assert.equal(d.component('b2Fnc').attrs.txt, 'Night');
  assert.equal(d.component('b3Fnc').hidden, true);
  assert.equal(d.component('b1Fnc').attrs.pco, 31);
});

test('select popup uses its invocation items and selection, not the snapshot sample', () => {
  const d = buildPreviewDisplay(layout('landscape'), 5, {
    type: 'select',
    title: 'Choose mode',
    select_mode: 'full',
    multiple: false,
    selected: 'heat',
    items: [
      { value: 'heat', name: 'Heating' },
      { value: 'cool', name: 'Cooling' },
    ],
  }, null, { state: PREVIEW_STATE, host: {} });
  assert.equal(d.component('tTitle').attrs.txt, 'Choose mode');
  assert.equal(d.component('bSelFull1').attrs.txt, 'Heating');
  assert.equal(d.component('bSelFull1').attrs.pco, 62694);
  assert.equal(d.component('bSelFull2').attrs.txt, 'Cooling');
  assert.equal(d.component('bSelFull2').attrs.pco, 19773);
  assert.equal(d.component('bSelFull3').hidden, true);
  assert.equal(d.component('bSel1').hidden, true);

  const sample = buildPreviewDisplay(layout('landscape'), 5, { type: 'select' }, null, {
    state: PREVIEW_STATE, host: {},
  });
  assert.ok(!sample.component('bSelFull1').hidden || !sample.component('bSel1').hidden);
});

test('clocktwo panel colors and notification visibility overlay the snapshot', () => {
  const d = buildPreviewDisplay(layout('landscape'), 8, {
    type: 'clocktwo',
    off_color: '#000000',
    letter_color: '#ff0000',
    special_color: '#00ff00',
    show_notifications: false,
  }, null, { state: PREVIEW_STATE, host: {} });
  assert.equal(d.component('l1').attrs.pco, 63488);
  assert.equal(d.component('s1').attrs.pco, 2016);
  assert.equal(d.component('tNotif').hidden, true);
});

test('previewStateFor resolves entries by page id and applyPreviewState reports misses', () => {
  assert.equal(previewStateFor(PREVIEW_STATE, 18).page, 18);
  assert.equal(previewStateFor(PREVIEW_STATE, 999), null);
  const d = buildPreviewDisplay(layout('landscape'), 18, {}, null, { seed: false });
  assert.equal(applyPreviewState(d, null), false);
  assert.equal(applyPreviewState(d, PREVIEW_STATE['18']), true);
});

test('loadPreviewState loads the snapshot through an injected loader', () => {
  return loadPreviewState(() => Promise.resolve({ 9: { page: 9, commands: [] } }))
    .then((state) => assert.equal(state['9'].page, 9));
});

test('device colour overrides replace the snapshot palette values', () => {
  const host = {
    _deviceConfig: { color_overrides: { header_background: 65535, component_active: 2016 } },
  };
  const map = colorSubstitutions(host);
  assert.equal(map[6339], 65535);   // header_background
  assert.equal(map[19773], 2016);   // component_active
  assert.equal(substituteColors('tHeader.bco=6339', map), 'tHeader.bco=65535');
  assert.equal(substituteColors('bUp.pco=19773', map), 'bUp.pco=2016');

  const d = buildPreviewDisplay(layout('landscape'), 18, { type: 'cover' }, null, {
    state: PREVIEW_STATE, host, colorMap: map,
  });
  assert.equal(d.component('tHeader').attrs.bco, 65535);
  assert.equal(d.component('bUp').attrs.pco, 2016);
});

test('colours shared by several palette keys only substitute when they agree', () => {
  // header_text and component_text both default to 65535: one override alone is
  // ambiguous, so the default value is kept.
  const partial = colorSubstitutions({ _deviceConfig: { color_overrides: { header_text: 1 } } });
  assert.equal(partial[65535], undefined);
  const agreed = colorSubstitutions({
    _deviceConfig: { color_overrides: { header_text: 1, component_text: 1 } },
  });
  assert.equal(agreed[65535], 1);
});

test('no overrides leaves the snapshot colours untouched', () => {
  assert.deepEqual(colorSubstitutions({}), {});
  assert.equal(substituteColors('tHeader.bco=6339', {}), 'tHeader.bco=6339');
});

const GRID_HOST = {
  hass: {
    states: {
      'light.kitchen': { state: 'on' },
      'switch.fan': { state: 'off' },
      'scene.movie': { state: 'unknown' },
    },
  },
};

const GRID_PANEL = {
  type: 'grid',
  title: 'My Rooms',
  items: [
    {
      item: 'light.kitchen', name: 'Kitchen Light', icon: 'mdi:lightbulb',
      back_color: 63488, text_color: '#00ff00', show_power_button: true,
    },
    { item: 'switch.fan', name: 'Fan', icon: 'mdi:fan', back_color: { on: 2016, off: 57176 } },
    { item: 'scene.movie', name: 'Movie', icon: 'mdi:movie', show_power_button: true },
  ],
};

test('grid tiles show the configured panel items, not the snapshot samples', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, GRID_PANEL, null, {
    state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
  });
  assert.equal(d.component('tTitle').attrs.txt, 'My Rooms');
  assert.equal(d.component('g1Name').attrs.txt, 'Kitchen Light');
  assert.equal(d.component('g2Name').attrs.txt, 'Fan');
  assert.equal(d.component('g3Name').attrs.txt, 'Movie');
  // Slots without a configured item are hidden, not left with sample content.
  for (const name of ['g4Name', 'g4Btn', 'g5Name', 'g6Btn']) {
    assert.equal(d.component(name).hidden, true, `${name} hidden`);
  }
});

test('grid tiles apply the item colour settings from the panel config', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, GRID_PANEL, null, {
    state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
  });
  const palette = devicePalette(GRID_HOST);
  // text_color "#00ff00" -> RGB565 green; back_color 63488 -> red.
  assert.equal(d.component('g1Name').attrs.pco, 2016);
  assert.equal(d.component('g1Btn').attrs.bco, 63488);
  assert.equal(d.component('g1Name').attrs.bco, 63488);
  // State-keyed back_color resolves to the entity's state ('off').
  assert.equal(d.component('g2Btn').attrs.bco, 57176);
  // No override falls back to the device palette, not the sample colours.
  assert.equal(d.component('g2Name').attrs.pco, palette.text);
  assert.equal(d.component('g3Btn').attrs.bco, palette.background);
});

test('grid power buttons follow show_power_button and the item state', () => {
  const d = buildPreviewDisplay(layout('landscape'), 9, GRID_PANEL, null, {
    state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
  });
  const palette = devicePalette(GRID_HOST);
  assert.equal(d.component('g1Power').hidden, false);          // configured
  assert.equal(d.component('g1Power').attrs.pco, palette.component_active);  // item is on
  assert.equal(d.component('g2Power').hidden, true);           // not configured
  assert.equal(d.component('g3Power').hidden, false);
  // An inactive item's power button uses the pressed background colour
  // (hub: get_grid_colors only uses power_color while the item is active).
  assert.equal(d.component('g3Power').attrs.pco, palette.component_pressed);
});

test('row entries use the configured items and their colours', () => {
  const rowPanel = {
    type: 'row',
    title: 'Devices',
    items: [{ item: 'light.kitchen', name: 'Kitchen', icon: 'mdi:lightbulb', back_color: 63488 }],
  };
  const d = buildPreviewDisplay(layout('landscape'), 10, rowPanel, null, {
    state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
  });
  assert.equal(d.component('r1Name').attrs.txt, 'Kitchen');
  assert.equal(d.component('r1Btn' in {} ? '' : 'r1Name').attrs.bco, 63488);
  assert.equal(d.component('r2Name').hidden, true);
});

test('itemColorRgb565 resolves every configured colour form', () => {
  assert.equal(itemColorRgb565({ item: 'light.a', back_color: 63488 }, 'back_color'), 63488);
  assert.equal(itemColorRgb565({ item: 'light.a', back_color: '#ff0000' }, 'back_color'), 63488);
  assert.equal(itemColorRgb565({ item: 'light.a', back_color: '[255, 0, 0]' }, 'back_color'), 63488);
  const host = { hass: { states: { 'light.a': { state: 'off' } } } };
  assert.equal(
    itemColorRgb565({ item: 'light.a', back_color: { on: 63488, off: 2016 } }, 'back_color', host),
    2016,
  );
  assert.equal(itemColorRgb565({ item: 'light.a' }, 'back_color'), null);
});

test('configured backgrounds win over the snapshot sample background', () => {
  const clock = buildPreviewDisplay(layout('landscape'), 7, {
    type: 'clock', background: 'summer',
  }, null, { state: PREVIEW_STATE, host: {} });
  // BACKGROUNDS.summer = 4; the page's Preinitialize code reads this variable
  // to pick the background pictures.
  assert.equal(clock.component('background').attrs.val, 4);
  assert.equal(clock.component('tTime').attrs.picc, 4);

  // No background option: the snapshot's value is replayed unchanged.
  const plain = buildPreviewDisplay(layout('landscape'), 7, { type: 'clock' }, null, {
    state: PREVIEW_STATE, host: {},
  });
  assert.equal(plain.component('background').attrs.val, 1);
});

test('clock entity buttons show the configured items', () => {
  const clock = buildPreviewDisplay(layout('landscape'), 7, {
    type: 'clock',
    items: [{ item: 'light.kitchen', name: 'Kitchen', icon: 'mdi:lightbulb' }],
  }, null, { state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME });
  assert.equal(clock.component('bEntity1').hidden, false);
  assert.ok(clock.component('bEntity1').attrs.txt, 'icon written to the button');
  assert.equal(clock.component('bEntity2').hidden, true);
});test('clock entity buttons stay hidden when no items are configured', () => {
  // The snapshot's sampled clock shows two entity buttons; a real panel with
  // no `items` must not leak them.
  const clock = buildPreviewDisplay(layout('landscape'), 7, {
    type: 'clock',
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  for (let i = 1; i <= 6; i += 1) {
    assert.equal(clock.component(`bEntity${i}`).hidden, true, `bEntity${i} hidden`);
  }
});

test('the QR page shows configured credentials in small mode by default', () => {
  const d = buildPreviewDisplay(layout('landscape'), 11, {
    type: 'qr', essid: 'HomeNet', password: 'secret',
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  const code = 'WIFI:S:HomeNet;T:WPA;P:secret;;';
  assert.equal(d.component('qrCode').attrs.txt, code);
  assert.equal(d.component('qrCodeBig').attrs.txt, code);
  assert.equal(d.component('qrCode').hidden, false);
  assert.equal(d.component('qrCodeBig').hidden, true);
  for (const name of ['q1Icon', 'q1Title', 'q1Text', 'q1TextAdd', 'q2Icon', 'q2Title', 'q2Text', 'q2TextAdd']) {
    assert.equal(d.component(name).hidden, false, `${name} visible in small mode`);
  }
  assert.equal(d.component('q1Text').attrs.txt, 'HomeNet');
  assert.equal(d.component('q2Text').attrs.txt, 'secret');
});

test('the QR page honors start_big_qr and hides detail widgets', () => {
  const d = buildPreviewDisplay(layout('landscape'), 11, {
    type: 'qr', essid: 'HomeNet', password: 'secret', start_big_qr: true,
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  const code = 'WIFI:S:HomeNet;T:WPA;P:secret;;';
  assert.equal(d.component('qrCode').attrs.txt, code);
  assert.equal(d.component('qrCodeBig').attrs.txt, code);
  assert.equal(d.component('qrCode').hidden, true);
  assert.equal(d.component('qrCodeBig').hidden, false);
  for (const name of ['q1Icon', 'q1Title', 'q1Text', 'q1TextAdd', 'q2Icon', 'q2Title', 'q2Text', 'q2TextAdd']) {
    assert.equal(d.component(name).hidden, true, `${name} hidden in big mode`);
  }
});

test('QR detail widgets stay hidden when show_info is disabled', () => {
  const d = buildPreviewDisplay(layout('landscape'), 11, {
    type: 'qr', essid: 'HomeNet', show_info: false,
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  assert.equal(d.component('qrCode').hidden, false);
  for (const name of ['q1Icon', 'q1Title', 'q1Text', 'q1TextAdd', 'q2Icon', 'q2Title', 'q2Text', 'q2TextAdd']) {
    assert.equal(d.component(name).hidden, true, `${name} hidden when show_info is false`);
  }
});

test('QR header icons follow the configured navigation mode', () => {
  const navigable = {
    type: 'qr', key: 'wifi', show_in_navigation: true, essid: 'HomeNet',
  };
  const navHost = {
    _deviceConfig: {},
    _devicePanels: () => [navigable, { type: 'grid', key: 'rooms' }],
  };
  const nav = buildPreviewDisplay(layout('landscape'), 11, navigable, null, {
    state: PREVIEW_STATE, host: navHost, byName: BY_NAME,
  });
  assert.equal(ICON_MAP[nav.component('bFncLPri').attrs.txt], 'chevron-left');
  assert.equal(ICON_MAP[nav.component('bFncRPri').attrs.txt], 'chevron-right');
  assert.equal(nav.component('bFncLPri').hidden, false);
  assert.equal(nav.component('bFncRPri').hidden, false);

  const nonNavigable = { ...navigable, show_in_navigation: false };
  const nonNavHost = {
    _deviceConfig: {},
    _devicePanels: () => [nonNavigable, { key: 'rooms' }, { key: 'weather' }],
  };
  const nonNav = buildPreviewDisplay(layout('landscape'), 11, nonNavigable, null, {
    state: PREVIEW_STATE, host: nonNavHost, byName: BY_NAME,
  });
  assert.equal(ICON_MAP[nonNav.component('bFncLPri').attrs.txt], 'chevron-up');
  assert.equal(ICON_MAP[nonNav.component('bFncRPri').attrs.txt], 'close');
  assert.equal(nonNav.component('bFncLPri').hidden, false);
  assert.equal(nonNav.component('bFncRPri').hidden, false);
});

test('the big QR zoom button keeps the header accent color', () => {
  const panel = { type: 'qr', key: 'wifi', start_big_qr: true, essid: 'HomeNet' };
  const host = {
    _deviceConfig: { color_overrides: { component_text: 63488, header_text: 65535, header_accent: 2016 } },
    _devicePanels: () => [panel, { key: 'rooms' }],
  };
  const d = buildPreviewDisplay(layout('landscape'), 11, panel, null, {
    state: PREVIEW_STATE, host, byName: BY_NAME,
  });
  assert.equal(ICON_MAP[d.component('bFncRSec').attrs.txt], 'loupe');
  assert.equal(d.component('bFncRSec').attrs.pco, 2016);
});

test('a single navigation panel promotes secondary actions into primary slots', () => {
  const panel = { type: 'qr', key: 'wifi', show_in_navigation: true, essid: 'HomeNet' };
  const host = { _deviceConfig: {}, _devicePanels: () => [panel] };
  const d = buildPreviewDisplay(layout('landscape'), 11, panel, null, {
    state: PREVIEW_STATE, host, byName: BY_NAME,
  });
  assert.equal(ICON_MAP[d.component('bFncRPri').attrs.txt], 'loupe');
  assert.equal(d.component('bFncRPri').hidden, false);
  assert.equal(d.component('bFncRSec').hidden, true);
  assert.equal(d.component('bFncLPri').hidden, true);
  assert.equal(d.component('bFncLSec').hidden, true);
});

test('popup-capable pages and paginated grids use their configured header slots', () => {
  const lightPanel = {
    type: 'light', key: 'desk', show_in_navigation: true, show_home_button: true,
  };
  const lightHost = {
    _deviceConfig: {},
    _devicePanels: () => [lightPanel, { key: 'rooms' }],
  };
  const light = buildPreviewDisplay(layout('landscape'), 13, lightPanel, {
    type_key: 'light', can_show_popup: true,
  }, { state: PREVIEW_STATE, host: lightHost, byName: BY_NAME });
  assert.equal(ICON_MAP[light.component('bFncLPri').attrs.txt], 'home-outline');
  assert.equal(light.component('bFncLPri').hidden, false);
  assert.equal(light.component('bFncLSec').hidden, true);

  const gridPanel = {
    type: 'grid', key: 'rooms', show_in_navigation: true,
    items: Array.from({ length: 7 }, (_, i) => ({ item: `light.room_${i}`, name: `Room ${i}` })),
  };
  const gridHost = {
    _deviceConfig: {},
    _devicePanels: () => [gridPanel, { key: 'wifi' }],
  };
  const grid = buildPreviewDisplay(layout('landscape'), 9, gridPanel, null, {
    state: PREVIEW_STATE, host: gridHost, byName: BY_NAME,
  });
  assert.equal(ICON_MAP[grid.component('bFncRPri').attrs.txt], 'chevron-right');
  assert.equal(ICON_MAP[grid.component('bFncRSec').attrs.txt], 'chevron-double-down');
  assert.equal(grid.component('bFncRSec').hidden, false);
});

test('media source buttons show the configured items', () => {
  const d = buildPreviewDisplay(layout('landscape'), 14, {
    type: 'media',
    item: { item: 'media_player.tv' },
    items: [{ item: 'light.kitchen', name: 'Kitchen', icon: 'mdi:lightbulb' }],
  }, null, { state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME });
  assert.equal(d.component('m1Name').attrs.txt, 'Kitchen');
  assert.equal(d.component('m1Btn').hidden, false);
});

test('every colour form the editor stores is applied to a tile', () => {
  const forms = [
    ['#rrggbb', '#0000ff'],
    ['[r, g, b]', '[255, 0, 0]'],
    ['array', [0, 255, 0]],
    ['rgb565 int', 63488],
    ['numeric string', '63488'],
  ];
  for (const [label, backColor] of forms) {
    const panel = {
      type: 'grid',
      items: [{ item: 'light.kitchen', name: 'K', back_color: backColor }],
    };
    const d = buildPreviewDisplay(layout('landscape'), 9, panel, null, {
      state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
    });
    const bco = d.component('g1Btn').attrs.bco;
    assert.notEqual(bco, devicePalette(GRID_HOST).background, label + ' must not fall back');
    if (label === '#rrggbb') assert.equal(bco, 31, 'blue');
    if (label === '[r, g, b]' || label === 'rgb565 int' || label === 'numeric string') {
      assert.equal(bco, 63488, label);
    }
    if (label === 'array') assert.equal(bco, 2016, 'green');
  }
});

test('power buttons honour a string boolean from an older store', () => {
  const panel = {
    type: 'grid',
    items: [
      { item: 'light.kitchen', name: 'On', show_power_button: 'true' },
      { item: 'light.kitchen', name: 'Off', show_power_button: 'false' },
    ],
  };
  const d = buildPreviewDisplay(layout('landscape'), 9, panel, null, {
    state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME,
  });
  assert.equal(d.component('g1Power').hidden, false);
  assert.equal(d.component('g2Power').hidden, true);
});

test('media controls follow the configured player features', () => {
  const controls = ['bShuffle', 'bRepeat', 'bPlay', 'bPrev', 'bNext', 'bVolDown', 'bVolUp', 'bPower'];
  const show = (features, state) => {
    const host = {
      hass: {
        states: { 'media_player.tv': { state, attributes: { supported_features: features } } },
      },
    };
    const d = buildPreviewDisplay(layout('landscape'), 14, {
      type: 'media', item: { item: 'media_player.tv' },
    }, null, { state: PREVIEW_STATE, host, byName: BY_NAME });
    return Object.fromEntries(controls.map((n) => [n, !d.component(n).hidden]));
  };

  // Full-featured player: every control (bPower is the dead page widget: the
  // hub's power control is the header function button, so it stays hidden).
  const full = 32768 | 262144 | 16384 | 1 | 16 | 32 | 4 | 128;
  const all = show(full, 'playing');
  for (const n of controls.filter((c) => c !== 'bPower')) {
    assert.equal(all[n], true, n + ' shown');
  }
  assert.equal(all.bPower, false, 'bPower never shown');

  // Play/pause only: nothing else may appear.
  const minimal = show(16384, 'idle');
  assert.equal(minimal.bPlay, true);
  for (const n of ['bShuffle', 'bRepeat', 'bPrev', 'bNext', 'bVolDown', 'bVolUp', 'bPower']) {
    assert.equal(minimal[n], false, n + ' hidden');
  }
});

test('media controls fall back to showing everything when the entity is unknown', () => {
  const d = buildPreviewDisplay(layout('landscape'), 14, {
    type: 'media', item: { item: 'media_player.not_loaded' },
  }, null, { state: PREVIEW_STATE, host: { hass: { states: {} } }, byName: BY_NAME });
  for (const n of ['bShuffle', 'bRepeat', 'bPlay', 'bPrev', 'bNext', 'bVolDown', 'bVolUp']) {
    assert.equal(d.component(n).hidden, false, n + ' shown');
  }
});

test('vacuum controls follow the configured vacuum features and state', () => {
  const host = (features, state) => ({
    hass: { states: { 'vacuum.robot': { state, attributes: { supported_features: features } } } },
  });
  const build = (features, state) => buildPreviewDisplay(layout('landscape'), 15, {
    type: 'vacuum', item: { item: 'vacuum.robot' },
  }, null, { state: PREVIEW_STATE, host: host(features, state), byName: BY_NAME });

  const full = build(32 | 16 | 512 | 8192, 'cleaning');
  for (const n of ['bFan', 'bAction', 'bHome', 'bLocate']) {
    assert.equal(full.component(n).hidden, false, n + ' shown');
  }
  assert.equal(full.component('tStatus').attrs.txt, 'Cleaning');

  const docked = build(16, 'docked');
  assert.equal(docked.component('bHome').hidden, false);
  // Visibility is the feature gate: no START/FAN_SPEED/LOCATE -> those hide.
  for (const n of ['bFan', 'bAction', 'bLocate']) {
    assert.equal(docked.component(n).hidden, true, n + ' hidden');
  }
  assert.equal(docked.component('tStatus').attrs.txt, 'Docked');
});

test('the vacuum action button follows the state and its features', () => {
  const build = (features, state) => buildPreviewDisplay(layout('landscape'), 15, {
    type: 'vacuum', item: { item: 'vacuum.robot' },
  }, null, {
    state: PREVIEW_STATE,
    host: { hass: { states: { 'vacuum.robot': { state, attributes: { supported_features: features } } } } },
    byName: BY_NAME,
  });
  const icon = (ch) => ICON_MAP[ch] || '?';
  // Working with PAUSE -> pause icon; with only STOP -> stop icon.
  assert.equal(icon(build(8192 | 4 | 8, 'cleaning').component('bAction').attrs.txt), 'pause');
  assert.equal(icon(build(8192 | 8, 'returning').component('bAction').attrs.txt), 'stop');
  // Docked/idle with START -> play icon.
  assert.equal(icon(build(8192, 'docked').component('bAction').attrs.txt), 'play');
  // No START -> the action control is not offered at all.
  assert.equal(build(4 | 8, 'idle').component('bAction').hidden, true);
  // A working vacuum without PAUSE/STOP renders the action button disabled.
  const disabled = build(8192, 'cleaning');
  assert.equal(disabled.component('bAction').attrs.pco, devicePalette({}).text_disabled);
});

test('vacuum status text uses the translated state labels', () => {
  const status = (vacState) => buildPreviewDisplay(layout('landscape'), 15, {
    type: 'vacuum', item: { item: 'vacuum.robot' },
  }, null, {
    state: PREVIEW_STATE,
    host: { hass: { states: { 'vacuum.robot': { state: vacState, attributes: { supported_features: 8192 } } } } },
    byName: BY_NAME,
  }).component('tStatus').attrs.txt;
  assert.equal(status('returning'), 'Returning to dock');
  assert.equal(status('paused'), 'Paused');
  assert.equal(status('weird_state'), 'Weird_state');
});

test('the vacuum battery icon comes from the configured battery sensor', () => {
  const build = (extra) => buildPreviewDisplay(layout('landscape'), 15, {
    type: 'vacuum', item: { item: 'vacuum.robot' }, ...extra,
  }, null, {
    state: PREVIEW_STATE,
    host: {
      hass: {
        states: {
          'vacuum.robot': { state: 'cleaning', attributes: { supported_features: 8192 } },
          'sensor.batt': { state: '82', attributes: {} },
        },
      },
    },
    byName: BY_NAME,
  });
  // 82 % maps onto the MDI 10 % step, like the hub's _battery_icon_name.
  const withBattery = build({ battery_sensor: { item: 'sensor.batt' } });
  assert.equal(withBattery.component('bFncRSec').hidden, false);
  assert.equal(ICON_MAP[withBattery.component('bFncRSec').attrs.txt], 'battery-80');
  // No sensor -> no header battery icon.
  assert.equal(build({}).component('bFncRSec').hidden, true);
});

test('tile icons take the entity state colour, like the hub', () => {
  const palette = devicePalette(GRID_HOST);
  const d = buildPreviewDisplay(layout('landscape'), 9, {
    type: 'grid',
    items: [
      { item: 'light.kitchen', name: 'On' },      // on  -> entity_on
      { item: 'switch.fan', name: 'Off' },        // off -> entity_off
      { item: 'light.gone', name: 'Missing' },    // not loaded -> palette text
      { item: 'light.kitchen', name: 'Override', color: 63488 },
    ],
  }, null, { state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME });
  assert.equal(d.component('g1Icon').attrs.pco, palette.entity_on);
  assert.equal(d.component('g2Icon').attrs.pco, palette.entity_off);
  assert.equal(d.component('g3Icon').attrs.pco, palette.text);
  assert.equal(d.component('g4Icon').attrs.pco, 63488);
});

test('row entries show the control their item type calls for', () => {
  const host = {
    hass: {
      states: {
        'light.kitchen': { state: 'on' },
        'cover.blind': { state: 'open', attributes: { current_position: 60 } },
        'number.level': { state: '42', attributes: { min: 0, max: 100, step: 1 } },
        'scene.movie': { state: '2024-01-01T00:00:00' },
      },
    },
  };
  const d = buildPreviewDisplay(layout('landscape'), 10, {
    type: 'row',
    items: [
      { item: 'light.kitchen', name: 'Light' },
      { item: 'cover.blind', name: 'Blind' },
      { item: 'number.level', name: 'Level' },
      { item: 'scene.movie', name: 'Movie' },
    ],
  }, null, { state: PREVIEW_STATE, host, byName: BY_NAME });

  const detail = ['BtnUp', 'BtnStop', 'BtnDown', 'Slider', 'SliderTxt', 'BtnText', 'Toggle'];
  const shown = (n) => detail.filter((s) => !d.component(`r${n}${s}`).hidden);
  assert.deepEqual(shown(1), ['Toggle']);                       // light
  assert.deepEqual(shown(2), ['BtnUp', 'BtnStop', 'BtnDown']);   // cover
  assert.deepEqual(shown(3), ['Slider', 'SliderTxt']);           // number
  assert.deepEqual(shown(4), ['BtnText']);                       // scene -> button
  // The value cells carry the entity's state.
  assert.equal(d.component('r1Toggle').attrs.val, 1);
  assert.equal(d.component('r3Slider').attrs.val, 42);
  assert.equal(d.component('r3SliderTxt').attrs.txt, '42');
});

test('row slots without a configured item are fully hidden', () => {
  const d = buildPreviewDisplay(layout('landscape'), 10, {
    type: 'row',
    items: [{ item: 'light.kitchen', name: 'Light' }],
  }, null, { state: PREVIEW_STATE, host: GRID_HOST, byName: BY_NAME });
  const names = ['Name', 'Icon', 'Overlay', 'BtnUp', 'BtnStop', 'BtnDown',
    'Slider', 'SliderTxt', 'BtnText', 'Toggle'];
  for (let n = 2; n <= 5; n += 1) {
    for (const suffix of names) {
      assert.equal(d.component(`r${n}${suffix}`).hidden, true, `r${n}${suffix} hidden`);
    }
  }
});

test('the media page never shows its unused page-level power button', () => {
  // The hub puts the power control on a header function button; the page's
  // own bPower is dead and must stay hidden whatever the player supports.
  const full = 128 | 16384 | 1 | 32768 | 262144 | 16 | 32 | 4;
  const host = {
    hass: { states: { 'media_player.tv': { state: 'playing', attributes: { supported_features: full } } } },
  };
  const d = buildPreviewDisplay(layout('landscape'), 14, {
    type: 'media', item: { item: 'media_player.tv' },
  }, null, { state: PREVIEW_STATE, host, byName: BY_NAME });
  assert.equal(d.component('bPower').hidden, true);
});

test('the notification popup shows an example notification instead of blank', () => {
  const d = buildPreviewDisplay(layout('landscape'), 4, { type: 'notify' }, null, {
    state: PREVIEW_STATE, host: {}, byName: BY_NAME,
  });
  // Without one the preview was empty: no icon, no text, no buttons.
  assert.equal(d.component('tIcon').hidden, false);
  assert.equal(ICON_MAP[d.component('tIcon').attrs.txt], 'information-outline');
  assert.match(d.component('tText').attrs.txt, /Example notification/);
  assert.equal(d.component('tText').hidden, false);
  // Buttons belong to the notification, not the panel: hidden when unset.
  assert.equal(d.component('bBtnLeft').hidden, true);
  assert.equal(d.component('bBtnRight').hidden, true);
});

test('the notification example follows the severity, icon and text settings', () => {
  const palette = devicePalette({});
  const critical = buildPreviewDisplay(layout('landscape'), 4, {
    type: 'notify', notif_type: 'critical',
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  assert.equal(ICON_MAP[critical.component('tIcon').attrs.txt], 'alert-octagon-outline');
  assert.equal(critical.component('tIcon').attrs.pco, palette.component_active);

  const warning = buildPreviewDisplay(layout('landscape'), 4, {
    type: 'notify', notif_type: 'warning',
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  assert.equal(ICON_MAP[warning.component('tIcon').attrs.txt], 'alert-outline');
  assert.equal(warning.component('tIcon').attrs.pco, palette.header_accent);

  const custom = buildPreviewDisplay(layout('landscape'), 4, {
    type: 'notify',
    notification: 'Garage door left open for 10 minutes.',
    icon: 'mdi:garage-open',
    btn_left: 'mdi:close',
    btn_right: 'mdi:check',
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME });
  assert.equal(custom.component('tText').attrs.txt, 'Garage door left open for 10 minutes.');
  assert.equal(custom.component('tText').attrs.font, 3);   // short text -> large
  assert.equal(ICON_MAP[custom.component('tIcon').attrs.txt], 'garage-open');
  assert.equal(custom.component('bBtnLeft').hidden, false);
  assert.equal(custom.component('bBtnRight').hidden, false);
});

test('longer notification text uses a smaller font, like the hub', () => {
  const font = (notification) => buildPreviewDisplay(layout('landscape'), 4, {
    type: 'notify', notification,
  }, null, { state: PREVIEW_STATE, host: {}, byName: BY_NAME }).component('tText').attrs.font;
  assert.equal(font('Short message.'), 3);
  assert.equal(font('x'.repeat(80)), 2);
  assert.equal(font('x'.repeat(200)), 1);
});
