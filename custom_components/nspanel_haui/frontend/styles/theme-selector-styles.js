/**
 * NSPanel HAUI - theme selector CSS.
 *
 * The unified predefined/custom theme dropdown used by the Theme sidebar. The
 * fields follow Home Assistant's form look: a filled surface, no border, and a
 * primary outline while focused. The library controls (.cp-theme-name,
 * .cp-theme-error) come from color-dialog-styles.js.
 */
import { css } from '../lit-import.js';

export const themeSelectorStyles = css`
  .haui-theme-selector { display: grid; gap: 10px; margin-block: 12px 4px; }
  .haui-theme-selector .form-group { margin: 0; }
  .haui-theme-selector .form-group label { margin-bottom: 6px; }

  /* The picker is one field: a chip of the palette, the name, the chevron. Focus
     rings the whole field, so the select itself draws no ring. */
  .haui-theme-selector-field {
    position: relative;
    overflow: hidden;
    border-radius: 8px;
    background: var(--ha-color-form-background, var(--haui-surface-soft));
  }
  .haui-theme-selector-field:focus-within {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 2px;
  }
  .haui-theme-selector-chip {
    position: absolute;
    inset-inline-start: 12px;
    top: 50%;
    translate: 0 -50%;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    width: 26px;
    height: 26px;
    overflow: hidden;
    box-sizing: border-box;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 7px;
    pointer-events: none;
  }
  .haui-theme-selector-chip i { display: block; }

  /* Every select in the Theme sidebar is that same filled field. */
  .haui-theme-sidebar .native-select {
    width: 100%;
    max-width: none;
    min-height: 44px;
    padding: 0 40px 0 12px;
    border: 0;
    border-radius: 8px;
    background-color: var(--ha-color-form-background, var(--haui-surface-soft));
    background-position: right 12px center;
    color: var(--primary-text-color, #212121);
    font-size: 15px;
    font-weight: 500;
  }
  .haui-theme-sidebar .native-select:hover { border-color: transparent; }
  .haui-theme-sidebar .native-select:focus-visible {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 2px;
  }
  /* Inside the picker the field paints the surface and rings the focus, and the
     palette chip takes the leading space the select text starts after. */
  .haui-theme-selector .haui-theme-selector-field .native-select {
    min-height: 48px;
    padding-inline: 50px 40px;
    border-radius: 0;
    background-color: transparent;
    outline: none;
  }

  /* Library and theme actions share one compact row, like Home Assistant's card
     actions: quiet text buttons for the library, icon only for the selected
     theme's own Duplicate/Rename/Delete. */
  .haui-theme-selector-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
  }
  .haui-theme-selector-actions .haui-theme-selector-action {
    min-height: 30px;
    padding: 0 10px;
    font-size: 13px;
  }
  .haui-theme-selector-divider {
    width: 1px;
    height: 18px;
    margin-inline: 6px;
    background: var(--divider-color, #e0e0e0);
  }
  .haui-theme-selector-actions .haui-row-action.is-danger { color: var(--error-color, #db4437); }
  .haui-theme-selector-actions .haui-row-action.is-danger:hover:not(:disabled) { background: var(--haui-bad-soft); }
`;
