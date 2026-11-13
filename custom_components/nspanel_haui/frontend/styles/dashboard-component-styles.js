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
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-pill);
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
    border-color: color-mix(in srgb, var(--primary-color, #03a9f4) 45%, var(--divider-color, #e0e0e0));
  }
  .haui-button:disabled, .haui-icon-button:disabled { cursor: not-allowed; opacity: .55; }
  /* A single ring keeps keyboard focus consistent across editor controls. */
  .haui-button:focus-visible,
  .haui-icon-button:focus-visible,
  .haui-segmented-option:focus-visible,
  .haui-menu-item:focus-visible,
  .haui-row-action:focus-visible,
  .haui-device-rail-item:focus-visible,
  .haui-device-card-select:focus-visible,
  .haui-device-row-name:focus-visible,
  .haui-panel-row:focus-visible,
  .haui-panel-thumb:focus-visible,
  .haui-event-list > header button:focus-visible,
  .haui-pill button:focus-visible,
  .haui-item-row-main:focus-visible,
  .haui-panel-info-preview.is-toggle:focus-visible,
  .haui-panels-overview-role-tile:focus-visible,
  .haui-panel-catalog-option:focus-visible,
  .haui-panel-catalog-section > summary:focus-visible,
  .haui-panel-catalog-group > summary:focus-visible,
  button.haui-diag-tile:focus-visible,
  button.haui-diag-entity:focus-visible,
  .haui-conn-status-button:focus-visible,
  .haui-logs-filter button:focus-visible,
  .haui-switch:focus-visible,
  .haui-firmware-hero-action:focus-visible {
    outline: var(--haui-focus-ring);
    outline-offset: var(--haui-focus-offset);
  }
  .haui-panel-row:focus-visible, .haui-item-row-main:focus-visible { outline-offset: -2px; }
  .haui-pill button:focus-visible { outline-offset: 1px; }
  .haui-firmware-hero-action:focus-visible { outline-offset: -3px; }
  .haui-icon-button {
    display: inline-grid;
    width: 40px;
    height: 40px;
    place-items: center;
    border: 0;
    border-radius: var(--haui-radius-round);
    background: transparent;
    cursor: pointer;
  }
  .haui-icon-button:hover:not(:disabled) { background: var(--haui-surface-soft); }
  /* The actions at the end of a table row or card: Edit/Settings, then More. */
  .haui-row-action { width: 32px; height: 32px; flex: 0 0 auto; padding: 0; border-radius: var(--haui-radius-control); color: var(--secondary-text-color, #666); --mdc-icon-size: 18px; transition: background 120ms ease, color 120ms ease; }
  .haui-row-action:hover:not(:disabled), .haui-row-action[aria-expanded="true"] { background: var(--haui-surface-strong); color: var(--primary-text-color, #212121); }
  .haui-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: var(--haui-radius-pill);
    background: var(--secondary-background-color, #f5f5f5);
    font-size: var(--haui-text-caption);
    line-height: 1.3;
  }
  /* Tinted rather than filled, so a count shows on a hovered or open row as well;
     the tones below still colour it. */
  .haui-badge-count { box-sizing: border-box; min-width: 20px; justify-content: center; background: color-mix(in srgb, var(--secondary-text-color, #666) 12%, transparent); color: var(--secondary-text-color, #666); font-weight: 500; font-variant-numeric: tabular-nums; }
  .haui-badge-primary { background: color-mix(in srgb, var(--primary-color, #03a9f4) 14%, var(--card-background-color, #fff)); color: var(--primary-color, #03a9f4); }
  .haui-badge-success { background: var(--haui-good-soft); color: var(--haui-good); }
  .haui-badge-warning { background: var(--haui-warn-soft); color: var(--haui-warn); }
  .haui-badge-danger { background: var(--haui-bad-soft); color: var(--haui-bad); }
  .haui-status-dot { display: inline-block; width: 8px; height: 8px; flex: 0 0 auto; border-radius: var(--haui-radius-round); background: var(--disabled-text-color, #888); }
  .haui-status-dot-online { background: var(--haui-good); }
  .haui-status-dot-offline { background: var(--haui-bad); }
  .haui-status-dot-stale { background: var(--haui-warn); }
  .haui-status-dot-unknown { background: var(--secondary-text-color, #666); }
  .haui-surface { min-width: 0; overflow: hidden; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--card-background-color, #fff); }
  .haui-surface-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .haui-surface-heading:last-child { border-bottom: 0; }
  .haui-surface-heading-toggle { cursor: pointer; user-select: none; }
  .haui-surface-heading h2 { margin: 0; font-size: var(--haui-text-title); font-weight: 500; }
  .haui-surface-heading p { margin: 4px 0 0; color: var(--secondary-text-color, #666); font-size: var(--haui-text-label); }
  /* A status badge in a card heading keeps its size while the copy truncates. */
  .haui-surface-heading > .haui-badge { flex: 0 0 auto; }
  .haui-surface-heading-copy { min-width: 0; }
  .haui-surface-body { min-width: 0; padding: 12px 16px; }
  .haui-segmented { display: inline-flex; align-items: center; gap: 4px; padding: 4px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-radius-pill); background: var(--secondary-background-color, #f5f5f5); }
  .haui-segmented-option { display: inline-flex; min-height: 32px; align-items: center; gap: 4px; padding: 0 12px; border: 0; border-radius: var(--haui-radius-pill); color: var(--secondary-text-color); background: transparent; font: inherit; cursor: pointer; }
  .haui-segmented-option.active { color: var(--primary-text-color); background: var(--card-background-color, #fff); box-shadow: var(--haui-shadow-card); }
  .haui-segmented-option:disabled { cursor: not-allowed; opacity: .5; }
  .haui-field-error { display: block; margin-top: 4px; color: var(--error-color, #db4437); font-size: var(--haui-text-caption); }
  .haui-field-warning { display: block; margin-top: 4px; color: var(--haui-warn); font-size: var(--haui-text-caption); }
  .haui-empty-state { display: grid; justify-items: center; gap: 8px; padding: 32px 20px; color: var(--secondary-text-color, #666); text-align: center; }
  .haui-empty-state h2, .haui-empty-state p { margin: 0; }
  .haui-empty-state-icon { display: block; --mdc-icon-size: 28px; }
  .haui-empty-state-compact { display: block; padding: 20px 16px; font-size: var(--haui-text-caption); }
  .haui-empty-state-compact p { color: var(--secondary-text-color, #666); }
  .haui-empty-state-inset { display: block; padding: 12px; border: 1px dashed var(--divider-color, #e0e0e0); border-radius: var(--haui-radius-control); font-size: var(--haui-text-caption); }
  .haui-empty-state-horizontal { display: flex; min-height: 72px; align-items: center; justify-content: center; gap: 8px; padding: 12px 16px; font-size: var(--haui-text-label); font-weight: var(--ha-font-weight-medium, 500); }
  .haui-empty-state-horizontal .haui-empty-state-icon { display: grid; width: 28px; height: 28px; flex: 0 0 auto; place-items: center; border-radius: var(--haui-radius-round); color: var(--haui-good); background: var(--haui-good-soft); --mdc-icon-size: 16px; }
  .haui-popover { position: fixed; z-index: 30; box-sizing: border-box; max-width: min(360px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow-y: auto; padding: 12px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--card-background-color, #fff); box-shadow: 0 8px 28px #0003; }
  .haui-popover[role="menu"] { display: grid; gap: 4px; width: max-content; min-width: min(236px, calc(100vw - 24px)); padding: 4px; }
  .haui-menu-separator { height: 1px; margin: 4px 4px; background: var(--divider-color, #e0e0e0); }
  .haui-menu-item { display: flex; width: 100%; min-height: 40px; align-items: center; gap: 8px; padding: 4px 8px; border: 0; border-radius: var(--haui-radius-control); background: transparent; text-align: left; cursor: pointer; }
  .haui-menu-item:hover { background: var(--secondary-background-color, #f5f5f5); }
  .haui-menu-item.danger { color: var(--error-color, #db4437); }

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
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }
  .haui-notification-header h2 { margin: 0; font-size: var(--haui-text-title); }
  .haui-notification-list { display: grid; gap: 0; }
  .haui-notification-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
  }
  .haui-notification-icon { color: var(--primary-color); padding-top: 4px; }
  .haui-notification-content { flex: 1; min-width: 0; }
  .haui-notification-content strong { display: block; overflow-wrap: anywhere; }
  .haui-notification-content p { margin: 4px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
  .haui-notification-meta { display: flex; gap: 12px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  @media (prefers-reduced-motion: reduce) {
    .haui-button, .haui-row-action { transition: none; }
  }
`;
