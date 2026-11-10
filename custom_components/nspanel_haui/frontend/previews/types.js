/**
 * What a panel-card render depends on.
 *
 * The API client rides along because rendering is a hub call; everything else
 * is data the card already has.
 *
 * @typedef {Object} PreviewContext
 * @property {string|null} entryId
 * @property {string|null} device
 * @property {import('../api/types.js').DeviceConfig|null} deviceConfig
 * @property {import('../api/types.js').PanelConfig[]|null} panels
 * @property {import('../api/types.js').DeviceInfo|null} deviceInfo
 * @property {import('../api/client.js').ApiClient} api
 */

export {};
