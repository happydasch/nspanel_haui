// Minimal browser globals so the vendored Lit bundle can be imported in Node.
// Import this before any editor module that pulls in Lit.
globalThis.HTMLElement ??= class {};
if (!globalThis.customElements) {
  // Records definitions so tests can reach element classes by tag name, and
  // define HA's elements to simulate HA loading them.
  const defined = new Map();
  const waiting = new Map();
  globalThis.customElements = {
    define(name, cls) {
      defined.set(name, cls);
      (waiting.get(name) || []).forEach((resolve) => resolve(cls));
      waiting.delete(name);
    },
    get(name) { return defined.get(name); },
    whenDefined(name) {
      if (defined.has(name)) return Promise.resolve(defined.get(name));
      return new Promise((resolve) => {
        if (!waiting.has(name)) waiting.set(name, []);
        waiting.get(name).push(resolve);
      });
    },
  };
}
globalThis.document ??= {
  createTreeWalker() { return {}; },
  createComment() { return {}; },
  createElement() { return {}; },
  querySelectorAll() { return []; },
  addEventListener() {},
  removeEventListener() {},
};
globalThis.addEventListener ??= () => {};
globalThis.window ??= globalThis;
