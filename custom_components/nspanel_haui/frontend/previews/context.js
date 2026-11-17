/**
 * NSPanel HAUI - the preview context of a device's panel cards.
 *
 * A card's render depends on an explicit object rather than on the editor
 * element: the hub entry, the device and its saved settings and panels, the
 * theme definition its pages draw in, the device info they show and the API
 * client that asks the hub for the render (`previews/types.js`).
 */

/**
 * Build the preview context shared by a device's panel cards.
 *
 * @param {string|null} entryId
 * @param {string|null} deviceName
 * @param {any} device - the device state (`{ config, panels }`)
 * @param {any} status - that device's status payload
 * @param {import('../api/client.js').ApiClient} api
 * @param {Object<string, any>|null|undefined} themes - the hub's theme library
 * @returns {import('./types.js').PreviewContext}
 */
export function buildPreviewContext(entryId, deviceName, device, status, api, themes) {
  return {
    entryId,
    device: deviceName,
    deviceConfig: device.config,
    panels: device.panels,
    theme: themes?.[device.config?.theme_id] || null,
    deviceInfo: status?.device_info || null,
    api,
  };
}
