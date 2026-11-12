/**
 * NSPanel HAUI - theme selector CSS.
 *
 * The unified predefined/custom theme dropdown shared by the Theme sidebar
 * (dialogs/theme.js) and the device settings' Theme section
 * (views/device-settings.js). The library controls (.cp-theme-actions,
 * .cp-theme-name, .cp-theme-error) come from color-dialog-styles.js.
 */
import { css } from '../lit-import.js';

export const themeSelectorStyles = css`
  .haui-theme-selector { display: grid; gap: 8px; margin-block: 12px; }
  .haui-theme-selector .form-group { margin: 0; }
  .haui-theme-selector select { width: 100%; max-width: none; min-height: 40px; border-radius: 8px; }
  .haui-theme-selector-swatches { display: flex; height: 18px; margin-top: 8px; overflow: hidden; border-radius: 5px; }
  .haui-theme-selector-swatches i { flex: 1 1 0; }
  .haui-theme-selector-actions { display: flex; flex-wrap: wrap; gap: 4px 12px; }
  .haui-theme-selector-actions button { padding: 2px 0; border: 0; background: transparent; color: var(--primary-color); font: inherit; font-size: 12px; cursor: pointer; }
  .haui-theme-selector-actions button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
`;
