/**
 * NSPanel HAUI - renders a NextionDisplay (nextion-display.js) as HTML.
 *
 * Every visible widget of the current page becomes an absolutely positioned
 * element at its Nextion pixel geometry, stacked in widget-id order like the
 * display draws them. The caller scales the result to fit.
 *
 * Icons are characters of the display's icon font (U+E000 and up); they are
 * drawn with Home Assistant's <ha-icon> through `iconName(char)`, which maps a
 * character back to its MDI name.
 */
import { html, nothing } from '../lit-import.js';
import { rgb565ToHex } from '../color-utils.js';
import { TYPE } from './nextion-display.js';
import { encodeQr } from './qr-encode.js';

// Nextion font sizes are line heights; Roboto's glyphs fill about 85 % of one.
const FONT_SCALE = 0.85;
const NO_PICTURE = 65535;

const ALIGN_X = ['flex-start', 'center', 'flex-end'];
const ALIGN_Y = ['flex-start', 'center', 'flex-end'];
const TEXT_ALIGN = ['left', 'center', 'right'];

export function color(value) {
  return rgb565ToHex(value);
}

function isIconChar(ch) {
  const cp = ch.codePointAt(0);
  return cp >= 0xe000 && cp <= 0xf8ff;
}

/**
 * Split widget text into plain-text and icon segments.
 *
 * @returns {Array<{text: string}|{icon: string|null, char: string}>}
 */
export function textSegments(text, iconName) {
  const segments = [];
  let plain = '';
  for (const ch of String(text ?? '')) {
    const icon = iconName(ch);
    if (isIconChar(ch) || icon) {
      if (plain) segments.push({ text: plain });
      plain = '';
      segments.push({ icon, char: ch });
    } else {
      plain += ch;
    }
  }
  if (plain) segments.push({ text: plain });
  return segments;
}

/** Format an XFloat value: `vvs1` decimals, `vvs0` integer digits (0 = as needed). */
export function formatXFloat(attrs) {
  const decimals = attrs.vvs1 || 0;
  const negative = attrs.val < 0;
  const scaled = Math.abs(attrs.val) / 10 ** decimals;
  let [intPart, frac] = scaled.toFixed(decimals).split('.');
  if (attrs.vvs0) intPart = intPart.padStart(attrs.vvs0, '0').slice(-attrs.vvs0);
  return `${negative ? '-' : ''}${intPart}${frac !== undefined ? `.${frac}` : ''}`;
}

/** The state-dependent fill attributes of a widget: pressed buttons and dual-state val=1 use the "2" set. */
function fillAttrs(comp) {
  const a = comp.attrs;
  const alt = (comp.type === TYPE.BUTTON && comp.pressed) || (comp.type === TYPE.DUAL_STATE && a.val);
  return alt
    ? { sta: a.sta, bco: a.bco2, pco: a.pco2, pic: a.pic2, picc: a.picc2 }
    : { sta: a.sta, bco: a.bco, pco: a.pco, pic: a.pic, picc: a.picc };
}

/**
 * CSS background for a widget fill: `sta` 0 crops the full-screen picture
 * `picc` at the widget's position, 1 is the solid colour `bco`, 2 draws picture
 * `pic` at the widget's origin, 3 is transparent.
 */
export function backgroundStyle(fill, attrs, pictureUrl) {
  if (fill.sta === 0 && fill.picc !== undefined && fill.picc !== NO_PICTURE) {
    return `background:url(${pictureUrl(fill.picc)}) -${attrs.x}px -${attrs.y}px no-repeat;`;
  }
  if (fill.sta === 1) return `background:${color(fill.bco)};`;
  if (fill.sta === 2 && fill.pic !== undefined && fill.pic !== NO_PICTURE) {
    return `background:url(${pictureUrl(fill.pic)}) 0 0 no-repeat;`;
  }
  return '';
}

