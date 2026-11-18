import { css } from '../lit-import.js';

/**
 * The dashboard card (card/card.js): the device's screen in its bezel, the
 * panel's status row, and the status tile a card without a screen shows.
 * Colours come from the shared tokens, so the frame reads as the same
 * hardware the editor's preview draws.
 */
export const cardStyles = css`
  :host { display: block; }
  .haui-card { overflow: hidden; }
  .haui-card-title {
    padding: 12px 16px 0;
    color: var(--primary-text-color, #212121);
    font-size: var(--haui-text-body);
    font-weight: 500;
  }
  /* A scaled-down screen keeps the row under it, centered with it (card.js). */
  .haui-card-body.is-screen { width: fit-content; max-width: 100%; margin: 0 auto; }
  /* The bezel: the pad around the screen and the hardware strip under it
     (card.js sets their size). */
  .haui-card-stage {
    position: relative;
    display: grid;
    justify-items: center;
    gap: var(--vp-frame-pad);
    padding: var(--vp-frame-pad);
    background: var(--haui-bezel);
  }
  /* Off: dark, as the panel is; disconnected: dimmed under its badge. */
  .haui-card-screen { display: grid; filter: brightness(var(--vp-screen-brightness, 1)); }
  .haui-card-stage > .haui-badge { position: absolute; top: 8px; inset-inline-end: 8px; }
  .haui-card-hw { display: grid; width: 100%; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--vp-frame-pad); }
  .haui-card-hw-button {
    display: flex;
    height: var(--vp-hw-height);
    align-items: flex-start;
    justify-content: center;
    gap: 4px;
    box-sizing: border-box;
    padding-top: calc(var(--vp-hw-height) * 0.25);
    border: 1px solid var(--haui-hardware-button-border);
    border-radius: var(--haui-radius-control);
    background: var(--haui-hardware-button);
  }
  /* The lights follow the button: its width, and its height for their thickness. */
  .haui-card-led {
    width: 23%;
    height: max(2px, calc(var(--vp-hw-height) * 0.16));
    border-radius: var(--haui-radius-pill);
    background: var(--haui-hardware-led-well);
    box-shadow: var(--haui-shadow-led-well);
    transition: background-color 150ms ease, box-shadow 150ms ease;
  }
  .haui-card-led[data-state="on"] {
    background: var(--haui-led-relay);
    box-shadow: 0 0 6px var(--haui-led-relay-glow), var(--haui-led-relay-shadow);
  }
  /* A button that switches an entity instead of its relay shows that entity. */
  .haui-card-led.entity[data-state="on"] {
    background: var(--haui-led-entity);
    box-shadow: 0 0 6px var(--haui-led-entity-glow), var(--haui-led-entity-shadow);
  }
  .haui-card-led-dot {
    width: max(3px, calc(var(--vp-hw-height) * 0.16));
    height: max(3px, calc(var(--vp-hw-height) * 0.16));
    align-self: center;
    border-radius: var(--haui-radius-round);
    background: var(--haui-hardware-led-well);
  }
  .haui-card-led-dot[data-state="on"] {
    background: var(--haui-led-relay);
    box-shadow: 0 0 5px var(--haui-led-relay-glow);
  }
  /* The panel itself: reachable or not, awake or dark, and what it runs. */
  .haui-card-status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 4px 12px;
    padding: 8px 16px 12px;
    font-size: var(--haui-text-caption);
  }
  .haui-card-status-device { display: inline-flex; min-width: 0; align-items: center; gap: 8px; }
  .haui-card-status-name {
    overflow: hidden;
    color: var(--primary-text-color, #212121);
    font-size: var(--haui-text-label);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-card-status-facts {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--secondary-text-color, #666);
    line-height: var(--haui-line-height-copy);
  }
  .haui-card-status-queued { display: inline-flex; align-items: center; gap: 4px; }
  .haui-card-status-queued ha-icon { --mdc-icon-size: 14px; }
  /* A card without a screen is a status tile: the row carries the whole card. */
  .haui-card-status:first-child { padding-top: 12px; }
  @media (prefers-reduced-motion: reduce) {
    .haui-card-led, .haui-card-led-dot { transition: none; }
  }
`;

