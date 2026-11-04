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
 * Build the preview the card chrome shows. The frame sizes itself from the
 * layout it draws, so the card needs no orientation of its own.
 *
 * @param {object} host - the Lit element instance
 * @param {object} panel - the panel config (user panel) or system panel entry
 * @param {number} panelIndex - index of the panel in the panels array (-1 for system)
 * @param {object|null} panelType - matched panel type descriptor / system entry
 * @returns {import("lit").TemplateResult}
 */
export function renderPanelPreview(host, panel, panelIndex, panelType) {
  return renderSimulatorPreview(host, panel, panelIndex, panelType);
}
