/**
 * A recording 2D context for the test DOM.
 *
 * happy-dom has no canvas, so `getContext('2d')` answers null and the virtual
 * panel would paint no picture at all. This installs the smallest context the
 * view uses - a fill colour and `fillRect` - and records what it was asked to
 * paint, so a test asserts the picture itself (`paintedFills`) instead of the
 * internals that produced it.
 */
import { window } from './browser.mjs';

/** Every rectangle a canvas' context was asked to fill, in paint order. */
const painted = new WeakMap();

function recordingContext(canvas) {
  const context = {
    fillStyle: '#000000',
    fillRect(x, y, w, h) {
      const runs = painted.get(canvas) || [];
      runs.push({ x, y, w, h, fill: context.fillStyle });
      painted.set(canvas, runs);
    },
    clearRect() {
      painted.set(canvas, []);
    },
  };
  return context;
}

window.HTMLCanvasElement.prototype.getContext = function getContext(kind) {
  if (kind !== '2d') return null;
  const key = '__hauiTestContext';
  if (!this[key]) this[key] = recordingContext(this);
  return this[key];
};

/**
 * What one canvas paints, in display pixels relative to its own top-left corner.
 *
 * @param {HTMLCanvasElement} canvas
 * @returns {Array<{x: number, y: number, w: number, h: number, fill: string}>}
 */
export function paintedFills(canvas) {
  return [...(painted.get(canvas) || [])];
}

/** Forget what a canvas painted, so a test can tell a repaint from a stale layer. */
export function resetPainted(canvas) {
  painted.set(canvas, []);
}
