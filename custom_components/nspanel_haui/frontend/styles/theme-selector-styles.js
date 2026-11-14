/**
 * NSPanel HAUI - theme selector CSS.
 *
 * The predefined/custom theme picker used by the Theme sidebar: one radio
 * group of tiles, each a miniature panel in the theme's colors with its name.
 * The library controls (.haui-theme-name, .haui-theme-error) come from
 * color-dialog-styles.js.
 */
import { css } from '../lit-import.js';

export const themeSelectorStyles = css`
  .haui-theme-selector { display: grid; gap: 8px; margin-block: 12px 0; }

  .haui-theme-picker { display: grid; gap: 8px; }
  .haui-theme-picker-heading { margin: 0; }
  .haui-theme-picker-heading:not(:first-child) { margin-top: 4px; }
  .haui-theme-picker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
    gap: 8px;
  }

  /* The radio stays in the tile for keyboard and assistive technology; the
     tile itself shows the checked and focused states. */
  .haui-theme-option {
    position: relative;
    display: grid;
    gap: 8px;
    padding: 8px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-card-radius);
    background: var(--haui-card-background);
    cursor: pointer;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .haui-theme-option input {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: 0;
    opacity: 0;
    pointer-events: none;
  }
  .haui-theme-option.is-selected {
    border-color: var(--primary-color, #03a9f4);
    box-shadow: inset 0 0 0 1px var(--primary-color, #03a9f4);
  }
  .haui-theme-option:has(input:focus-visible) {
    outline: var(--haui-focus-ring);
    outline-offset: var(--haui-focus-offset);
  }
  @media (hover: hover) {
    .haui-theme-option:not(.is-selected):hover { border-color: var(--haui-border-strong); }
  }

  .haui-theme-option-thumb {
    display: grid;
    grid-template-rows: 12px 1fr;
    height: 48px;
    overflow: hidden;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--vp-theme-thumb-background);
  }
  .haui-theme-option-thumb-header {
    display: flex;
    align-items: center;
    padding-inline: 8px;
    background: var(--vp-theme-thumb-header);
  }
  .haui-theme-option-thumb-header i {
    width: 24px;
    height: 3px;
    border-radius: var(--haui-radius-pill);
    background: var(--vp-theme-thumb-header-text);
  }
  .haui-theme-option-thumb-body {
    display: flex;
    align-items: center;
    gap: 4px;
    padding-inline: 8px;
  }
  .haui-theme-option-thumb-pill {
    width: 24px;
    height: 12px;
    border-radius: var(--haui-radius-pill);
    background: var(--vp-theme-thumb-component);
  }
  .haui-theme-option-thumb-pill.is-active { background: var(--vp-theme-thumb-active); }
  .haui-theme-option-thumb-dot {
    width: 8px;
    height: 8px;
    margin-inline-start: auto;
    border-radius: var(--haui-radius-round);
    background: var(--vp-theme-thumb-entity);
  }

  .haui-theme-option-name {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
    font-size: var(--haui-text-label);
    font-weight: 500;
  }
  .haui-theme-option-name > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-theme-option-check {
    flex: none;
    margin-inline-start: auto;
    color: var(--primary-color, #03a9f4);
    --mdc-icon-size: 16px;
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

  @media (prefers-reduced-motion: reduce) {
    .haui-theme-option { transition: none; }
  }
`;
