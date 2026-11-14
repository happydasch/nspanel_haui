import { css } from '../lit-import.js';

export const panelPillStyles = css`
  .haui-pill-list { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; min-width: 0; margin: 0; padding: 0; list-style: none; }
  .haui-pill-list li { display: inline-flex; align-items: center; gap: 4px; min-width: 0; max-width: 100%; }
  .haui-pill { height: 26px; padding-inline: 8px 4px; border-radius: var(--haui-radius-pill); background: var(--haui-surface-soft, var(--secondary-background-color, #f5f5f5)); color: var(--primary-text-color, #212121); font-size: var(--haui-text-caption); }
  .haui-pill-order { color: var(--secondary-text-color, #666); font-variant-numeric: tabular-nums; }
  .haui-pill span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-pill button { display: inline-grid; flex: 0 0 auto; width: 20px; height: 20px; place-items: center; padding: 0; border: 0; border-radius: var(--haui-radius-round); background: transparent; color: var(--secondary-text-color, #666); cursor: pointer; --mdc-icon-size: 14px; }
  .haui-pill button:hover:not(:disabled) { background: var(--divider-color, #e0e0e0); color: var(--primary-text-color, #212121); }
  .haui-pill button:disabled { cursor: not-allowed; opacity: .55; }
  .haui-pill-list select.haui-select { display: inline-block; width: fit-content; max-width: 100%; height: 26px; min-height: 26px; padding: 0 24px 0 8px; border-style: dashed; border-radius: var(--haui-radius-pill); background-position: right 8px center; color: var(--secondary-text-color, #666); font-size: var(--haui-text-caption); }
`;
