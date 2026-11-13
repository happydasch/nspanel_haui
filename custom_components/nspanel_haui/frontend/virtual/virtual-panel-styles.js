/**
 * NSPanel HAUI - styles for the virtual panel's rendered screen (nextion-view.js).
 */
import { css } from '../lit-import.js';

export const virtualPanelStyles = css`
  .vp-screen {
    position: relative;
    overflow: hidden;
    user-select: none;
    touch-action: var(--vp-touch-action, none);
  }
  .vp-widget {
    position: absolute;
    box-sizing: border-box;
    overflow: hidden;
  }
  .vp-text {
    display: flex;
  }
  .vp-text-inner {
    max-width: 100%;
  }
  .vp-icon {
    vertical-align: middle;
    display: inline-flex;
  }
  .vp-missing-icon {
    opacity: 0.5;
  }
  .vp-slider-fill,
  .vp-slider-cursor {
    position: absolute;
  }
  .vp-circle {
    border-radius: var(--haui-radius-round);
  }
  .vp-qr {
    display: flex;
    align-items: center;
    justify-content: center;
  }
`;
