/**
 * NSPanel HAUI - Nextion display model for the virtual panel.
 *
 * Holds what a Nextion display holds: the current page, every widget's
 * attributes, the `sysN` globals, global-scope widgets (which keep their
 * values across page changes), running timers and shapes drawn with
 * `xpic`/`cirs`/`cls`. The hub's commands and the HMI's own event code both
 * run through nextion-script.js against this model; nextion-view.js renders it.
 *
 * The layout comes from `layout_<orientation>.json`, written by
 * scripts/hmi_layout/gen_virtual_layout.py from the HMI files.
 */
import { runScript } from './nextion-script.js';

export const TYPE = Object.freeze({
  PAGE: 121,
  VARIABLE: 52,
  TEXT: 116,
  BUTTON: 98,
  DUAL_STATE: 53,
  PICTURE: 112,
  HOTSPOT: 109,
  SLIDER: 1,
  PROGRESS: 106,
  QR: 58,
  XFLOAT: 59,
  TIMER: 51,
});

const defaultScheduler = {
  every: (ms, fn) => setInterval(fn, ms),
  cancel: handle => clearInterval(handle),
};

// Components whose repaint paints nothing: hotspots are touch zones, a timer and
// a variable have no pixels. Their visibility change must not cut a drawn image.
const NON_PAINTING = new Set([TYPE.PAGE, TYPE.VARIABLE, TYPE.TIMER, TYPE.HOTSPOT]);

/** The identity of a fill: painting the same rectangle again replaces it. */
function fillKey(fill) {
  return `${fill.x},${fill.y},${fill.w},${fill.h}`;
}

/**
 * Split a fill around a rectangle a widget repaints.
 *
 * A widget repaints its own rectangle over the image, so the parts of the fill
 * inside it are gone and the parts outside survive - up to four rectangles.
 * Returns `[fill]` when the two do not overlap.
 */
function subtractRect(fill, rect) {
  const left = Math.max(fill.x, rect.x);
  const top = Math.max(fill.y, rect.y);
  const right = Math.min(fill.x + fill.w, rect.x + rect.w);
  const bottom = Math.min(fill.y + fill.h, rect.y + rect.h);
  if (left >= right || top >= bottom) return [fill];
  const pieces = [];
  const add = (x, y, w, h) => {
    if (w > 0 && h > 0) pieces.push({ ...fill, x, y, w, h });
  };
  add(fill.x, fill.y, fill.w, top - fill.y);
  add(fill.x, bottom, fill.w, fill.y + fill.h - bottom);
  add(fill.x, top, left - fill.x, bottom - top);
  add(right, top, fill.x + fill.w - right, bottom - top);
  return pieces;
}

export class NextionDisplay {
  /**
   * @param {object} layout - parsed layout JSON
   * @param {object} [opts]
   * @param {object} [opts.scheduler] - `{ every(ms, fn), cancel(handle) }` for timers
   * @param {function} [opts.onChange] - called after every change that needs a redraw
   * @param {function} [opts.onWarn] - called with unsupported-script messages
   */
  constructor(layout, opts = {}) {
    this.layout = layout;
    this.scheduler = opts.scheduler || defaultScheduler;
    this.onChange = opts.onChange || (() => {});
    this.onWarn = opts.onWarn || (msg => console.warn(`[virtual panel] ${msg}`));
    this.globals = { ...layout.globals };
    this.pageId = null;
    this.page = null;
    this.components = new Map(); // name -> { id, name, type, attrs, events, touch }
    this.byId = new Map();
    this.drawings = [];
    // The rectangles of the fills in `drawings`, so a refined image replaces
    // its own runs instead of scanning every drawing for each of the thousands
    // of runs a full pass sends.
    this._fillKeys = new Set();
    this.warnings = [];
    // Global-scope widgets keep their attributes across page changes; keyed
    // "<page>.<widget>".
    this._globalScope = new Map();
    this._timers = new Map();
    this._batch = 0;
    this._dirty = false;
    for (const [id, page] of Object.entries(layout.pages)) {
      for (const comp of page.components) {
        if (comp.attrs.vscope === 1) {
          this._globalScope.set(`${page.name}.${comp.name}`, { ...comp.attrs });
        }
      }
      page.id = Number(id);
    }
    this._pagesByName = new Map(Object.values(layout.pages).map(p => [p.name, p]));
  }

