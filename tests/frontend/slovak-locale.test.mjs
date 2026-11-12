import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { fetchTranslations, getLanguage, t } from '../../custom_components/nspanel_haui/frontend/localize.js';
import { LOCALE_OPTIONS } from '../../custom_components/nspanel_haui/frontend/constants.js';

test('Slovak HA language loads the real editor catalog', async () => {
  for (const language of ['sk', 'sk-SK', 'sk_SK', 'SK-sk']) {
    assert.equal(getLanguage({ language }), 'sk');
  }
  assert.ok(LOCALE_OPTIONS.some(({ value, label }) => value === 'sk_SK' && label === 'Slovenčina'));
  const catalog = JSON.parse(await readFile(new URL('../../custom_components/nspanel_haui/haui/locale/sk.json', import.meta.url), 'utf8'));
  await fetchTranslations({ editor: { translations: async (language) => {
    assert.equal(language, 'sk');
    return catalog.text;
  } } }, getLanguage({ language: 'sk' }));
  assert.equal(t('Settings'), 'Nastavenia');
  assert.equal(t('Save'), 'Uložiť');
});
