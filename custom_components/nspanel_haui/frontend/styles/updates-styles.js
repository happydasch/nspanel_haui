import { css } from '../lit-import.js';

export const updatesStyles = css`  /* ── Updates sidebar ────────────────────────────────────────────────
     Its body scrolls inside the sidebar's strip: a column of cards, the
     status lead first, then the installed versions, then the settings. */
  .haui-update-sidebar {
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
  .haui-update-sidebar > * { flex: 0 0 auto; }

  /* One surface for the status, check action and installed versions. */
  .haui-update-overview { overflow: hidden; }
    .haui-update-summary { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .haui-update-summary-status { --update-tone: var(--secondary-text-color, #666); display: flex; min-width: 0; flex: 1 1 auto; align-items: center; gap: 8px; }
  .haui-update-status-success { --update-tone: var(--haui-good); }
  .haui-update-status-warning { --update-tone: var(--haui-warn); }
  .haui-update-status-danger { --update-tone: var(--haui-bad); }
  .haui-update-status-busy { --update-tone: var(--primary-color, #03a9f4); }
  .haui-update-status-icon { display: grid; width: 24px; height: 24px; flex: 0 0 auto; place-items: center; color: var(--update-tone); --mdc-icon-size: 20px; }
  .haui-update-status-busy .haui-update-status-icon ha-icon { animation: haui-update-spin 1s linear infinite; }
  .haui-update-summary-copy { min-width: 0; }
  .haui-update-summary-copy strong { display: block; font-size: var(--haui-text-body); font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }
  .haui-update-summary-copy p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.4; overflow-wrap: anywhere; }
  .haui-update-check-action { display: flex; padding: 8px 12px; border-top: 1px solid var(--divider-color, #e0e0e0); }
  .haui-update-check-action ha-icon { --mdc-icon-size: 18px; }
  @keyframes haui-update-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .haui-update-status-busy .haui-update-status-icon ha-icon { animation: none; } }

  /* Installed versions and their optional per-component update actions. */
  .haui-update-versions { margin: 0; padding: 0; }
  .haui-update-version { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px; padding: 8px 12px; }
  .haui-update-version + .haui-update-version { border-top: 1px solid var(--divider-color, #e0e0e0); }
  .haui-update-version dt { display: grid; grid-template-columns: 24px minmax(0, 1fr); align-items: center; gap: 8px; }
  .haui-update-version-icon { display: grid; width: 24px; height: 24px; place-items: center; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  .haui-update-version-name { min-width: 0; font-size: var(--haui-text-body); font-weight: 600; overflow-wrap: anywhere; }
  .haui-update-version-name .haui-badge { margin-inline-start: 8px; font-weight: 500; vertical-align: baseline; }
  .haui-update-version-name small { display: block; margin-top: 4px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 400; line-height: 1.4; }
  .haui-update-version dd { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin: 0; }
  .haui-update-version-number { color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); white-space: nowrap; }
  .haui-update-version ha-button { flex: 0 0 auto; }
  .haui-update-sidebar > .haui-update-error {
    margin: 0;
    padding: 8px 12px;
    border-radius: var(--haui-radius-control);
    background: var(--haui-bad-soft);
    color: var(--haui-bad);
    font-size: var(--haui-text-label);
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  /* Update settings: a heading with the master switch, the decisions, then the folded rest. */
  .haui-update-settings-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); color: var(--primary-color, #03a9f4); --mdc-icon-size: 20px; }
  .haui-update-header { padding: 12px 16px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  /* The copy fills the row between the icon and the switch, which keeps the right edge. */
  .haui-update-header .haui-surface-heading-copy { min-width: 0; flex: 1 1 auto; }
  .haui-update-header h2 { margin: 0; font-size: var(--haui-text-title); font-weight: 500; }
  .haui-update-header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: 1.45; }
  .haui-update-header .haui-switch { flex: 0 0 auto; }
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
  /* A two-way choice: label and toggle share a row, the hint runs below both. */
  .haui-update-choice { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 4px 12px; }
  .haui-update-choice > .haui-update-row-hint { grid-column: 1 / -1; margin: 0; }
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
  .haui-update-sidebar .haui-update-picker { padding: 12px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--haui-card-background); }
`;
