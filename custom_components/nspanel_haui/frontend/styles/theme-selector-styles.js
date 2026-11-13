/**
 * NSPanel HAUI - theme selector CSS.
 *
 * The unified predefined/custom theme dropdown used by the Theme sidebar. It is
 * the shared .haui-select, like every other select in the sidebars, with the
 * selected palette's chip inside it. The library controls (.haui-theme-name,
 * .haui-theme-error) come from haui-color-dialog-styles.js.
 */
import { css } from '../lit-import.js';

export const themeSelectorStyles = css`
  .haui-theme-selector { display: grid; gap: 8px; margin-block: 12px 4px; }

  /* The chip sits over the select's start padding, so the select stays the
     focusable field with the shared border, hover and focus colours. */
  .haui-theme-selector-field { position: relative; }
  .haui-theme-selector-chip {
    position: absolute;
    inset-inline-start: 8px;
    top: 50%;
    translate: 0 -50%;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    width: 20px;
    height: 20px;
    overflow: hidden;
    box-sizing: border-box;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    pointer-events: none;
  }
  .haui-theme-selector-chip i { display: block; background: var(--haui-theme-swatch-color); }
  .haui-theme-selector-field .haui-select { padding-inline-start: 40px; }

  /* Library and theme actions share one compact row, like Home Assistant's card
     actions: quiet text buttons for the library, icon only for the selected
     theme's own Duplicate/Rename/Delete. */
  .haui-theme-selector-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }
  .haui-theme-selector-actions .haui-theme-selector-action {
    min-height: 30px;
    padding: 0 8px;
    font-size: var(--haui-text-label);
  }
  .haui-theme-selector-divider {
    width: 1px;
    height: 18px;
    margin-inline: 4px;
    background: var(--divider-color, #e0e0e0);
  }
  .haui-theme-selector-actions .haui-row-action.is-danger { color: var(--error-color, #db4437); }
  .haui-theme-selector-actions .haui-row-action.is-danger:hover:not(:disabled) { background: var(--haui-bad-soft); }
`;
