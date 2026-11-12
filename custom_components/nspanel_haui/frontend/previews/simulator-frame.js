/**
 * NSPanel HAUI - Lit element that renders a full HMI page preview via the
 * shared Nextion simulator and preview generator.
 *
 * Used as the panel-card preview renderer for every panel type, system panel
 * and popup alias. It asynchronously loads the layout + icon-map assets
 * (memoised) and the hub's render of the panel (`loadPanelRender`), replays it
 * in a NextionDisplay, and re-renders itself when the assets arrive or the card
 * width changes (scaled to fit while preserving the device orientation).
 */
import { isPortraitModel } from '../constants.js';
import { LitElement, html, css } from '../lit-import.js';
import { virtualPanelStyles } from '../virtual/virtual-panel-styles.js';
import { buildPreviewDisplay, lastPanelRender, loadPanelRender, previewRenderKey } from './previewer.js';
import {
  loadIconMap,
  loadLayout,
  pictureUrlFor,
  renderSimulatorScreen,
} from './simulator.js';

/** Fallback card width (px) used until the container is measured. */
const DEFAULT_WIDTH = 240;
const MAX_PORTRAIT_HEIGHT = 480;

/**
 * The preview of every panel card (`panel-previews.js`): mounts a
 * `<nspanel-simulator-frame>` that does the async work. A list of cards that
 * share one context passes its `renderKey`, computed once, instead of
 * serialising the device's settings and panels again for every card.
 */
export function renderSimulatorPreview(context, panel, pIdx, renderKey = previewRenderKey(context)) {
  return html`
    <nspanel-simulator-frame
      .context=${context} .panel=${panel}
      .portrait=${isPortraitModel(context?.deviceConfig?.display_model)}
      .byKey=${pIdx < 0}
      .renderKey=${renderKey}
    ></nspanel-simulator-frame>`;
}

let renderSource = null;

/**
 * Take card renders from `source(panel, byKey)` instead of the hub (the card
 * gallery, scripts/preview_gallery, and tests); null goes back to the hub.
 * @param {Function|null} source
 */
export function setPanelRenderSource(source) {
  renderSource = source;
}

export class SimulatorFrameElement extends LitElement {
  static get properties() {
    return {
      // Rebuilt by the editor on every render: what it holds reaches the frame
      // as renderKey, so a new context object alone is no reason to render.
      context: { type: Object, hasChanged: () => false },
      panel: { type: Object },
      portrait: { type: Boolean, reflect: true },
      // System panel cards render the device's configured panel by its key.
      byKey: { type: Boolean },
      // The hub/device/settings/panels a render depends on; a frame rebuilds
      // when what the hub renders with changes.
      renderKey: { type: String },
    };
  }

  static get styles() {
    return [virtualPanelStyles, css`
      :host {
        display: block;
        width: 100%;
        min-width: 0;
      }
      /* A card preview takes no touch input: a swipe that starts on it must
         scroll the list or carousel around it, as on the rest of the card. */
      .vp-screen {
        touch-action: auto;
      }
      .pg-sim {
        position: relative;
        max-width: 100%;
        margin: 0 auto;
        overflow: hidden;
        /* A picture page or a card still loading; a solid page sets its theme colour inline. */
        background: #000;
      }
      .pg-sim-scaler {
        position: absolute;
        left: 0;
        top: 0;
      }
      /* Holds the card's shape until the render arrives: the layouts'
         visible sizes (layout_landscape.json, layout_portrait.json). */
      .pg-sim-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        aspect-ratio: 450 / 320;
        color: var(--secondary-text-color, #999);
        opacity: 0.6;
      }
      .pg-sim-loading.portrait {
        aspect-ratio: 320 / 480;
        max-width: 320px;
        max-height: 480px;
        margin-inline: auto;
      }
    `];
  }

  constructor() {
    super();
    this.context = null;
    this.panel = null;
    this.portrait = false;
    this.byKey = false;
    this.renderKey = '';
    this._display = null;
    this._iconMap = null;
    this._scale = null;
    this._containerWidth = null;
    this._error = null;
    this._started = false;
    this._seq = 0;
    this._ro = null;
  }

