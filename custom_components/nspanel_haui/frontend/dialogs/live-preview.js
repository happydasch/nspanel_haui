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
import { toDisplayCoords } from '../virtual/touch-input.js';
import { VirtualPanelSession } from '../virtual/virtual-panel-session.js';
import { virtualPanelStyles } from '../virtual/virtual-panel-styles.js';

// Largest on-screen scale; the dialog shrinks it to fit narrower screens.
const MAX_SCALE = 1.5;
// Share of the window height the screen may take.
const MAX_HEIGHT_SHARE = 0.6;
// How long the "playing sound" hint stays.
const SOUND_HINT_MS = 2000;

class LivePreviewDialog extends HauiDialog {
  static get properties() {
    return {
      entryId: { type: String },
      device: { type: String },
      _error: { state: true },
      _stageWidth: { state: true },
      _sound: { state: true },
      _displayOff: { state: true },
    };
  }

  static styles = [
    ...HauiDialog.styles,
    virtualPanelStyles,
    css`
      ha-dialog {
        --ha-dialog-max-width: min(760px, 95vw);
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
      .vp-hint {
        margin: 8px 0 12px;
        color: var(--secondary-text-color);
        font-size: 0.9em;
      }
      .vp-hint.live {
        color: var(--warning-color, #ffa600);
      }
      .vp-stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }
      .vp-bezel {
        position: relative;
        padding: 12px;
        border-radius: 16px;
        background: #1c1c1c;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
      }
      .vp-screen-wrap {
        position: relative;
        overflow: hidden;
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
        display: flex;
        gap: 24px;
      }
      .vp-hw {
        min-width: 96px;
        padding: 10px 16px;
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        font: inherit;
        cursor: pointer;
      }
      .vp-hw:active {
        background: var(--divider-color);
      }
      .vp-status {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 16px;
        margin-top: 12px;
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
    e.currentTarget.setPointerCapture(e.pointerId);
    this._pointerId = e.pointerId;
    const { x, y } = this._coords(e);
    this._session.touch.press(x, y);
  }

  _onPointerMove(e) {
    if (e.pointerId !== this._pointerId) return;
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
    }
  }

  // -- render -----------------------------------------------------------------

  _renderScreen(session) {
    const layout = session.display.layout;
    const available = (this._stageWidth || layout.visible_width) - 24;
    // Fit the width and keep the portrait screen within the window's height.
    const availableHeight = (globalThis.innerHeight || layout.height / MAX_HEIGHT_SHARE) * MAX_HEIGHT_SHARE;
    const scale = Math.min(MAX_SCALE, available / layout.visible_width, availableHeight / layout.height);
    const width = Math.floor(layout.visible_width * scale);
    const height = Math.floor(layout.height * scale);
    const brightness = Math.max(session.brightness, 15) / 100;
    return html`
      <div
        class="vp-screen-wrap"
        style="width:${width}px;height:${height}px;filter:brightness(${brightness});"
        @pointerdown=${this._onPointerDown}
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
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
    `;
  }

  _renderStatus(session) {
    const simulated = session?.sandboxEntities || [];
    return html`
      <div class="vp-status">
        ${simulated.length ? html`
          <span title=${simulated.join('\n')}>
            <ha-icon icon="mdi:flask-outline"></ha-icon>
            ${t('Simulated entities: {count}').replace('{count}', String(simulated.length))}
          </span>
        ` : nothing}
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
    const live = Boolean(session?.live);
    const ready = Boolean(session?.ready);
    return html`
      <ha-dialog .open=${this.open} @closed=${this._close}>
        ${dialogHeader(t('Live preview: {device}').replace('{device}', this.device || ''), this._close)}

        <div class="dialog-body">
          <div class="vp-controls">
            <label class="vp-mode">
              ${renderToggle('vp-live', live, v => this._setLive(v), { disabled: !ready })}
              ${t('Live mode')}
            </label>
            <ha-button
              appearance="plain"
              ?disabled=${!ready || !session.sandboxEntities.length}
              @click=${this._resetSandbox}
            >
              <ha-icon slot="start" icon="mdi:restore"></ha-icon>
              ${t('Reset sandbox')}
            </ha-button>
            <ha-button appearance="plain" ?disabled=${!ready} @click=${() => session.idleTimeout()}>
              <ha-icon slot="start" icon="mdi:timer-sand"></ha-icon>
              ${t('Idle timeout')}
            </ha-button>
          </div>
          <p class="vp-hint ${live ? 'live' : ''}">
            ${live
              ? t('Live mode: touches switch your real devices. The panel\'s own relays and settings stay simulated.')
              : t('Sandbox mode: touches change simulated states only; your devices are not switched.')}
          </p>

          <div class="vp-stage">
            <div class="vp-bezel">
              ${ready
                ? this._renderScreen(session)
                : html`<div class="vp-loading" style="width:450px;max-width:70vw;height:300px;">${t('Starting the live preview…')}</div>`}
            </div>
            <div class="vp-hw-buttons">
              <button class="vp-hw" ?disabled=${!ready} @click=${() => session.pressButton('left')}>
                ${t('Left button')}
              </button>
              <button class="vp-hw" ?disabled=${!ready} @click=${() => session.pressButton('right')}>
                ${t('Right button')}
              </button>
            </div>
          </div>

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
