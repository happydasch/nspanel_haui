import { css } from '../lit-import.js';

export const sidebarFooterStyles = css`
  .haui-panel-editor-sidebar > .haui-footer-wrapper,
  .haui-device-settings-sidebar > .haui-footer-wrapper,
  .haui-theme-sidebar > .haui-footer-wrapper {
    flex: 0 0 auto;
    gap: 12px;
    box-sizing: border-box;
    padding: 12px 16px;
    border-top: 1px solid var(--divider-color);
    background: var(--card-background-color);
  }
`;
