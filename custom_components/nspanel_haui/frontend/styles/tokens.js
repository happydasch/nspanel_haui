import { css } from '../lit-import.js';

/** Shared aliases for the Home Assistant theme and measured editor scale. */
export const dashboardTokens = css`
  :host {
    /* The base text is the label step, so an element without a type rule reads as body text
       instead of borrowing the body step, which is a card or section heading. */
    font-size: var(--haui-text-label);
    /* The ladder is the editor's own and one step below Home Assistant's own type (its body text
       is 15px to HA's 16px), so the dense screens read a little tighter; every step follows HA's
       font size setting, which is what the scale multiplies. */
    --haui-text-eyebrow: calc(10px * var(--ha-font-size-scale, 1));
    /* A pill's own step, one below the caption: a label on a tinted ground sits inside the row's
       text, so it reads smaller than the meta line beside it. */
    --haui-text-badge: calc(11px * var(--ha-font-size-scale, 1));
    --haui-text-caption: calc(12px * var(--ha-font-size-scale, 1));
    --haui-text-label: calc(13px * var(--ha-font-size-scale, 1));
    /* Between a name and a card's own title: a thing that opens a card but is not its heading,
       such as the device name under a Fleet card's preview. */
    --haui-text-subtitle: calc(14px * var(--ha-font-size-scale, 1));
    --haui-text-body: calc(15px * var(--ha-font-size-scale, 1));
    --haui-text-title: calc(17px * var(--ha-font-size-scale, 1));
    --haui-text-headline: calc(19px * var(--ha-font-size-scale, 1));
    --haui-text-display: calc(23px * var(--ha-font-size-scale, 1));
    --haui-line-height: var(--ha-line-height-normal, 1.6);
    --haui-line-height-tight: var(--ha-line-height-condensed, 1.2);
    --haui-line-height-copy: 1.4;
    --haui-space-1: var(--ha-space-1, 4px);
    --haui-space-2: var(--ha-space-2, 8px);
    --haui-space-3: var(--ha-space-3, 12px);
    --haui-space-4: var(--ha-space-4, 16px);
    --haui-space-5: var(--ha-space-5, 20px);
    --haui-space-6: var(--ha-space-6, 24px);
    --haui-space-7: var(--ha-space-7, 28px);
    --haui-space-8: var(--ha-space-8, 32px);
    --haui-space-10: var(--ha-space-10, 40px);
    /* The screens' content column stops here and centres, so a wide monitor does not stretch the
       cards and the device table across the window; the titlebar and the footer stay full-bleed. */
    --haui-content-max-width: 1440px;
    /* The sticky titlebar (styles/content.js); page content that pins to the
       viewport starts below it. */
    --haui-header-height: calc(var(--header-height, 56px) + var(--safe-area-inset-top, 0px));
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
    /* Text in a tone, mixed with the theme's text colour as close to the tone
       as 4.5:1 on the card, the soft surface and the tone's soft tint allows in
       light and dark themes. Each tone carries its own share because warning
       orange loses contrast fastest; the plain tones above stay for fills, bars
       and dots. */
    --haui-good-text: color-mix(in srgb, var(--haui-good) 65%, var(--primary-text-color, #212121));
    --haui-warn-text: color-mix(in srgb, var(--haui-warn) 50%, var(--primary-text-color, #212121));
    --haui-bad-text: color-mix(in srgb, var(--haui-bad) 70%, var(--primary-text-color, #212121));
    --haui-accent-text: color-mix(in srgb, var(--primary-color, #03a9f4) 55%, var(--primary-text-color, #212121));
    /* The same tone on an icon, which is a graphic (3:1) and so keeps the tone
       the text version gives up: as close to the tone as 3:1 on the card and on
       the tone's own soft tint allows in light and dark themes. */
    --haui-good-icon: color-mix(in srgb, var(--haui-good) 94%, var(--primary-text-color, #212121));
    --haui-warn-icon: color-mix(in srgb, var(--haui-warn) 71%, var(--primary-text-color, #212121));
    --haui-bad-icon: var(--haui-bad);
    --haui-surface-soft: var(--secondary-background-color, #f5f5f5);
    /* The band that opens and closes a card — its heading and its footer — is a step of the
       theme's own text colour in the card ground, so it stays neutral in every theme and lands at
       the same contrast against the card in a light one and a dark one (6% is ~1.1:1 either way).
       It is deliberately lighter than the theme's secondary surface, which is heavy enough in a
       light theme to read as a bar across the card. The plain soft surface stays for tiles, chips
       and hover fills, where a step would compete with the content sitting on it. One token, so
       every band in the editor moves together. */
    --haui-surface-band: color-mix(in srgb, var(--primary-text-color, #212121) 6%,
      var(--card-background-color, #fff));
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
