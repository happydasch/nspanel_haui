import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { editorStyles } from '../../custom_components/nspanel_haui/frontend/styles.js';

test('gesture swipe pills use a distinct surface from their entry background', () => {
  assert.match(
    editorStyles.cssText,
    /\.haui-gesture-swipes \.haui-pill\s*\{\s*background: var\(--haui-card-background\);/,
  );
});

test('side-stack card summaries stay on one ellipsized line beside their controls', () => {
  assert.match(
    editorStyles.cssText,
    /\.haui-device-side-stack \.haui-surface-heading-copy p\s*\{[^}]*white-space: nowrap;/,
  );
});
