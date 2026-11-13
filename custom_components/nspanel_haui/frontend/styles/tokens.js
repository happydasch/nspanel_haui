import { css } from '../lit-import.js';

/** Shared aliases for the Home Assistant theme and measured editor scale. */
export const dashboardTokens = css`
  :host {
    --haui-text-eyebrow: var(--ha-font-size-xs, 10px);
    --haui-text-caption: var(--ha-font-size-s, 12px);
    --haui-text-label: 13px;
    --haui-text-body: var(--ha-font-size-m, 14px);
    --haui-text-title: var(--ha-font-size-l, 16px);
    --haui-text-display: var(--ha-font-size-2xl, 24px);
    --haui-line-height: var(--ha-line-height-normal, 1.6);
    --haui-space-1: var(--ha-space-1, 4px);
    --haui-space-2: var(--ha-space-2, 8px);
    --haui-space-3: var(--ha-space-3, 12px);
    --haui-space-4: var(--ha-space-4, 16px);
    --haui-space-5: var(--ha-space-5, 20px);
    --haui-space-6: var(--ha-space-6, 24px);
    --haui-space-7: var(--ha-space-7, 28px);
    --haui-space-8: var(--ha-space-8, 32px);
    --haui-space-10: var(--ha-space-10, 40px);
    --haui-radius-control: var(--ha-border-radius-md, 8px);
    --haui-radius-pill: var(--ha-border-radius-pill, 999px);
    --haui-radius-round: 50%;
    --haui-focus-ring: 2px solid var(--primary-color, #03a9f4);
    --haui-focus-offset: 2px;
    --haui-good: var(--success-color, #43a047);
    --haui-warn: var(--warning-color, #ffa600);
    --haui-bad: var(--error-color, #db4437);
    --haui-good-soft: color-mix(in srgb, var(--haui-good) 16%, var(--card-background-color, #fff));
    --haui-warn-soft: color-mix(in srgb, var(--haui-warn) 16%, var(--card-background-color, #fff));
    --haui-bad-soft: color-mix(in srgb, var(--haui-bad) 16%, var(--card-background-color, #fff));
    --haui-surface-soft: var(--secondary-background-color, #f5f5f5);
    --haui-surface-strong: var(--divider-color, #e0e0e0);
    --haui-border-strong: var(--secondary-text-color, #666);
    --haui-scrim: rgb(0 0 0 / 42%);
    --haui-screen: radial-gradient(ellipse at 50% 8%, light-dark(#f8fafb, #2a343d) 0,
      light-dark(#e6eaee, #171d23) 58%, light-dark(#d7dce1, #0e1216) 100%);
    --haui-screen-off: #000;
    --haui-shadow-led-well: inset 0 1px 2px rgb(0 0 0 / 67%);
    --haui-live-surface: color-mix(in srgb, #1f8a78 10%, var(--card-background-color, #fff));
    --haui-live-border: color-mix(in srgb, #1f8a78 45%, var(--divider-color, #e0e0e0));
    --haui-live-preview: radial-gradient(ellipse at 50% 8%, light-dark(#f1f8f6, #294b48) 0,
      light-dark(#dcece8, #1c3534) 58%, light-dark(#cbe0db, #142624) 100%);
    --haui-led-relay: #58b3ff;
    --haui-led-relay-glow: #55adff;
    --haui-led-relay-shadow: 0 0 15px #308bffb3;
    --haui-led-entity: #ffd23f;
    --haui-led-entity-glow: #ffcc33;
    --haui-led-entity-shadow: 0 0 15px #ffb300b3;
    --haui-hardware-button: #22252b;
    --haui-hardware-button-active: #292d34;
    --haui-hardware-button-border: #34383f;
    --haui-hardware-led-well: #20242a;
    --haui-shadow-device-preview: 0 2px 8px rgb(0 0 0 / 40%);
    --haui-wifi-good: #7cb342;
    --haui-mono: var(--ha-font-family-code, ui-monospace, "SFMono-Regular", Menlo, monospace);
    --haui-shadow-card: 0 1px 3px rgb(0 0 0 / 12%);
    --haui-shadow-overlay: 0 12px 32px rgb(0 0 0 / 24%);
    --haui-card-background: var(--ha-card-background, var(--card-background-color, #fff));
    --haui-card-border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
    --haui-card-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
    --haui-card-shadow: var(--ha-card-box-shadow, none);
    --haui-bezel: #171a1c;
  }
`;
