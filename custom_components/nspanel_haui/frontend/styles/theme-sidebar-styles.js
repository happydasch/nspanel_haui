/** Theme sidebar layout rules shared by its dialog and editor surface. */
import { css } from '../lit-import.js';

export const themeSidebarStyles = css`
  .haui-theme-sidebar { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .haui-theme-sidebar > .haui-dialog-body {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    box-sizing: border-box;
    padding: 0;
  }
  .haui-theme-section,
  .haui-theme-colors { padding: 16px; }
  /* The preview's bottom padding already spaces the intro under it. */
  .haui-theme-sidebar .haui-theme-section { padding-top: 4px; }
  /* The preview stays at the top of the body so every pick and color edit
     below it shows on the palette. It takes the sidebar's own surface, so it
     has no band of its own but still hides what scrolls under it. */
  .haui-theme-sidebar .haui-theme-preview {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 12px 16px;
    background: var(--card-background-color);
  }
  .haui-theme-color-group { padding-block: 12px; border-bottom: 1px solid var(--divider-color); }
  .haui-theme-color-group:first-child { padding-top: 0; }
  .haui-theme-color-group:last-child { padding-bottom: 0; border-bottom: 0; }
  @container haui-editor (max-width: 600px) {
    .haui-theme-section,
    .haui-theme-colors { padding: 12px; }
    .haui-theme-sidebar .haui-theme-preview { padding-inline: 12px; }
  }
`;
