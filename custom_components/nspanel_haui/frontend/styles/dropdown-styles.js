/**
 * NSPanel HAUI - Shared dropdown CSS.
 *
 * Reusable styles for autocomplete dropdowns used in entity, icon, and
 * panel-key pickers. Provides consistent positioning, scrolling, item
 * hover/active states, and scrollbar styling.
 */
import { css } from '../lit-import.js';

export const dropdownStyles = css`
  /* ── entity / icon / panel-key dropdown ── */
  .haui-entity-picker-wrap,
  .haui-icon-picker-wrap {
    position: relative;
  }
  /* ── domain filter area ──────────── */
  .haui-dropdown-filter-area {
    margin-top: 4px;
  }


  .haui-entity-picker-input,
  .haui-icon-picker-input {
    width: 100%;
  }

  .haui-entity-dropdown,
  .haui-icon-dropdown {
    position: absolute;
    z-index: 10;
    left: 0;
    right: 0;
    max-height: 220px;
    overflow-y: auto;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
    background: var(--card-background-color, #fff);
    margin-top: 4px;
    box-shadow: var(--haui-shadow-card);
  }
  .haui-entity-dropdown[hidden],
  .haui-icon-dropdown[hidden] {
    display: none;
  }

  /* ── dropdown items ──────────────── */
  .haui-entity-dropdown-item,
  .haui-icon-dropdown-item {
    cursor: pointer;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 120ms;
  }
  .haui-entity-dropdown-item:hover,
  .haui-entity-dropdown-item.is-active,
  .haui-icon-dropdown-item:hover,
  .haui-icon-dropdown-item.is-active {
    background: var(--primary-color, #03a9f4);
    color: #fff;
  }
  .haui-entity-dropdown-item.is-active .haui-entity-friendly-name,
  .haui-entity-dropdown-item.is-active .haui-entity-id,
  .haui-icon-dropdown-item.is-active span {
    color: #fff;
  }

  .haui-entity-dropdown-item .haui-entity-friendly-name {
    font-weight: 500;
    font-size: var(--haui-text-label);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-entity-dropdown-item .haui-entity-id {
    font-size: var(--haui-text-caption);
    opacity: 0.7;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* The entities the list leaves out: a note, not an option. */
  .haui-entity-dropdown-more {
    padding: 4px 8px;
    color: var(--secondary-text-color, #666);
    font-size: var(--haui-text-caption);
  }

  .haui-icon-dropdown-item span {
    font-size: var(--haui-text-caption);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .haui-icon-dropdown-item ha-icon {
    flex-shrink: 0;
  }

  /* ── scrollbar styling ──────────── */
  .haui-entity-dropdown::-webkit-scrollbar,
  .haui-icon-dropdown::-webkit-scrollbar {
    width: 6px;
  }
  .haui-entity-dropdown::-webkit-scrollbar-thumb,
  .haui-icon-dropdown::-webkit-scrollbar-thumb {
    background: var(--divider-color, #e0e0e0);
    border-radius: var(--haui-radius-control);
  }

  /* ── domain filter chips (entity picker) ── */
  .haui-domain-filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 4px;
  }
  .haui-domain-filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: var(--haui-card-radius);
    border: 1px solid var(--divider-color, #e0e0e0);
    background: transparent;
    cursor: pointer;
    font-size: var(--haui-text-caption);
    font-family: inherit;
    color: var(--secondary-text-color, #666);
    transition: all 120ms;
  }
  .haui-domain-filter-chip:hover {
    border-color: var(--primary-color, #03a9f4);
    color: var(--primary-color, #03a9f4);
  }
  .haui-domain-filter-chip.is-active {
    background: var(--primary-color, #03a9f4);
    border-color: var(--primary-color, #03a9f4);
    color: #fff;
  }

  @media (prefers-reduced-motion: reduce) {
    :host *, :host *::before, :host *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
  }
`;
