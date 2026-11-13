/** Theme sidebar layout rules shared by its dialog and editor surface. */
import { css } from '../lit-import.js';

export const themeSidebarStyles = css`
  .haui-theme-sidebar { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .haui-theme-sidebar > .haui-theme-preview {
    flex: 0 0 auto;
    padding: 12px 16px;
    border-bottom: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
  }
  .haui-theme-sidebar > .haui-dialog-body {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    box-sizing: border-box;
    padding: 16px;
  }
  .haui-theme-section { margin: 0 0 20px; }
  .haui-theme-color-group { padding-block: 12px; border-bottom: 1px solid var(--divider-color); }
  .haui-theme-color-group:first-child { padding-top: 0; }
  .haui-theme-color-group:last-child { padding-bottom: 0; border-bottom: 0; }
  @container haui-editor (max-width: 600px) {
    .haui-theme-sidebar > .haui-dialog-body { padding: 12px; }
  }
`;
