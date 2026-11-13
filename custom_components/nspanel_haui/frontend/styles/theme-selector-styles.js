/**
 * NSPanel HAUI - theme selector CSS.
 *
 * The unified predefined/custom theme dropdown used by the Theme sidebar. The
 * fields follow Home Assistant's form look: a filled surface, no border, and a
 * primary outline while focused. The library controls (.haui-theme-name,
 * .haui-theme-error) come from haui-color-dialog-styles.js.
 */
import { css } from '../lit-import.js';

export const themeSelectorStyles = css`
  .haui-theme-selector { display: grid; gap: 8px; margin-block: 12px 4px; }
  .haui-theme-selector .haui-field { margin: 0; }
  .haui-theme-selector .haui-field label { margin-bottom: 4px; }

  /* The picker is one field: a chip of the palette, the name, the chevron. Focus
     rings the whole field, so the select itself draws no ring. */
  .haui-theme-selector-field {
    position: relative;
    overflow: hidden;
    border-radius: var(--haui-radius-control);
    background: var(--ha-color-form-background, var(--haui-surface-soft));
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
    border-radius: var(--haui-radius-control);
    pointer-events: none;
  }
  .haui-theme-selector-chip i { display: block; background: var(--haui-theme-swatch-color); }

  /* Only the picker is that filled field; the selects inside the sidebar's
     collapsible sections keep the shared form look the other sidebars use. */
  .haui-theme-selector-field .haui-select {
    width: 100%;
    max-width: none;
    min-height: 48px;
    padding: 0 40px 0 40px;
    border: 0;
    border-radius: 0;
    background-color: transparent;
    color: var(--primary-text-color, #212121);
    font-size: var(--haui-text-title);
    font-weight: 500;
    outline: none;
  }

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
