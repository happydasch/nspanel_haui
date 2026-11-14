import { css } from '../lit-import.js';

export const deviceLayoutStyles = css`
  .haui-device-screen { display: flex; flex-direction: column; gap: 16px; }
  .haui-device-head { display: flex; align-items: center; gap: 12px 12px; min-width: 0; }
  .haui-device-head h1 { overflow: hidden; min-width: 0; flex: 0 1 auto; margin: 0; font-size: var(--haui-text-display); font-weight: 500; letter-spacing: -.01em; text-overflow: ellipsis; white-space: nowrap; }
  .haui-back-button { flex: 0 0 auto; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--secondary-text-color); transition: background 150ms ease, border-color 150ms ease, color 150ms ease; }
  /* Outranks the generic grey icon-button hover, which clashed with the blue border and arrow. */
  .haui-back-button:hover:not(:disabled) { border-color: var(--primary-color); color: var(--primary-color); background: color-mix(in srgb, var(--primary-color, #03a9f4) 10%, var(--card-background-color, #fff)); }
  /* The chips take the room the title leaves; when they do not fit, the shell
     collapses them into the dropdown. They stay laid out (hidden) while
     collapsed, so the next measurement can tell when they fit again. The chips
     are start-aligned inside the end-aligned rail: only an overflow at the end
     shows up in scrollWidth. */
  .haui-device-switch { position: relative; display: flex; min-width: 0; flex: 1 1 0; justify-content: flex-end; }
  .haui-device-rail { display: flex; min-width: 0; flex: 0 1 auto; gap: 4px; overflow: hidden; padding: 4px; }
  .haui-device-switch.is-collapsed .haui-device-rail { position: absolute; inset: 0; visibility: hidden; pointer-events: none; }
  .haui-device-select { display: none; min-width: 0; max-width: 100%; align-items: center; gap: 8px; height: 36px; padding: 0 4px 0 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill); background: var(--card-background-color); }
  .haui-device-switch.is-collapsed .haui-device-select { display: inline-flex; }
  .haui-device-select select { min-width: 0; max-width: 100%; height: 100%; border: 0; outline: 0; color: var(--primary-text-color); background: transparent; font: inherit; font-weight: 500; text-overflow: ellipsis; cursor: pointer; }
  .haui-device-select:focus-within { border-color: var(--primary-color); }
  .haui-device-rail-item { display: inline-flex; align-items: center; gap: 8px; flex: 0 0 auto; min-height: 36px; max-width: 220px; padding: 0 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill); color: var(--primary-text-color); background: var(--card-background-color); font: inherit; cursor: pointer; }
  .haui-device-rail-item.active { border-color: var(--primary-color); background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .haui-device-rail-item.active .haui-status-dot { background: currentColor; }
  .haui-device-rail-item > span:nth-of-type(2) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-rail-update { color: var(--warning-color); }
  /* Both columns stick to the viewport; the taller one sets the scrolling range for the shorter one.
     In one column, the lead sits above the workspace and the side stack below. */
  .haui-device-layout { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(280px, .9fr); grid-template-areas: "workspace side"; align-items: start; gap: 16px 20px; }
  .haui-device-side { position: sticky; top: 18px; display: flex; min-width: 0; flex-direction: column; gap: 16px; grid-area: side; }
  .haui-device-lead { min-width: 0; grid-area: lead; }
  .haui-device-workspace { position: sticky; top: 18px; grid-area: workspace; min-width: 0; overflow: hidden; border: 1px solid var(--divider-color); border-radius: var(--haui-card-radius); background: var(--card-background-color); box-shadow: var(--haui-shadow-card); transition: background 150ms ease, border-color 150ms ease; }
  .haui-device-workspace.is-live { border-color: var(--haui-live-border); background: var(--haui-live-surface); }
  .haui-device-workspace.is-live .haui-workspace-header { border-color: var(--haui-live-border); }
  .haui-device-side-stack { display: flex; min-width: 0; flex-direction: column; gap: 16px; grid-area: side; }
  .haui-device-side-stack > .haui-surface { box-shadow: var(--haui-shadow-card); }
  .haui-device-side-stack .haui-surface-heading-copy { min-width: 0; flex: 1 1 auto; }
  .haui-device-side-stack .haui-surface-heading-copy p { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-device-side-stack .haui-surface-heading .haui-button { flex: 0 0 auto; min-height: 32px; padding: 0 8px; font-size: var(--haui-text-label); }
  .haui-device-side-stack .haui-surface-body { display: grid; gap: 12px; }
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
  .haui-sidebar-title { overflow: hidden; font-size: var(--haui-text-title); font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
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
    background: var(--haui-scrim);
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
    padding: var(--safe-area-inset-top, 0) var(--safe-area-inset-right, 0) var(--safe-area-inset-bottom, 0) 0;
    /* Only the form inside scrolls; the strip and the footer stay in place. */
    overflow: hidden;
    overscroll-behavior: contain;
    border-radius: 0;
    box-shadow: -12px 0 36px #0003;
    outline: none;
    animation: haui-sidebar-in 180ms ease-out;
  }
  .haui-sidebar-layer > :is(nspanel-panel-editor, nspanel-device-settings, nspanel-theme-sidebar, nspanel-updates-sidebar) { display: block; overflow: hidden; }
  /* Give the shadow-root scroll area a definite-height containing block. */
  .haui-sidebar-layer > nspanel-updates-sidebar {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }
  /* The inner edge resizes the sidebar (ui/sidebar.js); its grip shows where to take it. */
  .haui-sidebar-resize { position: absolute; z-index: 3; top: 0; bottom: 0; left: 0; width: 8px; cursor: col-resize; touch-action: none; outline: none; }
  .haui-sidebar-resize::before { content: ""; position: absolute; top: 50%; left: 2px; width: 4px; height: 36px; border-radius: var(--haui-radius-control); background: var(--divider-color); transform: translateY(-50%); transition: background 120ms ease; }
  .haui-sidebar-resize::after { content: ""; position: absolute; top: 0; bottom: 0; left: 0; width: 2px; background: transparent; transition: background 120ms ease; }
  .haui-sidebar-resize:hover::before, .haui-sidebar-resize:focus-visible::before, .is-resizing > .haui-sidebar-resize::before { background: var(--primary-color); }
  .haui-sidebar-resize:hover::after, .haui-sidebar-resize:focus-visible::after, .is-resizing > .haui-sidebar-resize::after { background: var(--primary-color); }
  .haui-modal-sidebar.is-resizing { user-select: none; }
  @keyframes haui-scrim-in { from { opacity: 0; } to { opacity: 1; } }
  @keyframes haui-sidebar-in { from { transform: translateX(16px); opacity: .8; } to { transform: translateX(0); opacity: 1; } }
  /* A phone gets a page of its own: the sidebar covers the editor instead of
     hanging over it as a sheet, so nothing behind it is left visible or tappable. */
  @media (max-width: 600px) {
    .haui-modal-sidebar {
      inset: 0;
      width: auto;
      border: 0;
      border-radius: 0;
      box-shadow: none;
      /* The app draws under the status bar and the home indicator. */
      padding: var(--safe-area-inset-top, 0) var(--safe-area-inset-right, 0)
        var(--safe-area-inset-bottom, 0) var(--safe-area-inset-left, 0);
      animation-name: haui-page-in;
    }
    /* A full-width page leaves nothing behind it to tap. */
    .haui-sidebar-scrim { display: none; }
    /* A full-width page has no edge to drag. */
    .haui-sidebar-resize { display: none; }
  }
  @keyframes haui-page-in { from { transform: translateX(24px); } }
  @media (prefers-reduced-motion: reduce) {
    .haui-sidebar-scrim, .haui-modal-sidebar { animation: none; }
  }
  @container haui-editor (max-width: 980px) {
    .haui-device-layout { grid-template-columns: minmax(0, 1fr); grid-template-areas: "lead" "workspace" "side"; }
    .haui-device-side { display: contents; }
    .haui-device-workspace { position: static; }
  }
  /* Keep the preview controls compact on narrow screens while preserving accessible labels. */
  @container haui-editor (max-width: 600px) {
    /* The device switch already names the selected device. */
    .haui-device-head:has(.haui-device-switch) h1 { display: none; }
    .haui-device-workspace .haui-workspace-header { gap: 8px; padding: 8px 12px; }
    /* Keep the view toggle icon-only and its names available to screen readers. */
    .haui-workspace-header .haui-segmented-option > span {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip-path: inset(50%);
      white-space: nowrap;
    }
    .haui-workspace-header .haui-segmented-option > .haui-badge-count { display: none; }
    .haui-device-workspace .haui-preview-controls { gap: 4px; }
    .haui-device-workspace .haui-preview-controls .haui-preview-tool > ha-icon { display: none; }
  }
`;
