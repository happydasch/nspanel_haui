import { css } from '../lit-import.js';

/**
 * The quick start dialog: the configurations a device without panels can be
 * set up from (each with its name, the hub render of the home page it creates
 * and what it is for), and the one picked, read top to bottom - its name and
 * what it is for, the fields and switches that fill it in with their hints, a
 * gallery of every page with the hub's render of it and the count it holds,
 * and, under them, the banner with what the setup still needs.
 */
export const quickStartStyles = css`
  .haui-quick-start { display: grid; gap: 20px; }
  .haui-quick-start-intro { margin: 0; color: var(--secondary-text-color); font-size: var(--haui-text-label); }
  .haui-quick-start-error { margin: 0; color: var(--haui-bad-text); font-size: var(--haui-text-label); }
  .haui-quick-start-list { display: grid; gap: 12px; }
  /* The same card the Add panel catalog draws (device-panel-styles.js): the
     card radius, a 16px inset, the name at card size with its 20px icon and
     what it is for as text under it. */
  .haui-quick-start-card {
    display: grid;
    grid-template-columns: 128px minmax(0, 1fr);
    align-items: center;
    gap: 16px;
    padding: 16px;
    border: 1px solid var(--divider-color);
    border-radius: var(--haui-card-radius);
    background: var(--card-background-color);
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    transition: border-color 150ms, background-color 150ms, box-shadow 150ms;
  }
  .haui-quick-start-card:hover {
    border-color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color));
  }
  .haui-quick-start-card:focus-visible {
    outline: none;
    box-shadow: var(--haui-focus-ring);
  }
  .haui-quick-start-card:disabled { cursor: default; opacity: 0.6; }
  .haui-quick-start-preview {
    overflow: hidden;
    border-radius: var(--haui-radius-control);
    background: var(--haui-bezel);
  }
  .haui-quick-start-preview-empty {
    display: grid;
    min-height: 72px;
    place-items: center;
    color: #fff;
    --mdc-icon-size: 24px;
  }
  .haui-quick-start-copy { display: grid; gap: 4px; min-width: 0; }
  /* The configuration's name, above the sentence that says what it is for: the
     card repeats the pair the second step's heading shows, and its icon leads
     that name one step over the icon default, as the catalog's does. */
  .haui-quick-start-title {
    display: flex;
    align-items: center;
    gap: var(--haui-space-2);
    margin: 0;
    font-size: var(--haui-text-body);
    font-weight: 500;
  }
  .haui-quick-start-title ha-icon { color: var(--primary-color); --mdc-icon-size: 20px; }
  .haui-quick-start-description {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-label);
  }
  /* The chosen configuration's name and what it is for, above its controls;
     its counts belong to the pages gallery, what it needs to the closing
     block. */
  .haui-quick-start-heading { display: grid; gap: var(--haui-space-1); }
  .haui-quick-start-heading-title {
    display: flex;
    align-items: center;
    gap: var(--haui-space-2);
    margin: 0;
    font-size: var(--haui-text-body);
    font-weight: 500;
  }
  .haui-quick-start-heading-title ha-icon { color: var(--primary-color); --mdc-icon-size: 20px; }
  .haui-quick-start-heading-copy {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-label);
  }
  /* One column: the controls that fill the setup in, the pages it creates, the
     switches that add optional pages, then what it still needs. */
  .haui-quick-start-setup { display: grid; gap: var(--haui-space-5); }
  .haui-quick-start-form { display: grid; gap: var(--haui-space-2); min-width: 0; }
  .haui-quick-start-form > .haui-field-pair > .haui-field { margin: 0; min-width: 0; }
  .haui-quick-start-result { display: grid; gap: var(--haui-space-3); min-width: 0; }
  .haui-quick-start-toggles { display: grid; gap: var(--haui-space-2); min-width: 0; }
  .haui-quick-start-toggles > .haui-checkbox-wrap { margin: 0; min-width: 0; }
  .haui-quick-start-pages { display: grid; gap: var(--haui-space-2); }
  .haui-quick-start-pages-head {
    display: grid;
    gap: var(--haui-space-1);
  }
  .haui-quick-start-pages-meta {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-caption);
  }
  .haui-quick-start-section-title {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-eyebrow);
    font-weight: 600;
    text-transform: uppercase;
  }
  /* One page of the setup: its hub render, its role, and the panel type it is.
     Two beside each other wherever the dialog has the room - its own width, not
     the window's - and one under the other on a phone. */
  .haui-quick-start-page-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 240px), 1fr));
    gap: var(--haui-space-3) var(--haui-space-4);
  }
  .haui-quick-start-page {
    display: grid;
    grid-template-columns: minmax(0, 38%) minmax(0, 1fr);
    align-items: center;
    gap: var(--haui-space-2);
    min-width: 0;
  }
  .haui-quick-start-page-preview {
    overflow: hidden;
    border-radius: var(--haui-radius-control);
    background: var(--haui-bezel);
  }
  .haui-quick-start-page-copy { display: grid; gap: var(--haui-space-1); min-width: 0; }
  .haui-quick-start-page-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--haui-space-1);
  }
  .haui-quick-start-page-title {
    overflow: hidden;
    color: var(--primary-text-color);
    font-size: var(--haui-text-label);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-quick-start-page-meta {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-caption);
  }
  /* What the setup still needs and what it leaves out, in one banner under the
     pages and the switches that add more: the last thing read before the
     actions that create it. Where the pages end up is each page's own role
     marker. */
  .haui-quick-start-warnings {
    display: grid;
    gap: var(--haui-space-1);
    color: var(--secondary-text-color);
    font-size: var(--haui-text-caption);
  }
  /* Choices and a page gallery need more room than a form does, on a screen
     that has it; the full-screen rule for phones stays as it is. */
  @media all and (min-width: 451px) and (min-height: 501px) {
    ha-dialog.haui-quick-start-dialog { --ha-dialog-max-width: min(760px, 95vw); }
  }
  @media (prefers-reduced-motion: reduce) {
    .haui-quick-start-card { transition: none; }
  }
`;
