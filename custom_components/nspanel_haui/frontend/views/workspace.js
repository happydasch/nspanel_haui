/**
 * NSPanel HAUI - interactive device preview workspace.
 *
 * Shows a panel driven by the hub's real panel code: the screen as the device
 * draws it, touch and swipe with mouse or finger, the two hardware buttons, and
 * a switch between sandbox mode (virtual/virtual-panel-session.js: the device's
 * virtual app, simulated states) and live mode (virtual/live-panel-session.js:
 * the real panel and its entities).
 */
import { LitElement, css, html, nothing } from '../lit-import.js';
import { haStyle, dialogStyles } from '../styles.js';
import { previewStyles } from '../styles/preview-styles.js';
import { previewStage } from '../ui/preview-stage.js';
import { t } from '../localize.js';
import { renderDisplay } from '../virtual/nextion-view.js';
import { entityAt, toDisplayCoords } from '../virtual/touch-input.js';
import { LivePanelSession } from '../virtual/live-panel-session.js';
import { VirtualPanelSession } from '../virtual/virtual-panel-session.js';

// Largest on-screen scale; the workspace shrinks it to fit the available width.
const MAX_SCALE = 1.25;
// Keep a little vertical breathing room around the display in the workspace.
const MAX_HEIGHT_SHARE = 0.85;
// Frame around the screen and the hardware buttons below it (px).
const FRAME_PADDING = 8;
// Height of the hardware buttons in display px (a bit taller than the panel's
// 50 px title bar), drawn at the screen's scale.
const HW_BUTTON_HEIGHT = 60;
// Visible screen sizes (layout_landscape.json, layout_portrait.json): the
// frame keeps its size while the layout loads.
const SCREEN_SIZE = { landscape: [450, 320], portrait: [320, 480] };
// Entity tooltip: distance from the cursor, and the share of the frame past
// which it flips to the cursor's other side.
const TOOLTIP_OFFSET = 14;
const TOOLTIP_FLIP_SHARE = 0.6;

class PreviewWorkspace extends LitElement {
  static get properties() {
    return {
      // Home Assistant replaces hass on every state change. The screen is drawn
      // from the session, which reports its own changes, so a new hass alone
      // must not redraw it; the tooltip reads hass when the hover changes.
      hass: { type: Object, hasChanged: () => false },
      active: { type: Boolean },
      entryId: { type: String },
      device: { type: String },
      _error: { state: true },
      _stageWidth: { state: true },
      _hover: { state: true },
      mode: { type: String },
      showEntities: { type: Boolean },
      optionSelection: { type: String },
    };
  }

  static styles = [haStyle, dialogStyles, previewStyles, css`
    :host { display: block; width: 100%; min-width: 0; container: haui-workspace / inline-size; }
  `];

  constructor() {
    super();
    this.hass = null;
    this.active = false;
    this.entryId = '';
    this.device = '';
    this._session = null;
    this._error = '';
    this._stageWidth = 0;
    this._hover = null;
    this.mode = 'simulated';
    this.showEntities = false;
    this.optionSelection = '';
    this._pointerId = null;
    this._resizeObserver = null;
  }

  // -- session lifecycle ------------------------------------------------------

  updated(changed) {
    if (changed.has('active') || changed.has('device') || changed.has('entryId')) {
      if (this.active && this.device && this.entryId) {
        // Another device keeps the mode the user chose.
        if (!this._session || this._session.device !== this.device) this._startSession(this.mode === 'live');
      } else {
        this._stopSession();
      }
    }
    if (changed.has('mode')) this.setLive(this.mode === 'live');
    if (changed.has('showEntities') && !this.showEntities) this._hover = null;
    if (changed.has('optionSelection')) this._hover = null;
    const stage = this.renderRoot.querySelector('.haui-preview-stage');
    if (stage && !this._resizeObserver && typeof ResizeObserver === 'function') {
      this._resizeObserver = new ResizeObserver(entries => {
        this._stageWidth = entries[0].contentRect.width;
      });
      this._resizeObserver.observe(stage);
    }
    this._emitPreviewState();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopSession();
  }

  _startSession(live = false) {
    this._stopSession();
    this._error = '';
    const Session = live ? LivePanelSession : VirtualPanelSession;
    const session = new Session(this.hass, {
      entryId: this.entryId,
      device: this.device,
      // Opening a Simulated preview starts the virtual app over, as switching
      // back from Live does: a reused app may sit on its idle page, a popup or
      // a panel a previous preview left it on.
      openHome: !live,
      onUpdate: () => this.requestUpdate(),
      onAction: action => this._onAction(action),
      onError: msg => this._fail(msg),
    });
    this._session = session;
    session.start().catch(err => {
      if (this._session === session) this._fail(err);
    });
  }

  _stopSession() {
    const session = this._session;
    this._session = null;
    this._pointerId = null;
    this._hover = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    if (session) session.stop().catch(() => {});
  }

  _onAction(action) {
    if (action.name === 'play_sound' || action.name === 'play_rtttl') {
      const name = action.name === 'play_sound' ? String(action.value) : 'rtttl';
      this._notify(t('Sound: {name}').replace('{name}', name), 'info');
    }
  }

