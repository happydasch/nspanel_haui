import { css } from '../lit-import.js';

export const dashboardComponentStyles = css`
  .haui-button,
  .haui-icon-button,
  .haui-segmented-option,
  .haui-menu-item {
    color: var(--primary-text-color, #212121);
    font: inherit;
  }
  .haui-button {
    display: inline-flex;
    min-height: 40px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 16px;
    border: 1px solid var(--divider-color, #ddd);
    border-radius: 999px;
    background: var(--card-background-color, #fff);
    white-space: nowrap;
    cursor: pointer;
    transition: background 120ms ease, border-color 120ms ease;
  }
  .haui-button-primary { border-color: var(--primary-color, #03a9f4); background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
  .haui-button-primary:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color, #03a9f4) 85%, #000); border-color: color-mix(in srgb, var(--primary-color, #03a9f4) 85%, #000); }
  .haui-button-quiet { border-color: transparent; background: transparent; }
  /* A plain surface tint is invisible on a white card, so the hover also tints the border. */
  .haui-button-outline:hover:not(:disabled), .haui-button-quiet:hover:not(:disabled) {
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 10%, var(--card-background-color, #fff));
    border-color: color-mix(in srgb, var(--primary-color, #03a9f4) 45%, var(--divider-color, #ddd));
  }
  .haui-button:disabled, .haui-icon-button:disabled { cursor: not-allowed; opacity: .55; }
  .haui-button:focus-visible, .haui-icon-button:focus-visible,
  .haui-segmented-option:focus-visible, .haui-menu-item:focus-visible {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 2px;
  }
  .haui-icon-button {
    display: inline-grid;
    width: 40px;
    height: 40px;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: transparent;
    cursor: pointer;
  }
  .haui-icon-button:hover:not(:disabled) { background: var(--haui-surface-soft); }
  /* The actions at the end of a table row or card: Edit/Settings, then More. */
  .haui-row-action { width: 32px; height: 32px; flex: 0 0 auto; padding: 0; border-radius: 8px; color: var(--secondary-text-color, #666); --mdc-icon-size: 18px; transition: background 120ms ease, color 120ms ease; }
  .haui-row-action:hover:not(:disabled), .haui-row-action[aria-expanded="true"] { background: var(--haui-surface-strong); color: var(--primary-text-color, #212121); }
  .haui-badge, .haui-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color, #eee);
    font-size: 12px;
    line-height: 1.3;
  }
  .haui-badge-success { background: var(--haui-good-soft); color: var(--haui-good); }
  .haui-badge-warning { background: var(--haui-warn-soft); color: var(--haui-warn); }
  .haui-badge-danger { background: var(--haui-bad-soft); color: var(--haui-bad); }
  .haui-status-dot { display: inline-block; width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; background: var(--disabled-text-color, #888); }
  .haui-status-dot-online { background: var(--haui-good); }
  .haui-status-dot-offline { background: var(--haui-bad); }
  .haui-status-dot-stale { background: var(--haui-warn); }
  .haui-surface { min-width: 0; overflow: hidden; border: 1px solid var(--divider-color, #ddd); border-radius: 12px; background: var(--card-background-color, #fff); }
  .haui-surface-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--divider-color, #ddd); }
  .haui-surface-heading:last-child { border-bottom: 0; }
  .haui-surface-heading-toggle { cursor: pointer; user-select: none; }
  .haui-surface-heading h2 { margin: 0; font-size: 16px; font-weight: 500; }
  .haui-surface-heading p { margin: 4px 0 0; color: var(--secondary-text-color, #666); font-size: 13px; }
  /* A status badge in a card heading keeps its size while the copy truncates. */
  .haui-surface-heading > .haui-badge { flex: 0 0 auto; }
  .haui-surface-heading-copy { min-width: 0; }
  .haui-surface-body { min-width: 0; padding: 14px 18px; }
  .haui-surface-flush .haui-surface-body { padding: 0; }
  .haui-surface-gradient { border-color: transparent; background: linear-gradient(135deg, var(--primary-color, #009ac7), #004156); color: #fff; }
  .haui-segmented { display: inline-flex; gap: 2px; padding: 3px; border: 1px solid var(--divider-color, #ddd); border-radius: 999px; background: var(--secondary-background-color, #eee); }
  .haui-segmented-option { min-height: 30px; padding: 0 12px; border: 0; border-radius: 999px; background: transparent; cursor: pointer; }
  .haui-segmented-option.active { background: var(--card-background-color, #fff); box-shadow: 0 1px 2px #0002; }
  .haui-field-error { color: var(--error-color, #b00020); font-size: 12px; }
  .haui-empty-state { display: grid; justify-items: center; gap: 8px; padding: 32px 20px; color: var(--secondary-text-color, #666); text-align: center; }
  .haui-empty-state h2, .haui-empty-state p { margin: 0; }
  .haui-popover { position: fixed; z-index: 30; box-sizing: border-box; max-width: min(360px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow-y: auto; padding: 12px; border: 1px solid var(--divider-color, #ddd); border-radius: 12px; background: var(--card-background-color, #fff); box-shadow: 0 8px 28px #0003; }
  .haui-popover[role="menu"] { display: grid; gap: 2px; width: max-content; min-width: min(236px, calc(100vw - 24px)); padding: 6px; }
  .haui-menu-separator { height: 1px; margin: 5px 4px; background: var(--divider-color, #ddd); }
  .haui-menu-item { display: flex; width: 100%; min-height: 40px; align-items: center; gap: 10px; padding: 6px 10px; border: 0; border-radius: 6px; background: transparent; text-align: left; cursor: pointer; }
  .haui-menu-item:hover { background: var(--secondary-background-color, #eee); }
  .haui-menu-item.danger { color: var(--error-color, #b00020); }

  .haui-notification-popover {
    position: fixed;
    z-index: 30;
    top: 64px;
    right: 20px;
    width: min(420px, calc(100vw - 32px));
    max-width: min(420px, calc(100vw - 32px));
    max-height: min(70vh, 560px);
    overflow-y: auto;
    padding: 0;
  }
  .haui-notification-header {
    position: sticky;
    top: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    background: var(--card-background-color, #fff);
    border-bottom: 1px solid var(--divider-color, #ddd);
  }
  .haui-notification-header h2 { margin: 0; font-size: 16px; }
  .haui-notification-list { display: grid; gap: 0; }
  .haui-notification-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--divider-color, #ddd);
  }
  .haui-notification-icon { color: var(--primary-color); padding-top: 2px; }
  .haui-notification-content { flex: 1; min-width: 0; }
  .haui-notification-content strong { display: block; overflow-wrap: anywhere; }
  .haui-notification-content p { margin: 6px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
  .haui-notification-meta { display: flex; gap: 12px; color: var(--secondary-text-color); font-size: 12px; }
  .haui-notification-empty { margin: 0; padding: 20px 16px; color: var(--secondary-text-color); }
  /* ── Updates sidebar ────────────────────────────────────────────────
     Its body scrolls inside the sidebar's strip: a column of cards, the
     status lead first, then the installed versions, then the settings. */
  .haui-firmware-sidebar {
    display: flex;
    box-sizing: border-box;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: 16px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .haui-firmware-sidebar > * { flex: 0 0 auto; }

  /* The status lead: a standard surface with a restrained status accent. */
  .haui-firmware-hero { --haui-update-tone: var(--secondary-text-color, #666); overflow: hidden; border: 1px solid var(--divider-color, #ddd); border-radius: var(--haui-card-radius); background: var(--haui-card-background); }
  .haui-firmware-status-success { --haui-update-tone: var(--haui-good); }
  .haui-firmware-status-warning { --haui-update-tone: var(--haui-warn); }
  .haui-firmware-status-danger { --haui-update-tone: var(--haui-bad); }
  .haui-firmware-status-busy { --haui-update-tone: var(--primary-color, #03a9f4); }
  .haui-firmware-hero-body { display: flex; align-items: center; gap: 14px; padding: 16px; }
  .haui-firmware-status-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: 10px; background: color-mix(in srgb, var(--haui-update-tone) 12%, var(--haui-card-background)); color: var(--haui-update-tone); --mdc-icon-size: 20px; }
  .haui-firmware-status-busy .haui-firmware-status-icon ha-icon { animation: haui-firmware-spin 1s linear infinite; }
  .haui-firmware-hero-copy { min-width: 0; }
  .haui-firmware-hero-copy strong { display: block; font-size: 16px; font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }
  .haui-firmware-hero-copy p { margin: 3px 0 0; color: var(--secondary-text-color); font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }
  .haui-firmware-hero-action { display: flex; width: 100%; min-height: 42px; align-items: center; justify-content: center; gap: 7px; padding: 8px 16px; border: 0; border-top: 1px solid var(--divider-color, #ddd); color: var(--primary-color, #03a9f4); background: transparent; font: inherit; font-size: 13px; font-weight: 500; cursor: pointer; --mdc-icon-size: 18px; }
  .haui-firmware-hero-action:hover:not(:disabled) { background: var(--haui-surface-soft); }
  .haui-firmware-hero-action:focus-visible { outline: 2px solid var(--haui-update-tone); outline-offset: -3px; }
  .haui-firmware-hero-action:disabled { cursor: progress; opacity: .55; }
  @keyframes haui-firmware-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .haui-firmware-status-busy .haui-firmware-status-icon ha-icon { animation: none; } }

  /* Installed versions: compact rows with a small inline install action. */
  .haui-firmware-versions { margin: 0; }
  .haui-firmware-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 12px 16px; }
  .haui-firmware-row + .haui-firmware-row { border-top: 1px solid var(--divider-color, #ddd); }
  .haui-firmware-row dt { display: grid; grid-template-columns: 28px minmax(0, 1fr); align-items: center; gap: 10px; }
  .haui-firmware-row-icon { display: grid; width: 28px; height: 28px; place-items: center; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  .haui-firmware-row-name { min-width: 0; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
  .haui-firmware-row-name .haui-badge { margin-inline-start: 8px; font-weight: 500; vertical-align: baseline; }
  .haui-firmware-row-name small { display: block; margin-top: 3px; color: var(--secondary-text-color); font-size: 12px; font-weight: 400; line-height: 1.4; }
  .haui-firmware-row dd { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin: 0; }
  .haui-firmware-row-version { color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: 12px; white-space: nowrap; }
  .haui-firmware-row ha-button { flex: 0 0 auto; }
  .haui-firmware-row ha-button ha-icon { --mdc-icon-size: 18px; }
  .haui-firmware-sidebar > .device-update-error {
    margin: 0;
    padding: 10px 12px;
    border-radius: 8px;
    background: var(--haui-bad-soft);
    color: var(--haui-bad);
    font-size: 13px;
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  /* Update settings: a heading, a master strip, then one group per concern. */
  .haui-firmware-settings-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: 10px; background: var(--haui-surface-soft); color: var(--primary-color, #03a9f4); --mdc-icon-size: 20px; }
  .haui-update-header { display: flex; align-items: flex-start; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--divider-color, #ddd); }
  .haui-update-header-copy { min-width: 0; }
  .haui-update-header-copy h2 { margin: 0; font-size: 16px; font-weight: 500; }
  .haui-update-header-copy p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: 13px; line-height: 1.45; }
  .haui-update-master { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; padding: 14px 18px; border-bottom: 1px solid var(--divider-color, #ddd); background: var(--haui-surface-soft); }
  .haui-update-master .native-toggle { flex: 0 0 auto; margin-top: 2px; }
  .haui-update-group { display: grid; gap: 12px; padding: 14px 18px 16px; }
  .haui-update-settings-group { gap: 0; padding: 0; }
  .haui-update-channel { display: grid; gap: 12px; padding: 14px 18px 16px; }
  .haui-update-group + .haui-update-group { border-top: 1px solid var(--divider-color, #ddd); }
  .haui-update-group-title { display: flex; align-items: center; gap: 7px; margin: 0; color: var(--secondary-text-color); font-size: 11px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; --mdc-icon-size: 14px; }
  .haui-update-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
  .haui-update-row-copy { min-width: 0; }
  .haui-update-row-label { display: block; font-size: 14px; font-weight: 500; line-height: 1.35; }
  .haui-update-row-hint { margin: 3px 0 0; color: var(--secondary-text-color); font-size: 12px; line-height: 1.45; }
  .haui-update-row > .native-toggle { flex: 0 0 auto; margin-top: 2px; }
  .haui-update-field { display: grid; gap: 6px; }
  .haui-update-field-label, .haui-update-field label { font-size: 14px; font-weight: 500; line-height: 1.35; }
  .haui-update-field-control { display: flex; align-items: center; gap: 8px; }
  .haui-update-field-control .native-input { width: 96px; }
  .haui-update-field-control span { color: var(--secondary-text-color); font-size: 12px; }
  .haui-update-field > .haui-segmented { justify-self: start; }
  /* The manifest URL is an override: folded away until one is set. */
  .haui-update-advanced { padding-top: 11px; border-top: 1px dashed var(--divider-color, #ddd); }
  .haui-update-advanced > summary { display: flex; align-items: center; gap: 7px; color: var(--secondary-text-color); font-size: 12px; font-weight: 500; cursor: pointer; list-style: none; }
  .haui-update-advanced > summary::-webkit-details-marker { display: none; }
  .haui-update-advanced > summary::before { content: ""; width: 0; height: 0; flex: 0 0 auto; border-top: 4px solid transparent; border-bottom: 4px solid transparent; border-left: 5px solid currentColor; transition: transform 140ms ease; }
  .haui-update-advanced[open] > summary { color: var(--primary-text-color); }
  .haui-update-advanced[open] > summary::before { transform: rotate(90deg); }
  .haui-update-set { padding: 1px 7px; border-radius: 999px; background: var(--haui-warn-soft); color: var(--haui-warn); font-size: 10px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
  .haui-update-advanced > .haui-update-field { margin-top: 10px; }
  .haui-update-off-note { margin: 0; padding: 14px 18px; color: var(--secondary-text-color); font-size: 12px; }
  /* The install picker takes the card look of the sidebar it opens in. */
  .haui-firmware-sidebar .device-update-picker { padding: 14px; border: 1px solid var(--divider-color, #ddd); border-radius: var(--haui-card-radius); background: var(--haui-card-background); }
`;