  // -- page lifecycle -------------------------------------------------------

  /** Switch to a page by id or name and run its Preinitialize/Postinitialize code. */
  gotoPage(idOrName) {
    const page = typeof idOrName === 'number' || /^\d+$/.test(String(idOrName))
      ? this.layout.pages[String(idOrName)]
      : this._pagesByName.get(idOrName);
    if (!page) {
      this.warn(`unknown page ${idOrName}`);
      return;
    }
    this.batch(() => {
      if (this.page) this._runEvent(this._pageComponent(), 'unload');
      this._stopTimers();
      this.page = page;
      this.pageId = page.id;
      this.drawings = [];
      this._fillKeys.clear();
      this.components = new Map();
      this.byId = new Map();
      for (const comp of page.components) {
        const stored = comp.attrs.vscope === 1 ? this._globalScope.get(`${page.name}.${comp.name}`) : null;
        const state = {
          id: comp.id,
          name: comp.name,
          type: comp.type,
          attrs: stored || { ...comp.attrs },
          events: comp.events,
          touch: true,
          pressed: false,
        };
        this.components.set(comp.name, state);
        this.byId.set(comp.id, state);
      }
      this._runEvent(this._pageComponent(), 'load');
      this._runEvent(this._pageComponent(), 'loadend');
      for (const comp of this.components.values()) {
        if (comp.type === TYPE.TIMER && comp.attrs.en) this._startTimer(comp);
      }
    });
  }

  _pageComponent() {
    return this.byId.get(0);
  }

  // -- commands -------------------------------------------------------------

  /** Run one or more hub commands (`send_command` / `send_commands`). */
  exec(commands) {
    const list = Array.isArray(commands) ? commands : [commands];
    this.batch(() => {
      for (const cmd of list) runScript(cmd, this._host());
    });
  }

  /** Group changes so `onChange` fires once. */
  batch(fn) {
    this._batch++;
    try {
      fn();
    } finally {
      this._batch--;
      if (this._batch === 0 && this._dirty) {
        this._dirty = false;
        this.onChange();
      }
    }
  }

  _changed() {
    if (this._batch > 0) this._dirty = true;
    else this.onChange();
  }

  warn(msg) {
    this.warnings.push(msg);
    if (this.warnings.length > 100) this.warnings.shift();
    this.onWarn(msg);
  }

  /** Look up a widget of the current page by name or id. */
  component(nameOrId) {
    if (typeof nameOrId === 'number') return this.byId.get(nameOrId);
    if (/^\d+$/.test(nameOrId)) return this.byId.get(Number(nameOrId));
    return this.components.get(nameOrId);
  }

  /**
   * Answer a hub read request (`req_val` / `req_txt`) like the firmware does.
   *
   * @param {string} kind - "val" or "txt"
   * @param {string} name - widget name on the current page
   * @returns {string} the `esphome.read_response` payload (JSON)
   */
  readResponse(kind, name) {
    const comp = this.component(name);
    if (!comp) throw new Error(`unknown widget ${name}`);
    return kind === 'val'
      ? JSON.stringify({ name, type: 'number', value: comp.attrs.val })
      : JSON.stringify({ name, type: 'text', value: comp.attrs.txt });
  }

  // -- script host ----------------------------------------------------------

  _host() {
    return {
      getAttr: ref => this.getAttr(ref),
      setAttr: (ref, value) => this.setAttr(ref, value),
      command: (name, args) => this.command(name, args),
      warn: msg => this.warn(msg),
    };
  }

  _target(ref) {
    if (ref.page && ref.page !== this.page?.name) {
      const stored = this._globalScope.get(`${ref.page}.${ref.comp}`);
      if (!stored) throw new Error(`${ref.page}.${ref.comp} is not a global-scope widget`);
      return { attrs: stored };
    }
    const comp = this.component(ref.comp);
    if (!comp) throw new Error(`unknown widget ${ref.comp}`);
    return comp;
  }

