import { css } from '../lit-import.js';

export const fleetStyles = css`
  .haui-toolbar-brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; flex: 1; }
  .haui-toolbar-brand .haui-toolbar-title { flex-grow: 0; }
  @container haui-editor (max-width: 600px) { .haui-toolbar-context { display: none; } }
  .haui-toolbar-context { color: var(--secondary-text-color); font-size: var(--haui-text-body); font-weight: 500; }
  .haui-dashboard-content {
    width: calc(100% - 56px);
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
  .haui-event-list > header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    min-height: 0;
    padding: 12px 12px;
    border-bottom: 1px solid var(--divider-color);
  }
  /* Long log lists shrink into their scroll area, never into the heading. The title and the quiet
     actions share the heading's first line — three of them never squeeze the title into a column a
     few characters wide — and the line under it opens with the device the timeline is scoped to and
     closes with the window it covers, right-aligned where the actions used to sit. */
  .haui-event-list > header { flex-wrap: wrap; flex-shrink: 0; row-gap: var(--haui-space-1); }
  .haui-event-list > header > .haui-surface-heading { min-width: 0; flex: 1 1 100%; align-items: center; }
  /* Neither line wraps: the title gives way to the actions and the scope to the window, each
     ellipsizing instead of pushing the other out of the card. */
  .haui-event-list > header h2,
  .haui-event-list > header .haui-event-window { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* The scope line: the name gives way to the window, which ellipsizes only once the name is gone.
     The whole fleet reads quieter than a device name, since it is the list's scope and not one of
     its devices. */
  .haui-event-list > header .haui-event-bar { display: flex; min-width: 0; flex: 1 1 100%; align-items: baseline; gap: var(--haui-space-2); line-height: var(--haui-line-height-tight); }
  .haui-event-list > header .haui-event-scope { min-width: 0; flex: 1 1 0; overflow: hidden; color: var(--primary-text-color); font-size: var(--haui-text-caption); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
  .haui-event-list > header .haui-event-scope.is-all { color: var(--secondary-text-color); font-weight: 400; }
  .haui-event-list > header .haui-event-window { flex: 0 1 auto; min-width: 0; margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-device-inventory h2,
  .haui-event-list h2 {
    margin: 0;
    font-size: var(--haui-text-body);
    font-weight: 500;
    line-height: var(--haui-line-height-tight);
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
  /* An edge fades while the row has more real cards beyond it, so the card it stops on at either
     end is never faded; a row that fits keeps no fade and leaves its ghost outlines to their own
     mask. The mask leaves whatever theme surface is behind the row visible, and its second layer
     keeps the bottom padding, where the scrollbar runs, opaque. */
  .haui-fleet-carousel.is-clipped-start { --carousel-fade-start: transparent; }
  .haui-fleet-carousel.has-right-fade { --carousel-fade-end: transparent; }
  .haui-fleet-carousel.is-clipped-start,
  .haui-fleet-carousel.has-right-fade {
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
  /* The selected device: its card takes a primary ring and the row's selection tint. The ring is the
     border plus an outer shadow, since the positioned cover paints over an inset outline; it replaces
     the card shadow, which is usually none and cannot be listed with another shadow. */
  .haui-device-card.is-selected { border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color); }
  .haui-device-card.is-selected .haui-device-card-cover {
    background: linear-gradient(color-mix(in srgb, var(--primary-color) 10%, transparent), color-mix(in srgb, var(--primary-color) 10%, transparent)), var(--haui-screen);
  }
  .haui-device-card.is-selected .haui-device-card-info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }
  .haui-device-card.is-dragging, .haui-device-row.is-dragging { opacity: .5; }
  .haui-device-card.is-drop-target, .haui-device-row.is-drop-target { outline: 2px dashed var(--primary-color); outline-offset: -2px; }
  .haui-device-card-cover { position: relative; background: var(--haui-screen); padding: 12px 16px 16px; }
  .haui-device-card-select { display: block; width: 100%; min-height: 176px; border: 0; padding: 0; background: transparent; cursor: pointer; }
  .haui-device-card-select nspanel-simulator-frame { display: block; overflow: hidden; border: 8px solid var(--haui-bezel); border-radius: var(--haui-radius-control); box-sizing: border-box; }
  .haui-device-card-bezel { display: block; aspect-ratio: 450 / 320; border: 8px solid var(--haui-bezel); border-radius: var(--haui-radius-control); background: var(--haui-bezel); box-shadow: 0 4px 14px #0003; }
  .haui-device-card.is-portrait .haui-device-card-select { min-height: 176px; }
  .haui-device-card.is-portrait .haui-device-card-select nspanel-simulator-frame,
  .haui-device-card.is-portrait .haui-device-card-bezel { width: 116px; max-width: 100%; margin: 0 auto; aspect-ratio: 320 / 480; }
  .haui-device-update-badge { position: absolute; right: 8px; bottom: 8px; border-radius: var(--haui-radius-pill); padding: 4px 8px; background: var(--haui-warn-soft); color: var(--haui-warn-text); font-size: var(--haui-text-caption); font-weight: 500; }
  .haui-device-sort { position: absolute; top: 8px; left: 8px; transition: opacity 150ms ease; }
  .haui-device-card-info { display: flex; min-width: 0; align-items: center; gap: 8px; padding: 12px 12px 12px; }
  button.haui-device-card-info { width: 100%; border: 0; color: inherit; background: transparent; font: inherit; text-align: start; cursor: pointer; }
  .haui-device-card-name { overflow: hidden; min-width: 0; text-overflow: ellipsis; white-space: nowrap; }
  /* Decorative outlines are a clipped overlay, never carousel children: they cannot change real
     card sizing, scroll extents, snapping or the edge fades. */
  .haui-device-slots {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
  }
  .haui-device-slots.has-right-fade {
    mask: linear-gradient(to right, #000 calc(100% - 40px), transparent);
  }
  .haui-device-slot-card {
    position: absolute;
    top: var(--haui-device-slots-top);
    left: var(--haui-device-slot-left);
    width: var(--haui-device-slot-width);
    height: var(--haui-device-slot-height);
    box-sizing: border-box;
    border: 2px dashed var(--divider-color);
    border-radius: var(--haui-card-radius);
    background: transparent;
    box-shadow: none;
  }
  .haui-device-menu { min-width: 220px; }
  .haui-fleet-scan-error { margin: 8px 0 0; color: var(--haui-bad-text); font-size: var(--haui-text-label); }
  .haui-discovered { margin-top: 8px; overflow: hidden; }
  .haui-discovered > header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-discovered h2 { margin: 0; font-size: var(--haui-text-body); font-weight: 500; }
  .haui-discovered header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); }
  .haui-discovered ul { margin: 0; padding: 0; list-style: none; }
  .haui-discovered li { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 58px; padding: 0 16px; border-top: 1px solid var(--divider-color); }
  .haui-discovered li:first-child { border-top: 0; }
  .haui-discovered li > div { display: flex; min-width: 0; flex-direction: column; }
  .haui-discovered li > div > span { color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); }
  .haui-discovered li .haui-button { min-height: 34px; }
  .haui-device-card-name, .haui-device-row-name { border: 0; padding: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-weight: 500; text-align: start; cursor: pointer; }
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
  /* The summary strip is the inventory's header, and it is as tall as the Latest events header
     beside it — that one carries the title with the quiet actions on it, the scope line under it and
     its padding, plus the hairline over the timeline — so the first row under either card starts
     level. */
  .haui-inventory-overview {
    display: grid;
    align-content: center;
    box-sizing: border-box;
    min-height: calc(30px + var(--haui-space-1) + var(--haui-text-caption) * var(--haui-line-height-tight) + var(--haui-space-3) * 2 + 1px);
    padding: 20px 28px 16px;
  }
  .haui-fleet-inventory-heading { flex: 0 0 auto; }
  .haui-fleet-inventory-heading h2 { white-space: nowrap; }
  .haui-fleet-summary { display: grid; gap: 0; padding: 0; }
  /* The segments close the card: one per device in its connection tone, under the table. */
  .haui-inventory-footer { flex: 0 0 auto; padding: 16px 20px; border-top: 1px solid var(--divider-color); }
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
  .haui-fleet-lead strong { color: var(--secondary-text-color); font-size: var(--haui-text-label); font-variant-numeric: tabular-nums; font-weight: 500; line-height: var(--haui-line-height-tight); }
  .haui-fleet-lead > span { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  /* The figures keep their labels above the values, so the strip reads as one row. */
  .haui-fleet-facts { display: flex; gap: 20px; margin: 0 0 0 auto; }
  .haui-fleet-facts > div { display: grid; gap: 4px; }
  .haui-fleet-facts dt { color: var(--secondary-text-color); font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .05em; text-transform: uppercase; }
  .haui-fleet-facts dd { margin: 0; font-size: var(--haui-text-label); font-variant-numeric: tabular-nums; }
  .haui-fleet-bar { display: flex; gap: 4px; height: 6px; }
  .haui-fleet-bar span { flex: 1; border-radius: var(--haui-radius-pill); background: var(--primary-color, #03a9f4); }
  .haui-fleet-bar .is-offline { background: var(--haui-bad); }
  .haui-fleet-bar .is-unknown { background: var(--secondary-text-color); }
  .haui-stat-placeholder { display: block; width: 64px; height: 15px; margin: 4px 0; border-radius: var(--haui-radius-control); background: var(--secondary-background-color); }
  .haui-device-inventory, .haui-event-list { min-width: 0; }
  /* The table is flush: its rows run to the card's edges. It takes the height the grid row gives
     the card — the events card beside it sets a minimum — so the segments stay at the card's foot;
     a longer device list scrolls under its column heads and the free space stays below the last
     row (align-content), not spread between the rows. */
  .haui-device-inventory { display: flex; max-height: 720px; flex-direction: column; overflow: hidden; }
  .haui-inventory-update { min-height: 32px; padding: 0 12px; font-size: var(--haui-text-caption); }
  .haui-inventory-update ha-icon { --mdc-icon-size: 16px; }
  /* The rows share the table's tracks (subgrid), so the values and actions take their widest
     cell's width in every row and the device name takes the rest. */
  .haui-device-table { display: grid; grid-template-columns: minmax(200px, 1fr) repeat(3, max-content) auto; column-gap: 28px; flex: 1 1 auto; align-content: start; overflow: hidden auto; overscroll-behavior: contain; scrollbar-width: thin; }
  /* Roomy inventory rows keep device details easy to scan without making the table feel bulky. */
  .haui-device-row { display: grid; grid-column: 1 / -1; grid-template-columns: subgrid; align-items: center; min-height: 56px; padding: 0 20px; border-top: 1px solid var(--divider-color); font-size: var(--haui-text-label); }
  .haui-device-row:not(.haui-device-row-head):hover { background: color-mix(in srgb, var(--primary-text-color) 4%, transparent); }
  .haui-device-row[tabindex] { cursor: pointer; }
  .haui-device-row.is-selected,
  .haui-device-row.is-selected:hover {
    background: color-mix(in srgb, var(--primary-color) 10%, transparent);
    box-shadow: inset 3px 0 0 var(--primary-color);
  }
  .haui-device-row-head { position: sticky; z-index: 1; top: 0; min-height: 32px; background: color-mix(in srgb, var(--secondary-background-color) 60%, var(--haui-card-background)); color: var(--secondary-text-color); font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .05em; text-transform: uppercase; }
  .haui-device-row-identity { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .haui-device-row-identity > div { min-width: 0; }
  .haui-device-row-name { display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* Addresses and versions line up in the mono face, as Home Assistant aligns its table values. */
  .haui-device-row-ip, .haui-device-row-version { overflow: hidden; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-row-actions { display: flex; align-items: center; justify-content: end; gap: 4px; }
  .haui-device-row-actions .haui-badge { margin-inline-end: 4px; padding: 4px 8px; font-size: var(--haui-text-eyebrow); }
  .haui-device-row-version.is-mismatch { display: grid; justify-items: start; gap: 4px; white-space: normal; }
  .haui-device-row-version.is-mismatch > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-row-version .haui-device-row-mismatch { padding: 4px 4px; font-size: var(--haui-text-eyebrow); }
  /* The event list follows the inventory: it has no height of its own (size containment), so it
     stretches to the row the inventory sets and scrolls inside it. */
  .haui-event-list { display: flex; min-height: 320px; flex-direction: column; contain: size; }
  /* A quiet text action on the event list's title line. */
  .haui-event-list > header .haui-event-actions { display: flex; flex: 0 0 auto; align-items: center; gap: var(--haui-space-1); margin-inline-start: auto; }
  .haui-event-list > header .haui-event-logs,
  .haui-event-list > header .haui-event-restore,
  .haui-event-list > header .haui-event-reset { min-height: 30px; padding: 0 8px; border: 0; border-radius: var(--haui-radius-pill); color: var(--primary-color); background: transparent; font-size: var(--haui-text-caption); font-weight: 500; }
  .haui-event-list > header .haui-event-logs { margin-inline-end: -8px; }
  .haui-event-list > header .haui-event-logs:hover:not(:disabled),
  .haui-event-list > header .haui-event-restore:hover:not(:disabled),
  .haui-event-list > header .haui-event-reset:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  /* The events as a timeline: a rail through the level dots, so the eye follows time down. */
  .haui-event-list ol { display: grid; min-height: 0; flex: 1 1 auto; align-content: start; overflow-y: auto; overscroll-behavior: contain; margin: 0; padding: 4px 12px 8px; list-style: none; scrollbar-width: thin; }
  .haui-event-list li { position: relative; display: grid; grid-template-columns: 20px minmax(0, 1fr); align-items: start; gap: 8px; padding: 8px 0; border-top: 0; }
  .haui-event-list li::before { content: ''; position: absolute; top: 0; bottom: 0; left: 9px; width: 1px; background: color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
  .haui-event-list li:first-child::before { top: 18px; }
  .haui-event-list li:last-child::before { bottom: calc(100% - 22px); }
  /* A level dot is a signal indicator, like the connection icon's circle: it carries the tone
     itself, mixed toward the theme's text colour only as far as it still reads amber and red.
     The 4.5:1 text tones read almost black at 12px; a recognisable amber cannot reach 3:1 on a
     pale chip, so the level in the row's accessible text carries the state. */
  .haui-event-node { position: relative; z-index: 1; display: grid; width: 19px; height: 19px; margin-top: 4px; place-items: center; border-radius: var(--haui-radius-round); color: color-mix(in srgb, var(--state-icon-color, #44739e) 55%, var(--primary-color, #03a9f4)); background: color-mix(in srgb, currentcolor 14%, var(--card-background-color)); --mdc-icon-size: 12px; }
  .haui-event-warn .haui-event-node { color: color-mix(in srgb, var(--haui-warn) 80%, var(--primary-text-color, #212121)); }
  .haui-event-error .haui-event-node { color: color-mix(in srgb, var(--haui-bad) 92%, var(--primary-text-color, #212121)); }
  .haui-event-debug .haui-event-node { color: var(--secondary-text-color); }
  .haui-event-copy { display: grid; gap: 4px; min-width: 0; }
  .haui-event-copy p { display: -webkit-box; overflow: hidden; margin: 0; font-size: var(--haui-text-label); line-height: var(--haui-line-height-copy); overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .haui-event-meta { display: flex; min-width: 0; align-items: center; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-event-device { overflow: hidden; color: var(--primary-text-color); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
  .haui-event-device + time::before { content: '·'; margin: 0 4px; color: var(--disabled-text-color); }
  /* The device name gives way first; the time and the repeat count stay whole. */
  .haui-event-meta time, .haui-event-repeat { flex: 0 0 auto; white-space: nowrap; }
  .haui-event-repeat { margin-inline-start: 4px; padding: 0 4px; border-radius: var(--haui-radius-pill); background: var(--secondary-background-color); font-size: var(--haui-text-eyebrow); font-variant-numeric: tabular-nums; font-weight: 500; line-height: var(--haui-line-height); }
  .haui-event-warn .haui-event-repeat { background: var(--haui-warn-soft); color: var(--haui-warn-text); }
  .haui-event-error .haui-event-repeat { background: var(--haui-bad-soft); color: var(--haui-bad-text); }
  .haui-sort-handle { display: inline-flex; align-items: center; padding: 4px; border-radius: var(--haui-radius-control); color: var(--secondary-text-color); cursor: grab; --mdc-icon-size: 18px; }
  .haui-device-row .haui-row-action { width: 30px; height: 30px; --mdc-icon-size: 17px; }
  .haui-device-sort .haui-sort-handle { background: var(--card-background-color); }
  @container haui-editor (max-width: 560px) { .haui-fleet-facts { gap: 12px; } .haui-fleet-lead > span, .haui-fleet-inventory-heading { display: none; } }
  @container haui-editor (max-width: 1120px) { .haui-device-table { grid-template-columns: minmax(200px, 1fr) repeat(2, max-content) auto; } .haui-device-row-head > :nth-child(2), .haui-device-row > :nth-child(2) { display: none; } }
  /* Stacked, the event list has no neighbour to follow and takes its own height again. */
  @container haui-editor (max-width: 980px) { .haui-fleet-grid { grid-template-columns: minmax(0, 1fr); } .haui-event-list { min-height: 0; contain: none; } .haui-event-list ol { max-height: 480px; } }
  @container haui-editor (max-width: 720px) {
    .haui-inventory-overview { padding: 16px 12px 12px; }
    .haui-inventory-footer { padding: 12px; }
  }
  @container haui-editor (max-width: 720px) { .haui-dashboard-content { width: calc(100% - 28px); padding-top: 16px; } .haui-device-table { grid-template-columns: minmax(0, 1fr) repeat(2, max-content) auto; column-gap: 12px; } .haui-device-row { padding: 4px 12px; } .haui-device-row-head > :nth-child(2), .haui-device-row > :nth-child(2) { display: none; } .haui-device-row-actions { grid-column: 4; } }
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
  .haui-rollout-error { margin: 0; font-size: var(--haui-text-caption); color: var(--haui-bad-text); }
  .haui-rollout-actions { display: flex; justify-content: flex-end; margin-top: 8px; }
`;