  connectedCallback() {
    super.connectedCallback();
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => this._measure());
      this._ro.observe(this);
    }
  }

  // Start after the first render: Lit applies the `.panel`/`.context` bindings
  // around connection, and the preview must be built from the configured
  // panel, not from an empty default.
  firstUpdated() {
    this._start();
  }

  updated(changed) {
    // The editor reuses a frame when a card re-renders; rebuild when the panel,
    // orientation or what the hub renders with (renderKey) changed. The context
    // object itself is rebuilt on every card render, so its identity alone must
    // not restart the replay.
    if (!this._started) return;
    for (const key of ['panel', 'portrait', 'byKey', 'renderKey']) {
      if (changed.has(key)) {
        this._start(true);
        return;
      }
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._ro) {
      this._ro.disconnect();
      this._ro = null;
    }
  }

  async _start(force = false) {
    if (this._started && !force) return;
    this._started = true;
    this._error = null;
    // The panel may change while a render is on its way: the newest start wins.
    const seq = ++this._seq;
    const orientation = this.portrait ? 'portrait' : 'landscape';
    // A frame with nothing to show yet replays the card's last render until the
    // hub answers: after a reload the hub may first start the device's virtual app.
    const last = this._display || renderSource
      ? null
      : lastPanelRender(this.context, this.panel, this.byKey);
    try {
      // Settled while the assets load: a failure is thrown once it is awaited.
      const rendering = Promise.resolve(renderSource
        ? renderSource(this.panel, this.byKey)
        : loadPanelRender(this.context, this.panel, this.byKey))
        .then((rendered) => ({ rendered }), (error) => ({ error }));
      const [layoutObj, iconMap] = await Promise.all([loadLayout(orientation), loadIconMap()]);
      if (seq !== this._seq) return;
      this._iconMap = iconMap;
      if (last) {
        this._display = buildPreviewDisplay(layoutObj, last.page, { render: last });
        this._measure();
        this.requestUpdate();
      }
      const { rendered, error } = await rendering;
      if (seq !== this._seq) return;
      if (error) throw error;
      // No render yet (no device selected, editor still loading): the
      // placeholder, or the last render, stays until the render key changes
      // and a render arrives.
      if (rendered) this._display = buildPreviewDisplay(layoutObj, rendered.page, { render: rendered });
      else if (!last) this._display = null;
    } catch (err) {
      if (seq !== this._seq) return;
      this._error = (err && err.message) || String(err);
    }
    this._measure();
    this.requestUpdate();
  }

  _measure() {
    if (typeof this.getBoundingClientRect === 'function') {
      try {
        // The screen fills the content box: a border on the frame (the Fleet
        // card's bezel) is not drawable width, and scaling to it clips the screen.
        const width = this.clientWidth || this.getBoundingClientRect().width;
        if (width > 0) this._containerWidth = width;
      } catch (_e) { /* not mounted */ }
    }
    if (this._display && this._containerWidth) {
      const layout = this._display.layout;
      const widthScale = this._containerWidth / layout.visible_width;
      const heightScale = this.portrait ? MAX_PORTRAIT_HEIGHT / layout.height : Infinity;
      const scale = Math.min(widthScale, heightScale);
      if (scale !== this._scale) {
        this._scale = scale;
        this.requestUpdate();
      }
    }
  }

  render() {
    const orientation = this.portrait ? 'portrait' : 'landscape';
    if (this._error) {
      return html`<div class="pg-sim-loading ${orientation}" title=${this._error}>
        <ha-icon icon="mdi:alert-outline"></ha-icon>
      </div>`;
    }
    if (!this._display) {
      return html`<div class="pg-sim-loading ${orientation}">
        <ha-icon icon="mdi:progress-clock"></ha-icon>
      </div>`;
    }
    const w = this._display.layout.visible_width;
    const scale = this._scale != null ? this._scale : DEFAULT_WIDTH / w;
    return renderSimulatorScreen(this._display, {
      iconName: (ch) => (this._iconMap ? this._iconMap[ch] || null : null),
      pictureUrl: (id) => pictureUrlFor(orientation, id),
      scale,
    });
  }
}

globalThis.customElements && globalThis.customElements.define('nspanel-simulator-frame', SimulatorFrameElement);
