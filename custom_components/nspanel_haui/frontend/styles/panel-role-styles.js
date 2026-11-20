import { css } from '../lit-import.js';

/**
 * The marker a page carries for the role it plays on the device: the circle on
 * a panel list thumbnail and beside a quick start page. Home and idle are the
 * device's two role settings and keep their tone; a navigation or hidden page
 * is marked the same way without one.
 */
export const panelRoleStyles = css`
  .haui-panel-role {
    display: grid;
    width: 22px;
    height: 22px;
    place-items: center;
    border-radius: var(--haui-radius-round);
    box-shadow: var(--haui-shadow-card);
    --mdc-icon-size: 15px;
    line-height: 0;
  }
  .haui-panel-role-home { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .haui-panel-role-idle { background: var(--warning-color); color: var(--primary-text-color); }
  .haui-panel-role-navigation,
  .haui-panel-role-hidden { background: var(--haui-surface-strong); color: var(--secondary-text-color); }
  /* A hidden page is only reachable from another page, so its marker is the
     quieter one; the further idle panels cycle after the first one. */
  .haui-panel-role-hidden { opacity: 0.7; }
  .haui-panel-role-idle.is-extra { opacity: 0.55; }
`;
