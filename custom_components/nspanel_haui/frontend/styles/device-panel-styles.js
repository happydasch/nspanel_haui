import { css } from '../lit-import.js';

export const devicePanelStyles = css`  /* The Panels view's card in the side stack: the selected panel, or the list's
     overview. A plain surface like the device cards, with the panel's render. */
  /* The panel's card is its own container: the facts fit two per row while it is
     wide enough and one per row on a narrow screen (below the card's rules). */
  .haui-panel-info { container: haui-panel-info / inline-size; }
  .haui-panel-info .haui-surface-heading-copy { min-width: 0; flex: 1 1 auto; }
  /* The selected panel's subtitle and the overview's hint wrap: they carry text, not a status. */
  .haui-panel-info .haui-surface-heading-copy p { overflow: visible; white-space: normal; }
  .haui-panel-info-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border: 1px solid color-mix(in srgb, var(--primary-color) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color)); --mdc-icon-size: 20px; }
  /* The render and its description: open, the render takes the card's width with the
     description under it; folded, the render is a thumbnail with the description
     beside it. */
  .haui-panel-info-preview-block { display: grid; gap: 8px; }
  .haui-panel-info-preview-block.is-folded { grid-template-columns: 112px minmax(0, 1fr); align-items: center; gap: 12px; }
  .haui-panel-info-preview-block.is-folded:has(.is-portrait) { grid-template-columns: 62px minmax(0, 1fr); }
  .haui-panel-info-preview { display: block; box-sizing: border-box; overflow: hidden; width: 100%; max-width: 320px; aspect-ratio: 450 / 320; margin-inline: auto; padding: 0; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-control); background: var(--haui-screen); }
  .haui-panel-info-preview.is-portrait { max-width: 200px; aspect-ratio: 320 / 480; }
  /* The render is its own toggle: a chevron badge sits in its corner. */
  .haui-panel-info-preview.is-toggle { position: relative; color: inherit; font: inherit; cursor: pointer; }
  .haui-panel-info-preview.is-toggle:hover { border-color: var(--primary-color); }
  .haui-panel-info-preview.is-small { max-width: none; margin: 0; }
  .haui-panel-info-preview-toggle { position: absolute; top: 4px; right: 4px; display: grid; width: 20px; height: 20px; place-items: center; border-radius: var(--haui-radius-round); background: color-mix(in srgb, var(--card-background-color) 82%, transparent); box-shadow: var(--haui-shadow-card); color: var(--secondary-text-color); --mdc-icon-size: 14px; }
  .haui-panel-info-preview.is-portrait .haui-panel-info-preview-toggle { top: 3px; right: 3px; width: 16px; height: 16px; --mdc-icon-size: 12px; }
  .haui-panel-info-preview nspanel-simulator-frame { display: block; width: 100%; height: 100%; pointer-events: none; }
  .haui-panel-info-description { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.45; }
  /* The facts are label/value rows: two pairs per row, each value beside its own
     label, with no fill or frame of its own. */
  .haui-panel-info-facts { display: grid; grid-template-columns: max-content minmax(0, 1fr) max-content minmax(0, 1fr); align-items: baseline; gap: 8px 16px; margin: 0; padding: 0; }
  /* The pairs are the list's own items: that is what lines the labels and values up. */
  .haui-panel-info-facts > div { display: contents; }
  /* A little air before a row's second pair keeps the two apart; the pairs keep
     their own label column, so the values of a half still line up. */
  .haui-panel-info-facts > div:nth-child(2n) > dt { padding-inline-start: 12px; }
  .haui-panel-info-facts dt { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-panel-info-facts dd { margin: 0; overflow-wrap: anywhere; color: var(--primary-text-color); font-size: var(--haui-text-body); font-weight: 500; }
  .haui-panel-info-key { font-family: var(--haui-mono); font-size: var(--haui-text-caption); font-weight: 400; }
  /* A narrow card holds one fact per row. */
  @container haui-panel-info (max-width: 360px) {
    .haui-panel-info-facts { grid-template-columns: max-content minmax(0, 1fr); }
    .haui-panel-info-facts > div:nth-child(2n) > dt { padding-inline-start: 0; }
  }
  /* The actions mirror the row's menu; Delete reads as the destructive one. */
  .haui-panel-info .haui-card-actions .haui-button { flex: 1 1 auto; min-width: 0; min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-panel-info .haui-button-danger { color: var(--error-color, #db4437); }
  .haui-panel-info .haui-button-danger:hover:not(:disabled) {
    border-color: var(--error-color, #db4437);
    background: var(--haui-bad-soft);
  }
  /* The overview: one row per group with its count, then the list's tips on a soft block. */
  .haui-panels-overview-groups { display: grid; margin: 0; padding: 0; list-style: none; }
  .haui-panels-overview-groups > li { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; align-items: center; gap: 8px; min-height: 34px; border-bottom: 1px solid var(--divider-color); }
  .haui-panels-overview-groups > li:last-child { border-bottom: 0; }
  .haui-panels-overview-groups ha-icon { color: var(--secondary-text-color); --mdc-icon-size: 16px; }
  .haui-panels-overview-groups span { overflow: hidden; font-size: var(--haui-text-label); text-overflow: ellipsis; white-space: nowrap; }
  .haui-panels-overview-groups strong { box-sizing: border-box; min-width: 22px; padding: 4px 8px; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 500; text-align: center; }
  .haui-panels-overview-hints { display: grid; gap: 8px; margin: 0; padding: 8px 12px; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); list-style: none; }
  .haui-panels-overview-hints > li { display: grid; grid-template-columns: 18px minmax(0, 1fr); align-items: start; gap: 8px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.45; }
  .haui-panels-overview-hints ha-icon { margin-top: 4px; --mdc-icon-size: 15px; }
  /* Home and Idle are the two roles the device assigns to panels. */
  .haui-panels-overview-roles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 0; }
  .haui-panels-overview-role-tile { display: grid; min-width: 0; align-content: start; gap: 8px; padding: 8px; border: 0; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); color: inherit; font: inherit; text-align: start; cursor: pointer; transition: background 120ms ease; }
  .haui-panels-overview-role-tile:hover:not(:disabled) { background: var(--haui-surface-strong); }
  .haui-panels-overview-role-tile:disabled { cursor: not-allowed; opacity: .6; }
  .haui-panels-overview-role-heading { display: flex; min-width: 0; align-items: center; gap: 8px; }
  .haui-panels-overview-role-icon { width: 22px; height: 22px; flex: 0 0 auto; box-shadow: none; }
  .haui-panels-overview-role-label { overflow: hidden; color: var(--secondary-text-color); font-size: var(--haui-text-caption); text-overflow: ellipsis; white-space: nowrap; }
  .haui-panels-overview-role-value { color: var(--primary-text-color); font-size: var(--haui-text-label); font-weight: 600; line-height: 1.35; overflow-wrap: anywhere; }
  .haui-workspace-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-preview-controls { display: flex; flex: 0 0 auto; align-items: center; gap: 8px; }
  /* The editor's one search field, drawn like Home Assistant's outlined search
     input (ha-input-search): the placeholder is the label, the border is its
     quiet neutral and turns primary on focus, and the pill matches the segmented
     toggles it sits beside. Both search bars - the panel list's and the panel
     catalog's - carry this look; only their box takes a different share of its row. */
  .haui-panel-search,
  .haui-panel-catalog-search-field { box-sizing: border-box; min-width: 0; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border: 1px solid var(--ha-color-border-neutral-quiet, var(--divider-color)); border-radius: var(--ha-border-radius-pill, var(--haui-radius-pill)); color: var(--secondary-text-color); background: var(--card-background-color); --mdc-icon-size: 18px; transition: border-color 120ms ease, background-color 120ms ease; }
  .haui-panel-search:hover,
  .haui-panel-catalog-search-field:hover { border-color: var(--ha-color-border-neutral-normal, var(--secondary-text-color)); background: var(--ha-color-form-background-hover, var(--haui-surface-soft)); }
  .haui-panel-search:focus-within,
  .haui-panel-catalog-search-field:focus-within { border-color: var(--primary-color); background: var(--card-background-color); }
  .haui-panel-search > ha-icon,
  .haui-panel-catalog-search-field > ha-icon { flex: 0 0 auto; }
  .haui-panel-search input,
  .haui-panel-catalog-search-field input { box-sizing: border-box; width: 100%; min-width: 0; height: 100%; flex: 1 1 auto; border: 0; outline: 0; padding: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-size: var(--haui-text-body); }
  .haui-panel-search input::placeholder,
  .haui-panel-catalog-search-field input::placeholder { color: var(--ha-color-neutral-60, var(--secondary-text-color)); }
  /* Shares the row with the view toggle at every width: it takes what the toggle leaves, up to its full size. */
  .haui-panel-search { display: inline-flex; max-width: 260px; flex: 1 1 0; }
  /* The view toggle is as tall as the field beside it (34px options + the toggle's 3px padding). */
  .haui-workspace-header .haui-segmented-option { min-height: 34px; }
  .haui-preview-tool { display: inline-flex; min-height: 32px; align-items: center; gap: 4px; padding: 0 8px; border: 1px solid transparent; border-radius: var(--haui-radius-pill); color: var(--secondary-text-color); background: transparent; font: inherit; font-size: var(--haui-text-caption); font-weight: 500; white-space: nowrap; cursor: pointer; }
  .haui-preview-tool:hover:not(:disabled) { background: var(--haui-surface-soft); color: var(--primary-text-color); }
  .haui-preview-tool.is-active { background: var(--haui-surface-strong); color: var(--primary-text-color); }
  /* Live acts on the real panel: its pressed state takes the live tint. */
  .haui-preview-tool.is-live.is-active { background: var(--haui-live-border); }
  .haui-preview-tool:disabled { cursor: not-allowed; opacity: .5; }
  .haui-workspace-body.is-preview { display: flex; }
  .haui-workspace-body.is-preview > * { flex: 1 1 auto; }
  .haui-segmented-count { min-width: 18px; padding: 4px 4px; border-radius: var(--haui-radius-pill); background: var(--haui-surface-soft); font-size: var(--haui-text-eyebrow); text-align: center; }
  .haui-panel-catalog { display: grid; align-content: start; gap: 12px; overflow-y: auto; overscroll-behavior: contain; padding: 0 16px 16px; }
  /* The toolbar is the catalog's first row, so its own padding is the only space
     above the field: the grid has no top padding to double it. Negative inline
     margins let the bar and its divider span the full sidebar width. */
  .haui-panel-catalog-controls { position: sticky; z-index: 1; top: 0; margin-inline: -16px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); background: var(--card-background-color); }
  .haui-panel-catalog-controls-row { display: flex; min-width: 0; align-items: center; gap: 8px; }
  .haui-panel-catalog-layout { display: flex; flex: 0 0 auto; align-items: center; }
  /* 34px options in the toggle's 3px padding make the toggle as tall as the 40px field beside it. */
  .haui-panel-catalog-layout .haui-segmented-option { position: relative; box-sizing: border-box; width: 38px; min-height: 34px; justify-content: center; padding: 0; }
  .haui-panel-catalog-layout .haui-segmented-option > span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .haui-panel-catalog-layout .haui-segmented-option > ha-icon { --mdc-icon-size: 20px; }
  .haui-panel-catalog-hint { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); }
  .haui-panel-catalog > .haui-config-section-intro { margin: 0; }
  /* The catalog's field only adds its share of the toolbar row to the shared search look. */
  .haui-panel-catalog-search { display: flex; min-width: 0; flex: 1 1 auto; }
  .haui-panel-catalog-search-field { display: flex; flex: 1 1 auto; }
  .haui-panel-catalog-list { display: grid; gap: 8px; }
  .haui-panel-catalog-option { display: grid; grid-template-columns: 28px minmax(0, 1fr) 18px; align-items: center; gap: 8px; width: 100%; padding: 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-control); color: var(--primary-text-color); background: var(--card-background-color); font: inherit; text-align: start; cursor: pointer; }
  /* Large previews sit above their text; compact previews share the row. */
  .haui-panel-catalog-option[data-preview] { grid-template-columns: minmax(0, 1fr) 18px; gap: 8px 12px; }
  .haui-panel-catalog-preview { display: block; grid-column: 1 / -1; width: 100%; aspect-ratio: 450 / 320; overflow: hidden; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-control); background: var(--haui-screen); pointer-events: none; }
  .haui-panel-catalog-preview.is-portrait { width: 100%; max-width: 320px; aspect-ratio: 320 / 480; margin-inline: auto; }
  .haui-panel-catalog-option[data-preview] .haui-panel-catalog-preview nspanel-simulator-frame { display: block; width: 100%; height: 100%; }
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-option[data-preview] { grid-template-columns: 64px minmax(0, 1fr) 18px; gap: 8px; }
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-preview { grid-column: auto; grid-row: 1; width: 64px; aspect-ratio: 450 / 320; }
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-preview.is-portrait { width: 48px; max-width: none; aspect-ratio: 320 / 480; margin-inline: 0 auto; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) { display: grid; gap: 4px; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) > span { color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.35; }
  .haui-panel-catalog-option:hover { border-color: var(--primary-color); }
  /* Collapsible catalog sections and the device groups inside the copy section,
     drawn like the panel editor's config sections: a heading row in the content
     (no box around it), tinted while open or hovered, the chevron at its end.
     The row's 12px inset lines the icon up with the cards' content. */
  .haui-panel-catalog-section,
  .haui-panel-catalog-group { display: block; }
  .haui-panel-catalog-section > summary,
  .haui-panel-catalog-group > summary { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: var(--haui-radius-control); color: var(--primary-text-color); font-size: var(--haui-text-body); font-weight: 500; list-style: none; cursor: pointer; user-select: none; }
  .haui-panel-catalog-section > summary::-webkit-details-marker,
  .haui-panel-catalog-group > summary::-webkit-details-marker { display: none; }
  /* The same chevron the cards end with, turned down while the section is open. */
  .haui-panel-catalog-chevron { flex: 0 0 auto; margin-inline-start: auto; color: var(--secondary-text-color); --mdc-icon-size: 18px; transition: transform 150ms ease; }
  .haui-panel-catalog-section[open] > summary .haui-panel-catalog-chevron,
  .haui-panel-catalog-group[open] > summary .haui-panel-catalog-chevron { transform: rotate(90deg); }
  .haui-panel-catalog-section > summary:hover,
  .haui-panel-catalog-section[open] > summary,
  .haui-panel-catalog-group > summary:hover,
  .haui-panel-catalog-group[open] > summary { background: var(--secondary-background-color); }
  .haui-panel-catalog-section > summary > ha-icon,
  .haui-panel-catalog-group > summary > ha-icon { flex: 0 0 auto; color: var(--secondary-text-color); --mdc-icon-size: 18px; }
  .haui-panel-catalog-section > summary > span:first-of-type,
  .haui-panel-catalog-group > summary > span:first-of-type { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-panel-catalog-content { display: grid; gap: 8px; padding-block-start: 8px; }
  /* A device group sits inside its section: one step in, one step smaller. */
  .haui-panel-catalog-group { margin-inline-start: 12px; }
  .haui-panel-catalog-group > summary { font-size: var(--haui-text-label); }
  .haui-panel-catalog-content .haui-panel-catalog-hint { margin: 0; }
  .haui-panel-catalog-count { box-sizing: border-box; min-width: 20px; padding: 4px 8px; border-radius: var(--haui-radius-control); background: var(--card-background-color); color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 500; text-align: center; }
  .haui-panel-catalog-section > summary:hover .haui-panel-catalog-count,
  .haui-panel-catalog-section[open] > summary .haui-panel-catalog-count,
  .haui-panel-catalog-group > summary:hover .haui-panel-catalog-count,
  .haui-panel-catalog-group[open] > summary .haui-panel-catalog-count { background: var(--secondary-background-color); }
  /* Diagnostics: the collapsed heading carries the connection status; expanded shows tiles and hub details. */
  .haui-device-diagnostics { display: grid; gap: 12px; }
  /* The heading icon, drawn like the connection icon of the card above; its corner bubble counts the issues. */
  .haui-diag-status { --diag-tone: var(--haui-good); position: relative; display: grid; box-sizing: border-box; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border: 1px solid color-mix(in srgb, var(--diag-tone) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--diag-tone); background: color-mix(in srgb, var(--diag-tone) 12%, var(--card-background-color)); --mdc-icon-size: 20px; }
  .haui-diag-status.is-warning { --diag-tone: var(--haui-warn); }
  .haui-backup-status { display: grid; box-sizing: border-box; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border: 1px solid color-mix(in srgb, var(--secondary-text-color) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--secondary-text-color); background: color-mix(in srgb, var(--secondary-text-color) 12%, var(--card-background-color)); --mdc-icon-size: 20px; }
  .haui-diag-status-count { position: absolute; top: -4px; right: -4px; display: grid; box-sizing: border-box; min-width: 16px; height: 16px; place-items: center; padding: 0 4px; border-radius: var(--haui-radius-control); background: var(--diag-tone); box-shadow: 0 0 0 2px var(--card-background-color); color: var(--text-primary-color, #fff); font-size: var(--haui-text-eyebrow); font-weight: 600; line-height: 1; }
  /* The status icon leads the heading; the title takes the free room, so the chevron sits at the end. */
  .haui-device-details .haui-surface-heading-copy, .haui-diagnostics-card .haui-surface-heading-copy,
  .haui-yaml-card .haui-surface-heading-copy { flex: 1 1 auto; }
  .haui-expand-toggle { flex: 0 0 auto; }
  .haui-device-diagnostics .is-warning, .haui-device-details .haui-diag-tiles .is-warning { color: var(--haui-warn); }
  .haui-device-diagnostics .is-danger { color: var(--haui-bad); }
  .haui-diag-tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .haui-diag-tile { display: flex; min-width: 0; flex-direction: column; gap: 4px; padding: 8px 12px; border: 0; border-radius: var(--haui-radius-control); color: var(--primary-text-color); background: var(--haui-surface-soft); font: inherit; text-align: start; }
  button.haui-diag-tile { cursor: pointer; }
  .haui-diag-tile-label { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-tile-value { display: flex; align-items: flex-end; gap: 4px; font-size: var(--haui-text-title); font-weight: 500; }
  .haui-diag-tile-value .haui-rssi-bars { margin-bottom: 4px; }
  .haui-diag-check { display: flex; align-items: flex-start; gap: 8px; color: var(--primary-text-color); font-size: var(--haui-text-body); cursor: pointer; }
  .haui-diag-check input { flex: 0 0 auto; width: 18px; height: 18px; margin: 4px 0 0; accent-color: var(--primary-color); cursor: pointer; }
  .haui-diag-check-copy { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
  .haui-diag-check-hint { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-tools { display: flex; flex-wrap: wrap; gap: 8px; }
  .haui-diag-tools .haui-button { min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-diag-internals { border-top: 1px solid var(--divider-color); padding-top: 12px; }
  .haui-diag-internals dl { display: grid; margin: 4px 0 8px; }
  .haui-diag-internals dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-diag-internals dt { color: var(--secondary-text-color); }
  .haui-diag-internals dd { overflow: hidden; margin: 0; text-overflow: ellipsis; white-space: nowrap; }
  /* Watched entities: the name and live state, the entity id and attributes below; a row opens the entity. */
  .haui-diag-entities { display: grid; }
  .haui-diag-entity { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; width: 100%; padding: 4px 0; border: 0; border-bottom: 1px solid var(--divider-color); color: var(--primary-text-color); background: none; font: inherit; font-size: var(--haui-text-caption); text-align: start; }
  button.haui-diag-entity { cursor: pointer; }
  button.haui-diag-entity:hover .haui-diag-entity-name { color: var(--primary-color); }
  .haui-diag-entity-name, .haui-diag-entity-id { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-state { max-width: 12em; overflow: hidden; text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-id { grid-column: 1 / -1; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); }
  .haui-diag-internals-note { margin: 8px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-internals > .haui-button { min-height: 34px; margin-top: 8px; padding: 0 12px; font-size: var(--haui-text-label); }
  /* The connection state sits in the card heading; its details open over the body. */
  .haui-surface.haui-device-details { overflow: visible; }
  /* A tile's card opens past the bottom of the Diagnostics card too. */
  .haui-surface.haui-diagnostics-card { overflow: visible; }
  .haui-device-details .haui-surface-heading { position: relative; }
  .haui-conn-status { --conn-tone: var(--secondary-text-color); --conn-ring: var(--conn-tone); flex: 0 0 auto; }
  .haui-conn-status.online { --conn-tone: var(--haui-good); }
  .haui-conn-status.offline { --conn-tone: var(--haui-bad); }
  .haui-conn-status-button { position: relative; display: grid; width: 36px; height: 36px; place-items: center; padding: 0; border: 1px solid color-mix(in srgb, var(--conn-ring) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--conn-ring); background: color-mix(in srgb, var(--conn-ring) 12%, var(--card-background-color)); cursor: pointer; transition: background 150ms ease, border-color 150ms ease; --mdc-icon-size: 20px; }
  .haui-conn-status-button:hover, .haui-conn-status-button[aria-expanded="true"] { border-color: color-mix(in srgb, var(--conn-ring) 55%, transparent); background: color-mix(in srgb, var(--conn-ring) 20%, var(--card-background-color)); }
  /* The same icon, smaller and without the details card, in front of a Fleet table name. */
  .haui-conn-status-icon { position: relative; display: grid; box-sizing: border-box; width: 30px; height: 30px; place-items: center; border: 1px solid color-mix(in srgb, var(--conn-ring) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--conn-ring); background: color-mix(in srgb, var(--conn-ring) 12%, var(--card-background-color)); --mdc-icon-size: 17px; }
  .haui-conn-status-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: var(--haui-radius-round); background: var(--conn-tone); }
  /* The circle and its glyph show the Wi-Fi strength in the colours of the RSSI bars; the dot keeps the connection tone. */
  .haui-conn-status:has(ha-icon.haui-wifi-excellent) { --conn-ring: var(--haui-good); }
  .haui-conn-status:has(ha-icon.haui-wifi-good) { --conn-ring: var(--haui-wifi-good); }
  .haui-conn-status:has(ha-icon.haui-wifi-fair) { --conn-ring: var(--haui-warn); }
  .haui-conn-status:has(ha-icon.haui-wifi-weak) { --conn-ring: var(--haui-bad); }
  .haui-conn-status-button > .haui-conn-status-dot, .haui-conn-status-icon > .haui-conn-status-dot { position: absolute; top: 1px; right: 1px; box-shadow: 0 0 0 2px var(--card-background-color); }
  .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: haui-conn-pulse 2.4s ease-out infinite; }
  @keyframes haui-conn-pulse {
    0% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 2px color-mix(in srgb, var(--haui-good) 60%, transparent); }
    70%, 100% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 7px transparent; }
  }
  @media (prefers-reduced-motion: reduce) { .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: none; } }
  .haui-conn-card { position: absolute; z-index: 5; top: calc(100% - 6px); left: 12px; display: grid; width: min(280px, calc(100% - 24px)); gap: 8px; padding: 12px 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-card-radius); background: var(--card-background-color); box-shadow: var(--haui-shadow-overlay); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-conn-status:hover > .haui-conn-card, .haui-conn-status-button:focus-visible + .haui-conn-card, .haui-conn-status-button[aria-expanded="true"] + .haui-conn-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  .haui-conn-card-head { justify-content: flex-start; gap: 8px; padding: 0; border: 0; }
  .haui-conn-card-head .haui-surface-heading-copy { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
  .haui-conn-card-head h2 { margin: 0; font-size: var(--haui-text-body); font-weight: 500; }
  .haui-conn-card-head p { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-device-details .haui-conn-card dl > div { padding: 4px 0; }
  .haui-conn-card .haui-details-stale { margin: 0; color: var(--haui-warn); font-size: var(--haui-text-caption); line-height: 1.4; }
  .haui-device-details dl { display: grid; gap: 0; margin: 0; }
  .haui-device-details dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-device-details dl > div:last-child { border-bottom: 0; }
  .haui-device-details dt { color: var(--secondary-text-color); }
  .haui-device-details dd { overflow: hidden; margin: 0; font-family: var(--haui-mono); text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-surface-body { gap: 12px; }
  /* The Diagnostics tiles, with values that can run long (page names), cut off; dimmed while stale. */
  .haui-device-details .haui-diag-tile-value { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-diag-tiles.is-stale .haui-diag-tile-value { color: var(--secondary-text-color); }
  /* Offline is the current state, not a stale reading. */
  .haui-device-details .haui-diag-tiles .haui-diag-tile-value.is-danger { color: var(--haui-bad); }
  .haui-device-details .haui-diag-tile-value .haui-rssi-bars { margin-inline-start: 4px; }
  /* A tile shows its label and value; hover, focus or a tap opens its facts below it (ui/info-tile.js), a right-hand tile's aligned to its right edge. */
  .haui-tile-info { position: relative; min-width: 0; }
  .haui-tile-info > .haui-diag-tile { width: 100%; height: 100%; }
  .haui-tile-card { position: absolute; z-index: 5; top: calc(100% + 6px); left: 0; display: grid; box-sizing: border-box; width: max-content; min-width: 100%; max-width: min(280px, calc(200% + 8px)); gap: 8px; padding: 12px 12px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--card-background-color, #fff); box-shadow: var(--haui-shadow-overlay); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-tile-info:nth-child(even) > .haui-tile-card { right: 0; left: auto; }
  .haui-tile-card > strong { font-size: var(--haui-text-body); font-weight: 500; overflow-wrap: anywhere; }
  .haui-tile-card dl { display: grid; margin: 0; }
  .haui-tile-card dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-tile-card dl > div:last-child { border-bottom: 0; }
  .haui-tile-card dt { color: var(--secondary-text-color); white-space: nowrap; }
  .haui-tile-card dd { overflow: hidden; margin: 0; font-family: var(--haui-mono); text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-tile-card > p { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-tile-info > .haui-diag-tile:focus-visible + .haui-tile-card, .haui-tile-info > .haui-diag-tile[aria-expanded="true"] + .haui-tile-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  /* Only a real pointer hovers: a tap's sticky hover would keep the card open after a second tap. */
  @media (hover: hover) {
    .haui-tile-info > .haui-diag-tile:hover { background: var(--haui-surface-strong); }
    .haui-tile-info:hover > .haui-tile-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  }
  .haui-details-more > summary { display: flex; align-items: center; gap: 4px; padding: 4px 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); list-style: none; cursor: pointer; user-select: none; }
  .haui-details-more > summary::-webkit-details-marker { display: none; }
  .haui-details-more > summary::after { content: ""; width: 5px; height: 5px; border-right: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(-45deg); transition: transform 150ms ease; }
  .haui-details-more[open] > summary::after { transform: rotate(45deg); }
  .haui-details-more > summary:hover { color: var(--primary-text-color); }
  .haui-card-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  /* Two equal columns, so a pair of actions (YAML Import and Export) never wraps unevenly; a lead card's lone secondary action spans it. */
  .haui-yaml-actions, .haui-action-card-secondary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  /* The lead card (ui/action-card.js): tinted and never collapsed, so the view's next actions stand apart from the side-stack cards. */
  .haui-action-card { container: haui-action-card / inline-size; border: 1px solid color-mix(in srgb, var(--primary-color) 35%, var(--divider-color)); border-radius: var(--haui-card-radius); background: color-mix(in srgb, var(--primary-color) 9%, var(--card-background-color)); box-shadow: var(--haui-shadow-card); }
  .haui-action-card-inner { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; grid-template-areas: "icon copy tool" "actions actions actions" "note note note" "management management management"; align-items: center; gap: 12px; padding: 16px 16px; }
  .haui-action-card-inner:not(.is-with-note):not(.is-with-management) { grid-template-areas: "icon copy tool" "actions actions actions"; }
  .haui-action-card-inner.is-with-note:not(.is-with-management) { grid-template-areas: "icon copy tool" "actions actions actions" "note note note"; }
  .haui-action-card-inner.is-with-management:not(.is-with-note) { grid-template-areas: "icon copy tool" "actions actions actions" "management management management"; }
  .haui-action-card-icon { display: grid; width: 40px; height: 40px; grid-area: icon; place-items: center; border-radius: var(--haui-radius-round); background: var(--primary-color); color: var(--text-primary-color, #fff); --mdc-icon-size: 22px; }
  .haui-action-card-copy { min-width: 0; grid-area: copy; }
  .haui-action-card-copy h2 { margin: 0; font-size: var(--haui-text-title); font-weight: 600; }
  .haui-action-card-copy p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: 1.4; }
  /* The settings cog at the end of the heading; pulled into the card's padding so its glyph lines up with the edge. */
  .haui-action-card-tool { grid-area: tool; align-self: start; margin: -4px -8px 0 0; }
  .haui-action-card-actions { display: grid; min-width: 0; grid-area: actions; gap: 8px; }
  .haui-action-card-secondary .haui-button, .haui-details-updates { min-width: 0; min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-action-card-secondary > :only-child { grid-column: 1 / -1; }
  .haui-action-card-note { grid-area: note; margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: 1.45; }
  .haui-action-card-management { grid-area: management; min-width: 0; }
  .haui-device-option-controls { display: grid; gap: 12px; min-width: 0; padding-top: 12px; border-top: 1px solid color-mix(in srgb, var(--primary-color) 20%, var(--divider-color)); }
  /* Three options, always one row: plain buttons, tinted with the lead card's own
     accent so they belong to it rather than reading as cards inside a card. */
  .haui-device-option-buttons { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  .haui-device-option-buttons .haui-device-option { min-width: 0; min-height: 40px; padding: 0 12px; border-color: color-mix(in srgb, var(--primary-color) 26%, transparent); background: color-mix(in srgb, var(--primary-color) 10%, transparent); font-size: var(--haui-text-label); }
  .haui-device-option-buttons .haui-device-option > ha-icon { flex: 0 0 auto; color: var(--primary-color); --mdc-icon-size: 18px; }
  .haui-device-option-buttons .haui-device-option > span { overflow: hidden; text-overflow: ellipsis; }
  /* Only a real pointer hovers, and the tint stays translucent on the tinted card. */
  @media (hover: hover) {
    .haui-device-option-buttons .haui-device-option:hover:not(:disabled) { border-color: color-mix(in srgb, var(--primary-color) 45%, transparent); background: color-mix(in srgb, var(--primary-color) 16%, transparent); }
  }
  /* A tight row drops the icons before it truncates the labels. */
  @container haui-action-card (max-width: 320px) {
    .haui-device-option-buttons .haui-device-option > ha-icon { display: none; }
  }
  /* One option's editor in the modal sidebar: the form scrolls, its action stays. */
  .haui-device-option-panel { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .haui-device-option-panel-body { display: grid; flex: 1 1 auto; align-content: start; gap: 12px; min-height: 0; overflow-y: auto; box-sizing: border-box; padding: 16px; overscroll-behavior: contain; }
  .haui-device-option-panel-actions { display: flex; flex: 0 0 auto; gap: 8px; box-sizing: border-box; padding: 12px 16px; border-top: 1px solid var(--divider-color); background: var(--card-background-color); }
  .haui-device-option-panel-actions .haui-button { flex: 1 1 auto; min-width: 0; }
  /* Keep the management controls on a full-width row below the primary action. */
  @container haui-action-card (min-width: 560px) {
    .haui-action-card-inner { grid-template-columns: 40px minmax(0, 1fr) auto auto; grid-template-areas: "icon copy actions tool" ". note actions tool" "management management management management"; row-gap: 4px; }
    .haui-action-card-inner:not(.is-with-note):not(.is-with-management) { grid-template-areas: "icon copy actions tool"; }
    .haui-action-card-inner.is-with-note:not(.is-with-management) { grid-template-areas: "icon copy actions tool" ". note note note"; }
    .haui-action-card-inner.is-with-management:not(.is-with-note) { grid-template-areas: "icon copy actions tool" "management management management management"; }
    .haui-action-card-tool { align-self: center; margin: 0 -8px 0 0; }
    .haui-action-card-actions.is-stacked { display: grid; align-items: stretch; }
    .haui-action-card-actions.is-stacked .haui-action-card-secondary { display: grid; width: 100%; }
    .haui-action-card-actions, .haui-action-card-secondary { display: flex; align-items: center; }
  }
`;