function fontStyle(layout, fontId) {
  const font = layout.fonts[fontId] || layout.fonts[0];
  return `font-family:${font.family},sans-serif;font-weight:${font.weight};`
    + `font-size:${Math.round(font.size * FONT_SCALE)}px;line-height:${font.size}px;`
    + `--mdc-icon-size:${Math.round(font.size * FONT_SCALE)}px;`;
}

function renderText(segments) {
  return segments.map(seg => (seg.text !== undefined
    ? html`<span>${seg.text}</span>`
    : seg.icon
      ? html`<ha-icon class="vp-icon" icon="mdi:${seg.icon}"></ha-icon>`
      : html`<span class="vp-missing-icon" title="U+${seg.char.codePointAt(0).toString(16)}">□</span>`));
}

function box(attrs) {
  return `left:${attrs.x}px;top:${attrs.y}px;width:${attrs.w}px;height:${attrs.h}px;`;
}

function renderTextWidget(comp, layout, ctx, text) {
  const a = comp.attrs;
  const fill = fillAttrs(comp);
  const style = box(a) + backgroundStyle(fill, a, ctx.pictureUrl) + fontStyle(layout, a.font)
    + `color:${color(fill.pco)};justify-content:${ALIGN_X[a.xcen] || 'flex-start'};`
    + `align-items:${ALIGN_Y[a.ycen] || 'flex-start'};text-align:${TEXT_ALIGN[a.xcen] || 'left'};`
    + `white-space:${a.isbr ? 'pre-wrap' : 'pre'};`
    + (a.spax ? `letter-spacing:${a.spax}px;` : '');
  return html`<div class="vp-widget vp-text" data-comp=${comp.id} style=${style}><div class="vp-text-inner">${renderText(textSegments(text, ctx.iconName))}</div></div>`;
}

function renderSlider(comp, ctx) {
  const a = comp.attrs;
  const span = Math.max(a.maxval - a.minval, 1);
  const pct = Math.min(100, Math.max(0, ((a.val - a.minval) / span) * 100));
  const vertical = a.mode === 1;
  const track = backgroundStyle({ sta: a.sta, bco: a.bco, pic: a.pic, picc: a.picc }, a, ctx.pictureUrl);
  const fillColor = a.bco1 !== undefined ? `background:${color(a.bco1)};` : '';
  const fill = vertical
    ? `left:0;bottom:0;width:100%;height:${pct}%;${fillColor}`
    : `left:0;top:0;height:100%;width:${pct}%;${fillColor}`;
  let cursor = nothing;
  if (a.wid > 0 && a.hig > 0) {
    const pos = vertical
      ? `left:calc(50% - ${a.wid / 2}px);bottom:calc(${pct}% - ${a.hig / 2}px);`
      : `top:calc(50% - ${a.hig / 2}px);left:calc(${pct}% - ${a.wid / 2}px);`;
    cursor = html`<div class="vp-slider-cursor" style="${pos}width:${a.wid}px;height:${a.hig}px;background:${color(a.pco)};"></div>`;
  }
  return html`<div class="vp-widget vp-slider" data-comp=${comp.id} style="${box(a)}${track}"><div class="vp-slider-fill" style=${fill}></div>${cursor}</div>`;
}

function renderProgress(comp) {
  const a = comp.attrs;
  const pct = Math.min(100, Math.max(0, a.val));
  const fill = a.dez ? `bottom:0;left:0;width:100%;height:${pct}%;` : `top:0;left:0;height:100%;width:${pct}%;`;
  return html`<div class="vp-widget" data-comp=${comp.id} style="${box(a)}background:${color(a.bco)};"><div class="vp-slider-fill" style="${fill}background:${color(a.pco)};"></div></div>`;
}

function renderPicture(comp, ctx) {
  const a = comp.attrs;
  if (a.pic === undefined || a.pic === NO_PICTURE) return nothing;
  return html`<div class="vp-widget" data-comp=${comp.id} style="${box(a)}background:url(${ctx.pictureUrl(a.pic)}) 0 0 no-repeat;"></div>`;
}

