/** Logs sidebar styles; kept out of the dialog's behavior module. */
import { css } from '../lit-import.js';

export const logsStyles = css`
  :host { display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
  .haui-logs-tools { display: grid; flex: 0 0 auto; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-logs-search-row { display: flex; align-items: center; gap: 4px; }
  .haui-logs-search {
    display: flex; flex: 1 1 auto; align-items: center; gap: 8px; min-width: 0; min-height: 38px;
    padding: 0 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill);
    background: var(--haui-surface-soft); color: var(--secondary-text-color); --mdc-icon-size: 18px;
  }
  .haui-logs-search:focus-within { border-color: var(--primary-color); }
  .haui-logs-search input {
    flex: 1 1 auto; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--primary-text-color); font: inherit; font-size: var(--haui-text-label);
  }
  .haui-logs-search-row .haui-icon-button { flex: 0 0 auto; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  .haui-logs-filter { display: flex; flex-wrap: wrap; gap: 4px; }
  .haui-logs-filter button {
    display: inline-flex; align-items: center; gap: 4px; min-height: 30px; padding: 0 4px 0 12px;
    border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill); background: transparent;
    color: var(--secondary-text-color); font: inherit; font-size: var(--haui-text-caption); cursor: pointer;
  }
  .haui-logs-filter button:hover { background: var(--haui-surface-soft); }
  .haui-logs-filter button[aria-pressed="true"] {
    border-color: var(--primary-color); color: var(--primary-text-color);
    background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color));
  }
  .haui-logs-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding-bottom: 12px; }
  .haui-logs-list h3 {
    position: sticky; top: 0; z-index: 1; margin: 0; padding: 8px 16px 4px;
    border-bottom: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 600;
  }
  .haui-logs-list ol { margin: 0; padding: 0; list-style: none; }
  .haui-log {
    display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px;
    padding: 8px 16px 8px 12px; border-inline-start: 3px solid transparent;
    font-size: var(--haui-text-label); line-height: 1.45;
  }
  .haui-log + .haui-log { border-top: 1px solid color-mix(in srgb, var(--divider-color) 55%, transparent); }
  .haui-log time {
    color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption);
    font-variant-numeric: tabular-nums; line-height: 1.65;
  }
  .haui-log p { min-width: 0; margin: 0; overflow-wrap: anywhere; }
  .haui-log-text { white-space: pre-wrap; }
  .haui-log-tag {
    display: inline-block; margin-inline-end: 4px; padding: 0 4px; border-radius: var(--haui-radius-control);
    font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .03em; line-height: 1.6;
    text-transform: uppercase; vertical-align: 1px;
  }
  .haui-log-device { margin-inline-end: 4px; color: var(--secondary-text-color); font-weight: 500; }
  .haui-log-warning { border-inline-start-color: var(--haui-warn); background: color-mix(in srgb, var(--haui-warn) 7%, transparent); }
  .haui-log-warning .haui-log-tag { background: var(--haui-warn-soft); color: var(--haui-warn); }
  .haui-log-error { border-inline-start-color: var(--haui-bad); background: color-mix(in srgb, var(--haui-bad) 8%, transparent); }
  .haui-log-error .haui-log-tag { background: var(--haui-bad-soft); color: var(--haui-bad); }
  .haui-log-debug .haui-log-text { color: var(--secondary-text-color); }
  .haui-log-debug .haui-log-tag { background: var(--haui-surface-soft); color: var(--secondary-text-color); }
`;