  /**
   * Keep an error for the stage, which shows it while there is no screen. Once
   * the screen is up the stage stays clean, so the error goes out as a notice.
   * @param {unknown} error
   */
  _fail(error) {
    this._error = /** @type {any} */ (error)?.message || String(error);
    if (this._session?.ready) {
      this._notify(t('Live preview error: {error}').replace('{error}', this._error), 'error');
    }
  }

  /** Hand a message to the editor, which shows it as a haui-toast. */
  _notify(message, type) {
    this._emit('preview-notice', { message, type });
  }

  /** Tell the Device screen something it owns, such as a haui-toast. */
  _emit(type, detail = {}) {
    if (typeof this.dispatchEvent !== 'function') return;
    this.dispatchEvent(new CustomEvent(type, { bubbles: true, composed: true, detail }));
  }

  /**
   * Tell the Device screen what the session is doing: the header's Live and
   * Idle controls follow the session, not a second copy of its state.
   */
  _emitPreviewState() {
    if (typeof this.dispatchEvent !== 'function') return;
    const session = this._session;
    const detail = {
      mode: session?.live ? 'live' : 'simulated',
      idle: Boolean(session?.idle),
      ready: Boolean(session?.ready),
      canInteract: Boolean(session?.canInteract),
      sandboxChanged: Boolean(session?.sandboxChanged),
      connected: session?.physical?.connected ?? null,
    };
    const key = JSON.stringify(detail);
    if (key === this.__previewStateKey) return;
    this.__previewStateKey = key;
    this.dispatchEvent(new CustomEvent('preview-state', {
      bubbles: true,
      composed: true,
      detail,
    }));
  }

  // -- input ------------------------------------------------------------------

  _coords(e) {
    const screen = this.renderRoot.querySelector('.vp-screen');
    return toDisplayCoords(e.clientX, e.clientY, screen.getBoundingClientRect(), this._session.display.layout);
  }

  _onPointerDown(e) {
    if (!this._session?.canInteract || this._pointerId !== null) return;
    e.preventDefault();
    this._hover = null;
    e.currentTarget.setPointerCapture(e.pointerId);
    this._pointerId = e.pointerId;
    const { x, y } = this._coords(e);
    this._session.touch.press(x, y);
  }

  _onPointerMove(e) {
    if (e.pointerId !== this._pointerId) {
      if (this._pointerId === null && e.pointerType === 'mouse') this._updateHover(e);
      return;
    }
    const { x, y } = this._coords(e);
    this._session.touch.move(x, y);
  }

  _onPointerUp(e) {
    if (e.pointerId !== this._pointerId) return;
    this._pointerId = null;
    const { x, y } = this._coords(e);
    this._session.touch.release(x, y);
  }

  _onPointerCancel(e) {
    if (e.pointerId !== this._pointerId) return;
    this._pointerId = null;
    this._session.touch.cancel();
  }

  /** Name the entity under the mouse, if the widget there shows one. */
  _updateHover(e) {
    const session = this._session;
    if (!session?.ready || !this.showEntities) return;
    const { x, y } = this._coords(e);
    const entityId = entityAt(session.display, session.entityMap, x, y);
    if (!entityId) {
      this._hover = null;
      return;
    }
    const bezel = this.renderRoot.querySelector('.haui-preview-bezel').getBoundingClientRect();
    this._hover = {
      entityId,
      x: e.clientX - bezel.left,
      y: e.clientY - bezel.top,
      width: bezel.width,
      height: bezel.height,
    };
  }

  _renderTooltip() {
    const hover = this._hover;
    if (!hover) return nothing;
    const name = this.hass?.states?.[hover.entityId]?.attributes?.friendly_name;
    // Keep it inside the frame: left of the cursor on the right side, above it
    // near the bottom.
    const horizontal = hover.x > hover.width * TOOLTIP_FLIP_SHARE
      ? `--vp-tooltip-right:${hover.width - hover.x + TOOLTIP_OFFSET}px`
      : `--vp-tooltip-left:${hover.x + TOOLTIP_OFFSET}px`;
    const vertical = hover.y > hover.height * TOOLTIP_FLIP_SHARE
      ? `--vp-tooltip-bottom:${hover.height - hover.y + TOOLTIP_OFFSET}px`
      : `--vp-tooltip-top:${hover.y + TOOLTIP_OFFSET}px`;
    return html`
      <div class="vp-tooltip" style="${horizontal};${vertical}">
        ${name ? html`<div>${name}</div>` : nothing}
        <div class="vp-tooltip-id">${hover.entityId}</div>
      </div>
    `;
  }

  /**
   * Switch modes. The modes are independent: Live drops the simulated states,
   * and back from Live the sandbox starts over on its home panel.
   */
  setLive(live) {
    if (!this.active || !this._session || this._session.live === live) return;
    if (live && this._session.sandboxChanged) {
      // Sent before the sandbox unsubscribes; the hub handles a connection's
      // messages in order, so it still knows the session.
      this._session.resetSandbox().catch(err => this._fail(err));
    }
    this._startSession(live);
  }

