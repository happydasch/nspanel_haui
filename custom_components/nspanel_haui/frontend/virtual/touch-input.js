/**
 * NSPanel HAUI - touch input for the virtual panel.
 *
 * Turns a press / move / release in display coordinates into what a real
 * panel does:
 *
 * - the Nextion: the topmost visible, touch-enabled widget under the finger
 *   gets the touch; its Touch Press/Release code runs, buttons show their
 *   pressed state, sliders follow the finger and dual-state buttons toggle;
 * - the firmware (esphome/nspanel_haui/display.yaml, scripts_interaction.yaml):
 *   `esphome.component` "page,id,state" when the widget's Send Component ID
 *   covers that edge, `esphome.touch_start` / `esphome.touch_end` with the
 *   start and end coordinates, and `esphome.gesture` for a swipe.
 */
import { TYPE } from './nextion-display.js';

// Send Component ID ("sendkey"): bit 0 = on press, bit 1 = on release.
const SEND_ON_PRESS = 1;
const SEND_ON_RELEASE = 2;

const NOT_TOUCHABLE = new Set([TYPE.PAGE, TYPE.VARIABLE, TYPE.TIMER]);

// process_touch_gesture thresholds.
const SWIPE = { minDistanceX: 200, minDistanceY: 150, maxAngle: 20, borderMargin: 40 };

/**
 * Detect a swipe like the firmware's process_touch_gesture.
 *
 * @returns {string|null} "swipe_left" / "swipe_right" / "swipe_up" / "swipe_down"
 */
export function detectGesture(x1, y1, x2, y2, layout) {
  if (!x1 || !y1 || !x2 || !y2) return null;
  const visibleWidth = layout.visible_width;
  const screenH = layout.height;
  const isHorizontal = Math.abs(x2 - x1) > Math.abs(y2 - y1);
  const nearBorder = x1 < SWIPE.borderMargin || y1 < SWIPE.borderMargin
    || x1 > visibleWidth - SWIPE.borderMargin || y1 > screenH - SWIPE.borderMargin;
  const dx = Math.abs(x2 - x1);
  const dy = Math.abs(y2 - y1);
  const distance = Math.trunc(Math.sqrt(dx * dx + dy * dy));
  const angle = Math.trunc((Math.atan2(dy, dx) * 180) / Math.PI);
  const farEnough = isHorizontal ? distance >= SWIPE.minDistanceX : distance >= SWIPE.minDistanceY;
  const straightEnough = isHorizontal
    ? Math.abs(angle) <= SWIPE.maxAngle
    : Math.abs(angle) >= 90 - SWIPE.maxAngle;
  if (!nearBorder || !farEnough || !straightEnough) return null;
  if (isHorizontal) return x2 > x1 ? 'swipe_right' : 'swipe_left';
  return y2 > y1 ? 'swipe_down' : 'swipe_up';
}

/**
 * Map a pointer position to display coordinates.
 *
 * @param {number} clientX
 * @param {number} clientY
 * @param {{left: number, top: number, width: number, height: number}} rect - the rendered screen
 * @param {object} layout
 */
export function toDisplayCoords(clientX, clientY, rect, layout) {
  const x = Math.round(((clientX - rect.left) * layout.visible_width) / rect.width);
  const y = Math.round(((clientY - rect.top) * layout.height) / rect.height);
  // The firmware treats 0 as "no touch".
  return {
    x: Math.min(Math.max(x, 1), layout.width - 1),
    y: Math.min(Math.max(y, 1), layout.height - 1),
  };
}

function contains(comp, x, y) {
  const a = comp.attrs;
  return x >= a.x && x < a.x + a.w && y >= a.y && y < a.y + a.h;
}

export class TouchInput {
  /**
   * @param {NextionDisplay} display
   * @param {function(string, string): void} send - sends a device event to the hub
   */
  constructor(display, send) {
    this.display = display;
    this.send = send;
    this._touch = null;
  }

  /** The widget a touch at (x, y) goes to: the topmost hit, else the page. */
  hitTest(x, y) {
    const hits = [...this.display.components.values()].filter(c => c.id !== 0
      && !NOT_TOUCHABLE.has(c.type) && !c.hidden && c.touch && contains(c, x, y));
    hits.sort((a, b) => b.id - a.id);
    return hits[0] || this.display.component(0);
  }

  press(x, y) {
    if (this._touch) this.release(this._touch.last.x, this._touch.last.y);
    const comp = this.hitTest(x, y);
    const page = this.display.pageId;
    this._touch = { comp, page, start: { x, y }, last: { x, y } };
    this.display.batch(() => {
      if (comp.type === TYPE.DUAL_STATE) this.display.setAttr({ comp: comp.name, attr: 'val' }, comp.attrs.val ? 0 : 1);
      if (comp.type === TYPE.SLIDER) this._slide(comp, x, y);
      this.display.touchEvent(comp, 'down');
    });
    if (comp.attrs.sendkey & SEND_ON_PRESS) {
      this.send('esphome.component', `${page},${comp.id},1`);
      this.send('esphome.touch_start', '1');
    }
    this.send('esphome.touch_start', '');
  }

  move(x, y) {
    if (!this._touch) return;
    this._touch.last = { x, y };
    const { comp } = this._touch;
    if (comp.type === TYPE.SLIDER && this.display.pageId === this._touch.page) {
      this.display.batch(() => this._slide(comp, x, y));
    }
  }

  release(x, y) {
    if (!this._touch) return;
    const { comp, page, start } = this._touch;
    this._touch.last = { x, y };
    this._touch = null;
    // The page may have changed during the touch (a press can navigate).
    if (this.display.pageId === page) {
      this.display.touchEvent(comp, 'up');
      if (comp.attrs.sendkey & SEND_ON_RELEASE) this.send('esphome.component', `${page},${comp.id},0`);
    }
    this.send('esphome.touch_end', `${start.x},${start.y},${x},${y}`);
    const gesture = detectGesture(start.x, start.y, x, y, this.display.layout);
    if (gesture) this.send('esphome.gesture', gesture);
  }

  /** Abandon a touch without a release (pointer lost); still ends it for the hub. */
  cancel() {
    if (this._touch) this.release(this._touch.last.x, this._touch.last.y);
  }

  _slide(comp, x, y) {
    const a = comp.attrs;
    const fraction = a.mode === 1 ? (a.y + a.h - y) / a.h : (x - a.x) / a.w;
    const span = a.maxval - a.minval;
    const val = Math.round(a.minval + Math.min(Math.max(fraction, 0), 1) * span);
    if (val !== a.val) this.display.setAttr({ comp: comp.name, attr: 'val' }, val);
  }
}
