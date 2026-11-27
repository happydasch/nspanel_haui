import { css } from '../lit-import.js';

export const devicePanelStyles = css`  /* The Panels view's side stack: the selected panel as a card, or the list's overview as
     plain content. A plain surface like the device cards, with the panel's render. */
  /* The selected panel's card is its own container: the facts fit two per row while it is
     wide enough and one per row on a narrow screen (below the card's rules). */
  .haui-panel-info { container: haui-panel-info / inline-size; }
  .haui-panel-info .haui-surface-heading-copy { min-width: 0; flex: 1 1 auto; }
  /* The selected panel's subtitle wraps: it carries text, not a status. */
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
  .haui-panel-info-description { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  /* The facts are label/value rows: two pairs per row, each value beside its own
     label, with no fill or frame of its own. */
  .haui-panel-info-facts { display: grid; grid-template-columns: max-content minmax(0, 1fr) max-content minmax(0, 1fr); align-items: baseline; gap: 8px 16px; margin: 0; padding: 0; }
  /* The pairs are the list's own items: that is what lines the labels and values up. */
  .haui-panel-info-facts > div { display: contents; }
  /* A little air before a row's second pair keeps the two apart; the pairs keep
     their own label column, so the values of a half still line up. */
  .haui-panel-info-facts > div:nth-child(2n) > dt { padding-inline-start: 12px; }
  .haui-panel-info-facts dt { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-panel-info-facts dd { margin: 0; overflow-wrap: anywhere; color: var(--primary-text-color); font-size: var(--haui-text-label); font-weight: 500; }
  .haui-panel-info-key { font-family: var(--haui-mono); font-size: var(--haui-text-label); font-weight: 400; }
  /* The role toggles lead the card above its render; actions follow the facts.
     Keep the two controls together without a divider beneath them. */
  .haui-panel-info-roles,
  .haui-panel-info-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .haui-panel-info-roles .haui-button,
  .haui-panel-info-actions .haui-button { min-width: 0; min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-panel-info-roles > :last-child:nth-child(odd),
  .haui-panel-info-actions > .haui-button:first-child:only-child,
  .haui-panel-info-actions > .haui-button:first-child:nth-last-child(n + 3) { grid-column: 1 / -1; }
  .haui-panel-info-roles .haui-button.is-active { border-color: var(--haui-surface-strong); background: var(--haui-surface-strong); font-weight: 500; }
  .haui-panel-info-roles .haui-button.is-active:hover:not(:disabled) { border-color: var(--divider-color); background: var(--haui-surface-strong); }
  /* A narrow card holds one fact per row. */
  @container haui-panel-info (max-width: 360px) {
    .haui-panel-info-facts { grid-template-columns: max-content minmax(0, 1fr); }
    .haui-panel-info-facts > div:nth-child(2n) > dt { padding-inline-start: 0; }
  }
  /* Narrower than this, a pair of buttons no longer fits: one per row. */
  @container haui-panel-info (max-width: 320px) {
    .haui-panel-info-roles,
    .haui-panel-info-actions { grid-template-columns: minmax(0, 1fr); }
  }
  /* Delete reads as the destructive one. */
  .haui-panel-info .haui-button-danger { color: var(--haui-bad-text); }
  .haui-panel-info .haui-button-danger ha-icon { color: var(--haui-bad-icon); }
  .haui-panel-info .haui-button-danger:hover:not(:disabled) {
    border-color: var(--error-color, #db4437);
    background: var(--haui-bad-soft);
  }
  /* The overview is plain content in the side stack, not a card: no frame, no heading,
     only the list's own facts. It is its own container for the role tiles' width. */
  .haui-panels-overview { container: haui-panels-overview / inline-size; display: grid; gap: 12px; }
  /* The overview: the counts and the list's tips are plain rows, not blocks of
     their own, and sit flush with the side stack's edges. */
  .haui-panels-overview-groups,
  .haui-panels-overview-hints { display: grid; margin: 0; padding: 0; list-style: none; }
  /* A count row keeps the table's height, so the three groups read as one list. */
  .haui-panels-overview-groups > li { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; align-items: center; gap: 8px; min-height: 34px; }
  .haui-panels-overview-groups ha-icon { color: var(--secondary-text-color); --mdc-icon-size: 16px; }
  .haui-panels-overview-groups > li > span:not(.haui-badge) { overflow: hidden; font-size: var(--haui-text-label); text-overflow: ellipsis; white-space: nowrap; }
  /* The tips are separate statements, so they keep a gap between them. */
  .haui-panels-overview-hints { gap: 8px; }
  .haui-panels-overview-hints > li { display: grid; grid-template-columns: 18px minmax(0, 1fr); align-items: start; gap: 8px; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  .haui-panels-overview-hints ha-icon { --mdc-icon-size: 15px; }
  /* Home and Idle are the two roles the device assigns to panels. */
  .haui-panels-overview-roles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 0; }
  .haui-panels-overview-role-tile { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; min-width: 0; gap: 8px; padding: 8px; border: 0; border-radius: var(--haui-radius-control); background: var(--haui-surface-soft); color: inherit; font: inherit; text-align: start; cursor: pointer; transition: background 120ms ease; }
  .haui-panels-overview-role-tile:hover:not(:disabled) { background: var(--haui-surface-strong); }
  .haui-panels-overview-role-tile:disabled { cursor: not-allowed; opacity: .6; }
  .haui-panels-overview-role-text { display: grid; min-width: 0; gap: 4px; }
  .haui-panels-overview-role-icon { width: 22px; height: 22px; box-shadow: none; }
  .haui-panels-overview-role-label { overflow: hidden; color: var(--secondary-text-color); font-size: var(--haui-text-caption); text-overflow: ellipsis; white-space: nowrap; }
  .haui-panels-overview-role-value { color: var(--primary-text-color); font-size: var(--haui-text-label); font-weight: 500; line-height: var(--haui-line-height-tight); overflow-wrap: anywhere; }
  /* A narrow side stack stacks the two role tiles so their value keeps its room. */
  @container haui-panels-overview (max-width: 360px) {
    .haui-panels-overview-roles { grid-template-columns: minmax(0, 1fr); }
  }
  /* The workspace's own band, like every card heading on the pages it opens. */
  .haui-workspace-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); background: var(--haui-surface-band); }
  .haui-preview-controls { display: flex; flex: 0 0 auto; align-items: center; gap: 8px; }
  /* The panel list's search (.haui-search-field) shares the row with the view toggle at every width: it takes what the toggle leaves, up to its full size. */
  .haui-panel-search { display: inline-flex; max-width: 260px; height: 40px; flex: 1 1 0; }
  /* The view toggle is as tall as the 40px field beside it: 30px options, the toggle's 4px padding and 1px border. */
  .haui-workspace-header .haui-segmented-option { min-height: 30px; }
  .haui-preview-tool { display: inline-flex; min-height: 32px; align-items: center; gap: 4px; padding: 0 8px; border: 1px solid transparent; border-radius: var(--haui-radius-pill); color: var(--secondary-text-color); background: transparent; font: inherit; font-size: var(--haui-text-caption); font-weight: 500; white-space: nowrap; cursor: pointer; }
  .haui-preview-tool:hover:not(:disabled) { background: var(--haui-surface-soft); color: var(--primary-text-color); }
  .haui-preview-tool.is-active { background: var(--haui-surface-strong); color: var(--primary-text-color); }
  /* Live acts on the real panel: its pressed state takes the live tint. */
  .haui-preview-tool.is-live.is-active { background: var(--haui-live-border); }
  .haui-preview-tool:disabled { cursor: not-allowed; opacity: .5; }
  .haui-workspace-body.is-preview { display: flex; }
  .haui-workspace-body.is-preview > * { flex: 1 1 auto; }
  .haui-panel-catalog { display: grid; align-content: start; gap: 12px; overflow-y: auto; overscroll-behavior: contain; padding: 0 16px; }
  /* The space below the last section is a row, not bottom padding: Firefox leaves a
     scroller's end padding (and its last child's margin) out of the scroll range while
     a sticky child (the toolbar) is inside. The 12px row gap plus this row make 16px. */
  .haui-panel-catalog::after { content: ""; height: 4px; }
  /* The toolbar is the catalog's first row, so its own padding is the only space
     above the field: the grid has no top padding to double it. Negative inline
     margins let the bar and its divider span the full sidebar width. */
  .haui-panel-catalog-controls { position: sticky; z-index: 1; top: 0; margin-inline: -16px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); background: var(--card-background-color); }
  .haui-panel-catalog-controls-row { display: flex; min-width: 0; align-items: center; gap: 8px; }
  .haui-panel-catalog-layout { display: flex; flex: 0 0 auto; align-items: center; }
  /* 30px options in the toggle's 4px padding and 1px border make it as tall as the 40px field beside it. */
  .haui-panel-catalog-layout .haui-segmented-option { position: relative; box-sizing: border-box; width: 38px; min-height: 30px; justify-content: center; padding: 0; }
  .haui-panel-catalog-layout .haui-segmented-option > span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .haui-panel-catalog-layout .haui-segmented-option > ha-icon { --mdc-icon-size: 20px; }
  .haui-panel-catalog-hint { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); }
  .haui-panel-catalog > .haui-config-section-intro { margin: 0; }
  /* The catalog's field only adds its share of the toolbar row to the shared search look. */
  .haui-panel-catalog-search { display: flex; min-width: 0; flex: 1 1 auto; }
  /* As tall as the layout toggle beside it. */
  .haui-panel-catalog-search-field { display: flex; height: 40px; flex: 1 1 auto; }
  .haui-panel-catalog-list { display: grid; gap: 12px; }
  /* One card per choice, read like the quick start card (quick-start-styles.js):
     the card radius and a roomier 16px inset, its title at body size with its
     icon (20px, one step over the icon default, as it leads a 16px title) and
     the description as the text under it. */
  .haui-panel-catalog-option { display: grid; grid-template-columns: 28px minmax(0, 1fr) 18px; align-items: center; gap: 12px; width: 100%; padding: 16px; border: 1px solid var(--divider-color); border-radius: var(--haui-card-radius); color: var(--primary-text-color); background: var(--card-background-color); font: inherit; text-align: start; cursor: pointer; }
  /* Large previews sit above their text; compact previews share the row. */
  .haui-panel-catalog-option[data-preview] { grid-template-columns: minmax(0, 1fr) 18px; gap: 12px 16px; }
  .haui-panel-catalog-preview { display: block; grid-column: 1 / -1; width: 100%; aspect-ratio: 450 / 320; overflow: hidden; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-control); background: var(--haui-screen); pointer-events: none; }
  .haui-panel-catalog-preview.is-portrait { width: 100%; max-width: 320px; aspect-ratio: 320 / 480; margin-inline: auto; }
  .haui-panel-catalog-option[data-preview] .haui-panel-catalog-preview nspanel-simulator-frame { display: block; width: 100%; height: 100%; }
  /* A compact thumb is as wide as the quick start card's preview column
     (quick-start-styles.js), so a layout reads the same in both lists, and the
     row takes that card's 16px between the thumb and its text (the thumb is a
     picture, not an icon). */
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-option[data-preview] { grid-template-columns: 128px minmax(0, 1fr) 18px; gap: 16px; }
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-preview { grid-column: auto; grid-row: 1; width: 128px; aspect-ratio: 450 / 320; }
  .haui-panel-catalog.is-compact-previews .haui-panel-catalog-preview.is-portrait { max-width: none; aspect-ratio: 320 / 480; margin-inline: 0 auto; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) { display: grid; gap: 4px; }
  /* A card with a preview carries the panel type's icon in its title, the pair
     the quick start card shows, because the thumbnail took the icon's column. */
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) > strong { display: flex; align-items: center; gap: var(--haui-space-2); font-size: var(--haui-text-body); }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) > strong > ha-icon { flex: 0 0 auto; color: var(--primary-color); --mdc-icon-size: 20px; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) > span { color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: var(--haui-line-height-copy); }
  .haui-panel-catalog-option:hover { border-color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color)); }
  /* Collapsible catalog sections and the device groups inside the copy section,
     drawn like the panel editor's config sections: a heading row in the content
     (no box around it), tinted while open or hovered, the chevron at its end.
     The row's 16px inset lines the icon up with the cards' content. */
  .haui-panel-catalog-section,
  .haui-panel-catalog-group { display: block; }
  .haui-panel-catalog-section > summary,
  .haui-panel-catalog-group > summary { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: var(--haui-radius-control); color: var(--primary-text-color); font-size: var(--haui-text-body); font-weight: 500; list-style: none; cursor: pointer; user-select: none; }
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
  /* Diagnostics: the collapsed heading carries the connection status; expanded shows tiles and hub details. */
  .haui-device-diagnostics { display: grid; gap: 12px; }
  .haui-diag-status-wrap { position: relative; display: block; flex: 0 0 auto; }
  .haui-diag-status { --diag-tone: var(--haui-good); position: relative; display: grid; box-sizing: border-box; width: 36px; height: 36px; place-items: center; padding: 0; border: 1px solid color-mix(in srgb, var(--diag-tone) 28%, transparent); border-radius: var(--haui-radius-round); color: var(--diag-tone); background: color-mix(in srgb, var(--diag-tone) 12%, var(--card-background-color)); font: inherit; cursor: pointer; transition: background 150ms ease, border-color 150ms ease; --mdc-icon-size: 20px; }
  .haui-diag-status.is-warning { --diag-tone: var(--haui-warn); }
  .haui-diag-status:hover, .haui-diag-status[aria-expanded="true"] { border-color: color-mix(in srgb, var(--diag-tone) 55%, transparent); background: color-mix(in srgb, var(--diag-tone) 20%, var(--card-background-color)); }
  .haui-diag-status-count { position: absolute; top: -4px; right: -4px; display: grid; box-sizing: border-box; min-width: 16px; height: 16px; place-items: center; padding: 0 4px; border-radius: var(--haui-radius-control); background: var(--diag-tone); box-shadow: 0 0 0 2px var(--card-background-color); color: var(--text-primary-color, #fff); font-size: var(--haui-text-caption); font-weight: 400; line-height: 1; }
  /* The status icon leads the heading; the title takes the free room, so the chevron sits at the end. */
  .haui-device-details .haui-surface-heading-copy, .haui-diagnostics-card .haui-surface-heading-copy { flex: 1 1 auto; }
  .haui-expand-toggle { flex: 0 0 auto; }
  .haui-device-diagnostics .is-warning, .haui-device-details .haui-diag-tiles .is-warning { color: var(--haui-warn-text); }
  .haui-device-details .haui-diag-tiles .is-good { color: var(--haui-good-text); }
  .haui-device-diagnostics .is-danger { color: var(--haui-bad-text); }
  .haui-diag-tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 0; }
  .haui-diag-tile { display: flex; min-width: 0; flex-direction: column; gap: 4px; padding: 8px 12px; border: 0; border-radius: var(--haui-radius-control); color: var(--primary-text-color); background: var(--haui-surface-soft); font: inherit; text-align: start; }
  button.haui-diag-tile { cursor: pointer; }
  .haui-diag-tile-label { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-tile-value { display: flex; align-items: flex-end; gap: 4px; font-size: var(--haui-text-label); font-weight: 500; }
  /* A tile's aside glyph (the Wi-Fi bars) belongs to the tile, not its value: it stands on the trailing edge, centred beside the label and the value. */
  .haui-diag-tile:has(> .haui-diag-tile-aside) { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-content: start; column-gap: 12px; row-gap: 4px; }
  .haui-diag-tile:has(> .haui-diag-tile-aside) > :not(.haui-diag-tile-aside) { grid-column: 1; }
  .haui-diag-tile-aside { display: flex; grid-column: 2; grid-row: 1 / span 2; align-self: center; }
  .haui-diag-tile-aside .haui-rssi-bars { height: 20px; }
  /* A value tile (ui/info-tile.js valueTile): a diagnostics tile that only shows, its icon before the label; the detail ends the value's row and wraps below it when the tile is too narrow. */
  .haui-value-tile { flex-flow: row wrap; align-items: baseline; align-content: flex-start; gap: 4px 12px; }
  .haui-value-tile > dt { display: flex; flex: 1 0 100%; align-items: flex-start; gap: 4px; --mdc-icon-size: 16px; }
  .haui-value-tile > dd { margin: 0; }
  .haui-value-tile > .haui-diag-tile-value.is-muted { color: var(--secondary-text-color); }
  .haui-value-tile > .haui-value-tile-detail { margin-inline-start: auto; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-check { display: flex; align-items: flex-start; gap: 8px; color: var(--primary-text-color); font-size: var(--haui-text-label); cursor: pointer; }
  .haui-diag-check input { flex: 0 0 auto; width: 18px; height: 18px; margin: 4px 0 0; accent-color: var(--primary-color); cursor: pointer; }
  .haui-diag-check-copy { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
  .haui-diag-check-hint { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-tools { display: flex; flex-wrap: wrap; gap: 8px; }
  .haui-diag-tools .haui-button { min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-diag-internals { border-top: 1px solid var(--divider-color); padding-top: 12px; }
  /* Open, the summary, the readings, the entities and the report each get their own room. */
  .haui-diag-internals[open] > summary { margin-bottom: 8px; }
  .haui-diag-internals dl { display: grid; margin: 0 0 16px; }
  .haui-diag-internals dl > div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-diag-internals dt { color: var(--secondary-text-color); }
  .haui-diag-internals dd { overflow: hidden; margin: 0; text-overflow: ellipsis; white-space: nowrap; }
  /* Watched entities: the name and live state, the entity id and attributes below; a row opens the entity. */
  .haui-diag-entities { display: grid; }
  .haui-diag-entity { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; width: 100%; padding: 8px 0; border: 0; border-bottom: 1px solid var(--divider-color); color: var(--primary-text-color); background: none; font: inherit; font-size: var(--haui-text-caption); text-align: start; }
  button.haui-diag-entity { cursor: pointer; }
  button.haui-diag-entity:hover .haui-diag-entity-name { color: var(--primary-color); }
  .haui-diag-entity-name, .haui-diag-entity-id { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-state { max-width: 12em; overflow: hidden; text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-id { grid-column: 1 / -1; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption); }
  .haui-diag-internals-note { margin: 12px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-internals > .haui-button { min-height: 34px; margin-top: 12px; padding: 0 12px; font-size: var(--haui-text-label); }
  /* The connection state sits in the card heading; its details open over the body. The card is its own
     container: how its two rows sit follows its own width, not the editor's. */
  .haui-surface.haui-device-details { overflow: visible; container: haui-device-details / inline-size; }
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
  .haui-conn-status:has(ha-icon.haui-wifi-good) { --conn-ring: var(--haui-good); }
  .haui-conn-status:has(ha-icon.haui-wifi-fair) { --conn-ring: var(--haui-warn); }
  .haui-conn-status:has(ha-icon.haui-wifi-weak) { --conn-ring: var(--haui-bad); }
  .haui-conn-status-button > .haui-conn-status-dot, .haui-conn-status-icon > .haui-conn-status-dot { position: absolute; top: 1px; right: 1px; box-shadow: 0 0 0 2px var(--card-background-color); }
  .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: haui-conn-pulse 2.4s ease-out infinite; }
  @keyframes haui-conn-pulse {
    0% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 2px color-mix(in srgb, var(--haui-good) 60%, transparent); }
    70%, 100% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 7px transparent; }
  }
  @media (prefers-reduced-motion: reduce) { .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: none; } }
  .haui-conn-card { position: absolute; z-index: 5; top: calc(100% - 6px); left: 12px; display: grid; grid-template-columns: minmax(0, 1fr); width: min(280px, calc(100% - 24px)); gap: 8px; padding: 12px 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-card-radius); background: var(--card-background-color); box-shadow: var(--haui-shadow-overlay); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-conn-status-button:focus-visible + .haui-conn-card, .haui-conn-status-button[aria-expanded="true"] + .haui-conn-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  .haui-diag-popover { width: min(280px, calc(100vw - 24px)); max-height: min(60vh, 320px); overflow: auto; }
  .haui-diag-status:focus-visible + .haui-diag-popover,
  .haui-diag-status[aria-expanded="true"] + .haui-diag-popover { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  .haui-diag-popover > strong { font-size: var(--haui-text-label); font-weight: 500; }
  .haui-diag-popover > p { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-diag-popover > ul { display: grid; gap: 4px; margin: 0; padding-inline-start: 20px; font-size: var(--haui-text-caption); }
  @media (prefers-reduced-motion: reduce) {
    .haui-diag-status, .haui-diag-popover { transition: none; }
  }
  .haui-conn-card-head { justify-content: flex-start; gap: 8px; padding: 0; border: 0; }
  .haui-conn-card-head .haui-surface-heading-copy { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
  .haui-conn-status.online .haui-conn-card-head h2 { color: var(--haui-good-text); }
  .haui-conn-status.offline .haui-conn-card-head h2 { color: var(--haui-bad-text); }
  .haui-conn-card-head h2 { margin: 0; font-size: var(--haui-text-label); font-weight: 500; }
  .haui-conn-card-head p { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-device-details .haui-conn-card dl > div { padding: 4px 0; }
  /* The facts below are the last ones read: the poll failed or the panel is offline. */
  .haui-device-details .haui-details-stale { margin: 8px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  .haui-conn-card .haui-details-stale { margin: 0; color: var(--haui-warn-text); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  .haui-device-details dl { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0; margin: 0; }
  .haui-device-details dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-device-details dl > div:last-child { border-bottom: 0; }
  .haui-device-details dt { color: var(--secondary-text-color); }
  .haui-device-details dd { overflow: hidden; margin: 0; font-family: var(--haui-mono); font-weight: 500; text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-surface-body { gap: 12px; }
  /* The Diagnostics tiles, with values that can run long (page names), cut off; dimmed while stale. */
  .haui-device-details .haui-diag-tile-value { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-diag-tiles.is-stale .haui-diag-tile-value { color: var(--secondary-text-color); }
  /* Offline is the current state, not a stale reading. */
  .haui-device-details .haui-diag-tiles .haui-diag-tile-value.is-danger { color: var(--haui-bad-text); }
  /* The buttons below the Device stack's cards, as content without a card of their own, naming their
     sidebar on the inline start edge and what it opens on its trailing edge - what the update settings
     hold, the selected theme's name. The wide side column gives each one a line of its own; the width
     one row underneath the workspace has does not, so it pairs them and a phone turns them into tiles. */
  .haui-details-actions { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; }
  .haui-details-actions .haui-button { justify-content: flex-start; min-width: 0; }
  .haui-details-actions .haui-button-detail { margin-left: auto; }
  /* Two by two: the value keeps the trailing edge and gives way first, with an ellipsis. */
  @container haui-editor (max-width: 980px) {
    .haui-details-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  /* A phone: one row of tiles, the icon over the label, one column per button the device has. The
     trailing value has no room here, so it stays in the button's name for a screen reader rather than
     disappearing with the box that showed it; the sidebar each one opens names it in its own title.
     The label keeps the whole track (no padding) so the longest translation still fits one line: Polish
     "Aktualizacje" needs 66px of the 73px a 355px screen leaves, and anything longer breaks inside its
     own tile instead of spilling over the next one. */
  @container haui-editor (max-width: 560px) {
    .haui-details-actions { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); }
    .haui-details-actions .haui-button {
      position: relative; flex-direction: column; justify-content: center; gap: 4px; min-height: 64px;
      padding: 8px 0; border-radius: var(--haui-card-radius); font-size: var(--haui-text-caption);
      line-height: var(--haui-line-height-tight); overflow-wrap: anywhere; text-align: center;
      white-space: normal; --mdc-icon-size: 18px;
    }
    .haui-details-actions .haui-button-detail {
      position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);
      margin: 0; white-space: nowrap;
    }
  }
  /* A tile shows its label and value; hover, focus or a tap opens its facts below it (ui/info-tile.js), a right-hand tile's aligned to its right edge. */
  .haui-tile-info { position: relative; min-width: 0; }
  .haui-tile-info > .haui-diag-tile { width: 100%; height: 100%; }
  /* The card is capped at twice a tile, so its tracks are capped too: with only the width limited, a long
     localized label or reading would spill over its edge instead of wrapping inside it. The cap leaves room
     for a label beside a reading such as "921600 bps": the longest translation (Polish) needs 282px. */
  .haui-tile-card { position: absolute; z-index: 5; top: calc(100% + 6px); left: 0; display: grid; grid-template-columns: minmax(0, 1fr); box-sizing: border-box; width: max-content; min-width: 100%; max-width: min(320px, calc(200% + 8px)); gap: 8px; padding: 12px 12px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: var(--haui-card-radius); background: var(--card-background-color, #fff); box-shadow: var(--haui-shadow-overlay); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-tile-info:nth-child(even) > .haui-tile-card { right: 0; left: auto; }
  .haui-tile-card > strong { font-size: var(--haui-text-label); font-weight: 500; overflow-wrap: anywhere; }
  .haui-tile-card dl { display: grid; grid-template-columns: minmax(0, 1fr); margin: 0; }
  /* A fact keeps its reading on its label's line: the label gives way first and wraps, holding on to the width
     of its longest word (min-content). Only a reading that cannot share the line at all moves to one of its
     own, flush right, before it is cut off. */
  .haui-tile-card dl > div { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; padding: 4px 0; border-bottom: 1px solid var(--divider-color); font-size: var(--haui-text-caption); }
  .haui-tile-card dl > div:last-child { border-bottom: 0; }
  .haui-tile-card dt { flex: 1 1 0; min-width: min-content; color: var(--secondary-text-color); overflow-wrap: break-word; }
  /* The reading keeps the row's step and is separated by weight and colour, so the row never grows
     past the card's width. */
  .haui-tile-card dd { overflow: hidden; min-width: 0; margin: 0; margin-inline-start: auto; font-weight: 500; text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-tile-card > p { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-tile-info > .haui-diag-tile:focus-visible + .haui-tile-card, .haui-tile-info > .haui-diag-tile[aria-expanded="true"] + .haui-tile-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  /* Only a real pointer hovers: a tap's sticky hover would keep a card open after a second tap. */
  @media (hover: hover) {
    .haui-tile-info > .haui-diag-tile:hover { background: var(--haui-surface-strong); }
    .haui-tile-info:hover > .haui-tile-card,
    .haui-conn-status:hover > .haui-conn-card,
    .haui-diag-status-wrap:hover > .haui-diag-popover { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  }
  .haui-details-more > summary { display: flex; align-items: center; gap: 4px; padding: 4px 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); list-style: none; cursor: pointer; user-select: none; }
  .haui-details-more > summary::-webkit-details-marker { display: none; }
  .haui-details-more > summary::after { content: ""; width: 5px; height: 5px; border-right: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(-45deg); transition: transform 150ms ease; }
  .haui-details-more[open] > summary::after { transform: rotate(45deg); }
  .haui-details-more > summary:hover { color: var(--primary-text-color); }
  /* Two equal columns, so a lead card's pair of actions never wraps unevenly. */
  .haui-action-card-secondary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  /* The lead card (ui/action-card.js): tinted and never collapsed, so the view's next actions stand apart from the side-stack cards. */
  .haui-action-card { container: haui-action-card / inline-size; border: 1px solid color-mix(in srgb, var(--primary-color) 35%, var(--divider-color)); border-radius: var(--haui-card-radius); background: color-mix(in srgb, var(--primary-color) 9%, var(--card-background-color)); box-shadow: var(--haui-shadow-card); }
  .haui-action-card-inner { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; grid-template-areas: "icon copy tool" "actions actions actions" "note note note"; align-items: center; gap: 12px; padding: 16px 16px; }
  .haui-action-card-inner:not(.is-with-note) { grid-template-areas: "icon copy tool" "actions actions actions"; }
  .haui-action-card-inner.is-with-note { grid-template-areas: "icon copy tool" "actions actions actions" "note note note"; }
  .haui-action-card-icon { display: grid; width: 40px; height: 40px; grid-area: icon; place-items: center; border-radius: var(--haui-radius-round); background: var(--primary-color); color: var(--text-primary-color, #fff); --mdc-icon-size: 22px; }
  .haui-action-card-copy { min-width: 0; grid-area: copy; }
  .haui-action-card-copy h2 { margin: 0; font-size: var(--haui-text-body); font-weight: 500; }
  .haui-action-card-copy p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); line-height: var(--haui-line-height-copy); }
  /* The settings cog at the end of the heading; pulled into the card's padding so its glyph lines up with the edge. */
  .haui-action-card-tool { grid-area: tool; align-self: start; margin: -4px -8px 0 0; }
  .haui-action-card-actions { display: grid; min-width: 0; grid-area: actions; gap: 8px; }
  .haui-action-card-secondary .haui-button { min-width: 0; min-height: 34px; padding: 0 12px; font-size: var(--haui-text-label); }
  .haui-action-card-secondary > :only-child { grid-column: 1 / -1; }
  .haui-action-card-note { grid-area: note; margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-caption); line-height: var(--haui-line-height-copy); }
  /* One option's editor in the modal sidebar: the form scrolls, its action stays. */
  .haui-device-option-panel { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  /* The form scrolls, so its rows keep their content's height: an auto row would shrink a card that clips (a surface) when the sidebar is short. */
  .haui-device-option-panel-body { display: grid; flex: 1 1 auto; align-content: start; grid-auto-rows: max-content; gap: 12px; min-height: 0; overflow-y: auto; box-sizing: border-box; padding: 16px; overscroll-behavior: contain; }
  .haui-device-option-panel-actions { display: flex; flex: 0 0 auto; gap: 8px; box-sizing: border-box; padding: 12px 16px; border-top: 1px solid var(--divider-color); background: var(--card-background-color); }
  .haui-device-option-panel-actions .haui-button { flex: 1 1 auto; min-width: 0; }
  @container haui-action-card (min-width: 560px) {
    .haui-action-card-inner { grid-template-columns: 40px minmax(0, 1fr) auto auto; grid-template-areas: "icon copy actions tool" ". note actions tool"; row-gap: 4px; }
    .haui-action-card-inner:not(.is-with-note) { grid-template-areas: "icon copy actions tool"; }
    .haui-action-card-inner.is-with-note { grid-template-areas: "icon copy actions tool" ". note note note"; }
    .haui-action-card-tool { align-self: center; margin: 0 -8px 0 0; }
    .haui-action-card-actions.is-stacked { display: grid; align-items: stretch; }
    .haui-action-card-actions.is-stacked .haui-action-card-secondary { display: grid; width: 100%; }
    .haui-action-card-actions, .haui-action-card-secondary { display: flex; align-items: center; }
  }
`;
