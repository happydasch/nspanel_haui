import { css } from '../lit-import.js';

/** The dashboard card (card/card.js): the device's screen, edge to edge in its ha-card. */
export const cardStyles = css`
  :host { display: block; }
  .haui-card { overflow: hidden; }
  .haui-card-stage { position: relative; }
  /* Off: dark, as the panel is; disconnected: dimmed under its badge. */
  .haui-card-screen { filter: brightness(var(--vp-screen-brightness, 1)); }
  .haui-card-stage > .haui-badge { position: absolute; top: 8px; inset-inline-end: 8px; }
`;
