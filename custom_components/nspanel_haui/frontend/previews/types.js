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
 * @property {object|null} [theme] - the selected custom theme definition
 * @property {import('../api/types.js').PanelConfig[]|null} panels
 * @property {import('../api/types.js').DeviceInfo|null} deviceInfo
 * @property {import('../api/client.js').ApiClient} api
 * @property {Object} [kwargs] - context the panel opens with on top of the
 *   hub's sample (the panel editor's sample entity for an entity popup)
 */

export {};
