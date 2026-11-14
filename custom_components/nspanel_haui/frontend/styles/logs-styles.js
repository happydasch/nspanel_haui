/** Logs sidebar styles; kept out of the dialog's behavior module. */
import { css } from '../lit-import.js';

export const logsStyles = css`
  :host { display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
  .haui-logs-tools { display: grid; flex: 0 0 auto; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-logs-search-row { display: flex; align-items: center; gap: 8px; }
  .haui-logs-search { flex: 1 1 auto; height: 36px; }
  .haui-logs-search-row .haui-icon-button { flex: 0 0 auto; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  /* The device selector: a round twin of the search pill, the native select invisible over it. */
  .haui-logs-device {
    position: relative; display: inline-grid; flex: 0 0 auto; box-sizing: border-box; width: 36px; height: 36px;
    place-items: center; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-round);
    background: var(--card-background-color); color: var(--secondary-text-color); cursor: pointer;
    --mdc-icon-size: 18px; transition: border-color 150ms, background 150ms, color 150ms;
  }
  .haui-logs-device select { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; font: inherit; }
  .haui-logs-device:hover, .haui-logs-device:focus-within { border-color: var(--primary-color); }
  .haui-logs-device:has(select:focus-visible) { outline: var(--haui-focus-ring); outline-offset: var(--haui-focus-offset); }
  .haui-logs-device.is-filtered {
    border-color: var(--primary-color); color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color));
  }
  .haui-logs-tools .haui-segmented { display: flex; }
  .haui-logs-tools .haui-segmented-option { flex: 1 1 0; justify-content: center; min-height: 30px; font-size: var(--haui-text-label); }
  @media (prefers-reduced-motion: reduce) { .haui-logs-device { transition: none; } }
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
