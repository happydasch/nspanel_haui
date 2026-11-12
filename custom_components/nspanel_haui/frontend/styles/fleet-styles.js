import { css } from '../lit-import.js';

export const fleetStyles = css`
  .toolbar-brand { display: flex; align-items: baseline; gap: 14px; min-width: 0; flex: 1; }
  .toolbar-brand .toolbar-title { flex-grow: 0; }
  @container haui-editor (max-width: 600px) { .toolbar-context { display: none; } }
  .toolbar-context { color: var(--secondary-text-color); font-size: 14px; font-weight: 500; }
  .haui-dashboard-content {
    width: min(100% - 56px, 1440px);
    margin: 0 auto;
    padding: 28px 0 32px;
    box-sizing: border-box;
    flex: 1 0 auto;
    color: var(--primary-text-color);
  }
  /* Section headers: one quiet rank for both cards, with the count as a chip. */
  .haui-section-heading { display: flex; min-width: 0; align-items: center; gap: 8px; }
  .haui-section-count {
    padding: 1px 7px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: 17px;
  }
  .haui-inventory-overview > header,
  .haui-event-list > header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    min-height: 0;
    padding: 12px 14px;
    border-bottom: 1px solid var(--divider-color);
  }
  .haui-device-inventory h2,
  .haui-event-list h2 {
    margin: 0;
    font-size: 15px;
    font-weight: var(--ha-font-weight-medium, 500);
    letter-spacing: -0.005em;
    line-height: 1.3;
  }
  .haui-device-card, .haui-discovered, .haui-device-inventory, .haui-event-list {
    box-sizing: border-box;
    border: var(--haui-card-border);
    border-radius: var(--haui-card-radius);
    background: var(--haui-card-background);
    box-shadow: var(--haui-card-shadow);
  }
  .haui-fleet-carousel {
    display: grid; grid-auto-flow: column; grid-auto-columns: minmax(240px, 264px);
    gap: 16px; overflow-x: auto; padding: 4px 4px 16px;
    scroll-snap-type: x mandatory; scrollbar-width: thin;
  }
  .haui-fleet-carousel-wrap { position: relative; }
  .haui-carousel-arrow { position: absolute; z-index: 1; top: 74px; display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--divider-color); border-radius: 50%; color: var(--primary-text-color); background: var(--card-background-color); box-shadow: var(--haui-shadow-card); font-size: 24px; line-height: 1; cursor: pointer; opacity: 0; transition: opacity 150ms ease; }
  .haui-fleet-carousel-wrap:hover .haui-carousel-arrow, .haui-fleet-carousel-wrap:focus-within .haui-carousel-arrow { opacity: 1; }
  .haui-carousel-arrow.is-left { left: -4px; }
  .haui-carousel-arrow.is-right { right: -4px; }
  .haui-device-card { scroll-snap-align: start; min-width: 0; overflow: hidden; }
  .haui-device-card.is-dragging, .haui-device-row.is-dragging { opacity: .5; }
  .haui-device-card.is-drop-target, .haui-device-row.is-drop-target { outline: 2px dashed var(--primary-color); outline-offset: -2px; }
  .haui-device-card-cover { position: relative; background: var(--haui-screen); padding: 12px 18px 0; }
  .haui-device-card-select { display: block; width: 100%; min-height: 176px; border: 0; padding: 0; background: transparent; cursor: pointer; }
  .haui-device-card-select nspanel-simulator-frame { display: block; max-height: 196px; overflow: hidden; border: 8px solid var(--haui-bezel); border-radius: 10px; box-sizing: border-box; }
  .haui-device-card-bezel { display: block; aspect-ratio: 450 / 320; border: 8px solid var(--haui-bezel); border-radius: 10px; background: #111; box-shadow: 0 4px 14px #0003; }
  .haui-device-card.portrait .haui-device-card-select { min-height: 176px; }
  .haui-device-card.portrait .haui-device-card-select nspanel-simulator-frame,
  .haui-device-card.portrait .haui-device-card-bezel { width: 116px; max-width: 100%; margin: 0 auto; aspect-ratio: 320 / 480; }
  .haui-device-update-badge { position: absolute; right: 8px; bottom: 8px; border-radius: 999px; padding: 4px 8px; background: var(--haui-warn-soft); color: var(--warning-color); font-size: 11px; font-weight: 600; }
  .haui-device-sort { position: absolute; top: 8px; left: 8px; opacity: 0; transition: opacity 150ms ease; }
  .haui-device-card:hover .haui-device-sort, .haui-device-card:focus-within .haui-device-sort { opacity: 1; }
  .haui-device-card-info { display: flex; min-width: 0; align-items: center; gap: 8px; padding: 12px 14px 14px; }
  .haui-device-card-name { overflow: hidden; min-width: 0; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-menu { min-width: 220px; }
  .haui-fleet-scan-error { margin: 8px 0 0; color: var(--haui-bad); font-size: 13px; }
  .haui-discovered { margin-top: 8px; overflow: hidden; }
  .haui-discovered > header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 18px; border-bottom: 1px solid var(--divider-color); }
  .haui-discovered h2 { margin: 0; font-size: 16px; font-weight: 600; }
  .haui-discovered header p { margin: 3px 0 0; color: var(--secondary-text-color); font-size: 13px; }
  .haui-discovered ul { margin: 0; padding: 0; list-style: none; }
  .haui-discovered li { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 58px; padding: 0 18px; border-top: 1px solid var(--divider-color); }
  .haui-discovered li:first-child { border-top: 0; }
  .haui-discovered li > div { display: flex; min-width: 0; flex-direction: column; }
  .haui-discovered li > div > span { color: var(--secondary-text-color); font: 11px/1.4 var(--haui-mono); }
  .haui-discovered li .haui-button { min-height: 34px; }
  .haui-device-card-name, .haui-device-row-name { border: 0; padding: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-weight: var(--ha-font-weight-medium, 500); text-align: start; cursor: pointer; }
  .haui-carousel-arrow:disabled { opacity: 0; pointer-events: none; }
  .haui-fleet-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .85fr); gap: 16px; margin-top: 8px; }
  .haui-inventory-overview {
    display: grid;
    grid-template-columns: minmax(140px, .75fr) minmax(0, 1.5fr);
    align-items: center;
    gap: 24px;
    padding: 20px 28px 16px;
  }
  /* The header column is narrow: Install updates wraps below the heading rather than squeezing it. */
  .haui-inventory-overview > header {
    flex-wrap: wrap;
    justify-content: flex-start;
    gap: 10px 16px;
    min-width: 0;
    padding: 0;
    border: 0;
  }
  .haui-inventory-overview h2 { white-space: nowrap; }
  .haui-fleet-summary { display: grid; gap: 0; padding: 0; }
  .haui-inventory-bar { padding: 0 28px 16px; }
  .haui-fleet-band-top { display: flex; min-width: 0; align-items: center; gap: 11px; }
  .haui-fleet-orb {
    display: grid;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 50%;
    color: var(--haui-good);
    background: color-mix(in srgb, currentcolor 15%, transparent);
    --mdc-icon-size: 18px;
  }
  .haui-fleet-band-warning .haui-fleet-orb { color: var(--haui-warn); }
  .haui-fleet-band-danger .haui-fleet-orb { color: var(--haui-bad); }
  .haui-fleet-band-neutral .haui-fleet-orb { color: var(--secondary-text-color); }
  .haui-fleet-lead { display: grid; min-width: 0; gap: 1px; }
  .haui-fleet-lead strong { font-size: 15px; font-variant-numeric: tabular-nums; font-weight: var(--ha-font-weight-medium, 500); line-height: 1.25; }
  .haui-fleet-lead span { color: var(--secondary-text-color); font-size: 11.5px; }
  /* The figures keep their labels above the values, so the strip reads as one row. */
  .haui-fleet-facts { display: flex; gap: 20px; margin: 0 0 0 auto; }
  .haui-fleet-facts > div { display: grid; gap: 1px; }
  .haui-fleet-facts dt { color: var(--secondary-text-color); font-size: 10px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; }
  .haui-fleet-facts dd { margin: 0; font-size: 13px; font-variant-numeric: tabular-nums; }
  .haui-fleet-bar { display: flex; gap: 3px; height: 4px; }
  .haui-fleet-bar span { flex: 1; border-radius: 999px; background: var(--primary-color, #03a9f4); }
  .haui-fleet-bar .offline { background: var(--haui-bad); }
  .haui-fleet-bar .unknown { background: color-mix(in srgb, var(--secondary-text-color) 40%, transparent); }
  .haui-stat-placeholder { display: block; width: 64px; height: 15px; margin: 2px 0; border-radius: 6px; background: var(--secondary-background-color); }
  .haui-device-inventory, .haui-event-list { min-width: 0; }
  /* The table is flush: its rows run to the card's edges. */
  .haui-device-inventory { overflow: hidden; }
  .haui-inventory-update { min-height: 32px; padding: 0 12px; font-size: var(--ha-font-size-s, 12px); }
  .haui-inventory-update ha-icon { --mdc-icon-size: 16px; }
  /* The rows share the table's tracks (subgrid), so the values and actions take their widest
     cell's width in every row and the device name takes the rest. */
  .haui-device-table { display: grid; grid-template-columns: minmax(200px, 1fr) repeat(3, max-content) auto; column-gap: 28px; }
  /* A dense data table: 46 px rows, 13 px cells, 10 px uppercase column labels. */
  .haui-device-row { display: grid; grid-column: 1 / -1; grid-template-columns: subgrid; align-items: center; min-height: 46px; padding: 0 14px; border-top: 1px solid var(--divider-color); font-size: 13px; }
  .haui-device-row:not(.haui-device-row-head):hover { background: color-mix(in srgb, var(--primary-text-color) 4%, transparent); }
  .haui-device-row-head { min-height: 32px; background: color-mix(in srgb, var(--secondary-background-color) 60%, transparent); color: var(--secondary-text-color); font-size: 10px; font-weight: 600; letter-spacing: .075em; text-transform: uppercase; }
  .haui-device-row-identity { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .haui-device-row-identity > div { min-width: 0; }
  .haui-device-row-name { display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* Addresses and versions line up in the mono face, as Home Assistant aligns its table values. */
  .haui-device-row-ip, .haui-device-row-version { overflow: hidden; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: 11.5px; letter-spacing: -.01em; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-row-actions { display: flex; align-items: center; justify-content: end; gap: 2px; }
  .haui-device-row-actions .haui-badge { margin-inline-end: 6px; padding: 2px 7px; font-size: 10.5px; }
  .haui-event-list { align-self: start; }
  /* A plain Home Assistant text button. */
  .haui-event-list > header button { min-height: 30px; margin-inline-end: -8px; padding: 0 10px; border: 0; border-radius: 999px; color: var(--primary-color); background: transparent; font: inherit; font-size: var(--ha-font-size-s, 12px); font-weight: var(--ha-font-weight-medium, 500); cursor: pointer; }
  .haui-event-list > header button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  .haui-event-list > header button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  /* The events as a timeline: a rail through the level dots, so the eye follows time down. */
  .haui-event-list ol { display: grid; margin: 0; padding: 2px 14px 8px; list-style: none; }
  .haui-event-list li { position: relative; display: grid; grid-template-columns: 20px minmax(0, 1fr); align-items: start; gap: 10px; padding: 8px 0; border-top: 0; }
  .haui-event-list li::before { content: ''; position: absolute; top: 0; bottom: 0; left: 9px; width: 1px; background: color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
  .haui-event-list li:first-child::before { top: 18px; }
  .haui-event-list li:last-child::before { bottom: calc(100% - 22px); }
  .haui-event-node { position: relative; z-index: 1; display: grid; width: 19px; height: 19px; margin-top: 1px; place-items: center; border-radius: 50%; color: var(--state-icon-color, var(--secondary-text-color)); background: color-mix(in srgb, currentcolor 14%, var(--card-background-color)); --mdc-icon-size: 12px; }
  .haui-event-warning .haui-event-node { color: var(--haui-warn); }
  .haui-event-error .haui-event-node { color: var(--haui-bad); }
  .haui-event-copy { display: grid; gap: 3px; min-width: 0; }
  .haui-event-copy p { display: -webkit-box; overflow: hidden; margin: 0; font-size: 12.5px; line-height: 17px; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .haui-event-meta { display: flex; min-width: 0; align-items: center; color: var(--secondary-text-color); font-size: 11px; }
  .haui-event-device { overflow: hidden; color: var(--primary-text-color); font-weight: var(--ha-font-weight-medium, 500); text-overflow: ellipsis; white-space: nowrap; }
  .haui-event-device + time::before { content: '·'; margin: 0 5px; color: var(--disabled-text-color); }
  .haui-event-repeat { margin-left: 6px; padding: 0 5px; border-radius: 999px; background: var(--secondary-background-color); font-variant-numeric: tabular-nums; font-weight: var(--ha-font-weight-medium, 500); }
  /* The device name gives way first; the time and the repeat count stay whole. */
  .haui-event-meta time, .haui-event-repeat { flex: 0 0 auto; white-space: nowrap; }
  .haui-event-repeat { margin-inline-start: 6px; padding: 0 6px; border-radius: 999px; background: var(--secondary-background-color); font-size: 10.5px; font-variant-numeric: tabular-nums; font-weight: var(--ha-font-weight-medium, 500); line-height: 16px; }
  .haui-event-warning .haui-event-repeat { background: var(--haui-warn-soft); color: var(--haui-warn); }
  .haui-event-error .haui-event-repeat { background: var(--haui-bad-soft); color: var(--haui-bad); }
  .haui-event-empty { display: flex; box-sizing: border-box; min-height: 72px; align-items: center; justify-content: center; gap: 10px; margin: 0; padding: 12px 16px; color: var(--secondary-text-color); font-size: 13px; font-weight: var(--ha-font-weight-medium, 500); }
  .haui-event-empty-icon { display: grid; width: 28px; height: 28px; flex: 0 0 auto; place-items: center; border-radius: 50%; color: var(--haui-good); background: var(--haui-good-soft); --mdc-icon-size: 16px; }
  .haui-sort-handle { display: inline-flex; align-items: center; padding: 3px; border-radius: 6px; color: var(--secondary-text-color); cursor: grab; --mdc-icon-size: 18px; }
  .haui-device-row .haui-row-action { width: 30px; height: 30px; --mdc-icon-size: 17px; }
  .haui-device-sort .haui-sort-handle { background: var(--card-background-color); }
  @container haui-editor (max-width: 560px) { .haui-fleet-facts { gap: 14px; } .haui-fleet-lead span { display: none; } }
  @container haui-editor (max-width: 1120px) { .haui-device-table { grid-template-columns: minmax(200px, 1fr) repeat(2, max-content) auto; } .haui-device-row-head > :nth-child(4), .haui-device-row > :nth-child(4) { display: none; } }
  @container haui-editor (max-width: 980px) { .haui-fleet-grid { grid-template-columns: minmax(0, 1fr); } }
  @container haui-editor (max-width: 600px) {
    .haui-fleet-carousel { grid-auto-columns: minmax(0, calc(100% - 40px)); }
  }
  @container haui-editor (max-width: 720px) {
    .haui-inventory-overview { grid-template-columns: minmax(0, 1fr); gap: 12px; padding: 16px 14px 12px; }
    .haui-inventory-bar { padding: 0 14px 14px; }
  }
  @container haui-editor (max-width: 720px) { .haui-dashboard-content { width: min(100% - 28px, 1440px); padding-top: 18px; } .haui-device-table { grid-template-columns: minmax(0, 1fr) auto; column-gap: 12px; } .haui-device-row { padding: 6px 12px; } .haui-device-row-head > :not(:first-child), .haui-device-row > :nth-child(2), .haui-device-row > :nth-child(3), .haui-device-row > :nth-child(4) { display: none; } .haui-device-row-actions { grid-column: 2; } }
  @media (prefers-reduced-motion: reduce) { .haui-device-sort { transition: none; } }
`;