  getAttr(ref) {
    if (ref.global !== undefined) {
      if (!(ref.global in this.globals)) throw new Error(`unknown variable ${ref.global}`);
      return this.globals[ref.global];
    }
    const target = this._target(ref);
    if (!(ref.attr in target.attrs)) throw new Error(`${ref.comp} has no attribute ${ref.attr}`);
    return target.attrs[ref.attr];
  }

  setAttr(ref, value) {
    if (ref.global !== undefined) {
      // The display rejects a variable its Program.s does not declare.
      if (!(ref.global in this.globals)) throw new Error(`unknown variable ${ref.global}`);
      this.globals[ref.global] = value;
      return;
    }
    const target = this._target(ref);
    if (!(ref.attr in target.attrs)) throw new Error(`${ref.comp} has no attribute ${ref.attr}`);
    const old = target.attrs[ref.attr];
    target.attrs[ref.attr] = typeof old === 'number' && typeof value === 'string'
      ? (parseInt(value, 10) || 0)
      : value;
    if (target.type === TYPE.TIMER && ref.attr === 'en') {
      if (value) this._startTimer(target);
      else this._stopTimer(target);
    }
    if (!ref.page || ref.page === this.page?.name) this._clipFillsUnder(target);
    this._changed();
  }

  /** Whether a widget's repaint paints its rectangle; hidden and non-drawing widgets do not. */
  _draws(comp) {
    return !comp.hidden && !NON_PAINTING.has(comp.type);
  }

  /**
   * Paint a widget's rectangle over a drawn image: keep the parts of a fill
   * outside it.
   *
   * The hub's image program paints after the page's widgets, but the panel does
   * not keep the image on top: a widget the hub updates (a clock tick, a value,
   * a visibility change, a `ref`) repaints its own rectangle over it. Only the
   * image outside that rectangle survives, which is why a fill is split instead
   * of dropped - a whole fill would take the picture around the widget with it.
   * A hidden widget and one without pixels (a hotspot, a timer, a variable)
   * paint nothing, so the image under them stays.
   */
  _clipFillsUnder(comp) {
    if (!this._draws(comp)) return;
    const { x, y, w, h } = comp.attrs;
    if (![x, y, w, h].every(Number.isFinite) || w <= 0 || h <= 0) return;
    const rect = { x, y, w, h };
    const next = [];
    let changed = false;
    for (const drawing of this.drawings) {
      if (drawing.kind !== 'fill') {
        next.push(drawing);
        continue;
      }
      const pieces = subtractRect(drawing, rect);
      if (pieces.length !== 1 || pieces[0] !== drawing) changed = true;
      next.push(...pieces);
    }
    if (!changed) return;
    this.drawings = next;
    this._fillKeys = new Set(next.filter(d => d.kind === 'fill').map(fillKey));
  }

