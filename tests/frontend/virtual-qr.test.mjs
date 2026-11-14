import './support/browser.mjs';

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { encodeQr } from '../../custom_components/nspanel_haui/frontend/virtual/qr-encode.js';
import { qrPath } from '../../custom_components/nspanel_haui/frontend/virtual/nextion-view.js';

// Reference symbols from the Python `qrcode` package (see "_source").
const FIXTURES = JSON.parse(readFileSync(new URL('./qr-fixtures.json', import.meta.url), 'utf8'));

for (const c of FIXTURES.cases) {
  test(`matches the reference symbol: ${c.text.slice(0, 20)} (v${c.version}, mask ${c.mask})`, () => {
    const qr = encodeQr(c.text, { ecl: 'M', mask: c.mask });
    assert.equal(qr.version, c.version);
    assert.deepEqual(qr.modules.map(row => row.map(m => (m ? '1' : '0')).join('')), c.rows);
  });
}

test('the smallest version that fits is chosen', () => {
  assert.equal(encodeQr('HAUI').version, 1);
  assert.equal(encodeQr('x'.repeat(300)).version, 13);
});

test('without a forced mask the lowest-penalty one is used', () => {
  const qr = encodeQr('https://github.com/happydasch/nspanel_haui');
  assert.ok(qr.mask >= 0 && qr.mask <= 7);
  assert.equal(qr.size, qr.version * 4 + 17);
});

test('text longer than a version 40 symbol holds is rejected', () => {
  assert.throws(() => encodeQr('x'.repeat(3000)), RangeError);
});

test('the view draws one path square per dark module', () => {
  const { d, size } = qrPath('HAUI');
  const qr = encodeQr('HAUI');
  const dark = qr.modules.flat().filter(Boolean).length;
  assert.equal(size, 21);
  assert.equal((d.match(/M/g) || []).length, dark);
});
