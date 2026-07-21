/**
 * NSPanel HAUI - Grid view CSS.
 *
 * Styles for `.pg-*` classes used by panel-grid.js.
 */
import { css } from '../lit-import.js';

export const panelGridStyles = css`
  /* ── panel grid (card view) ────────── */

  .pg-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
    padding: 12px 0;
  }

  .pg-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    transition: border-color 0.15s, box-shadow 0.15s;
    position: relative;
  }
  .pg-card:hover {
    border-color: var(--primary-color, #03a9f4);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .pg-card-top-row {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    cursor: pointer;
  }

  .pg-card-type-icon {
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color, #666);
    opacity: 0.55;
    flex-shrink: 0;
  }

  .pg-card-more {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    cursor: pointer;
    border-radius: 4px;
    transition: background 0.15s;
    outline: none;
    color: var(--secondary-text-color, #666);
  }
  .pg-card-more:hover {
    background: var(--secondary-background-color, #eee);
  }
  .pg-card-more:focus-visible {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 1px;
  }
  .pg-card-more.active {
    background: var(--secondary-background-color, #e0e0e0);
  }
  .pg-card-more ha-icon {
    --mdc-icon-size: 14px;
    display: flex;
  }

  .pg-card-bottom-row {
    display: flex;
    align-items: center;
    width: 100%;
    min-height: 24px;
  }

  .pg-card-actions {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    position: relative;
  }

  .pg-card-dropdown-wrap {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 300;
  }
  .pg-card-dropdown-wrap .pl-dropdown {
    position: static;
  }

  .pg-card-preview {
    container-type: inline-size;
    display: flex;
    flex-direction: column;
    width: 100%;
    border-radius: 8px;
    background: var(--card-background-color, #2a2a2a);
    cursor: pointer;
    overflow: hidden;
  }
  .pg-card-preview-header {
    display: flex;
    align-items: center;
    padding: 5px 5px;
    background: rgba(0, 0, 0, 0.45);
    flex-shrink: 0;
    position: relative;
  }
  .pg-sim-btn-group {
    display: flex;
    gap: 3px;
    z-index: 1;
  }
  .pg-sim-btn {
    width: 20px;
    height: 20px;
    border-radius: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pg-sim-btn ha-icon {
    --mdc-icon-size: 14px;
    color: #fff;
    display: flex;
  }
  .pg-sim-btn ha-icon.icon-accent {
    color: var(--accent-color, var(--primary-color, #4fc3f7));
  }
  .pg-sim-btn.active ha-icon {
    color: var(--primary-color, #4fc3f7);
  }
  .pg-sim-btn-group-right {
    margin-left: auto;
  }
  .pg-sim-title {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.85em;
    font-weight: 500;
    color: #fff;
    opacity: 0.85;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 50%;
    pointer-events: none;
  }
  .pg-card-preview-screen {
    display: flex;
    align-items: stretch;
    justify-content: center;
    flex: 1;
    padding: 0 4px 4px;
    background: rgba(0, 0, 0, 0.12);
  }
  .pg-card-preview--with-header {
    aspect-ratio: 3 / 2;
  }
  .pg-card-preview--with-header .pg-card-preview-screen {
    border-radius: 0;
  }
  .pg-card-preview:not(.pg-card-preview--with-header) {
    aspect-ratio: 3 / 2;
  }
  .pg-card-preview-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    width: 100%;
    max-width: 100%;
    flex: 1;
    align-self: stretch;
  }
  .pg-card-preview-icon {
    --mdc-icon-size: 32px;
    color: var(--primary-color, #4fc3f7);
  }
  .pg-card-preview-desc {
    font-size: 0.82em;
    color: var(--secondary-text-color, #aaa);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
    max-width: 100%;
  }

  .pg-sys-card {
    /* Minimal: card visuals without edit/dropdown chrome */
  }

  .pg-card-title {
    font-weight: 500;
    font-size: 0.95em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
    color: var(--primary-text-color, #000);
  }
  .pg-card-title .pg-unnamed {
    color: var(--secondary-text-color, #999);
    font-style: italic;
  }

  .pg-card-key {
    font-size: 0.72em;
    color: var(--secondary-text-color, #666);
    background: var(--secondary-background-color, #eee);
    padding: 1px 6px;
    border-radius: 4px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .pg-card-badges {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
  }
  .pg-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: auto;
    min-width: 22px;
    height: 20px;
    border-radius: 3px;
    background: var(--secondary-background-color, #e0e0e0);
    color: var(--primary-background-color, #fff);
  }
  .pg-badge ha-icon {
    --mdc-icon-size: 14px;
  }
  .pg-badge-home {
    background: var(--primary-color, #03a9f4);
  }
  .pg-badge-sleep {
    background: var(--warning-color, #ffa726);
  }
  .pg-badge-wakeup {
    background: var(--success-color, #43a047);
  }
`;