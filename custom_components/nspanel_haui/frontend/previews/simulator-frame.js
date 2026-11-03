/**
 * NSPanel HAUI - Lit element that renders a full HMI page preview via the
 * shared Nextion simulator (previews/simulator.js).
 *
 * Used as the default panel-card preview renderer for every panel type,
 * system panel and popup alias. It asynchronously loads the layout + icon-map
 * assets (memoised), builds a seeded NextionDisplay, and re-renders itself
 * when the assets arrive or the card width changes (scaled to fit while
 * preserving the device orientation).
 *
 * The static preview opens no VirtualPanelSession and no WebSocket — it only
 * fetches the committed layout/icon-map JSON and picture assets.
 */
import { LitElement, html, css } from '../lit-import.js';
import { virtualPanelStyles } from '../virtual/virtual-panel-styles.js';
import { colorSubstitutions, isPortraitDevice } from './utils.js';
import {
  buildPreviewDisplay,
  buildIconCharMap,
  loadIconMap,
  loadLayout,
  loadPreviewState,
  pictureUrlFor,
  renderSimulatorScreen,
  resolvePageId,
} from './simulator.js';

/** Fallback card width (px) used until the container is measured. */
const DEFAULT_WIDTH = 240;

/**
 * The registered renderer function returned by the preview registry for every
 * panel type. It mounts a `<haui-simulator-frame>` that does the async work.
 */
export function renderSimulatorPreview(host, panel, _pIdx, panelType) {
  return html`
    <nspanel-simulator-frame
      .host=${host} .panel=${panel} .type=${panelType}
      .portrait=${isPortraitDevice(host)}
    ></nspanel-simulator-frame>`;
}

/**
 * Inject asset loaders applied by default (tests only). `layout(orientation)`
 * returns the parsed layout JSON, `icon()` the char→name map.
 * @param {{layout: Function, icon: Function}|null} loaders
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
      .pg-sim-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        justify-self: stretch;
        min-height: 120px;
        color: var(--secondary-text-color, #999);
        opacity: 0.6;
      }
    `];
  }

  constructor() {
    super();
    this.host = null;
    this.panel = null;
    this.type = null;
    this.portrait = false;
    this._display = null;
    this._iconMap = null;
    this._byName = null;
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
    // page type, host or orientation changed.
    if (!this._started) return;
    for (const key of ['panel', 'type', 'host', 'portrait']) {
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
      state: () => (injected ? injected.state() : loadPreviewState()),
    };
  }

  async _start(force = false) {
    if (this._started && !force) return;
    this._started = true;
    const { layout, icon, state } = this._loaders();
    const orientation = this.portrait ? 'portrait' : 'landscape';
    try {
      const [layoutObj, iconMap, previewState] = await Promise.all([
        layout(orientation), icon(), state(),
      ]);
      this._iconMap = iconMap;
      this._byName = buildIconCharMap(iconMap);
      this._display = buildPreviewDisplay(
        layoutObj,
        resolvePageId(this.panel, this.type),
        this.panel,
        this.type,
        {
          byName: this._byName,
          host: this.host,
          portrait: this.portrait,
          state: previewState,
          colorMap: colorSubstitutions(this.host),
        },
      );
    } catch (err) {
      this._error = (err && err.message) || String(err);
    }
    this._measure();
    this.requestUpdate();
  }

  _measure() {
    if (!this._containerWidth && typeof this.getBoundingClientRect === 'function') {
      try {
        const w = this.getBoundingClientRect().width;
        if (w) this._containerWidth = w;
      } catch (_e) { /* not mounted */ }
    }
    if (this._display && this._containerWidth) {
      this._scale = this._containerWidth / this._display.layout.visible_width;
      this.requestUpdate();
    }
  }

  render() {
    if (this._error) {
      return html`<div class="pg-sim-loading"><ha-icon icon="mdi:alert-outline"></ha-icon></div>`;
    }
    if (!this._display) {
      return html`<div class="pg-sim-loading"><ha-icon icon="mdi:progress-clock"></ha-icon></div>`;
    }
    const w = this._display.layout.visible_width;
    const scale = this._scale != null ? this._scale : DEFAULT_WIDTH / w;
    const orientation = this.portrait ? 'portrait' : 'landscape';
    return renderSimulatorScreen(this._display, {
      iconName: (ch) => (this._iconMap ? this._iconMap[ch] || null : null),
      pictureUrl: (id) => pictureUrlFor(orientation, id),
      scale,
    });
  }
}

globalThis.customElements && globalThis.customElements.define('nspanel-simulator-frame', SimulatorFrameElement);
