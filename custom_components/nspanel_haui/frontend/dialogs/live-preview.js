/**
 * NSPanel HAUI - Live preview dialog.
 *
 * Shows a virtual panel driven by the hub's real panel code
 * (virtual/virtual-panel-session.js): the screen as the device draws it, touch
 * and swipe with mouse or finger, the two hardware buttons, and a switch
 * between sandbox mode (simulated entity states) and live mode (real service
 * calls).
 */
import { css, html, nothing } from '../lit-import.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { renderToggle } from '../form-fields.js';
import { t } from '../localize.js';
import { renderDisplay } from '../virtual/nextion-view.js';
import { entityAt, toDisplayCoords } from '../virtual/touch-input.js';
import { VirtualPanelSession } from '../virtual/virtual-panel-session.js';
import { virtualPanelStyles } from '../virtual/virtual-panel-styles.js';

// Largest on-screen scale; the dialog shrinks it to fit narrower screens.
const MAX_SCALE = 1.5;
// Share of the window height the frame may take.
const MAX_HEIGHT_SHARE = 0.6;
// Frame around the screen and the hardware buttons below it (px).
const FRAME_PADDING = 8;
// Height of the hardware buttons in display px (a bit taller than the panel's
// 50 px title bar), drawn at the screen's scale.
const HW_BUTTON_HEIGHT = 60;
// Visible screen sizes (layout_landscape.json, layout_portrait.json): the
// frame keeps its size while the layout loads.
const SCREEN_SIZE = { landscape: [450, 320], portrait: [320, 480] };
// How long the "playing sound" hint stays.
const SOUND_HINT_MS = 2000;
// Entity tooltip: distance from the cursor, and the share of the frame past
// which it flips to the cursor's other side.
const TOOLTIP_OFFSET = 14;
const TOOLTIP_FLIP_SHARE = 0.6;

class LivePreviewDialog extends HauiDialog {
  static get properties() {
    return {
      entryId: { type: String },
      device: { type: String },
      _error: { state: true },
      _stageWidth: { state: true },
      _sound: { state: true },
      _displayOff: { state: true },
      _hover: { state: true },
      _showEntities: { state: true },
      _showTools: { state: true },
    };
  }

