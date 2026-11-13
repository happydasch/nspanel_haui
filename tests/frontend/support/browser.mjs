// Test rules: never inspect Lit template internals, pin CSS/pixel geometry, or read component internals; assert real DOM behavior instead.
import { Window } from 'happy-dom';

export const window = new Window({ url: 'http://localhost/' });
window.happyDOM.settings.disableCSSFileLoading = true;

const browserGlobals = [
  'window', 'document', 'HTMLElement', 'customElements', 'CSSStyleSheet', 'ShadowRoot',
  'Node', 'Element', 'Event', 'CustomEvent', 'KeyboardEvent', 'MouseEvent', 'PointerEvent', 'MutationObserver', 'getComputedStyle',
  'requestAnimationFrame', 'cancelAnimationFrame', 'location', 'localStorage', 'Document',
  'DocumentFragment', 'Text', 'Comment', 'EventTarget', 'DOMParser', 'navigator', 'CSS',
];
for (const key of browserGlobals) {
  Object.defineProperty(globalThis, key, {
    configurable: true,
    writable: true,
    value: key === 'window' ? window : window[key],
  });
}

const listeners = new WeakMap();
const addEventListener = window.EventTarget.prototype.addEventListener;
const removeEventListener = window.EventTarget.prototype.removeEventListener;
window.EventTarget.prototype.addEventListener = function (type, listener, options) {
  if (listener) {
    const registered = listeners.get(this) || new Map();
    const entries = registered.get(type) || new Set();
    entries.add(listener);
    registered.set(type, entries);
    listeners.set(this, registered);
  }
  return addEventListener.call(this, type, listener, options);
};
window.EventTarget.prototype.removeEventListener = function (type, listener, options) {
  listeners.get(this)?.get(type)?.delete(listener);
  return removeEventListener.call(this, type, listener, options);
};

export function eventListeners(element) {
  return listeners.get(element) || new Map();
}

export function resetBrowser() {
  document.body.replaceChildren();
  localStorage.clear();
}
