import './support/browser.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  dateFormatOptions,
  displayModelOptions,
  logLevelOptions,
  timeFormatOptions,
} from '../../custom_components/nspanel_haui/frontend/constants.js';
import { fetchTranslations } from '../../custom_components/nspanel_haui/frontend/localize.js';
import { createApiClient } from '../../custom_components/nspanel_haui/frontend/api/client.js';

test('the device settings choose their option labels in the language loaded after import', async () => {
  const translations = {
    Critical: 'Kritisch',
    'European (standard)': 'Europäisch (Standard)',
    'Default (24-hour)': 'Standard (24 Stunden)',
    'Default (locale-based)': 'Standard (sprachabhängig)',
  };
  const hass = { fetchWithAuth: async () => ({ ok: true, json: async () => translations }) };

  await fetchTranslations(createApiClient(() => hass), 'de');

  assert.equal(logLevelOptions()[0].label, 'Kritisch');
  assert.equal(displayModelOptions()[0].label, 'Europäisch (Standard)');
  assert.equal(timeFormatOptions()[0].label, 'Standard (24 Stunden)');
  assert.equal(dateFormatOptions()[0].label, 'Standard (sprachabhängig)');
  // The values are what the device stores, so they never follow the language.
  assert.deepEqual(
    logLevelOptions().map((option) => option.value),
    ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
  );
});
