import { css } from '../lit-import.js';

/** Device workspace panel groups: band headers, rows, thumbnails, drop zones. */
export const panelListStyles = css`
  .haui-panel-groups { display: flex; flex-direction: column; }
  .haui-panel-group { display: flex; flex-direction: column; }
  .haui-panel-group + .haui-panel-group { border-top: 1px solid var(--divider-color); }
  .haui-panel-group-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 14px 16px 10px;
    background: var(--haui-surface-soft);
    border-bottom: 1px solid var(--divider-color);
  }
  .haui-panel-group-heading strong { font-size: 14px; font-weight: 600; }
  .haui-panel-group-heading span { color: var(--secondary-text-color); font-size: 12px; }
  .haui-panel-group-title { display: flex; min-width: 0; align-items: center; gap: 2px; }
  .haui-panel-group-toggle { width: 28px; height: 28px; flex: 0 0 auto; --mdc-icon-size: 20px; }
  .haui-panel-list { display: flex; min-height: 48px; flex-direction: column; }
  .haui-panel-list[hidden] { display: none; }
  .haui-panel-row {
    display: grid;
    grid-template-columns: 28px auto minmax(0, 1fr) auto auto auto;
    align-items: center;
    gap: 12px;
    min-height: 58px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--divider-color);
    cursor: pointer;
    transition: background 120ms ease, opacity 150ms ease;
  }
  .haui-panel-row:hover { background: var(--haui-surface-soft); }
  /* The row the side card describes: a tint and an edge marker, kept while hovered. */
  .haui-panel-row.is-selected,
  .haui-panel-row.is-selected:hover {
    background: color-mix(in srgb, var(--primary-color) 10%, transparent);
    box-shadow: inset 3px 0 0 var(--primary-color);
  }
  .haui-panel-row:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
  .haui-panel-row.is-dragging { opacity: .5; }
  .haui-panel-row.is-drop-before { box-shadow: inset 0 2px 0 var(--primary-color); }
  .haui-panel-row.is-drop-after { box-shadow: inset 0 -2px 0 var(--primary-color); }
  .haui-panel-group.is-drop-target > .haui-panel-group-heading { box-shadow: inset 0 -2px 0 var(--primary-color); }
  /* Every row keeps the grip column, so rows without a grip line up with the others. */
  .haui-panel-row-grip { display: flex; align-self: stretch; margin: -8px 0 -8px -8px; }
  /* The grip fills the row's height, so it is easy to grab. */
  .haui-panel-handle {
    display: inline-flex;
    flex: 1 1 auto;
    align-items: center;
    justify-content: center;
    color: var(--disabled-text-color);
    cursor: grab;
  }
  .haui-panel-handle:hover { color: var(--primary-text-color); }
  .haui-panel-handle.is-disabled { opacity: .4; cursor: not-allowed; }
  .haui-panel-handle.is-disabled:hover { color: var(--disabled-text-color); }
  .haui-panel-handle ha-icon { --mdc-icon-size: 18px; }
  .haui-panel-row-main { display: flex; min-width: 0; align-items: center; flex-wrap: wrap; gap: 4px 8px; }
  .haui-panel-row-title {
    overflow: hidden;
    max-width: 100%;
    padding: 0;
    border: 0;
    color: var(--primary-text-color);
    background: transparent;
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    text-align: start;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }
  .haui-panel-row-title:disabled { cursor: default; }
  .haui-panel-row-sub { color: var(--secondary-text-color); font-size: 11px; }
  .haui-panel-row-lock { color: var(--secondary-text-color); font-size: 11px; font-style: italic; }
  .haui-panel-row-key {
    color: var(--secondary-text-color);
    font-family: var(--haui-mono);
    font-size: 11px;
    white-space: nowrap;
  }
  .haui-panel-row-count { color: var(--secondary-text-color); font-size: 11px; white-space: nowrap; }
  /* Wide enough for Edit and More, so More lines up in rows that only have it. */
  .haui-panel-row-actions { display: flex; min-width: 66px; align-items: center; justify-content: flex-end; gap: 2px; }
  .haui-panel-thumb {
    position: relative;
    display: block;
    width: 72px;
    height: 51px;
    flex: 0 0 auto;
    overflow: hidden;
    padding: 0;
    border: 1px solid var(--divider-color);
    border-radius: 6px;
    background: var(--haui-screen);
    font: inherit;
    cursor: zoom-in;
  }
  .haui-panel-thumb:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-panel-thumb.portrait { width: 40px; height: 60px; }
  .haui-panel-thumb-view { display: block; width: 100%; height: 100%; }
  /* The enlarged preview: the same render, lifted out of the row beside its thumbnail. */
  .haui-panel-thumb.is-zoomed .haui-panel-thumb-view {
    position: fixed;
    z-index: 30;
    overflow: hidden;
    border: 1px solid var(--divider-color);
    border-radius: 10px;
    background: var(--haui-screen);
    box-shadow: 0 12px 32px rgb(0 0 0 / 45%);
    pointer-events: none;
  }
  .haui-panel-thumb nspanel-simulator-frame { display: block; width: 100%; height: 100%; pointer-events: none; }
  .haui-panel-thumb-roles {
    position: absolute;
    top: 2px;
    right: 2px;
    display: flex;
    gap: 2px;
    z-index: 1;
  }
  .haui-panel-thumb.portrait .haui-panel-thumb-roles { flex-direction: column; }
  .haui-panel-role {
    display: grid;
    width: 22px;
    height: 22px;
    place-items: center;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgb(0 0 0 / 55%);
  }
  .haui-panel-role { --mdc-icon-size: 15px; line-height: 0; }
  .haui-panel-role.home { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .haui-panel-role.idle { background: var(--warning-color); color: #14181c; }
  .haui-panel-thumb.portrait .haui-panel-role { width: 18px; height: 18px; --mdc-icon-size: 12px; }
  .haui-panel-empty { margin: 0; padding: 14px 16px; color: var(--secondary-text-color); font-size: 12px; }
  .haui-panel-menu { min-width: 220px; }
  @container haui-editor (max-width: 720px) {
    .haui-panel-row { grid-template-columns: 18px auto minmax(0, 1fr) auto; }
    .haui-panel-row-key, .haui-panel-row-count, .haui-panel-row-sub,
    .haui-panel-group-heading > span { display: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .haui-panel-row { transition: none; }
  }
`;
