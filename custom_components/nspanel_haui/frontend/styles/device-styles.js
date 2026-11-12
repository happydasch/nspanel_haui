import { css } from '../lit-import.js';

export const deviceStyles = css`
  .haui-device-screen { display: flex; flex-direction: column; gap: 18px; }
  .haui-device-head { display: flex; align-items: center; gap: 12px 14px; min-width: 0; }
  .haui-device-head h1 { overflow: hidden; min-width: 0; flex: 0 1 auto; margin: 0; font-size: 24px; font-weight: 500; letter-spacing: -.01em; text-overflow: ellipsis; white-space: nowrap; }
  .haui-back-button { flex: 0 0 auto; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--secondary-text-color); transition: border-color 150ms ease, color 150ms ease; }
  .haui-back-button:hover { border-color: var(--primary-color); color: var(--primary-color); }
  /* The chips take the room the title leaves; when they do not fit, the shell
     collapses them into the dropdown. They stay laid out (hidden) while
     collapsed, so the next measurement can tell when they fit again. The chips
     are start-aligned inside the end-aligned rail: only an overflow at the end
     shows up in scrollWidth. */
  .haui-device-switch { position: relative; display: flex; min-width: 0; flex: 1 1 0; justify-content: flex-end; }
  .haui-device-rail { display: flex; min-width: 0; flex: 0 1 auto; gap: 6px; overflow: hidden; padding: 2px; }
  .haui-device-switch.is-collapsed .haui-device-rail { position: absolute; inset: 0; visibility: hidden; pointer-events: none; }
  .haui-device-select { display: none; min-width: 0; max-width: 100%; align-items: center; gap: 8px; height: 36px; padding: 0 6px 0 12px; border: 1px solid var(--divider-color); border-radius: 999px; background: var(--card-background-color); }
  .haui-device-switch.is-collapsed .haui-device-select { display: inline-flex; }
  .haui-device-select select { min-width: 0; max-width: 100%; height: 100%; border: 0; outline: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-weight: 500; text-overflow: ellipsis; cursor: pointer; }
  .haui-device-select:focus-within { border-color: var(--primary-color); }
  .haui-device-rail-item { display: inline-flex; align-items: center; gap: 8px; flex: 0 0 auto; min-height: 36px; max-width: 220px; padding: 0 12px; border: 1px solid var(--divider-color); border-radius: 999px; color: var(--primary-text-color); background: var(--card-background-color); font: inherit; cursor: pointer; }
  .haui-device-rail-item.active { border-color: var(--primary-color); background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .haui-device-rail-item.active .haui-status-dot { background: currentColor; }
  .haui-device-rail-item > span:nth-of-type(2) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-rail-update { color: var(--warning-color); }
  /* Both columns stick to the viewport; the taller one sets the scrolling range for the shorter one.
     In one column, the lead sits above the workspace and the side stack below. */
  .haui-device-layout { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .9fr); grid-template-areas: "workspace side"; align-items: start; gap: 18px 20px; }
  .haui-device-side { position: sticky; top: 18px; display: flex; min-width: 0; flex-direction: column; gap: 18px; grid-area: side; }
  .haui-device-lead { min-width: 0; grid-area: lead; }
  .haui-device-workspace { position: sticky; top: 18px; grid-area: workspace; min-width: 0;overflow: hidden; border: 1px solid var(--divider-color); border-radius: 12px; background: var(--card-background-color); box-shadow: var(--haui-shadow-card); transition: background 200ms ease, border-color 200ms ease; }
  .haui-device-workspace.is-live { border-color: var(--haui-live-border); background: var(--haui-live-surface); }
  .haui-device-workspace.is-live .haui-workspace-header { border-color: var(--haui-live-border); }
  .haui-device-side-stack { display: flex; min-width: 0; flex-direction: column; gap: 18px; grid-area: side; }
  .haui-device-side-stack > .haui-surface { box-shadow: var(--haui-shadow-card); }
  .haui-device-side-stack .haui-surface-heading-copy { min-width: 0; flex: 1 1 auto; }
  .haui-device-side-stack .haui-surface-heading-copy p { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-side-stack .haui-surface-heading .haui-button { flex: 0 0 auto; min-height: 32px; padding: 0 10px; font-size: 13px; }
  .haui-device-side-stack .haui-surface-body { display: grid; gap: 14px; }
  .haui-workspace-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 12px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  .haui-preview-controls { display: flex; flex: 0 0 auto; align-items: center; gap: 8px; }
  /* Shares the row with the view toggle at every width: it takes what the toggle leaves, up to its full size. */
  .haui-panel-search { display: inline-flex; box-sizing: border-box; max-width: 260px; min-width: 0; flex: 1 1 0; align-items: center; gap: 8px; height: 36px; padding: 0 12px; border: 1px solid var(--divider-color); border-radius: 999px; background: var(--haui-surface-soft); color: var(--secondary-text-color); --mdc-icon-size: 18px; }
  .haui-panel-search:focus-within { border-color: var(--primary-color); }
  .haui-panel-search input { min-width: 0; flex: 1 1 auto; border: 0; outline: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-size: 13px; }
  .haui-preview-tool { display: inline-flex; min-height: 32px; align-items: center; gap: 6px; padding: 0 10px; border: 1px solid transparent; border-radius: 999px; color: var(--secondary-text-color); background: transparent; font: inherit; font-size: 12px; font-weight: 500; white-space: nowrap; cursor: pointer; }
  .haui-preview-tool:hover:not(:disabled) { background: var(--haui-surface-soft); color: var(--primary-text-color); }
  .haui-preview-tool.is-active { background: var(--haui-surface-strong); color: var(--primary-text-color); }
  /* Live acts on the real panel: its pressed state takes the live tint. */
  .haui-preview-tool.is-live.is-active { background: var(--haui-live-border); }
  .haui-preview-tool:disabled { cursor: not-allowed; opacity: .5; }
  .haui-workspace-body.is-preview { display: flex; }
  .haui-workspace-body.is-preview > * { flex: 1 1 auto; }
  .haui-segmented { display: inline-flex; align-items: center; gap: 3px; padding: 3px; border-radius: 999px; background: var(--haui-surface-soft); }
  .haui-segmented-option { display: inline-flex; align-items: center; gap: 6px; min-height: 32px; padding: 0 12px; border: 0; border-radius: 999px; color: var(--secondary-text-color); background: transparent; font: inherit; cursor: pointer; }
  .haui-segmented-option.active { color: var(--primary-text-color); background: var(--card-background-color); box-shadow: var(--haui-shadow-card); }
  .haui-segmented-option:disabled { cursor: not-allowed; opacity: .5; }
  .haui-segmented-count { min-width: 18px; padding: 1px 5px; border-radius: 999px; background: var(--haui-surface-soft); font-size: 10px; text-align: center; }
  .haui-panel-catalog { display: grid; align-content: start; gap: 14px; overflow-y: auto; overscroll-behavior: contain; padding: 16px; }
  .haui-panel-catalog-hint { margin: 0; color: var(--secondary-text-color); font-size: 13px; }
  .haui-panel-catalog-search { display: grid; gap: 6px; color: var(--secondary-text-color); font-size: 12px; }
  .haui-panel-catalog-search input { min-height: 38px; border: 1px solid var(--haui-border-strong); border-radius: 8px; padding: 0 10px; color: var(--primary-text-color); background: var(--card-background-color); font: inherit; }
  .haui-panel-catalog-list { display: grid; gap: 8px; }
  .haui-panel-catalog-option { display: grid; grid-template-columns: 28px minmax(0, 1fr) 18px; align-items: center; gap: 10px; width: 100%; padding: 11px; border: 1px solid var(--divider-color); border-radius: 9px; color: var(--primary-text-color); background: var(--card-background-color); font: inherit; text-align: start; cursor: pointer; }
  /* A card with a preview: the full-width render on top, then the texts and the chevron. */
  .haui-panel-catalog-option[data-preview] { grid-template-columns: minmax(0, 1fr) 18px; gap: 8px 12px; }
  .haui-panel-catalog-preview { display: block; grid-column: 1 / -1; width: 100%; aspect-ratio: 450 / 320; overflow: hidden; border: 1px solid var(--divider-color); border-radius: 6px; background: var(--haui-screen); pointer-events: none; }
  .haui-panel-catalog-preview.portrait { width: 100%; max-width: 320px; aspect-ratio: 320 / 480; margin-inline: auto; }
  .haui-panel-catalog-preview nspanel-simulator-frame { display: block; width: 100%; height: 100%; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) { display: grid; gap: 3px; }
  .haui-panel-catalog-option > span:not(.haui-panel-catalog-preview) > span { color: var(--secondary-text-color); font-size: 11px; line-height: 1.35; }
  .haui-panel-catalog-option:hover { border-color: var(--primary-color); }
  .haui-panel-catalog-option:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-panel-catalog-empty { color: var(--secondary-text-color); font-size: 13px; }
  /* Collapsible catalog sections and the device groups inside the copy section,
     drawn like the panel editor's config sections: a heading row in the content
     (no box around it), tinted while open or hovered, the chevron at its end.
     The row's 12px inset lines the icon up with the cards' content. */
  .haui-panel-catalog-section,
  .haui-panel-catalog-group { display: block; }
  .haui-panel-catalog-section > summary,
  .haui-panel-catalog-group > summary { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 8px; color: var(--primary-text-color); font-size: 14px; font-weight: 500; list-style: none; cursor: pointer; user-select: none; }
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
  .haui-panel-catalog-section > summary:focus-visible,
  .haui-panel-catalog-group > summary:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-panel-catalog-section > summary > ha-icon,
  .haui-panel-catalog-group > summary > ha-icon { flex: 0 0 auto; color: var(--secondary-text-color); --mdc-icon-size: 18px; }
  .haui-panel-catalog-section > summary > span:first-of-type,
  .haui-panel-catalog-group > summary > span:first-of-type { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-panel-catalog-content { display: grid; gap: 8px; padding-block-start: 8px; }
  /* A device group sits inside its section: one step in, one step smaller. */
  .haui-panel-catalog-group { margin-inline-start: 12px; }
  .haui-panel-catalog-group > summary { font-size: 13px; }
  .haui-panel-catalog-content .haui-panel-catalog-hint { margin: 0; }
  .haui-panel-catalog-count { box-sizing: border-box; min-width: 20px; padding: 1px 7px; border-radius: 10px; background: var(--card-background-color); color: var(--secondary-text-color); font-size: 12px; font-weight: 500; text-align: center; }
  .haui-panel-catalog-section > summary:hover .haui-panel-catalog-count,
  .haui-panel-catalog-section[open] > summary .haui-panel-catalog-count,
  .haui-panel-catalog-group > summary:hover .haui-panel-catalog-count,
  .haui-panel-catalog-group[open] > summary .haui-panel-catalog-count { background: var(--secondary-background-color); }
  /* Diagnostics: the collapsed heading carries the connection status; expanded shows tiles and hub details. */
  .haui-device-diagnostics { display: grid; gap: 12px; }
  /* The heading icon, drawn like the connection icon of the card above; its corner bubble counts the issues. */
  .haui-diag-status { --haui-diag-tone: var(--haui-good); position: relative; display: grid; box-sizing: border-box; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border: 1px solid color-mix(in srgb, var(--haui-diag-tone) 28%, transparent); border-radius: 50%; color: var(--haui-diag-tone); background: color-mix(in srgb, var(--haui-diag-tone) 12%, var(--card-background-color)); --mdc-icon-size: 20px; }
  .haui-diag-status.warn { --haui-diag-tone: var(--haui-warn); }
  .haui-backup-status { display: grid; box-sizing: border-box; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border: 1px solid color-mix(in srgb, var(--secondary-text-color) 28%, transparent); border-radius: 50%; color: var(--secondary-text-color); background: color-mix(in srgb, var(--secondary-text-color) 12%, var(--card-background-color)); --mdc-icon-size: 20px; }
  .haui-diag-status-count { position: absolute; top: -4px; right: -4px; display: grid; box-sizing: border-box; min-width: 16px; height: 16px; place-items: center; padding: 0 4px; border-radius: 8px; background: var(--haui-diag-tone); box-shadow: 0 0 0 2px var(--card-background-color); color: var(--text-primary-color, #fff); font-size: 10px; font-weight: 600; line-height: 1; }
  /* The status icon leads the heading; the title takes the free room, so the chevron sits at the end. */
  .haui-device-details .haui-surface-heading-copy, .haui-diagnostics-card .haui-surface-heading-copy,
  .haui-yaml-card .haui-surface-heading-copy { flex: 1 1 auto; }
  .haui-expand-toggle { flex: 0 0 auto; }
  .haui-device-diagnostics .warn, .haui-device-details .haui-diag-tiles .warn { color: var(--haui-warn); }
  .haui-device-diagnostics .bad { color: var(--haui-bad); }
  .haui-diag-tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .haui-diag-tile { display: flex; min-width: 0; flex-direction: column; gap: 2px; padding: 10px 12px; border: 0; border-radius: 10px; color: var(--primary-text-color); background: var(--haui-surface-soft); font: inherit; text-align: start; }
  button.haui-diag-tile { cursor: pointer; }
  button.haui-diag-tile:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-diag-tile-label { color: var(--secondary-text-color); font-size: 12px; }
  .haui-diag-tile-value { display: flex; align-items: flex-end; gap: 6px; font-size: 15px; font-weight: 500; }
  .haui-diag-tile-value .rssi-bars { margin-bottom: 3px; }
  .haui-diag-check { display: flex; align-items: flex-start; gap: 10px; color: var(--primary-text-color); font-size: 14px; cursor: pointer; }
  .haui-diag-check input { flex: 0 0 auto; width: 18px; height: 18px; margin: 1px 0 0; accent-color: var(--primary-color); cursor: pointer; }
  .haui-diag-check-copy { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
  .haui-diag-check-hint { color: var(--secondary-text-color); font-size: 12px; }
  .haui-diag-tools { display: flex; flex-wrap: wrap; gap: 8px; }
  .haui-diag-tools .haui-button { min-height: 34px; padding: 0 12px; font-size: 13px; }
  .haui-diag-internals { border-top: 1px solid var(--divider-color); padding-top: 12px; }
  .haui-diag-internals dl { display: grid; margin: 4px 0 8px; }
  .haui-diag-internals dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--divider-color); font-size: 12px; }
  .haui-diag-internals dt { color: var(--secondary-text-color); }
  .haui-diag-internals dd { overflow: hidden; margin: 0; text-overflow: ellipsis; white-space: nowrap; }
  /* Watched entities: the name and live state, the entity id and attributes below; a row opens the entity. */
  .haui-diag-entities { display: grid; }
  .haui-diag-entity { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 12px; width: 100%; padding: 6px 0; border: 0; border-bottom: 1px solid var(--divider-color); color: var(--primary-text-color); background: none; font: inherit; font-size: 12px; text-align: start; }
  button.haui-diag-entity { cursor: pointer; }
  button.haui-diag-entity:hover .haui-diag-entity-name { color: var(--primary-color); }
  button.haui-diag-entity:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-diag-entity-name, .haui-diag-entity-id { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-state { max-width: 12em; overflow: hidden; text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-diag-entity-id { grid-column: 1 / -1; color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: 11px; }
  .haui-diag-internals-note { margin: 8px 0 0; color: var(--secondary-text-color); font-size: 11px; }
  .haui-diag-internals > .haui-button { min-height: 34px; margin-top: 10px; padding: 0 12px; font-size: 13px; }
  /* The connection state sits in the card heading; its details open over the body. */
  .haui-surface.haui-device-details { overflow: visible; }
  /* A tile's card opens past the bottom of the Diagnostics card too. */
  .haui-surface.haui-diagnostics-card { overflow: visible; }
  .haui-device-details .haui-surface-heading { position: relative; }
  .haui-conn-status { --haui-conn-tone: var(--secondary-text-color); --haui-conn-ring: var(--haui-conn-tone); flex: 0 0 auto; }
  .haui-conn-status.online { --haui-conn-tone: var(--haui-good); }
  .haui-conn-status.offline { --haui-conn-tone: var(--haui-bad); }
  .haui-conn-status-button { position: relative; display: grid; width: 36px; height: 36px; place-items: center; padding: 0; border: 1px solid color-mix(in srgb, var(--haui-conn-ring) 28%, transparent); border-radius: 50%; color: var(--haui-conn-ring); background: color-mix(in srgb, var(--haui-conn-ring) 12%, var(--card-background-color)); cursor: pointer; transition: background 150ms ease, border-color 150ms ease; --mdc-icon-size: 20px; }
  .haui-conn-status-button:hover, .haui-conn-status-button[aria-expanded="true"] { border-color: color-mix(in srgb, var(--haui-conn-ring) 55%, transparent); background: color-mix(in srgb, var(--haui-conn-ring) 20%, var(--card-background-color)); }
  .haui-conn-status-button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  /* The same icon, smaller and without the details card, in front of a Fleet table name. */
  .haui-conn-status-icon { position: relative; display: grid; box-sizing: border-box; width: 30px; height: 30px; place-items: center; border: 1px solid color-mix(in srgb, var(--haui-conn-ring) 28%, transparent); border-radius: 50%; color: var(--haui-conn-ring); background: color-mix(in srgb, var(--haui-conn-ring) 12%, var(--card-background-color)); --mdc-icon-size: 17px; }
  .haui-conn-status-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; background: var(--haui-conn-tone); }
  /* The circle and its glyph show the Wi-Fi strength in the colours of the RSSI bars; the dot keeps the connection tone. */
  .haui-conn-status:has(ha-icon.wifi-excellent) { --haui-conn-ring: var(--haui-good); }
  .haui-conn-status:has(ha-icon.wifi-good) { --haui-conn-ring: #7cb342; }
  .haui-conn-status:has(ha-icon.wifi-fair) { --haui-conn-ring: var(--haui-warn); }
  .haui-conn-status:has(ha-icon.wifi-weak) { --haui-conn-ring: var(--haui-bad); }
  .haui-conn-status-button > .haui-conn-status-dot, .haui-conn-status-icon > .haui-conn-status-dot { position: absolute; top: 1px; right: 1px; box-shadow: 0 0 0 2px var(--card-background-color); }
  .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: haui-conn-pulse 2.4s ease-out infinite; }
  @keyframes haui-conn-pulse {
    0% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 2px color-mix(in srgb, var(--haui-good) 60%, transparent); }
    70%, 100% { box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 7px transparent; }
  }
  @media (prefers-reduced-motion: reduce) { .haui-conn-status.online .haui-conn-status-button > .haui-conn-status-dot { animation: none; } }
  .haui-conn-card { position: absolute; z-index: 5; top: calc(100% - 6px); left: 12px; display: grid; width: min(280px, calc(100% - 24px)); gap: 10px; padding: 12px 14px; border: 1px solid var(--divider-color); border-radius: 12px; background: var(--card-background-color); box-shadow: 0 12px 32px rgb(0 0 0 / 28%); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-conn-status:hover > .haui-conn-card, .haui-conn-status-button:focus-visible + .haui-conn-card, .haui-conn-status-button[aria-expanded="true"] + .haui-conn-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  .haui-conn-card-head { display: flex; align-items: center; gap: 10px; }
  .haui-conn-card-head > div { display: flex; min-width: 0; flex-direction: column; gap: 2px; }
  .haui-conn-card-head strong { font-size: 14px; font-weight: 500; }
  .haui-conn-card-head span:not(.haui-conn-status-dot) { color: var(--secondary-text-color); font-size: 12px; }
  .haui-device-details .haui-conn-card dl > div { padding: 5px 0; }
  .haui-conn-card .haui-details-stale { margin: 0; color: var(--haui-warn); font-size: 12px; line-height: 1.4; }
  .haui-device-details dl { display: grid; gap: 0; margin: 0; }
  .haui-device-details dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--divider-color); font-size: 12px; }
  .haui-device-details dl > div:last-child { border-bottom: 0; }
  .haui-device-details dt { color: var(--secondary-text-color); }
  .haui-device-details dd { overflow: hidden; margin: 0; font-family: var(--haui-mono); text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-surface-body { gap: 12px; }
  /* The Diagnostics tiles, with values that can run long (page names), cut off; dimmed while stale. */
  .haui-device-details .haui-diag-tile-value { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-details .haui-diag-tiles.stale .haui-diag-tile-value { color: var(--secondary-text-color); }
  /* Offline is the current state, not a stale reading. */
  .haui-device-details .haui-diag-tiles .haui-diag-tile-value.bad { color: var(--haui-bad); }
  .haui-device-details .haui-diag-tile-value .rssi-bars { margin-inline-start: 6px; }
  /* A tile shows its label and value; hover, focus or a tap opens its facts below it (ui/info-tile.js), a right-hand tile's aligned to its right edge. */
  .haui-tile-info { position: relative; min-width: 0; }
  .haui-tile-info > .haui-diag-tile { width: 100%; height: 100%; }
  .haui-tile-card { position: absolute; z-index: 5; top: calc(100% + 6px); left: 0; display: grid; box-sizing: border-box; width: max-content; min-width: 100%; max-width: min(280px, calc(200% + 8px)); gap: 8px; padding: 12px 14px; border: 1px solid var(--divider-color, #ddd); border-radius: 12px; background: var(--card-background-color, #fff); box-shadow: 0 12px 32px rgb(0 0 0 / 28%); opacity: 0; pointer-events: none; transform: translateY(-4px); transition: opacity 120ms ease, transform 120ms ease, visibility 0s linear 120ms; visibility: hidden; }
  .haui-tile-info:nth-child(even) > .haui-tile-card { right: 0; left: auto; }
  .haui-tile-card > strong { font-size: 14px; font-weight: 500; overflow-wrap: anywhere; }
  .haui-tile-card dl { display: grid; margin: 0; }
  .haui-tile-card dl > div { display: flex; justify-content: space-between; gap: 12px; padding: 5px 0; border-bottom: 1px solid var(--divider-color); font-size: 12px; }
  .haui-tile-card dl > div:last-child { border-bottom: 0; }
  .haui-tile-card dt { color: var(--secondary-text-color); white-space: nowrap; }
  .haui-tile-card dd { overflow: hidden; margin: 0; font-family: var(--haui-mono); text-align: end; text-overflow: ellipsis; white-space: nowrap; }
  .haui-tile-card > p { margin: 0; color: var(--secondary-text-color); font-size: 12px; }
  .haui-tile-info > .haui-diag-tile:focus-visible + .haui-tile-card, .haui-tile-info > .haui-diag-tile[aria-expanded="true"] + .haui-tile-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  /* Only a real pointer hovers: a tap's sticky hover would keep the card open after a second tap. */
  @media (hover: hover) {
    .haui-tile-info > .haui-diag-tile:hover { background: var(--haui-surface-strong); }
    .haui-tile-info:hover > .haui-tile-card { opacity: 1; transform: none; transition-delay: 0s; visibility: visible; }
  }
  .haui-details-more > summary { display: flex; align-items: center; gap: 6px; padding: 2px 0; color: var(--secondary-text-color); font-size: 12px; list-style: none; cursor: pointer; user-select: none; }
  .haui-details-more > summary::-webkit-details-marker { display: none; }
  .haui-details-more > summary::after { content: ""; width: 5px; height: 5px; border-right: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(-45deg); transition: transform 150ms ease; }
  .haui-details-more[open] > summary::after { transform: rotate(45deg); }
  .haui-details-more > summary:hover { color: var(--primary-text-color); }
  .haui-card-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  /* Two equal columns, so a pair of actions (YAML Import and Export) never wraps unevenly; a lead card's lone secondary action spans it. */
  .haui-yaml-actions, .haui-action-card-secondary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  /* The lead card (ui/action-card.js): tinted and never collapsed, so the view's next actions stand apart from the side-stack cards. */
  .haui-action-card { container: haui-action-card / inline-size; border: 1px solid color-mix(in srgb, var(--primary-color) 35%, var(--divider-color)); border-radius: var(--haui-card-radius); background: color-mix(in srgb, var(--primary-color) 9%, var(--card-background-color)); box-shadow: var(--haui-shadow-card); }
  .haui-action-card-inner { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; grid-template-areas: "icon copy tool" "actions actions actions" "note note note"; align-items: center; gap: 14px; padding: 16px 18px; }
  .haui-action-card-icon { display: grid; width: 40px; height: 40px; grid-area: icon; place-items: center; border-radius: 50%; background: var(--primary-color); color: var(--text-primary-color, #fff); --mdc-icon-size: 22px; }
  .haui-action-card-copy { min-width: 0; grid-area: copy; }
  .haui-action-card-copy h2 { margin: 0; font-size: 17px; font-weight: 600; }
  .haui-action-card-copy p { margin: 2px 0 0; color: var(--secondary-text-color); font-size: 13px; line-height: 1.4; }
  /* The settings cog at the end of the heading; pulled into the card's padding so its glyph lines up with the edge. */
  .haui-action-card-tool { grid-area: tool; align-self: start; margin: -6px -8px 0 0; }
  .haui-action-card-actions { display: grid; min-width: 0; grid-area: actions; gap: 8px; }
  .haui-action-card-secondary .haui-button, .haui-details-updates { min-width: 0; min-height: 34px; padding: 0 12px; font-size: 13px; }
  .haui-action-card-secondary > :only-child { grid-column: 1 / -1; }
  .haui-action-card-note { grid-area: note; margin: 0; color: var(--secondary-text-color); font-size: 12px; line-height: 1.45; }
  /* Full width above the workspace: the actions move beside the heading. */
  @container haui-action-card (min-width: 560px) {
    .haui-action-card-inner { grid-template-columns: 40px minmax(0, 1fr) auto auto; grid-template-areas: "icon copy actions tool" ". note actions tool"; row-gap: 4px; }
    .haui-action-card-tool { align-self: center; margin: 0 -8px 0 0; }
    .haui-action-card-actions.is-stacked { display: grid; align-items: stretch; }
    .haui-action-card-actions.is-stacked .haui-action-card-secondary { display: grid; width: 100%; }
    .haui-action-card-actions, .haui-action-card-secondary { display: flex; align-items: center; }
  }
  /* Keep Add panel and Theme together in the device management card, with the secondary action narrower. */
  .haui-action-card-actions.is-inline { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); align-items: stretch; }
  .haui-action-card-actions.is-inline > .haui-button, .haui-action-card-actions.is-inline .haui-action-card-secondary .haui-button { width: 100%; box-sizing: border-box; }
  .haui-action-card-actions.is-inline .haui-action-card-secondary { width: auto; min-width: 0; }
  /* Keep the role settings directly in the shared card body, not nested cards. */
  .haui-panel-roles { container: haui-panel-roles / inline-size; }
  .haui-panel-roles .haui-surface-body { display: grid; gap: 20px; }
  @container haui-panel-roles (min-width: 640px) {
    .haui-panel-roles .haui-surface-body { grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: start; }
  }
  .haui-role-field { display: grid; grid-template-columns: 40px minmax(0, 1fr); align-items: center; gap: 12px; min-width: 0; color: var(--secondary-text-color); font-size: 12px; }
  .haui-role-field-icon { position: relative; display: grid; flex: 0 0 40px; width: 40px; height: 40px; place-items: center; border-radius: 12px; background: var(--haui-surface-soft); color: var(--primary-color); --mdc-icon-size: 19px; }
  .haui-role-icon-count { position: absolute; top: -5px; right: -5px; display: grid; min-width: 18px; height: 18px; box-sizing: border-box; place-items: center; padding: 0 4px; border: 2px solid var(--card-background-color); border-radius: 999px; background: var(--primary-color); color: var(--text-primary-color, #fff); font-size: 10px; font-weight: 600; line-height: 1; }
  .haui-role-content { display: grid; gap: 9px; min-width: 0; }
  .haui-role-heading { position: relative; display: flex; min-width: 0; align-items: center; gap: 12px; }
  .haui-role-heading .haui-role-field-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
  .haui-role-hint { color: var(--secondary-text-color); font-size: 11px; line-height: 1.45; }
  .haui-role-extra { align-items: center; }
  .haui-role-description { margin: -3px 0 0; color: var(--secondary-text-color); font-size: 12px; line-height: 1.45; }
  .haui-role-field-idle .haui-role-hint { padding-top: 9px; border-top: 1px solid var(--divider-color); }
  .haui-role-field-idle .haui-pill.is-dragging { opacity: .5; }
  .haui-role-field-idle .haui-pill.is-drop-before { box-shadow: inset 0 2px 0 var(--primary-color); }
  .haui-role-field-idle .haui-pill.is-drop-after { box-shadow: inset 0 -2px 0 var(--primary-color); }
  .haui-pill .haui-sort-handle { display: inline-flex; flex: 0 0 auto; align-items: center; overflow: visible; padding: 2px; color: var(--secondary-text-color); cursor: grab; white-space: normal; --mdc-icon-size: 16px; }
  .haui-pill .haui-sort-handle:hover { color: var(--primary-text-color); }
  .haui-button:focus-visible, .haui-icon-button:focus-visible, .haui-device-rail-item:focus-visible, .haui-device-card-select:focus-visible, .haui-device-row-name:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .haui-sidebar { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .haui-sidebar-strip {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--divider-color);
  }
  .haui-sidebar-title { overflow: hidden; font-size: 15px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
  .haui-sidebar-body { display: flex; flex: 1 1 auto; flex-direction: column; min-height: 0; }
  .haui-sidebar-body > *, .haui-sidebar-layer > * { flex: 1 1 auto; min-height: 0; }
  /* A sidebar opened from another (Colors from Device settings) covers it; the one below stays rendered, so its draft survives. */
  .haui-sidebar-layer { display: contents; }
  .haui-sidebar-layer[hidden] { display: none; }
  .haui-sidebar-scrim {
    touch-action: none;
    position: fixed;
    z-index: 40;
    inset: 0;
    background: rgb(0 0 0 / 42%);
    animation: haui-scrim-in 140ms ease-out;
  }
  .haui-modal-sidebar {
    box-sizing: border-box;
    min-width: 0;
    border-inline-start: 1px solid var(--divider-color);
    background: var(--card-background-color);
    position: fixed;
    z-index: 41;
    inset: 0 0 0 auto;
    display: flex;
    flex-direction: column;
    width: min(var(--haui-sidebar-width, 380px), calc(100vw - 32px));
    height: 100dvh;
    max-height: 100dvh;
    /* The Home Assistant app draws under the status bar and the home indicator:
       keep the strip and the footer out of them. */
    padding: var(--safe-area-inset-top, 0px) var(--safe-area-inset-right, 0px) var(--safe-area-inset-bottom, 0px) 0;
    /* Only the form inside scrolls; the strip and the footer stay in place. */
    overflow: hidden;
    overscroll-behavior: contain;
    border-radius: 0;
    box-shadow: -12px 0 36px #0003;
    outline: none;
    animation: haui-sidebar-in 180ms ease-out;
  }
  .haui-sidebar-layer > :is(nspanel-panel-editor, nspanel-device-settings, nspanel-theme-sidebar, nspanel-firmware-popover) { display: block; overflow: hidden; }
  /* Give the shadow-root scroll area a definite-height containing block. */
  .haui-sidebar-layer > nspanel-firmware-popover {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }
  /* The inner edge resizes the sidebar (ui/sidebar.js); its grip shows where to take it. */
  .haui-sidebar-resize { position: absolute; z-index: 3; top: 0; bottom: 0; left: 0; width: 8px; cursor: col-resize; touch-action: none; outline: none; }
  .haui-sidebar-resize::before { content: ""; position: absolute; top: 50%; left: 2px; width: 4px; height: 36px; border-radius: 2px; background: var(--divider-color); transform: translateY(-50%); transition: background 120ms ease; }
  .haui-sidebar-resize::after { content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 2px; background: transparent; transition: background 120ms ease; }
  .haui-sidebar-resize:hover::before, .haui-sidebar-resize:focus-visible::before, .is-resizing > .haui-sidebar-resize::before { background: var(--primary-color); }
  .haui-sidebar-resize:hover::after, .haui-sidebar-resize:focus-visible::after, .is-resizing > .haui-sidebar-resize::after { background: var(--primary-color); }
  .haui-modal-sidebar.is-resizing { user-select: none; }
  @keyframes haui-scrim-in { from { opacity: 0; } to { opacity: 1; } }
  @keyframes haui-sidebar-in { from { transform: translateX(16px); opacity: .8; } to { transform: translateX(0); opacity: 1; } }
  @keyframes haui-sheet-in { from { transform: translateY(24px); opacity: .8; } to { transform: translateY(0); opacity: 1; } }
  /* A phone gets a bottom sheet, as Home Assistant's own sheets: the page stays
     visible above it, so the strip sits clear of the status bar and a tap
     above the sheet closes it. */
  @media (max-width: 600px) {
    .haui-modal-sidebar {
      inset: auto 0 0 0;
      width: 100vw;
      height: min(90dvh, calc(100dvh - max(var(--safe-area-inset-top, 0px), 48px)));
      padding: 0 var(--safe-area-inset-right, 0px) var(--safe-area-inset-bottom, 0px) var(--safe-area-inset-left, 0px);
      border-inline-start: 0;
      border-top: 1px solid var(--divider-color);
      border-radius: 16px 16px 0 0;
      box-shadow: 0 -12px 36px #0003;
      animation-name: haui-sheet-in;
    }
    /* A bottom sheet already spans the screen. */
    .haui-sidebar-resize { display: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .haui-sidebar-scrim, .haui-modal-sidebar { animation: none; }
  }
  @container haui-editor (max-width: 980px) {
    .haui-device-layout { grid-template-columns: minmax(0, 1fr); grid-template-areas: "lead" "workspace" "side"; }
    .haui-device-side { display: contents; }
    .haui-device-workspace { position: static; }
  }
  /* A narrow workspace keeps its header in one row: the preview controls show their icon only. */
  @container haui-editor (max-width: 600px) {
    /* The device switch already names the selected device. */
    .haui-device-head:has(.haui-device-switch) h1 { display: none; }
    .haui-workspace-header { gap: 8px; padding: 10px 12px; }
    .haui-preview-controls { gap: 4px; }
    .haui-preview-controls .haui-preview-tool { width: 32px; justify-content: center; padding: 0; }
    .haui-preview-controls .haui-preview-tool span { display: none; }
  }
`;
