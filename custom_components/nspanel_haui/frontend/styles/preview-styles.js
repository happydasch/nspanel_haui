import { css } from '../lit-import.js';

/** Shared live/device preview stage, bezel, hardware controls, and display feedback. */
export const previewStyles = css`
  /* The stage fills the workspace card edge to edge; the card clips its corners. */
  .haui-preview-stage {
    display: grid;
    min-height: 360px;
    box-sizing: border-box;
    place-items: center;
    align-content: center;
    gap: 12px;
    padding: 40px;
    background: var(--haui-screen);
    transition: background 150ms ease;
  }
  @container haui-editor (max-width: 600px) {
    .haui-preview-stage { min-height: 240px; padding: 24px; }
  }
  .haui-preview-stage.is-live { background: var(--haui-live-preview); }
  .haui-preview-bezel {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--vp-frame-pad);
    padding: var(--vp-frame-pad);
    overflow: hidden;
    border-radius: calc(var(--vp-frame-pad) * 1.5);
    background: var(--haui-bezel);
    box-shadow: var(--haui-shadow-device-preview);
  }
  .haui-preview-loading {
    display: flex;
    min-height: 200px;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
  }
  .haui-preview-error {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    border-radius: var(--haui-radius-control);
    background: color-mix(in srgb, var(--error-color, #db4437) 14%, var(--card-background-color, #fff));
    color: var(--error-color, #db4437);
    font-size: var(--haui-text-label);
  }
  .haui-preview-stage .haui-empty-state { color: var(--secondary-text-color); }
  .vp-screen-wrap {
    position: relative;
    overflow: hidden;
    border-radius: var(--haui-radius-control);
    cursor: pointer;
    touch-action: none;
  }
  .vp-off { position: absolute; inset: 0; background: var(--haui-screen-off); pointer-events: none; }
  .vp-hw-buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--vp-frame-pad); }
  .vp-hw {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    box-sizing: border-box;
    width: 100%;
    height: var(--vp-hw-height);
    padding: calc(var(--vp-hw-height) * 0.15) 0 0;
    border: 1px solid var(--haui-hardware-button-border);
    border-radius: var(--haui-radius-control);
    background: var(--haui-hardware-button);
    cursor: pointer;
  }
  .vp-hw:disabled { cursor: default; opacity: .6; }
  .vp-hw:active:not(:disabled) { background: var(--haui-hardware-button-active); }
  /* The lights follow the button: its width, and its height for their thickness. */
  .vp-relay-light {
    width: 23%;
    height: max(2px, calc(var(--vp-hw-height) * 0.07));
    border-radius: var(--haui-radius-pill);
    background: var(--haui-hardware-led-well);
    box-shadow: var(--haui-shadow-led-well);
    transition: background-color 150ms ease, box-shadow 150ms ease;
  }
  .vp-relay-light[data-state="on"] {
    background: var(--haui-led-relay);
    box-shadow: 0 0 6px var(--haui-led-relay-glow), var(--haui-led-relay-shadow);
  }
  /* A button that switches an entity instead of its relay shows that entity. */
  .vp-relay-light.entity[data-state="on"] {
    background: var(--haui-led-entity);
    box-shadow: 0 0 6px var(--haui-led-entity-glow), var(--haui-led-entity-shadow);
  }
  .vp-relay-indicators { display: flex; width: 100%; align-items: center; justify-content: center; gap: 4px; }
  .vp-relay-dot {
    width: max(3px, calc(var(--vp-hw-height) * 0.08));
    height: max(3px, calc(var(--vp-hw-height) * 0.08));
    border-radius: var(--haui-radius-round);
    background: var(--haui-hardware-led-well);
  }
  .vp-relay-dot[data-state="on"] {
    background: var(--haui-led-relay);
    box-shadow: 0 0 5px var(--haui-led-relay-glow);
  }
  .vp-tooltip {
    position: absolute;
    z-index: 2;
    max-width: 260px;
    padding: 4px 8px;
    border-radius: var(--haui-radius-control);
    background: var(--haui-bezel);
    color: var(--text-primary-color, #fff);
    font-size: var(--haui-text-caption);
    line-height: 1.35;
    pointer-events: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .vp-tooltip .vp-tooltip-id { opacity: .7; font-family: var(--haui-mono); }
  @media (prefers-reduced-motion: reduce) {
    .haui-preview-stage, .vp-relay-light { transition: none; }
  }
`;
