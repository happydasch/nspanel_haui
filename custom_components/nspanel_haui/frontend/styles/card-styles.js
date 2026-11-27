import { css } from '../lit-import.js';

/** Dashboard card surfaces follow HA's card, theme, type and spacing tokens. */
export const cardStyles = css`
  :host { display: block; }
  .haui-card { overflow: hidden; container: haui-card / inline-size; }
  .haui-card-title {
    padding: var(--haui-space-4) var(--haui-space-4) 0;
    color: var(--primary-text-color, #212121);
    font-size: var(--haui-text-body);
    font-weight: 500;
  }
  .haui-card-panel {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-card-radius);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
  }
  .haui-card-panel:not(.is-fleet-item) { border: 0; border-radius: 0; background: transparent; }
  .haui-card-panel-screen {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    justify-items: center;
    min-width: 0;
    overflow: hidden;
    padding: var(--haui-space-2);
    background: var(--haui-surface-soft);
  }
  .haui-card-panel.is-big .haui-card-panel-screen { padding: var(--haui-space-3); }
  .haui-card-stage {
    position: relative;
    display: grid;
    justify-items: center;
    padding: var(--vp-frame-pad);
    border-radius: var(--haui-radius-control);
    background: var(--haui-bezel);
  }
  .haui-card-screen { display: grid; filter: brightness(var(--vp-screen-brightness, 1)); }
  .haui-card-stage > .haui-badge { position: absolute; top: var(--haui-space-2); inset-inline-end: var(--haui-space-2); }
  .haui-card-status {
    display: grid;
    min-width: 0;
    gap: var(--haui-space-2);
    padding: var(--haui-space-3) var(--haui-space-4);
  }
  .haui-card-status-heading {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--haui-space-1) var(--haui-space-2);
  }
  .haui-card-status-name {
    min-width: 0;
    font-size: var(--haui-text-subtitle);
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  .haui-card-status-connection { display: inline-flex; flex: 0 0 auto; align-items: center; gap: var(--haui-space-2); color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); }
  .haui-card-status-facts {
    display: flex;
    min-width: 0;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--haui-space-2) var(--haui-space-3);
    color: var(--secondary-text-color, #666);
    font-size: var(--haui-text-caption);
    line-height: var(--haui-line-height-copy);
  }
  .haui-card-status-display,
  .haui-card-queued { display: inline-flex; align-items: center; gap: var(--haui-space-1); }
  .haui-card-status-display ha-icon,
  .haui-card-queued ha-icon { --mdc-icon-size: 16px; }
  .haui-card-hardware { display: inline-flex; flex-wrap: wrap; align-items: center; gap: var(--haui-space-1) var(--haui-space-2); }
  .haui-card-hardware-side { display: inline-flex; align-items: center; gap: var(--haui-space-1); }
  .haui-card-hardware-label { color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); }
  .haui-card-led {
    width: 8px;
    height: 8px;
    flex: 0 0 auto;
    border-radius: var(--haui-radius-round);
    background: var(--disabled-text-color, #888);
    transition: background-color 150ms ease, box-shadow 150ms ease;
  }
  .haui-card-led[data-state="on"] { background: var(--haui-led-relay); box-shadow: 0 0 5px var(--haui-led-relay-glow); }
  .haui-card-led.is-entity[data-state="on"] { background: var(--haui-led-entity); box-shadow: 0 0 5px var(--haui-led-entity-glow); }
  .haui-card-led-dot { width: 6px; height: 6px; flex: 0 0 auto; border-radius: var(--haui-radius-round); background: var(--disabled-text-color, #888); }
  .haui-card-led-dot[data-state="on"] { background: var(--haui-led-relay); box-shadow: 0 0 4px var(--haui-led-relay-glow); }
  .haui-card-panel.is-small.has-preview {
    display: grid;
    grid-template-columns: min(40%, 144px) minmax(0, 1fr);
    align-items: center;
    gap: var(--haui-space-3);
    padding: var(--haui-space-3);
  }
  .haui-card-panel.is-small .haui-card-panel-screen { padding: 0; background: transparent; }
  .haui-card-panel.is-small.has-preview > .haui-card-status { padding: 0; }
  .haui-card-panel.is-small.has-preview .haui-card-status-heading { align-items: flex-start; flex-direction: column; }
  .haui-card-panel.is-small.has-preview > .haui-card-note { grid-column: 1 / -1; padding: 0; }
  .haui-card-fleet { display: grid; gap: var(--haui-space-3); padding: var(--haui-space-3); }
  .haui-card-fleet.is-big { grid-template-columns: minmax(0, 1fr); }
  .haui-card-fleet.is-small,
  .haui-card-fleet.is-status { grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); }
  .haui-card-note { padding: var(--haui-space-2) var(--haui-space-4); color: var(--haui-bad-text); font-size: var(--haui-text-caption); }
  @container haui-card (max-width: 480px) {
    .haui-card-fleet { padding: var(--haui-space-2); }
    .haui-card-panel.is-small.has-preview { gap: var(--haui-space-2); padding: var(--haui-space-2); }
    .haui-card-status { padding: var(--haui-space-2) var(--haui-space-3); }
    .haui-card-status-facts { gap: var(--haui-space-1) var(--haui-space-2); }
  }
  @container haui-card (max-width: 260px) {
    .haui-card-panel.is-small.has-preview { grid-template-columns: minmax(0, 1fr); }
    .haui-card-panel.is-small.has-preview > .haui-card-panel-screen { width: min(100%, 144px); }
  }
  @media (prefers-reduced-motion: reduce) {
    .haui-card-led { transition: none; }
  }
`;