const qrPathCache = new Map();

/** SVG path of a QR code's dark modules (one unit per module), and its size. */
export function qrPath(text) {
  let entry = qrPathCache.get(text);
  if (!entry) {
    const qr = encodeQr(text);
    let d = '';
    qr.modules.forEach((row, y) => row.forEach((dark, x) => { if (dark) d += `M${x} ${y}h1v1h-1z`; }));
    entry = { d, size: qr.size };
    if (qrPathCache.size > 50) qrPathCache.clear();
    qrPathCache.set(text, entry);
  }
  return entry;
}

function renderQr(comp) {
  const a = comp.attrs;
  const style = `${box(a)}background:${color(a.bco)};`;
  if (!a.txt) return html`<div class="vp-widget" data-comp=${comp.id} style=${style}></div>`;
  const { d, size } = qrPath(a.txt);
  // One module of quiet zone, like the display draws.
  return html`<div class="vp-widget vp-qr" data-comp=${comp.id} title=${a.txt} style=${style}><svg viewBox="-1 -1 ${size + 2} ${size + 2}" width="100%" height="100%" shape-rendering="crispEdges"><path d=${d} fill=${color(a.pco)}></path></svg></div>`;
}

function renderWidget(comp, layout, ctx) {
  switch (comp.type) {
    case TYPE.TEXT:
    case TYPE.BUTTON:
    case TYPE.DUAL_STATE:
      return renderTextWidget(comp, layout, ctx, comp.attrs.txt);
    case TYPE.XFLOAT:
      return renderTextWidget(comp, layout, ctx, formatXFloat(comp.attrs));
    case TYPE.SLIDER:
      return renderSlider(comp, ctx);
    case TYPE.PROGRESS:
      return renderProgress(comp);
    case TYPE.PICTURE:
      return renderPicture(comp, ctx);
    case TYPE.QR:
      return renderQr(comp);
    default:
      // Hotspots, variables, timers and the page itself draw nothing.
      return nothing;
  }
}

function renderDrawing(d, ctx) {
  if (d.kind === 'xpic') {
    return html`<div class="vp-widget" style="left:${d.x}px;top:${d.y}px;width:${d.w}px;height:${d.h}px;background:url(${ctx.pictureUrl(d.pic)}) -${d.sx}px -${d.sy}px no-repeat;"></div>`;
  }
  return html`<div class="vp-widget vp-circle" style="left:${d.x - d.r}px;top:${d.y - d.r}px;width:${d.r * 2}px;height:${d.r * 2}px;background:${color(d.color)};"></div>`;
}

/**
 * Render the display's current page.
 *
 * @param {NextionDisplay} display
 * @param {object} ctx
 * @param {function(string): (string|null)} ctx.iconName - icon character -> MDI name
 * @param {function(number): string} ctx.pictureUrl - picture id -> URL
 */
export function renderDisplay(display, ctx) {
  const { layout } = display;
  // Only the visible part: the landscape panel hides its rightmost 30 px.
  const size = `width:${layout.visible_width}px;height:${layout.height}px;`;
  if (!display.page) {
    return html`<div class="vp-screen" style="${size}background:#000;"></div>`;
  }
  const pageComp = display.component(0);
  const pageBg = backgroundStyle(pageComp.attrs, { x: 0, y: 0 }, ctx.pictureUrl)
    || 'background:#000;';
  const widgets = [...display.components.values()]
    .filter(c => c.id !== 0 && !c.hidden)
    .sort((a, b) => a.id - b.id);
  return html`
    <div class="vp-screen" style="${size}${pageBg}">
      ${widgets.map(c => renderWidget(c, layout, ctx))}
      ${display.drawings.map(d => renderDrawing(d, ctx))}
    </div>`;
}
