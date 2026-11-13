/** Shared composition for the editor and independent dialog shadow roots. */
import { css } from './lit-import.js';

import { colorDialogStyles } from './styles/color-dialog-styles.js';
import { colorPickerStyles } from './styles/color-picker-styles.js';
import { contentStyles } from './styles/content.js';
import { dashboardComponentStyles } from './styles/dashboard-component-styles.js';
import { dashboardTokens } from './styles/tokens.js';
import { firmwareStyles } from './styles/firmware-styles.js';
import { deviceLayoutStyles } from './styles/device-layout-styles.js';
import { devicePanelStyles } from './styles/device-panel-styles.js';
import { dropdownStyles } from './styles/dropdown-styles.js';
import { entryStyles } from './styles/entry-styles.js';
import { fleetStyles } from './styles/fleet-styles.js';
import { formCommonStyles } from './styles/form-common-styles.js';
import { itemListStyles } from './styles/item-list-styles.js';
import { panelListStyles } from './styles/panel-list-styles.js';
import { panelPillStyles } from './styles/panel-pill-styles.js';
import { previewStyles } from './styles/preview-styles.js';

export const haStyle = css`
  :host { display: block; }
  .haui-container { display: flex; flex: 1; flex-direction: column; padding-bottom: var(--haui-space-6); }
  ha-icon-button { color: var(--secondary-text-color, #666); }
  .haui-w-full { width: 100%; }
  .haui-text-caption { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  .haui-text-label { font-size: var(--haui-text-label); }
  .haui-text-body { font-size: var(--haui-text-body); }
  .haui-text-title { font-size: var(--haui-text-title); }
  .haui-text-display { font-size: var(--haui-text-display); }
  .haui-eyebrow { color: var(--secondary-text-color); font-size: var(--haui-text-eyebrow);
    font-weight: 600; letter-spacing: .05em; text-transform: uppercase; font-variant-numeric: tabular-nums; }
  .haui-text-mono { font-family: var(--haui-mono); }
`;

export const editorContainerStyles = css`
  :host { container-type: inline-size; container-name: haui-editor; min-height: 100dvh; display: flex; flex-direction: column; }
`;

export const haStyleDialog = css`
  ha-dialog { --ha-dialog-max-width: min(600px, 95vw); max-height: calc(100vh - 96px); }
  @media all and (max-width: 450px), all and (max-height: 500px) {
    ha-dialog { --ha-dialog-max-width: 100vw; max-height: 100vh; width: 100vw; }
  }
`;

export const sharedStyles = css`
  ${dashboardTokens}${dashboardComponentStyles}${panelPillStyles}${entryStyles}
  ${colorDialogStyles}${colorPickerStyles}${dropdownStyles}${itemListStyles}${formCommonStyles}${contentStyles}
`;

export const dialogStyles = css`${sharedStyles}${firmwareStyles}`;
export const editorStyles = css`${dialogStyles}${panelListStyles}${fleetStyles}${deviceLayoutStyles}${devicePanelStyles}${previewStyles}`;
