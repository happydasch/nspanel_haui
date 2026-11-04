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
import { LitElement, html, css } from '../lit-import.js';
import { virtualPanelStyles } from '../virtual/virtual-panel-styles.js';
import { isPortraitDevice } from './utils.js';
import { buildPreviewDisplay, loadPanelRender, previewRenderKey } from './previewer.js';
import {
  loadIconMap,
  loadLayout,
  pictureUrlFor,
  renderSimulatorScreen,
} from './simulator.js';

/** Fallback card width (px) used until the container is measured. */
const DEFAULT_WIDTH = 240;

/**
 * The preview of every panel card (`panel-previews.js`): mounts a
 * `<nspanel-simulator-frame>` that does the async work.
 */
export function renderSimulatorPreview(host, panel, pIdx, panelType) {
  return html`
    <nspanel-simulator-frame
      .host=${host} .panel=${panel} .type=${panelType}
      .portrait=${isPortraitDevice(host)}
      .byKey=${pIdx < 0}
      .renderKey=${previewRenderKey(host)}
    ></nspanel-simulator-frame>`;
}

/**
 * Inject asset loaders applied by default (tests and the card gallery,
 * scripts/preview_gallery). `layout(orientation)` returns the parsed layout
 * JSON, `icon()` the char→name map and the optional `render(panel, byKey)` the
 * hub's render of the frame's panel.
 * @param {{layout: Function, icon: Function, render?: Function}|null} loaders
 */
export function setSimulatorLoaders(loaders) {
  globalThis.__HAUI_SIM_LOADERS = loaders || null;
}

export function getSimulatorLoaders() {
  return globalThis.__HAUI_SIM_LOADERS || null;
}

export class SimulatorFrameElement extends LitElement {
  static get properties() {
    return {
      host: { type: Object },
      panel: { type: Object },
      type: { type: Object },
      portrait: { type: Boolean },
      // System panel cards render the device's configured panel by its key.
      byKey: { type: Boolean },
      // The saved device settings and panels live on the same host object:
      // this key changes when what the hub renders with does.
      renderKey: { type: String },
    };
  }

  static get styles() {
    return [virtualPanelStyles, css`
      :host {
        display: block;
        width: 100%;
      }
      .pg-sim {
        position: relative;
        width: 100%;
        margin: 0 auto;
        overflow: hidden;
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
      }
    `];
  }

  constructor() {
    super();
    this.host = null;
    this.panel = null;
    this.type = null;
    this.portrait = false;
    this.byKey = false;
    this.renderKey = '';
    this._display = null;
    this._iconMap = null;
    this._scale = null;
    this._containerWidth = null;
    this._error = null;
    this._started = false;
    this._ro = null;
  }

  connectedCallback() {
    super.connectedCallback();
    if (typeof ResizeObserver !== 'undefined') {
      this._ro = new ResizeObserver(() => this._measure());
      this._ro.observe(this);
    }
  }

  // Start after the first render: Lit applies the `.panel`/`.type`/`.host`
  // bindings around connection, and the preview must be built from the
  // configured panel, not from an empty default.
  firstUpdated() {
    this._start();
  }

  updated(changed) {
    // The editor reuses a frame when a card re-renders; rebuild when the panel,
    // page type, host, orientation or what the hub renders with changed.
    if (!this._started) return;
    for (const key of ['panel', 'type', 'host', 'portrait', 'byKey', 'renderKey']) {
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

  _loaders() {
    const injected = getSimulatorLoaders();
    return {
      layout: (o) => (injected ? injected.layout(o) : loadLayout(o)),
      icon: () => (injected ? injected.icon() : loadIconMap()),
      render: () => (injected
        ? injected.render?.(this.panel, this.byKey) ?? null
        : loadPanelRender(this.host, this.panel, this.byKey)),
    };
  }

  async _start(force = false) {
    if (this._started && !force) return;
    this._started = true;
    this._error = null;
    const { layout, icon, render } = this._loaders();
    const orientation = this.portrait ? 'portrait' : 'landscape';
    try {
      const [layoutObj, iconMap, rendered] =
        await Promise.all([layout(orientation), icon(), render()]);
      this._iconMap = iconMap;
      // No render yet (no device selected, editor still loading): the
      // placeholder stays until the render key changes and a render arrives.
      this._display = rendered
        ? buildPreviewDisplay(layoutObj, rendered.page, { render: rendered })
        : null;
    } catch (err) {
      this._error = (err && err.message) || String(err);
    }
    this._measure();
    this.requestUpdate();
  }

  _measure() {
    if (typeof this.getBoundingClientRect === 'function') {
      try {
        const width = this.getBoundingClientRect().width;
        if (width > 0) this._containerWidth = width;
      } catch (_e) { /* not mounted */ }
    }
    if (this._display && this._containerWidth) {
      const scale = this._containerWidth / this._display.layout.visible_width;
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
