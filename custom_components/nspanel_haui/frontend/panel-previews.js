/**
 * NSPanel HAUI - Panel card preview.
 *
 * One shared renderer draws every panel-card preview (user panels, system
 * panels and popup aliases, in both orientations): the Nextion simulator
 * (`previews/simulator-frame.js`). It loads the real virtual-panel layout and
 * icon-map assets, jumps to the panel type's physical HMI page, replays the
 * hub's own display output, overlays the configured panel's content and renders
 * the whole page scaled to the card.
 *
 * There are no per-type preview renderers and no registration step: a panel
 * type only needs `PageDescriptor.page_id` (see AGENTS.md).
 */
import { getDeviceColors, deviceThemeCss, isPortraitDevice } from './previews/utils.js';
import { renderSimulatorPreview } from './previews/simulator-frame.js';

/**
 * Build the preview result the card chrome consumes.
 *
 * @param {object} host - the Lit element instance
 * @param {object} panel - the panel config (user panel) or system panel entry
 * @param {number} panelIndex - index of the panel in the panels array (-1 for system)
 * @param {object|null} panelType - matched panel type descriptor / system entry
 * @returns {{content, hasHeader, deviceStyle, deviceColors, portrait}}
 */
export function renderPanelPreview(host, panel, panelIndex, panelType) {
  const colors = getDeviceColors(host);
  return {
    content: renderSimulatorPreview(host, panel, panelIndex, panelType),
    // The HMI page draws its own header and function buttons.
    hasHeader: false,
    deviceStyle: deviceThemeCss(colors),
    deviceColors: colors,
    portrait: isPortraitDevice(host),
  };
}