  static styles = [
    ...HauiDialog.styles,
    virtualPanelStyles,
    css`
      ha-dialog {
        --ha-dialog-max-width: min(760px, 95vw);
      }
      .dialog-body {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .vp-controls {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px 16px;
      }
      .vp-mode {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
      .vp-toolbar {
        margin: 0;
      }
      .vp-toolbar-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 8px 12px;
      }
      .vp-toolbar-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      @media (max-width: 600px) {
        .vp-idle-label {
          display: none;
        }
      }
      .vp-toolbar .view-toggle-btn:disabled {
        cursor: default;
        opacity: 0.5;
      }
      /* Live mode switches real devices: the toolbar says so in the warning colour. */
      .vp-toolbar.live .view-toggle-group {
        border-color: var(--warning-color, #ffa600);
      }
      .vp-toolbar.live .view-toggle-btn.active {
        background: var(--warning-color, #ffa600);
      }
      .vp-mode-note {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin: 0;
        padding: 9px 11px;
        border-inline-start: 3px solid var(--primary-color);
        border-radius: 6px;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.08));
        color: var(--secondary-text-color);
        font-size: 0.85em;
        line-height: 1.4;
      }
      .vp-mode-note ha-icon {
        flex: 0 0 auto;
        --mdc-icon-size: 18px;
      }
      .vp-mode-note.live {
        border-inline-start-color: var(--warning-color, #ffa600);
        color: var(--primary-text-color);
      }
      .vp-mode-note.live ha-icon {
        color: var(--warning-color, #ffa600);
      }
      .vp-more {
        flex: 0 0 auto;
      }
      .vp-more ha-icon {
        --mdc-icon-size: 20px;
      }
      .vp-more.active {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 50%;
      }
      .vp-tools {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin-top: 8px;
      }
      .vp-stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .vp-bezel {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: var(--vp-frame-pad);
        padding: var(--vp-frame-pad);
        overflow: hidden;
        border-radius: calc(var(--vp-frame-pad) * 1.5);
        background: #17191e;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
      }
      .vp-screen-wrap {
        position: relative;
        overflow: hidden;
        border-radius: 4px;
        cursor: pointer;
        touch-action: none;
      }
      .vp-off {
        position: absolute;
        inset: 0;
        background: #000;
        pointer-events: none;
      }
      .vp-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #aaa;
      }
      .vp-hw-buttons {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: var(--vp-frame-pad);
      }
      .vp-hw {
        display: flex;
        align-items: flex-start;
        justify-content: center;
        box-sizing: border-box;
        width: 100%;
        height: var(--vp-hw-height);
        padding: calc(var(--vp-hw-height) * 0.15) 0 0;
        border: 1px solid #34383f;
        border-radius: 6px;
        background: #22252b;
        cursor: pointer;
      }
      .vp-hw:disabled {
        cursor: default;
        opacity: 0.6;
      }
      .vp-hw:active:not(:disabled) {
        background: #292d34;
      }
      .vp-relay-light {
        width: 24px;
        height: 4px;
        border-radius: 999px;
        background: #20242a;
        box-shadow: inset 0 1px 2px #000a;
        transition: background-color 150ms ease, box-shadow 150ms ease;
      }
      .vp-relay-light[data-state="on"] {
        background: #58b3ff;
        box-shadow: 0 0 6px #55adff, 0 0 15px #308bffb3;
      }
      /* A button that switches an entity instead of its relay shows that entity. */
      .vp-relay-light.entity[data-state="on"] {
        background: #ffd23f;
        box-shadow: 0 0 6px #ffcc33, 0 0 15px #ffb300b3;
      }
      .vp-relay-indicators {
        display: inline-flex;
        align-items: center;
        gap: 5px;
      }
      .vp-relay-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #20242a;
      }
      .vp-relay-dot[data-state="on"] {
        background: #58b3ff;
        box-shadow: 0 0 5px #55adff;
      }
      .vp-status {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 16px;
        color: var(--secondary-text-color);
        font-size: 0.9em;
      }
      .vp-status ha-icon {
        --mdc-icon-size: 18px;
        vertical-align: middle;
      }
      .vp-error {
        color: var(--error-color);
      }
      .vp-tooltip {
        position: absolute;
        z-index: 2;
        max-width: 260px;
        padding: 6px 10px;
        border-radius: 6px;
        background: rgba(0, 0, 0, 0.85);
        color: #fff;
        font-size: 0.85em;
        line-height: 1.35;
        pointer-events: none;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .vp-tooltip .vp-tooltip-id {
        opacity: 0.7;
        font-family: var(--code-font-family, monospace);
      }
    `,
  ];

  constructor() {
    super();
    this.entryId = '';
    this.device = '';
    this._session = null;
    this._error = '';
    this._stageWidth = 0;
    this._sound = '';
    this._displayOff = false;
    this._hover = null;
    this._showEntities = false;
    this._showTools = false;
    this._pointerId = null;
    this._soundTimer = null;
    this._resizeObserver = null;
  }

  // -- session lifecycle ------------------------------------------------------

