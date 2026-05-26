/**
 * NSPanel HAUI - Editor - Panel preview registry.
 *
 * Central registry for panel preview renderers and main entry point.
 */
import { html } from '../lit-import.js';
import { getDeviceColors, deviceThemeCss } from './utils.js';

/** @type {Map<string, Function>} */
const panelPreviewRenderers = new Map();

/**
 * Register a custom preview renderer for a panel type.
 * The renderer returns only the visual content (what goes inside
 * `.pg-card-preview-content`). Description text is rendered automatically
 * by the card wrapper for ALL panel types.
 *
 * @param {string} typeKey  - the panel type key (e.g. 'qr', 'climate')
 * @param {Function} renderFn
 *   (host, panel, panelIndex, panelTypeDescriptor) => {
 *     content,              // TemplateResult — the preview body
 *     contentClass?,        // optional CSS class for the content wrapper
 *     containerClass?,      // optional CSS class for the preview container
 *     headerButtonOverrides? // optional { leftPri?, leftSec?, rightPri?, rightSec? }
 *                           // overrides header button icons. Each value is a plain MDI
 *                           // icon string (e.g. 'mdi:power') or { icon, accent? }.
 *   }
 */
export function registerPanelPreview(typeKey, renderFn) {
  panelPreviewRenderers.set(typeKey, renderFn);
}

/**
 * Default fallback: icon only.
 */
function renderDefaultPreview(_host, _p, _pIdx, pt) {
  return {
    content: html`
      <ha-icon class="pg-card-preview-icon" icon="${pt ? pt.icon : 'mdi:view-dashboard-outline'}"></ha-icon>`,
  };
}

/**
 * Single entry-point: look up the registered renderer for `panel.type`
 * and call it with consistent args. Falls back to the default icon renderer.
 *
 * @param {object} host      - the Lit element instance
 * @param {object} panel     - the panel config object
 * @param {number} panelIndex - index of the panel in the full panels array
 * @param {object|null} panelType - matched panel type descriptor from host._panelTypes
 * @returns {{ content, contentClass?, containerClass?, headerButtonOverrides?, deviceStyle?, deviceColors? }}
 * headerButtonOverrides keys: leftPri?, leftSec?, rightPri?, rightSec? — each a string or { icon, accent? }.
 */
export function renderPanelPreview(host, panel, panelIndex, panelType) {
  const renderFn = panelPreviewRenderers.get(panel.type) || renderDefaultPreview;
  const result = renderFn(host, panel, panelIndex, panelType);
  const colors = getDeviceColors(host);
  result.deviceStyle = deviceThemeCss(colors);
  result.deviceColors = colors;
  return result;
}
