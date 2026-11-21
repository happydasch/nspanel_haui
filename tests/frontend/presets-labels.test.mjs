import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { presets, presetByKey } from '../../custom_components/nspanel_haui/frontend/presets.js';
import { fetchTranslations } from '../../custom_components/nspanel_haui/frontend/localize.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';

test('the quick start catalog carries the language loaded after the module was imported', async () => {
  const translations = {
    'Room panel': 'Raum-Panel',
    'One room: its lights, blind, thermostat and media, with a clock at night.':
      'Ein Raum: Licht, Rollladen, Thermostat und Medien, nachts mit Uhr.',
    Clock: 'Uhr',
    'Add an idle panel': 'Leerlauf-Panel hinzufügen',
  };
  const hass = { fetchWithAuth: async () => ({ ok: true, json: async () => translations }) };

  await fetchTranslations(createApiClient(() => hass), 'de');

  const room = presetByKey('room');
  assert.equal(presets()[0].label, 'Raum-Panel');
  assert.equal(
    room.description, 'Ein Raum: Licht, Rollladen, Thermostat und Medien, nachts mit Uhr.',
  );
  // The pages a setup creates carry that language too, not the import-time English.
  assert.ok(room.pages.some((page) => page.panel.title === 'Uhr'));
  assert.equal(
    room.toggles.find((toggle) => toggle.key === 'idle').label, 'Leerlauf-Panel hinzufügen',
  );
});
