import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { browserUrl } from '../../scripts/preview_gallery/capture.mjs';

function makeProfile() {
  return mkdtempSync(join(tmpdir(), 'haui-capture-test-'));
}

test('Chrome startup reports an early exit and stderr diagnostics', async () => {
  const profile = makeProfile();
  try {
    await assert.rejects(
      browserUrl(profile, Promise.resolve({ code: 1, signal: null }), () => 'sandbox denied', '/fake/chrome'),
      /\/fake\/chrome exited before creating DevToolsActivePort \(code 1, signal null\)[\s\S]*sandbox denied/,
    );
  } finally {
    rmSync(profile, { recursive: true, force: true });
  }
});

test('Chrome startup timeout reports the missing endpoint and stderr', async () => {
  const profile = makeProfile();
  try {
    await assert.rejects(
      browserUrl(profile, new Promise(() => {}), () => 'startup diagnostic', '/fake/chrome', 20),
      /did not expose DevToolsActivePort within 20 ms[\s\S]*startup diagnostic/,
    );
  } finally {
    rmSync(profile, { recursive: true, force: true });
  }
});

test('Chrome startup accepts its DevTools endpoint', async () => {
  const profile = makeProfile();
  try {
    writeFileSync(join(profile, 'DevToolsActivePort'), '9222\n/devtools/browser/test\n');
    assert.equal(
      await browserUrl(profile, new Promise(() => {}), () => '', '/fake/chrome', 100),
      'ws://127.0.0.1:9222/devtools/browser/test',
    );
  } finally {
    rmSync(profile, { recursive: true, force: true });
  }
});
