/**
 * NSPanel HAUI - Panel preview utilities.
 *
 * Device helpers for the panel-card chrome around the hub-rendered preview.
 */
import { isPortraitModel } from '../constants.js';

/**
 * Whether the selected device runs the portrait (320x480) TFT layout.
 * The simulator frame loads the portrait layout for it.
 * @param {object} host - the Lit element instance (carries _deviceConfig)
 */
export function isPortraitDevice(host) {
  return isPortraitModel(host && host._deviceConfig && host._deviceConfig.display_model);
}
