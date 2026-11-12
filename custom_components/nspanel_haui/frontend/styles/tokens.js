import { css } from '../lit-import.js';

/** Shared dashboard-only aliases; Home Assistant remains the source of theme values. */
export const dashboardTokens = css`
  :host {
    --haui-good: var(--success-color, #43a047);
    --haui-warn: var(--warning-color, #ffa600);
    --haui-bad: var(--error-color, #db4437);
    /* Tints are mixed into the card colour, so they are dark in a dark theme. */
    --haui-good-soft: color-mix(in srgb, var(--haui-good) 16%, var(--card-background-color, #fff));
    --haui-warn-soft: color-mix(in srgb, var(--haui-warn) 16%, var(--card-background-color, #fff));
    --haui-bad-soft: color-mix(in srgb, var(--haui-bad) 16%, var(--card-background-color, #fff));
    --haui-surface-soft: var(--secondary-background-color, #f5f5f5);
    --haui-surface-strong: var(--divider-color, #e0e0e0);
    --haui-border-strong: var(--secondary-text-color, #666);
    /* light-dark() follows the color-scheme Home Assistant sets for the active theme. */
    --haui-screen: radial-gradient(ellipse at 50% 8%, light-dark(#f8fafb, #2a343d) 0,
      light-dark(#e6eaee, #171d23) 58%, light-dark(#d7dce1, #0e1216) 100%);
    --haui-live-surface: color-mix(in srgb, #1f8a78 10%, var(--card-background-color, #fff));
    --haui-live-border: color-mix(in srgb, #1f8a78 45%, var(--divider-color, #ddd));
    --haui-mono: var(--ha-font-family-code, ui-monospace, "SFMono-Regular", Menlo, monospace);
    --haui-shadow-card: 0 1px 3px rgba(0, 0, 0, .12);
    /* ha-card's own variables, so a theme that restyles Home Assistant's cards restyles ours. */
    --haui-card-background: var(--ha-card-background, var(--card-background-color, #fff));
    --haui-card-border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
    --haui-card-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
    --haui-card-shadow: var(--ha-card-box-shadow, none);
    --haui-bezel: #171a1c;
  }
`;
