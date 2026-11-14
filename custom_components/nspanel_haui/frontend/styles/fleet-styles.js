import { css } from '../lit-import.js';

export const fleetStyles = css`
  .haui-toolbar-brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; flex: 1; }
  .haui-toolbar-brand .haui-toolbar-title { flex-grow: 0; }
  @container haui-editor (max-width: 600px) { .haui-toolbar-context { display: none; } }
  .haui-toolbar-context { color: var(--secondary-text-color); font-size: var(--haui-text-body); font-weight: 500; }
  .haui-dashboard-content {
    width: min(100% - 56px, 1440px);
    margin: 0 auto;
    padding: 28px 0 32px;
    box-sizing: border-box;
    flex: 1 0 auto;
    color: var(--primary-text-color);
  }
  /* Section headers: one quiet rank for both cards, with the count as a badge. The badge sits on
     the title's baseline, not centred on the title and subtitle together. */
  .haui-section-heading.haui-surface-heading { justify-content: flex-start; align-items: baseline; gap: 8px; padding: 0; border: 0; }
  .haui-section-heading h2 { margin: 0; }
  .haui-inventory-overview > header,
  .haui-event-list > header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    min-height: 0;
    padding: 12px 12px;
    border-bottom: 1px solid var(--divider-color);
  }
  /* Long log lists shrink into their scroll area, never into the heading. */
  .haui-event-list > header { flex-shrink: 0; }
  .haui-device-inventory h2,
  .haui-event-list h2 {
    margin: 0;
    font-size: var(--haui-text-title);
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
    display: grid; grid-auto-flow: column; grid-auto-columns: minmax(280px, 320px);
    gap: 16px; overflow-x: auto; padding: 4px 4px 16px;
    scroll-snap-type: x mandatory; scrollbar-width: thin;
  }
  .haui-fleet-carousel-wrap { position: relative; }
  /* An edge with more cards beyond it fades out. A mask, not an overlay, so it fades into whatever
     the theme puts behind the row; its second layer keeps the bottom padding, where the scrollbar
     runs, opaque. */
  .haui-fleet-carousel-wrap.is-clipped-start { --carousel-fade-start: transparent; }
  .haui-fleet-carousel-wrap.is-clipped-end { --carousel-fade-end: transparent; }
  .haui-fleet-carousel-wrap.is-clipped-start .haui-fleet-carousel,
  .haui-fleet-carousel-wrap.is-clipped-end .haui-fleet-carousel {
    mask:
      linear-gradient(to right, var(--carousel-fade-start, #000), #000 40px, #000 calc(100% - 40px), var(--carousel-fade-end, #000)) top / 100% calc(100% - 16px) no-repeat,
      linear-gradient(#000, #000) bottom / 100% 16px no-repeat;
  }
  /* Centred on the preview of a 280px card: the row only scrolls once its cards have shrunk to that width. */
  .haui-carousel-arrow { position: absolute; z-index: 1; top: 90px; display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-round); color: var(--primary-text-color); background: var(--card-background-color); box-shadow: var(--haui-shadow-card); --mdc-icon-size: 18px; line-height: 1; cursor: pointer; transition: opacity 150ms ease; }
  .haui-carousel-arrow.is-left { left: -4px; }
  .haui-carousel-arrow.is-right { right: -4px; }
  /* The scroll extents keep the first and the last card at their edge; every card between them snaps to the centre. */
  .haui-device-card { scroll-snap-align: center; min-width: 0; overflow: hidden; }
  .haui-device-card.is-dragging, .haui-device-row.is-dragging { opacity: .5; }
  .haui-device-card.is-drop-target, .haui-device-row.is-drop-target { outline: 2px dashed var(--primary-color); outline-offset: -2px; }
  .haui-device-card-cover { position: relative; background: var(--haui-screen); padding: 12px 16px 16px; }
  .haui-device-card-select { display: block; width: 100%; min-height: 176px; border: 0; padding: 0; background: transparent; cursor: pointer; }
  .haui-device-card-select nspanel-simulator-frame { display: block; overflow: hidden; border: 8px solid var(--haui-bezel); border-radius: var(--haui-radius-control); box-sizing: border-box; }
  .haui-device-card-bezel { display: block; aspect-ratio: 450 / 320; border: 8px solid var(--haui-bezel); border-radius: var(--haui-radius-control); background: var(--haui-bezel); box-shadow: 0 4px 14px #0003; }
  .haui-device-card.is-portrait .haui-device-card-select { min-height: 176px; }
  .haui-device-card.is-portrait .haui-device-card-select nspanel-simulator-frame,
  .haui-device-card.is-portrait .haui-device-card-bezel { width: 116px; max-width: 100%; margin: 0 auto; aspect-ratio: 320 / 480; }
  .haui-device-update-badge { position: absolute; right: 8px; bottom: 8px; border-radius: var(--haui-radius-pill); padding: 4px 8px; background: var(--haui-warn-soft); color: var(--warning-color); font-size: var(--haui-text-caption); font-weight: 600; }
  .haui-device-sort { position: absolute; top: 8px; left: 8px; transition: opacity 150ms ease; }
  .haui-device-card-info { display: flex; min-width: 0; align-items: center; gap: 8px; padding: 12px 12px 12px; }
  .haui-device-card-name { overflow: hidden; min-width: 0; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-menu { min-width: 220px; }
  .haui-fleet-scan-error { margin: 8px 0 0; color: var(--haui-bad); font-size: var(--haui-text-label); }
  .haui-discovered { margin-top: 8px; overflow: hidden; }
  .haui-discovered > header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-discovered h2 { margin: 0; font-size: var(--haui-text-title); font-weight: 600; }
  .haui-discovered header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); }
  .haui-discovered ul { margin: 0; padding: 0; list-style: none; }
  .haui-discovered li { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 58px; padding: 0 16px; border-top: 1px solid var(--divider-color); }
  .haui-discovered li:first-child { border-top: 0; }
  .haui-discovered li > div { display: flex; min-width: 0; flex-direction: column; }
  .haui-discovered li > div > span { color: var(--secondary-text-color); font: 11px/1.4 var(--haui-mono); }
  .haui-discovered li .haui-button { min-height: 34px; }
  .haui-device-card-name, .haui-device-row-name { border: 0; padding: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-weight: var(--ha-font-weight-medium, 500); text-align: start; cursor: pointer; }
  .haui-carousel-arrow:disabled { opacity: 0; pointer-events: none; }
  /* A mouse shows the arrows and the grip on hover or focus; a touch screen keeps them
     shown, since a tap cannot hover and a hidden control would still take the tap. */
  @media (hover: hover) {
    .haui-carousel-arrow, .haui-device-sort { opacity: 0; }
    .haui-fleet-carousel-wrap:hover .haui-carousel-arrow:not(:disabled),
    .haui-fleet-carousel-wrap:focus-within .haui-carousel-arrow:not(:disabled),
    .haui-device-card:hover .haui-device-sort, .haui-device-card:focus-within .haui-device-sort { opacity: 1; }
  }
  .haui-fleet-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .85fr); gap: 16px; margin-top: 8px; }
  .haui-inventory-overview { padding: 20px 28px 16px; }
  .haui-fleet-inventory-heading { flex: 0 0 auto; }
  .haui-fleet-inventory-heading h2 { white-space: nowrap; }
  .haui-fleet-summary { display: grid; gap: 0; padding: 0; }
  .haui-inventory-bar { padding: 0 28px 16px; }
  .haui-fleet-band-top { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 12px; }
  .haui-fleet-orb {
    display: grid;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    place-items: center;
    border-radius: var(--haui-radius-round);
    color: var(--haui-good);
    background: color-mix(in srgb, currentcolor 15%, transparent);
    --mdc-icon-size: 18px;
  }
  .haui-fleet-band-warning .haui-fleet-orb { color: var(--haui-warn); }
  .haui-fleet-band-danger .haui-fleet-orb { color: var(--haui-bad); }
  .haui-fleet-band-neutral .haui-fleet-orb { color: var(--secondary-text-color); }
  .haui-fleet-lead { display: grid; min-width: 0; gap: 4px; }
  .haui-fleet-lead-heading { display: flex; align-items: center; gap: 16px; }
  .haui-fleet-lead strong { font-size: var(--haui-text-title); font-variant-numeric: tabular-nums; font-weight: var(--ha-font-weight-medium, 500); line-height: 1.25; }
  .haui-fleet-lead > span { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  /* The figures keep their labels above the values, so the strip reads as one row. */
  .haui-fleet-facts { display: flex; gap: 20px; margin: 0 0 0 auto; }
  .haui-fleet-facts > div { display: grid; gap: 4px; }
  .haui-fleet-facts dt { color: var(--secondary-text-color); font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .07em; text-transform: uppercase; }
  .haui-fleet-facts dd { margin: 0; font-size: var(--haui-text-label); font-variant-numeric: tabular-nums; }
  .haui-fleet-bar { display: flex; gap: 4px; height: 4px; }
  .haui-fleet-bar span { flex: 1; border-radius: var(--haui-radius-pill); background: var(--primary-color, #03a9f4); }
  .haui-fleet-bar .is-offline { background: var(--haui-bad); }
  .haui-fleet-bar .is-unknown { background: color-mix(in srgb, var(--secondary-text-color) 40%, transparent); }
  .haui-stat-placeholder { display: block; width: 64px; height: 15px; margin: 4px 0; border-radius: var(--haui-radius-control); background: var(--secondary-background-color); }
  .haui-device-inventory, .haui-event-list { min-width: 0; }
  /* The table is flush: its rows run to the card's edges. The inventory sets the row's height,
     up to its maximum; a longer device list scrolls under its column heads. */
  .haui-device-inventory { display: flex; max-height: 720px; flex-direction: column; overflow: hidden; }
  .haui-inventory-update { min-height: 32px; padding: 0 12px; font-size: var(--ha-font-size-s, 12px); }
  .haui-inventory-update ha-icon { --mdc-icon-size: 16px; }
  /* The rows share the table's tracks (subgrid), so the values and actions take their widest
     cell's width in every row and the device name takes the rest. */
  .haui-device-table { display: grid; grid-template-columns: minmax(200px, 1fr) repeat(3, max-content) auto; column-gap: 28px; overflow: hidden auto; overscroll-behavior: contain; scrollbar-width: thin; }
  /* Roomy inventory rows keep device details easy to scan without making the table feel bulky. */
  .haui-device-row { display: grid; grid-column: 1 / -1; grid-template-columns: subgrid; align-items: center; min-height: 56px; padding: 0 20px; border-top: 1px solid var(--divider-color); font-size: var(--haui-text-label); }
  .haui-device-row:not(.haui-device-row-head):hover { background: color-mix(in srgb, var(--primary-text-color) 4%, transparent); }
  .haui-device-row-head { position: sticky; z-index: 1; top: 0; min-height: 32px; background: color-mix(in srgb, var(--secondary-background-color) 60%, var(--haui-card-background)); color: var(--secondary-text-color); font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .075em; text-transform: uppercase; }
  .haui-device-row-identity { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .haui-device-row-identity > div { min-width: 0; }
  .haui-device-row-name { display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* Addresses and versions line up in the mono face, as Home Assistant aligns its table values. */
  .haui-device-row-ip, .haui-device-row-version { overflow: hidden; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); letter-spacing: -.01em; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-row-actions { display: flex; align-items: center; justify-content: end; gap: 4px; }
  .haui-device-row-actions .haui-badge { margin-inline-end: 4px; padding: 4px 8px; font-size: var(--haui-text-eyebrow); }
  .haui-device-row-version.is-mismatch { display: grid; justify-items: start; gap: 4px; white-space: normal; }
  .haui-device-row-version.is-mismatch > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-row-version .haui-device-row-mismatch { padding: 4px 4px; font-size: var(--haui-text-eyebrow); }
  /* The event list follows the inventory: it has no height of its own (size containment), so it
     stretches to the row the inventory sets and scrolls inside it. */
  .haui-event-list { display: flex; min-height: 320px; flex-direction: column; contain: size; }
  /* A quiet text action beside the event-list heading. */
  .haui-event-list > header .haui-event-logs { min-height: 30px; margin-inline-end: -8px; padding: 0 8px; border: 0; border-radius: var(--haui-radius-pill); color: var(--primary-color); background: transparent; font-size: var(--ha-font-size-s, 12px); font-weight: var(--ha-font-weight-medium, 500); }
  .haui-event-list > header .haui-event-logs:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  /* The events as a timeline: a rail through the level dots, so the eye follows time down. */
  .haui-event-list ol { display: grid; min-height: 0; flex: 1 1 auto; align-content: start; overflow-y: auto; overscroll-behavior: contain; margin: 0; padding: 4px 12px 8px; list-style: none; scrollbar-width: thin; }
  .haui-event-list li { position: relative; display: grid; grid-template-columns: 20px minmax(0, 1fr); align-items: start; gap: 8px; padding: 8px 0; border-top: 0; }
  .haui-event-list li::before { content: ''; position: absolute; top: 0; bottom: 0; left: 9px; width: 1px; background: color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
  .haui-event-list li:first-child::before { top: 18px; }
  .haui-event-list li:last-child::before { bottom: calc(100% - 22px); }
  .haui-event-node { position: relative; z-index: 1; display: grid; width: 19px; height: 19px; margin-top: 4px; place-items: center; border-radius: var(--haui-radius-round); color: var(--state-icon-color, var(--secondary-text-color)); background: color-mix(in srgb, currentcolor 14%, var(--card-background-color)); --mdc-icon-size: 12px; }
  .haui-event-warn .haui-event-node { color: var(--haui-warn); }
  .haui-event-error .haui-event-node { color: var(--haui-bad); }
  .haui-event-debug .haui-event-node { color: var(--secondary-text-color); }
  .haui-event-copy { display: grid; gap: 4px; min-width: 0; }
  .haui-event-copy p { display: -webkit-box; overflow: hidden; margin: 0; font-size: var(--haui-text-label); line-height: 1.3; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .haui-event-meta { display: flex; min-width: 0; align-items: center; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-event-device { overflow: hidden; color: var(--primary-text-color); font-weight: var(--ha-font-weight-medium, 500); text-overflow: ellipsis; white-space: nowrap; }
  .haui-event-device + time::before { content: '·'; margin: 0 4px; color: var(--disabled-text-color); }
  /* The device name gives way first; the time and the repeat count stay whole. */
  .haui-event-meta time, .haui-event-repeat { flex: 0 0 auto; white-space: nowrap; }
  .haui-event-repeat { margin-inline-start: 4px; padding: 0 4px; border-radius: var(--haui-radius-pill); background: var(--secondary-background-color); font-size: var(--haui-text-eyebrow); font-variant-numeric: tabular-nums; font-weight: var(--ha-font-weight-medium, 500); line-height: 1.6; }
  .haui-event-warn .haui-event-repeat { background: var(--haui-warn-soft); color: var(--haui-warn); }
  .haui-event-error .haui-event-repeat { background: var(--haui-bad-soft); color: var(--haui-bad); }
  .haui-sort-handle { display: inline-flex; align-items: center; padding: 4px; border-radius: var(--haui-radius-control); color: var(--secondary-text-color); cursor: grab; --mdc-icon-size: 18px; }
  .haui-device-row .haui-row-action { width: 30px; height: 30px; --mdc-icon-size: 17px; }
  .haui-device-sort .haui-sort-handle { background: var(--card-background-color); }
  @container haui-editor (max-width: 560px) { .haui-fleet-facts { gap: 12px; } .haui-fleet-lead > span, .haui-fleet-inventory-heading { display: none; } }
  @container haui-editor (max-width: 1120px) { .haui-device-table { grid-template-columns: minmax(200px, 1fr) repeat(2, max-content) auto; } .haui-device-row-head > :nth-child(2), .haui-device-row > :nth-child(2) { display: none; } }
  /* Stacked, the event list has no neighbour to follow and takes its own height again. */
  @container haui-editor (max-width: 980px) { .haui-fleet-grid { grid-template-columns: minmax(0, 1fr); } .haui-event-list { min-height: 0; contain: none; } .haui-event-list ol { max-height: 480px; } }
  @container haui-editor (max-width: 720px) {
    .haui-inventory-overview { padding: 16px 12px 12px; }
    .haui-inventory-bar { padding: 0 12px 12px; }
  }
  @container haui-editor (max-width: 720px) { .haui-dashboard-content { width: min(100% - 28px, 1440px); padding-top: 16px; } .haui-device-table { grid-template-columns: minmax(0, 1fr) repeat(2, max-content) auto; column-gap: 12px; } .haui-device-row { padding: 4px 12px; } .haui-device-row-head > :nth-child(2), .haui-device-row > :nth-child(2) { display: none; } .haui-device-row-actions { grid-column: 4; } }
  @container haui-editor (max-width: 560px) { .haui-device-table { grid-template-columns: minmax(0, 1fr) max-content auto; } .haui-device-row-head > :nth-child(4), .haui-device-row > :nth-child(4) { display: none; } .haui-device-row-actions { grid-column: 3; } }
  @media (prefers-reduced-motion: reduce) { .haui-device-sort { transition: none; } }
  .haui-rollout { margin-bottom: 16px; }
  .haui-rollout-summary { margin: 0 0 8px; font-size: var(--haui-text-caption); color: var(--secondary-text-color); }
  .haui-rollout-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
  .haui-rollout-row { display: grid; gap: 4px; }
  .haui-rollout-row-head { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .haui-rollout-kind { font-size: var(--haui-text-caption); color: var(--secondary-text-color); }
  .haui-rollout-cancel { margin-left: auto; }
  .haui-rollout-row .haui-update-progress { padding: 0; }
  .haui-rollout-error { margin: 0; font-size: var(--haui-text-caption); color: var(--error-color, #db4437); }
  .haui-rollout-actions { display: flex; justify-content: flex-end; margin-top: 8px; }
`;