  updated(changed) {
    if (changed.has('open') || changed.has('device') || changed.has('entryId')) {
      if (this.open && this.device && this.entryId) {
        if (!this._session || this._session.device !== this.device) this._startSession();
      } else {
        this._stopSession();
      }
    }
    const stage = this.renderRoot.querySelector('.vp-stage');
    if (stage && !this._resizeObserver) {
      this._resizeObserver = new ResizeObserver(entries => {
        this._stageWidth = entries[0].contentRect.width;
      });
      this._resizeObserver.observe(stage);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopSession();
  }

  _startSession() {
    this._stopSession();
    this._error = '';
    this._displayOff = false;
    const session = new VirtualPanelSession(this.hass, {
      entryId: this.entryId,
      device: this.device,
      onUpdate: () => this.requestUpdate(),
      onAction: action => this._onAction(action),
      onError: msg => { this._error = msg; },
    });
    this._session = session;
    session.start().catch(err => {
      if (this._session === session) this._error = err?.message || String(err);
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
      this._sound = action.name === 'play_sound' ? String(action.value) : 'rtttl';
      clearTimeout(this._soundTimer);
      this._soundTimer = setTimeout(() => { this._sound = ''; }, SOUND_HINT_MS);
    } else if (action.name === 'display_off') {
      this._displayOff = true;
    } else if (action.name === 'display_on') {
      this._displayOff = false;
    }
  }

  _close() {
    this._stopSession();
    this._dispatchClose();
  }

  // -- input ------------------------------------------------------------------

  _coords(e) {
    const screen = this.renderRoot.querySelector('.vp-screen');
    return toDisplayCoords(e.clientX, e.clientY, screen.getBoundingClientRect(), this._session.display.layout);
  }

  _onPointerDown(e) {
    if (!this._session?.ready || this._pointerId !== null) return;
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
    if (!session?.ready || !this._showEntities) return;
    const { x, y } = this._coords(e);
    const entityId = entityAt(session.display, session.entityMap, x, y);
    if (!entityId) {
      this._hover = null;
      return;
    }
    const bezel = this.renderRoot.querySelector('.vp-bezel').getBoundingClientRect();
    this._hover = {
      entityId,
      x: e.clientX - bezel.left,
      y: e.clientY - bezel.top,
      width: bezel.width,
      height: bezel.height,
    };
  }

  _setShowEntities(show) {
    this._showEntities = show;
    if (!show) this._hover = null;
  }

  /** The extra tools are hidden by default; hiding them switches entity hover off too. */
  _setShowTools(show) {
    this._showTools = show;
    if (!show) this._setShowEntities(false);
  }

  _renderTooltip() {
    const hover = this._hover;
    if (!hover) return nothing;
    const name = this.hass?.states?.[hover.entityId]?.attributes?.friendly_name;
    // Keep it inside the frame: left of the cursor on the right side, above it
    // near the bottom.
    const horizontal = hover.x > hover.width * TOOLTIP_FLIP_SHARE
      ? `right:${hover.width - hover.x + TOOLTIP_OFFSET}px;`
      : `left:${hover.x + TOOLTIP_OFFSET}px;`;
    const vertical = hover.y > hover.height * TOOLTIP_FLIP_SHARE
      ? `bottom:${hover.height - hover.y + TOOLTIP_OFFSET}px;`
      : `top:${hover.y + TOOLTIP_OFFSET}px;`;
    return html`
      <div class="vp-tooltip" style="${horizontal}${vertical}">
        ${name ? html`<div>${name}</div>` : nothing}
        <div class="vp-tooltip-id">${hover.entityId}</div>
      </div>
    `;
  }

  async _setLive(live) {
    try {
      await this._session.setLive(live);
    } catch (err) {
      this._error = err?.message || String(err);
    }
  }

  async _resetSandbox() {
    try {
      await this._session.resetSandbox();
    } catch (err) {
      this._error = err?.message || String(err);
      this.requestUpdate();
    }
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
            ?disabled=${!session?.ready}
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

  /** The device: the screen with the two hardware buttons below it. */
  _renderFrame(session, scale, screen) {
    const buttonHeight = Math.floor(HW_BUTTON_HEIGHT * scale);
    return html`
      <div class="vp-bezel" style="--vp-frame-pad:${FRAME_PADDING}px;--vp-hw-height:${buttonHeight}px;">
        ${screen}
        ${this._renderHardwareButtons(session)}
        ${this._renderTooltip()}
      </div>
    `;
  }

  _renderScreen(session) {
    const layout = session.display.layout;
    const scale = this._fitScale(layout.visible_width, layout.height);
    const width = Math.floor(layout.visible_width * scale);
    const height = Math.floor(layout.height * scale);
    const brightness = Math.max(session.brightness, 15) / 100;
    return this._renderFrame(session, scale, html`
      <div
        class="vp-screen-wrap"
        style="width:${width}px;height:${height}px;filter:brightness(${brightness});"
        @pointerdown=${this._onPointerDown}
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
        @pointerleave=${() => { this._hover = null; }}
        @contextmenu=${e => e.preventDefault()}
      >
        <div style="transform:scale(${scale});transform-origin:0 0;">
          ${renderDisplay(session.display, {
            iconName: ch => session.iconName(ch),
            pictureUrl: id => session.pictureUrl(id),
          })}
        </div>
        ${this._displayOff ? html`<div class="vp-off"></div>` : nothing}
      </div>
    `);
  }

  _renderLoading(session) {
    const [screenWidth, screenHeight] = SCREEN_SIZE[session?.orientation || 'landscape'];
    const scale = this._fitScale(screenWidth, screenHeight);
    return this._renderFrame(session, scale, html`
      <div
        class="vp-loading"
        style="width:${Math.floor(screenWidth * scale)}px;height:${Math.floor(screenHeight * scale)}px;"
      >
        ${t('Starting the live preview…')}
      </div>
    `);
  }

  /** The current run mode and what it does. */
  _renderModeNote(session) {
    const live = Boolean(session?.live);
    return html`
      <div class="vp-mode-note ${live ? 'live' : ''}">
        <ha-icon icon=${live ? 'mdi:alert-circle-outline' : 'mdi:information-outline'}></ha-icon>
        <span>${live
          ? t('Live mode: touches and the hardware buttons switch your real devices, including the panel\'s relays. The panel\'s settings stay simulated.')
          : t('Simulated mode: touches update simulated states only; your devices are not switched.')}</span>
      </div>
    `;
  }

  /** Below the mode note: mode selection and the extra tools when opened. */
  _renderToolbar(session) {
    const live = Boolean(session?.live);
    const ready = Boolean(session?.ready);
    const mode = (value, icon, label) => html`
      <button
        class="view-toggle-btn ${live === value ? 'active' : ''}"
        aria-pressed=${live === value ? 'true' : 'false'}
        ?disabled=${!ready}
        @click=${() => { if (live !== value) this._setLive(value); }}
      >
        <ha-icon icon=${icon}></ha-icon>
        <span>${label}</span>
      </button>
    `;
    return html`
      <div class="vp-toolbar ${live ? 'live' : ''}">
        <div class="vp-toolbar-row">
          <div class="view-toggle-group" role="group">
            ${mode(false, 'mdi:flask-outline', t('Simulated'))}
            ${mode(true, 'mdi:access-point', t('Live'))}
          </div>
          <div class="vp-toolbar-actions">
            ${this._renderIdleButton(session)}
            <ha-icon-button
              class="vp-more ${this._showTools ? 'active' : ''}"
              title=${t('More tools')}
              label=${t('More tools')}
              aria-expanded=${this._showTools ? 'true' : 'false'}
              @click=${() => this._setShowTools(!this._showTools)}
            >
              <ha-icon icon="mdi:tune-variant"></ha-icon>
            </ha-icon-button>
          </div>
        </div>
        ${this._showTools ? this._renderTools(session) : nothing}
      </div>
    `;
  }

  _renderIdleButton(session) {
    const ready = Boolean(session?.ready);
    return html`
      <ha-button
        class="vp-idle-button"
        appearance=${session?.idle ? 'accent' : 'plain'}
        aria-pressed=${session?.idle ? 'true' : 'false'}
        ?disabled=${!ready}
        aria-label=${t('Idle timeout')}
        @click=${() => session.idleTimeout()}
      >
        <ha-icon slot="start" icon="mdi:sleep"></ha-icon>
        <span class="vp-idle-label">${t('Idle')}</span>
      </ha-button>
    `;
  }

  /** The extra tools: entity hover and sandbox reset. */
  _renderTools(session) {
    const ready = Boolean(session?.ready);
    const live = Boolean(session?.live);
    return html`
      <div class="vp-controls vp-tools">
        <label class="vp-mode">
          ${renderToggle('vp-show-entities', this._showEntities, v => this._setShowEntities(v), { disabled: !ready })}
          ${t('Show entities')}
        </label>
        <ha-button
          class="vp-reset-sandbox"
          appearance="plain"
          ?disabled=${!ready || live || !session?.sandboxChanged}
          @click=${() => this._resetSandbox()}
        >
          <ha-icon slot="start" icon="mdi:restore"></ha-icon>
          <span>${t('Reset sandbox')}</span>
        </ha-button>
      </div>
    `;
  }

  _renderStatus(session) {
    return html`
      <div class="vp-status">
        ${this._sound ? html`
          <span><ha-icon icon="mdi:volume-high"></ha-icon> ${t('Sound: {name}').replace('{name}', this._sound)}</span>
        ` : nothing}
        ${this._error ? html`
          <span class="vp-error">
            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
            ${t('Live preview error: {error}').replace('{error}', this._error)}
          </span>
        ` : nothing}
      </div>
    `;
  }

  render() {
    if (!this.open) return nothing;
    const session = this._session;
    return html`
      <ha-dialog .open=${this.open} @closed=${this._close}>
        ${dialogHeader(t('Live preview: {device}').replace('{device}', this.device || ''), this._close)}

        <div class="dialog-body">
          ${this._renderToolbar(session)}

          <div class="vp-stage">
            ${session?.ready ? this._renderScreen(session) : this._renderLoading(session)}
          </div>

          ${this._renderModeNote(session)}

          ${this._renderStatus(session)}
        </div>

        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button slot="primaryAction" @click=${this._close}>
              ${t('Close')}
            </ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }
}

customElements.define('nspanel-dialog-live-preview', LivePreviewDialog);
export { LivePreviewDialog };
