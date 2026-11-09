// The card gallery: the hub's renders of every panel card (out/renders.json,
// written by gen_preview_gallery.py) drawn by the editor's own card element.
// `?orientation=landscape&card=grid` shows one card alone at the display's
// resolution: what `gen_preview_gallery.py --png` captures.
import { html, render } from '../../custom_components/nspanel_haui/frontend/vendor/lit/index.js';
import { setPanelRenderSource } from '../../custom_components/nspanel_haui/frontend/previews/simulator-frame.js';
import { loadLayout } from '../../custom_components/nspanel_haui/frontend/previews/simulator.js';

async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status} — run gen_preview_gallery.py`);
  return response.json();
}

// Outside Home Assistant there is no <ha-icon>: draw the MDI webfont glyph at
// the size the simulator sets (--mdc-icon-size).
async function defineHaIcon() {
  const response = await fetch('out/mdi/materialdesignicons.css');
  if (!response.ok) throw new Error('out/mdi is missing — run gen_preview_gallery.py');
  const css = await response.text();
  const codepoints = new Map(
    [...css.matchAll(/\.mdi-([a-z0-9-]+)::before\s*\{\s*content:\s*"\\([0-9A-F]+)"/gi)]
      .map(([, name, hex]) => [name, parseInt(hex, 16)]),
  );
  customElements.define('ha-icon', class extends HTMLElement {
    static get observedAttributes() { return ['icon']; }

    connectedCallback() { this.draw(); }

    attributeChangedCallback() { this.draw(); }

    draw() {
      const name = String(this.getAttribute('icon') || '').replace(/^mdi:/, '');
      const codepoint = codepoints.get(name);
      this.style.fontFamily = '"Material Design Icons"';
      this.style.fontSize = 'var(--mdc-icon-size, 24px)';
      this.style.fontStyle = 'normal';
      this.style.lineHeight = '1';
      this.textContent = codepoint ? String.fromCodePoint(codepoint) : '';
    }
  });
}

const [renders] = await Promise.all([json('out/renders.json'), defineHaIcon()]);
setPanelRenderSource((panel) => renders[panel.orientation][panel.key]);

const frame = (orientation, card) => html`<nspanel-simulator-frame
  .panel=${{ key: card, orientation }} .portrait=${orientation === 'portrait'}
></nspanel-simulator-frame>`;

async function until(condition, timeout = 10000) {
  const start = Date.now();
  while (!condition()) {
    if (Date.now() - start > timeout) throw new Error('the card did not render in time');
    await new Promise((resolve) => { setTimeout(resolve, 20); });
  }
}

// The capture (capture.mjs) waits for `data-ready`: the card drawn with its
// fonts loaded and its background pictures decoded.
async function markReady(element) {
  await until(() => element._display || element._error);
  if (element._error) throw new Error(element._error);
  await element.updateComplete;
  await Promise.all(['24px "Material Design Icons"', '400 20px Roboto', '300 20px Roboto']
    .map((font) => document.fonts.load(font)));
  await document.fonts.ready;
  const pictures = [...element.shadowRoot.querySelectorAll('[style*="url("]')]
    .map((node) => /url\(["']?([^"')]+)/.exec(node.getAttribute('style'))[1]);
  await Promise.all([...new Set(pictures)].map((url) => {
    const image = new Image();
    image.src = url;
    return image.decode();
  }));
  document.body.dataset.ready = 'true';
}

const params = new URLSearchParams(window.location.search);
const card = params.get('card');
if (card) {
  const orientation = params.get('orientation') || 'landscape';
  const layout = await loadLayout(orientation);
  document.body.classList.add('single');
  render(html`<div style="width:${layout.visible_width}px">${frame(orientation, card)}</div>`,
    document.body);
  markReady(document.querySelector('nspanel-simulator-frame')).catch((err) => {
    document.body.dataset.error = err.message;
    document.body.dataset.ready = 'error';
  });
} else {
  render(Object.entries(renders).map(([orientation, cards]) => html`
    <h2>${orientation}</h2>
    <section class="cards ${orientation}">
      ${Object.keys(cards).map((name) => html`
        <figure>
          <a href="?orientation=${orientation}&card=${encodeURIComponent(name)}">
            ${frame(orientation, name)}
          </a>
          <figcaption>${name}</figcaption>
        </figure>`)}
    </section>`), document.querySelector('main'));
}