  command(name, args) {
    switch (name) {
      case 'vis': {
        const visible = Boolean(args[1]);
        if (args[0] === '255') {
          for (const comp of this.components.values()) {
            comp.hidden = !visible;
            this._clipFillsUnder(comp);
          }
        } else {
          const comp = this._commandTarget(args[0]);
          comp.hidden = !visible;
          this._clipFillsUnder(comp);
        }
        this._changed();
        return;
      }
      case 'tsw': {
        const enabled = Boolean(args[1]);
        if (args[0] === '255') {
          for (const comp of this.components.values()) comp.touch = enabled;
        } else {
          this._commandTarget(args[0]).touch = enabled;
        }
        return;
      }
      case 'click':
        this.touchEvent(this._commandTarget(args[0]), args[1] ? 'down' : 'up');
        return;
      case 'page':
        this.gotoPage(args[0]);
        return;
      case 'xpic': {
        const [x, y, w, h, sx, sy, pic] = args;
        this.drawings.push({ kind: 'xpic', x, y, w, h, sx, sy, pic });
        this.drawings = this.drawings.filter(
          (d, i, all) => d.kind !== 'xpic' || !all.slice(i + 1).some(
            n => n.kind === 'xpic' && n.x === d.x && n.y === d.y && n.w === d.w && n.h === d.h,
          ),
        );
        this._changed();
        return;
      }
      case 'cirs': {
        const [x, y, r, color] = args;
        this.drawings.push({ kind: 'cirs', x, y, r, color });
        this._changed();
        return;
      }
      case 'fill': {
        // The hub's image program: `fill x,y,w,h,color` — width and height, not
        // a second corner (the Nextion instruction set's own example:
        // `fill 20,20,150,50,1024` paints 150x50 from (20,20)). Painting the
        // same rectangle again replaces the previous fill, so a refined image
        // does not accumulate runs; the key set keeps that a lookup per run
        // instead of a scan of every drawing.
        const [x, y, w, h, color] = args;
        const fill = { kind: 'fill', x, y, w, h, color };
        const key = fillKey(fill);
        if (this._fillKeys.has(key)) {
          this.drawings = this.drawings.filter(
            d => d.kind !== 'fill' || d.x !== x || d.y !== y || d.w !== w || d.h !== h,
          );
        }
        this.drawings.push(fill);
        this._fillKeys.add(key);
        this._changed();
        return;
      }
      case 'ref': {
        // Redrawing a widget paints its rectangle over the image, so a fill
        // that overlaps it is split around it (the picture outside stays); a
        // shape drawn inside the widget goes completely.
        const comp = this._commandTarget(args[0]);
        this._clipFillsUnder(comp);
        if (this._draws(comp)) {
          const { x, y, w, h } = comp.attrs;
          this.drawings = this.drawings.filter(
            d => d.kind === 'fill' || !(d.x >= x && d.x < x + w && d.y >= y && d.y < y + h),
          );
        }
        this._changed();
        return;
      }
      case 'sendme':
      case 'doevents':
        return;
      default:
        this.warn(`unsupported command: ${name}`);
    }
  }

  _commandTarget(nameOrId) {
    const comp = this.component(String(nameOrId));
    if (!comp) throw new Error(`unknown widget ${nameOrId}`);
    return comp;
  }

  /**
   * Whether a press repaints the widget's rectangle.
   *
   * Only a button draws a pressed look (``fillAttrs`` takes its "2" set), and
   * only when that set differs from the normal one. A touch on a text, a slider
   * or a button whose pressed colours match its normal ones paints nothing, so
   * it must not cut a drawn image.
   */
  _pressRepaints(comp) {
    if (!this._draws(comp) || comp.type !== TYPE.BUTTON) return false;
    const a = comp.attrs;
    return a.bco2 !== a.bco || a.pco2 !== a.pco || a.pic2 !== a.pic || a.picc2 !== a.picc;
  }

  /** Press (`down`) or release (`up`) a widget: its pressed look and its Touch Press/Release code. */
  touchEvent(comp, edge) {
    comp.pressed = edge === 'down';
    if (this._pressRepaints(comp)) this._clipFillsUnder(comp);
    this._runEvent(comp, edge);
    this._changed();
  }

  _runEvent(comp, event) {
    const code = comp?.events?.[event];
    if (code) runScript(code, this._host());
  }

  // -- timers ---------------------------------------------------------------

  _startTimer(comp) {
    if (this._timers.has(comp.name)) return;
    const page = this.page;
    const handle = this.scheduler.every(Math.max(comp.attrs.tim || 50, 50), () => {
      if (this.page !== page) return;
      this.batch(() => this._runEvent(comp, 'timer'));
    });
    this._timers.set(comp.name, handle);
  }

  _stopTimer(comp) {
    const handle = this._timers.get(comp.name);
    if (handle !== undefined) {
      this.scheduler.cancel(handle);
      this._timers.delete(comp.name);
    }
  }

  _stopTimers() {
    for (const handle of this._timers.values()) this.scheduler.cancel(handle);
    this._timers.clear();
  }

  /** Stop every timer; call when the preview closes. */
  dispose() {
    this._stopTimers();
  }
}
