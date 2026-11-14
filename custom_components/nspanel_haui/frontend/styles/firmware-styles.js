import { css } from '../lit-import.js';

export const firmwareStyles = css`  /* ── Updates sidebar ────────────────────────────────────────────────
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
    gap: 12px;
    padding: 16px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .haui-firmware-sidebar > * { flex: 0 0 auto; }

  /* The status lead: a standard surface with a restrained status accent. */
  .haui-firmware-hero { --firmware-tone: var(--secondary-text-color, #666); overflow: hidden; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--haui-card-background); }
  .haui-firmware-status-success { --firmware-tone: var(--haui-good); }
  .haui-firmware-status-warning { --firmware-tone: var(--haui-warn); }
  .haui-firmware-status-danger { --firmware-tone: var(--haui-bad); }
  .haui-firmware-status-busy { --firmware-tone: var(--primary-color, #03a9f4); }
  .haui-firmware-hero-body { display: flex; align-items: center; gap: 12px; padding: 16px; }
  .haui-firmware-status-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: var(--haui-radius-control); background: color-mix(in srgb, var(--firmware-tone) 12%, var(--haui-card-background)); color: var(--firmware-tone); --mdc-icon-size: 20px; }
  .haui-firmware-status-busy .haui-firmware-status-icon ha-icon { animation: haui-firmware-spin 1s linear infinite; }
  .haui-firmware-hero-copy { min-width: 0; }
  .haui-firmware-hero-copy strong { display: block; font-size: var(--haui-text-title); font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }
  .haui-firmware-hero-copy p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: 1.45; overflow-wrap: anywhere; }
  .haui-firmware-hero-action { display: flex; width: 100%; min-height: 42px; align-items: center; justify-content: center; gap: 8px; padding: 8px 16px; border: 0; border-radius: 0; border-top: 1px solid var(--divider-color, #e0e0e0); color: var(--primary-color, #03a9f4); background: transparent; font: inherit; font-size: var(--haui-text-label); font-weight: 500; cursor: pointer; --mdc-icon-size: 18px; }
  .haui-firmware-hero-action:hover:not(:disabled) { background: var(--haui-surface-soft); }
  .haui-firmware-hero-action:disabled { cursor: progress; opacity: .55; }
  @keyframes haui-firmware-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .haui-firmware-status-busy .haui-firmware-status-icon ha-icon { animation: none; } }

  /* Installed versions: compact rows with a small inline install action. */
  .haui-firmware-versions { margin: 0; }
  .haui-firmware-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 12px 16px; }
  .haui-firmware-row + .haui-firmware-row { border-top: 1px solid var(--divider-color, #e0e0e0); }
  .haui-firmware-row dt { display: grid; grid-template-columns: 28px minmax(0, 1fr); align-items: center; gap: 8px; }
  .haui-firmware-row-icon { display: grid; width: 28px; height: 28px; place-items: center; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  .haui-firmware-row-name { min-width: 0; font-size: var(--haui-text-body); font-weight: 600; overflow-wrap: anywhere; }
  .haui-firmware-row-name .haui-badge { margin-inline-start: 8px; font-weight: 500; vertical-align: baseline; }
  .haui-firmware-row-name small { display: block; margin-top: 4px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 400; line-height: 1.4; }
  .haui-firmware-row dd { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin: 0; }
  .haui-firmware-row-version { color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); white-space: nowrap; }
  .haui-firmware-row ha-button { flex: 0 0 auto; }
  .haui-firmware-row ha-button ha-icon { --mdc-icon-size: 18px; }
  .haui-firmware-sidebar > .haui-update-error {
    margin: 0;
    padding: 8px 12px;
    border-radius: var(--haui-radius-control);
    background: var(--haui-bad-soft);
    color: var(--haui-bad);
    font-size: var(--haui-text-label);
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  /* Update settings: a heading, a master strip, the decisions, then the folded rest. */
  .haui-firmware-settings-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); color: var(--primary-color, #03a9f4); --mdc-icon-size: 20px; }
  .haui-update-header { align-items: flex-start; padding: 12px 16px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .haui-update-header .haui-surface-heading-copy { min-width: 0; }
  .haui-update-header h2 { margin: 0; font-size: var(--haui-text-title); font-weight: 500; }
  .haui-update-header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: 1.45; }
  .haui-update-master { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color, #e0e0e0); background: var(--haui-surface-soft); }
  .haui-update-master .haui-switch { flex: 0 0 auto; margin-top: 4px; }
  .haui-update-group { display: grid; gap: 12px; padding: 12px 16px 16px; }
  .haui-update-group + .haui-update-group { border-top: 1px solid var(--divider-color, #e0e0e0); }
  .haui-update-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .haui-update-row-copy { min-width: 0; }
  .haui-update-row-label { display: block; font-size: var(--haui-text-body); font-weight: 500; line-height: 1.35; }
  .haui-update-row-hint { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.45; }
  .haui-update-row > .haui-switch { flex: 0 0 auto; margin-top: 4px; }
  .haui-update-field { display: grid; gap: 4px; }
  .haui-update-field.haui-field { margin-bottom: 0; }
  .haui-update-field label { font-size: var(--haui-text-body); font-weight: 500; line-height: 1.35; }
  .haui-update-field > .haui-segmented { justify-self: start; }
  /* What most devices leave alone: folded away until a manifest URL is set. */
  .haui-update-advanced > summary { display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 500; cursor: pointer; list-style: none; }
  .haui-update-advanced > summary::-webkit-details-marker { display: none; }
  .haui-update-advanced > summary::before { content: ""; width: 0; height: 0; flex: 0 0 auto; border-top: 4px solid transparent; border-bottom: 4px solid transparent; border-left: 5px solid currentColor; transition: transform 140ms ease; }
  .haui-update-advanced[open] > summary { color: var(--primary-text-color); }
  .haui-update-advanced[open] > summary::before { transform: rotate(90deg); }
  .haui-update-advanced-body { display: grid; gap: 12px; padding-top: 12px; }
  .haui-update-off-note { margin: 0; padding: 12px 16px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-update-retry { margin: 0; padding: 8px 16px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-update-retry.is-stopped { color: var(--error-color, #db4437); }
  .haui-update-scheduled { display: grid; gap: 8px; padding: 12px 16px; }
  .haui-update-scheduled p { margin: 0; font-size: var(--haui-text-body); }
  .haui-update-scheduled-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .haui-update-progress { display: grid; gap: 8px; padding: 12px 16px; }
  .haui-update-steps { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; font-size: var(--haui-text-caption); color: var(--secondary-text-color); }
  .haui-update-steps li.is-current { color: var(--primary-text-color); font-weight: 600; }
  .haui-update-progress-bar { height: 4px; border-radius: var(--haui-radius-pill); background: var(--divider-color, #e0e0e0); overflow: hidden; }
  .haui-update-progress-bar span { display: block; height: 100%; width: var(--haui-update-progress, 0%); background: var(--primary-color, #03a9f4); }
  .haui-update-progress-time { margin: 0; font-size: var(--haui-text-caption); color: var(--secondary-text-color); }
  .haui-update-progress.is-failed .haui-update-progress-time { color: var(--error-color, #db4437); }
  /* The install picker takes the card look of the sidebar it opens in. */
  .haui-firmware-sidebar .haui-update-picker { padding: 12px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--haui-card-background); }
`;
