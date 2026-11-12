/**
 * NSPanel HAUI - styles.
 *
 * Split into modular exports:
 *   haStyle         — typography, layout utilities, link styles
 *   haStyleDialog   — responsive dialog sizing rules (adopted from HA's haStyleDialog)
 *   dialogStyles    — shared form/editor content styles without Fleet/Device layouts
 *   editorStyles    — dialogStyles plus the Fleet and Device dashboard screen styles
 *
 * Follows HA's resources/styles.ts pattern to avoid duplicate overlay/button/dialog
 * styles that ha-dialog and ha-button already provide.
 */

import { css } from './lit-import.js';

import { panelListStyles } from './styles/panel-list-styles.js';
import { contentStyles } from './styles/content.js';
import { dashboardTokens } from './styles/tokens.js';
import { dashboardComponentStyles } from './styles/dashboard-component-styles.js';
import { fleetStyles } from './styles/fleet-styles.js';
import { deviceStyles } from './styles/device-styles.js';
import { entryStyles } from './styles/entry-styles.js';
import { panelPillStyles } from './ui/panel-pills.js';


/**
 * Base HA-style typography and layout utilities.
 * Subset of HA's `haStyle` — only what this editor needs.
 *
 * NOTE: container-type is intentionally NOT on :host here.
 * It's on editorContainerStyles, which is only applied to NSPanelEditor
 * (not dialog components), so dialogs don't get layout containment and
 * position: fixed works relative to the viewport inside them.
 */
export const haStyle = css`
  :host {
    display: block;
  }
  .container {
    display: flex;
    flex-direction: column;
    flex: 1;
    padding-bottom: var(--ha-space-6);
  }
  ha-icon-button {
    color: var(--secondary-text-color, #666);
  }

  /* ── layout utility classes ───────── */
  .w-full {
    width: 100%;
  }
`;

/**
 * Container-type styles for the NSPanelEditor host only.
 * Kept separate from haStyle so that dialog components (colors,
 * edit-panel, etc.) do NOT get layout containment, allowing position: fixed
 * dropdowns inside them to be viewport-relative.
 */
export const editorContainerStyles = css`
  :host {
    container-type: inline-size;
    container-name: haui-editor;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }
`;

/**
 * Responsive dialog sizing rules, adopted from HA's haStyleDialog.
 * ha-dialog handles animations, overlay/scrim, focus management, and close
 * buttons; we only set min/max widths and a fullscreen breakpoint.
 */
export const haStyleDialog = css`
  ha-dialog {
    --ha-dialog-max-width: min(600px, 95vw);
    max-height: calc(100vh - 96px);
  }
  @media all and (max-width: 450px), all and (max-height: 500px) {
    ha-dialog {
      --ha-dialog-max-width: 100vw;
      max-height: 100vh;
      width: 100vw;
    }
  }
`;

/**
 * Shared form, panel, and legacy editor-content styles used by both shell and
 * dialog surfaces. Fleet and Device layout styles are composed separately below.
 */


/** Styles shared by dialog content without Fleet/Device screen layout rules. */
export const dialogStyles = css`
  ${dashboardTokens}${dashboardComponentStyles}${panelPillStyles}${entryStyles}${contentStyles}
`;

/** Styles for the editor shell, including Fleet and Device dashboard layouts. */
export const editorStyles = css`
  ${dashboardTokens}${dashboardComponentStyles}${panelListStyles}${fleetStyles}${deviceStyles}${panelPillStyles}${entryStyles}${contentStyles}
`;
