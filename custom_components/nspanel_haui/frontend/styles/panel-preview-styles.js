/**
 * NSPanel HAUI - Editor - Preview simulation CSS.
 *
 * Styles for simulated preview renderers shown inside grid card bodies.
 * Extracted from panel-grid-styles.js to separate card-layout CSS from
 * preview-visual CSS.
 */
import { css } from '../lit-import.js';
import { previewCommonStyles } from './preview/common.js';
import { previewGridStyles } from './preview/grid.js';
import { previewRowStyles } from './preview/row.js';
import { previewLightStyles } from './preview/light.js';
import { previewClockStyles } from './preview/clock.js';
import { previewWeatherStyles } from './preview/weather.js';
import { previewQRStyles } from './preview/qr.js';
import { previewAlarmStyles } from './preview/alarm.js';
import { previewMediaStyles } from './preview/media.js';

export const panelPreviewStyles = css`
  ${previewCommonStyles}
  ${previewGridStyles}
  ${previewRowStyles}
  ${previewLightStyles}
  ${previewClockStyles}
  ${previewWeatherStyles}
  ${previewQRStyles}
  ${previewAlarmStyles}
  ${previewMediaStyles}
`;
