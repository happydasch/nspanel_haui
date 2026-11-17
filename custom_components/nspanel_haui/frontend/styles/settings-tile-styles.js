/** The device settings' one-column list: one tile per group on the landing. */
import { css } from '../lit-import.js';

export const settingsTileStyles = css`
  /* Settings stay a single, readable list even when the sidebar is dragged wider. */
  .haui-settings-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--haui-space-2);
  }
  .haui-settings-tile {
    display: grid;
    /* Keep the category and navigation cue together; its summary spans below. */
    grid-template-columns: auto minmax(0, 1fr) auto;
    grid-template-areas: "icon name go" "value value value";
    align-items: center;
    gap: var(--haui-space-1);
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    padding: var(--haui-space-3);
    border: 1px solid var(--divider-color);
    border-radius: var(--haui-card-radius);
    background: var(--card-background-color);
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
    transition: border-color 120ms, background-color 120ms;
  }
  .haui-settings-tile-icon {
    grid-area: icon;
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: var(--haui-radius-control);
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 12%, transparent);
    color: var(--primary-color, #03a9f4);
  }
  /* The name column yields to the chevron, keeping long translations readable. */
  .haui-settings-tile-name {
    display: -webkit-box;
    grid-area: name;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    font-size: var(--haui-text-body);
    font-weight: 500;
    line-height: var(--haui-line-height-tight);
  }
  .haui-settings-tile-value {
    /* Two lines at most, aligned with the icon row and secondary to the group name. */
    display: -webkit-box;
    grid-area: value;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-caption);
    line-height: var(--haui-line-height-copy);
  }
  .haui-settings-tile-go { grid-area: go; display: grid; color: var(--secondary-text-color); }
  .haui-settings-tile-go > * { --mdc-icon-size: 16px; }
  .haui-settings-tile:hover {
    border-color: color-mix(in srgb, var(--primary-color, #03a9f4) 55%, var(--divider-color));
    background: color-mix(in srgb, var(--primary-color, #03a9f4) 6%, var(--card-background-color));
  }
  .haui-settings-tile:focus-visible { outline: var(--haui-focus-ring); outline-offset: var(--haui-focus-offset); }
`;