  /** Send the panel to its idle page, as its inactivity timeout would. */
  idleTimeout() {
    this._session?.idleTimeout();
  }

  /**
   * Show one of the device's panels in the simulated preview; Live already
   * shows what the device does.
   * @param {string} key
   * @param {boolean} [idle] - open it as the idle page
   */
  openPanel(key, idle = false) {
    if (this._session && !this._session.live) this._session.openPanel(key, idle);
  }

  async resetSandbox() {
    try {
      await this._session.resetSandbox();
    } catch (err) {
      this._fail(err);
    }
  }

  async resetInteractionTimer() {
    try {
      await this._session.resetInteractionTimer();
    } catch (err) {
      this._fail(err);
    }
  }

  /** The Diagnostics card's reset: the interaction timer in Live, the sandbox otherwise. */
  resetSession() {
    return this._session?.live ? this.resetInteractionTimer() : this.resetSandbox();
  }

  // -- render -----------------------------------------------------------------

  _renderHardwareButtons(session) {
    return html`
      <div class="vp-hw-buttons">
        ${['left', 'right'].map(side => html`
          <button
            class="vp-hw"
            aria-label=${side === 'left' ? t('Left button') : t('Right button')}
            title=${side === 'left' ? t('Left button') : t('Right button')}
            ?disabled=${!session?.canInteract}
            @click=${() => session?.pressButton(side)}
          >
            ${session?.buttonEntityStates?.[side] !== null
              && session?.buttonEntityStates?.[side] !== undefined
              ? html`
                <span class="vp-relay-indicators">
                  <span class="vp-relay-light entity" data-state=${session.buttonEntityStates[side]}></span>
                  <span class="vp-relay-dot" data-state=${session?.relays?.[side] || 'unknown'}></span>
                </span>
              `
              : html`<span class="vp-relay-light" data-state=${session?.relays?.[side] || 'unknown'}></span>`}
          </button>
        `)}
      </div>
    `;
  }

  /** Scale that fits a screen and the buttons below it into the stage. */
  _fitScale(screenWidth, screenHeight) {
    const availableWidth = (this._stageWidth || screenWidth) - 2 * FRAME_PADDING;
    const frameHeight = screenHeight + HW_BUTTON_HEIGHT;
    const availableHeight = (globalThis.innerHeight || frameHeight / MAX_HEIGHT_SHARE) * MAX_HEIGHT_SHARE
      - 3 * FRAME_PADDING;
    return Math.max(0, Math.min(MAX_SCALE, availableWidth / screenWidth, availableHeight / frameHeight));
  }

  /** Hardware button height for the current scale. */
  _hardwareHeight(session) {
    const layout = session?.display?.layout;
    const [width, height] = layout
      ? [layout.visible_width, layout.height]
      : SCREEN_SIZE[session?.orientation || 'landscape'];
    return Math.floor(HW_BUTTON_HEIGHT * this._fitScale(width, height));
  }

  _renderScreen(session) {
    const layout = session.display.layout;
    const scale = this._fitScale(layout.visible_width, layout.height);
    const width = Math.floor(layout.visible_width * scale);
    const height = Math.floor(layout.height * scale);
    return html`
      <div
        class="vp-screen-wrap"
        style="--vp-screen-width:${width}px;--vp-screen-height:${height}px;--vp-screen-brightness:${session.screenBrightness};"
        @pointerdown=${this._onPointerDown}
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
        @pointerleave=${() => { this._hover = null; }}
        @contextmenu=${e => e.preventDefault()}
      >
        <div class="vp-screen-scaler" style="--vp-screen-scale:${scale};">
          ${renderDisplay(session.display, {
            iconName: ch => session.iconName(ch),
            pictureUrl: id => session.pictureUrl(id),
          })}
        </div>
        ${session.displayOff ? html`<div class="vp-off"></div>` : nothing}
      </div>
    `;
  }

  /** The stage state for the render: loading, unrecoverable error, or the screen. */
  _stageState(session) {
    if (session?.ready) return 'ready';
    if (this._error) return 'error';
    return 'loading';
  }

  render() {
    if (!this.active || !this.device || !this.entryId) return nothing;
    const session = this._session;
    const title = t('Live preview: {device}').replace('{device}', this.device);
    const state = this._stageState(session);
    const stage = previewStage({
      screen: state === 'ready' ? this._renderScreen(session) : nothing,
      hardware: state === 'ready' ? this._renderHardwareButtons(session) : nothing,
      tooltip: state === 'ready' ? this._renderTooltip() : nothing,
      live: Boolean(session?.live),
      state,
      error: this._error,
      framePad: FRAME_PADDING,
      hardwareHeight: state === 'ready' ? this._hardwareHeight(session) : 60,
    });
    return html`<section class="vp-workspace" aria-label=${title}>
      <div class="vp-body">${stage}</div>
    </section>
`;
  }
}
customElements.define('nspanel-preview-workspace', PreviewWorkspace);
