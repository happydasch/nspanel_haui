/**
 * NSPanel HAUI - entry list CSS.
 *
 * The list editors built on ui/entry-list.js (the schedule and the gestures)
 * draw their entries as the same folding cards. The fields only one of them
 * has follow the cards.
 */
import { css } from '../lit-import.js';

export const entryStyles = css`
  /* min-width: 0 on the list and its cards: a card's head does not wrap, and without it a long
     summary (a sequence of swipes, a sun-offset window) widens the card past the side column. */
  .haui-entry-list { display: grid; gap: 12px; min-width: 0; }
  .haui-entry {
    min-width: 0;
    border: 1px solid var(--divider-color);
    border-radius: var(--haui-radius-control);
    background: var(--haui-surface-soft);
  }
  .haui-entry-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 8px 8px 12px;
    list-style: none;
    cursor: pointer;
    user-select: none;
  }
  .haui-entry-head::-webkit-details-marker { display: none; }
  .haui-entry-head:hover { background: var(--haui-surface-strong); border-radius: var(--haui-radius-control); }
  .haui-entry[open] > .haui-entry-head { border-bottom: 1px solid var(--divider-color); border-radius: var(--haui-radius-control) var(--haui-radius-control) 0 0; }
  .haui-entry-title { flex: 0 0 auto; font-size: var(--haui-text-label); font-weight: 600; }
  /* The head reads what starts the entry, which gives way first, then what it does. */
  .haui-entry-summary {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    color: var(--secondary-text-color);
    font-size: var(--haui-text-caption);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-entry-note {
    flex: 0 0 auto;
    max-width: 45%;
    overflow: hidden;
    color: var(--primary-text-color);
    font-size: var(--haui-text-caption);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-entry-head .haui-icon-button { flex: 0 0 auto; width: 32px; height: 32px; --mdc-icon-size: 18px; }
  /* The fold indicator: a CSS chevron, so the whole row is the one control. */
  .haui-entry-chevron {
    width: 6px;
    height: 6px;
    flex: 0 0 auto;
    margin: 0 8px 4px 4px;
    border-right: 2px solid var(--secondary-text-color);
    border-bottom: 2px solid var(--secondary-text-color);
    transform: rotate(-45deg);
    transition: transform 150ms ease;
  }
  .haui-entry[open] > .haui-entry-head .haui-entry-chevron {
    margin-bottom: -4px;
    transform: rotate(45deg);
  }
  .haui-entry-body { display: grid; gap: 12px; padding: 12px 12px 12px; }
  .haui-entry-body .haui-field { margin: 0; }
  .haui-entry-body .haui-field-hint { margin-top: 4px; }
  /* Two fields side by side, one above the other in a narrow column. */
  .haui-field-pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px 12px; }
  /* Paired fields keep a one-line label height without leaving a large gap above inputs. */
  .haui-field-pair > .haui-field > label { min-height: 1.3em; }
  /* Schedule: a boundary is its kind (time, sunrise, sunset) beside the time or offset. */
  .haui-schedule-boundary { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; }
  /* Gestures: the swipes are numbered pills that wrap, then the select that adds one. */
  .haui-gesture-swipes-label { display: block; margin-bottom: 4px; font-size: var(--haui-text-caption); font-weight: 500; }
  .haui-gesture-swipes { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; min-width: 0; }
  .haui-gesture-swipes > li { flex: 0 0 auto; width: fit-content; max-width: 100%; }
  /* The entry uses the soft surface too, so swipe pills need the card surface to stand out. */
  .haui-gesture-swipes .haui-pill { background: var(--haui-card-background); }
  .haui-gesture-swipes .haui-pill.is-dragging { opacity: .5; }
  .haui-gesture-swipes .haui-pill.is-drop-before { box-shadow: inset 0 2px 0 var(--primary-color); }
  .haui-gesture-swipes .haui-pill.is-drop-after { box-shadow: inset 0 -2px 0 var(--primary-color); }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
