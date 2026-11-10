/**
 * NSPanel HAUI - Panel card preview.
 *
 * One shared renderer draws every panel-card preview (user panels, system
 * panels and popup aliases, in both orientations): the Nextion simulator
 * frame (`previews/simulator-frame.js`) replays the hub's own render of the
 * panel (`previews/previewer.js`) on the panel type's physical HMI page,
 * title bar and function buttons included, scaled to the card.
 *
 * There are no per-type preview renderers and no registration step: a panel
 * type only needs `PageDescriptor.page_id` (see AGENTS.md).
 */
import { renderSimulatorPreview } from './previews/simulator-frame.js';

/**
 * The explicit data a card render needs, built once per card from the shell's
 * mirrored state.
 *
 * @param {object} host - the editor element
 * @returns {import('./previews/types.js').PreviewContext}
 */
export function previewContextFor(host) {
  return {
    entryId: host?.entryId || null,
    device: host?._selectedDevice || null,
    deviceConfig: host?._deviceConfig || null,
    panels: typeof host?._devicePanels === 'function' ? host._devicePanels() : [],
    deviceInfo: host?._deviceStatuses?.[host?._selectedDevice]?.device_info || null,
    api: host?.api,
  };
}

/**
 * Build the preview the card chrome shows. The frame sizes itself from the
 * layout it draws, so the card needs no orientation of its own.
 *
 * @param {object} host - the Lit element instance
 * @param {object} panel - the panel config (user panel) or system panel entry
 * @param {number} panelIndex - index of the panel in the panels array (-1 for system)
 * @returns {import("lit").TemplateResult}
 */
export function renderPanelPreview(host, panel, panelIndex) {
  return renderSimulatorPreview(previewContextFor(host), panel, panelIndex);
}
