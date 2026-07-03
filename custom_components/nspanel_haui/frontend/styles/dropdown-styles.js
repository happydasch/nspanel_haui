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
  .entity-picker-wrap,
  .icon-picker-wrap {
    position: relative;
  }
  /* ── domain filter area ──────────── */
  .dropdown-filter-area {
    margin-bottom: 4px;
  }


  .entity-picker-input,
  .icon-picker-input {
    width: 100%;
  }

  .entity-dropdown,
  .icon-dropdown {
    position: absolute;
    z-index: 10;
    left: 0;
    right: 0;
    max-height: 220px;
    overflow-y: auto;
    border: 1px solid var(--divider-color, #ddd);
    border-radius: 8px;
    background: var(--card-background-color, #fff);
    margin-top: 2px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }
  .entity-dropdown[hidden],
  .icon-dropdown[hidden] {
    display: none;
  }

  /* ── dropdown items ──────────────── */
  .entity-dropdown-item,
  .icon-dropdown-item {
    cursor: pointer;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.1s;
  }
  .entity-dropdown-item:hover,
  .entity-dropdown-item.active,
  .icon-dropdown-item:hover,
  .icon-dropdown-item.active {
    background: var(--primary-color, #03a9f4);
    color: #fff;
  }
  .entity-dropdown-item.active .entity-friendly-name,
  .entity-dropdown-item.active .entity-id,
  .icon-dropdown-item.active span {
    color: #fff;
  }

  .entity-dropdown-item .entity-friendly-name {
    font-weight: 500;
    font-size: 0.9em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .entity-dropdown-item .entity-id {
    font-size: 0.75em;
    opacity: 0.7;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .icon-dropdown-item span {
    font-size: 0.85em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .icon-dropdown-item ha-icon {
    flex-shrink: 0;
  }

  /* ── scrollbar styling ──────────── */
  .entity-dropdown::-webkit-scrollbar,
  .icon-dropdown::-webkit-scrollbar {
    width: 6px;
  }
  .entity-dropdown::-webkit-scrollbar-thumb,
  .icon-dropdown::-webkit-scrollbar-thumb {
    background: var(--divider-color, #ddd);
    border-radius: 3px;
  }

  /* ── domain filter chips (entity picker) ── */
  .domain-filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 6px;
  }
  .domain-filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 12px;
    border: 1px solid var(--divider-color, #ddd);
    background: transparent;
    cursor: pointer;
    font-size: 0.78em;
    font-family: inherit;
    color: var(--secondary-text-color, #666);
    transition: all 0.12s;
  }
  .domain-filter-chip:hover {
    border-color: var(--primary-color, #03a9f4);
    color: var(--primary-color, #03a9f4);
  }
  .domain-filter-chip.active {
    background: var(--primary-color, #03a9f4);
    border-color: var(--primary-color, #03a9f4);
    color: #fff;
  }
`;
