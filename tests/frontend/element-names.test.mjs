import './dom-shim.mjs';

import { test } from 'node:test';
import assert from 'node:assert/strict';

const names = [];
const origDefine = customElements.define.bind(customElements);
customElements.define = (name, cls, ...rest) => {
  names.push(name);
  return origDefine(name, cls, ...rest);
};

await import('../../custom_components/nspanel_haui/frontend/haui-editor.js');

test('editor only defines custom elements in the nspanel- namespace', () => {
  assert.ok(names.length > 0);
  const bad = names.filter((n) => !n.startsWith('nspanel-'));
  assert.deepEqual(bad, []);
});
