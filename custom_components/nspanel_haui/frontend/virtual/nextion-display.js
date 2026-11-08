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
    this.fill = null;
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
      this.fill = null;
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
    this._changed();
  }

  command(name, args) {
    switch (name) {
      case 'vis': {
        const visible = Boolean(args[1]);
        if (args[0] === '255') {
          for (const comp of this.components.values()) comp.hidden = !visible;
        } else {
          this._commandTarget(args[0]).hidden = !visible;
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
      case 'cls':
        this.fill = args[0];
        this.drawings = [];
        this._changed();
        return;
      case 'ref': {
        // Redrawing a widget paints over shapes drawn on top of it.
        const { x, y, w, h } = this._commandTarget(args[0]).attrs;
        const before = this.drawings.length;
        this.drawings = this.drawings.filter(d => !(d.x >= x && d.x < x + w && d.y >= y && d.y < y + h));
        if (this.drawings.length !== before) this._changed();
        return;
      }
      case 'sendme':
      case 'doevents':
      case 'printh':
      case 'prints':
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

  /** Press (`down`) or release (`up`) a widget: its pressed look and its Touch Press/Release code. */
  touchEvent(comp, edge) {
    comp.pressed = edge === 'down';
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
