/**
 * Payload shapes of the editor's REST and WebSocket API.
 *
 * These are JSDoc typedefs only; nothing is emitted at runtime. They describe
 * the payloads the integration's `api/` views and `web/websocket.py` already
 * return, so a client method and its caller agree without a build step.
 */

/**
 * @typedef {Object} HassConnection
 * @property {(message: Object) => Promise<any>} sendMessagePromise
 * @property {(callback: (event: Object) => void, eventType: string) => Promise<() => void>} subscribeEvents
 * @property {(callback: (message: Object) => void, message: Object, options?: Object) => Promise<() => void>} subscribeMessage
 */

/**
 * The part of Home Assistant's `hass` object the editor uses.
 *
 * @typedef {Object} Hass
 * @property {string} [language]
 * @property {(url: string, options?: Object) => Promise<Response>} fetchWithAuth
 * @property {(message: Object) => Promise<any>} callWS
 * @property {HassConnection} [connection]
 */

/**
 * @typedef {Object} PanelOption
 * @property {string} key
 * @property {string} label
 * @property {string} kind
 * @property {any} [default]
 * @property {any[]} [choices]
 * @property {number} [min]
 * @property {number} [max]
 */

/**
 * The *Add panel* catalog group a panel type is listed under, in the order the
 * hub lists the groups: backgrounds, entities, grouping, tools.
 *
 * @typedef {Object} PanelCategory
 * @property {string} key
 * @property {string} label
 * @property {string} icon
 */

/**
 * A starter template returned by `/api/nspanel_haui/panel_templates`: a keyless
 * panel config whose empty entity slots (`item: ''`) the user fills; an item-list
 * slot may carry a `domain` hint for the catalog's preview.
 *
 * @typedef {Object} PanelTemplate
 * @property {string} key
 * @property {string} label
 * @property {string} description
 * @property {string} icon
 * @property {PanelConfig} panel
 */

/**
 * A panel type descriptor returned by `/api/nspanel_haui/panel_types`.
 *
 * @typedef {Object} PanelTypeDescriptor
 * @property {string} type_key
 * @property {string} label
 * @property {string} [description]
 * @property {PanelCategory} category
 * @property {string} [icon]
 * @property {number} [page_id]
 * @property {boolean} [has_header]
 * @property {PanelOption[]} [options]
 * @property {PanelOption[]} [item_options]
 */

/**
 * @typedef {Object} UpdateConfig
 * @property {boolean} [enabled]
 * @property {boolean} [check_on_connect]
 * @property {boolean} [firmware_auto_update]
 * @property {number} [update_interval]
 * @property {string} [firmware_manifest_url]
 * @property {string} [firmware_update_channel]
 */

/**
 * A device setting block. Unknown keys are kept: the hub validates and merges
 * them, and the editor round-trips the whole object.
 *
 * @typedef {Object} DeviceConfig
 * @property {boolean} [enabled]
 * @property {string} [display_model]
 * @property {string} [theme_variant]
 * @property {string} [theme_id]
 * @property {string} [home_panel]
 * @property {string} [idle_panel]
 * @property {string} [idle_panel_extra]
 * @property {UpdateConfig} [update]
 */

/**
 * @typedef {Object} PanelConfig
 * @property {string} key
 * @property {string} type
 * @property {string} [title]
 * @property {string} [theme_id]
 * @property {boolean} [show_in_navigation]
 */

/**
 * A device in a panel store payload.
 *
 * @typedef {Object} DeviceEntry
 * @property {string} [friendly_name]
 * @property {DeviceConfig} [config]
 * @property {PanelConfig[]} [panels]
 */

/**
 * A fixed or editable system panel entry.
 *
 * @typedef {Object} SystemPanel
 * @property {string} key
 * @property {string} type
 * @property {string} label
 * @property {boolean} editable
 * @property {boolean} hub_driven
 * @property {number} [page_id]
 * @property {boolean} [has_header]
 */

/**
 * @typedef {Object} Theme
 * @property {string} name
 * @property {Object<string, number>} colors
 * @property {Object<string, Object<string, Object<string, number>>>} [icons]
 */

/**
 * The body of `GET /api/nspanel_haui/panels/{entry_id}`.
 *
 * @typedef {Object} PanelStore
 * @property {number} [version]
 * @property {string[]} [device_order]
 * @property {Object<string, DeviceEntry>} devices
 * @property {Object<string, Theme>} [themes]
 * @property {SystemPanel[]} [system_panels]
 */
/** @typedef {{ config: DeviceConfig }} DeviceSettingsPayload */
/** @typedef {{ panels: PanelConfig[] }} DevicePanelsPayload */
/** @typedef {{ device_order: string[] }} DeviceOrderPayload */


/**
 * @typedef {Object} DeviceInfo
 * @property {string} [name]
 * @property {string} [ip]
 * @property {string} [ssid]
 * @property {number|string} [rssi]
 * @property {string} [tft_version]
 * @property {string} [tft_required_version]
 * @property {string} [yaml_version]
 * @property {string|null} [last_panel_update]
 * @property {string|null} [last_connection]
 * @property {number} [connection_uptime]
 * @property {"on"|"dim"|"off"|null} [display_state]
 * @property {string} [temperature_entity_id]
 */

/**
 * The TFT/firmware update state of a device.
 *
 * @typedef {Object} UpdateState
 * @property {boolean} [enabled]
 * @property {string} [state]
 * @property {string|null} [version]
 * @property {string|null} [started_at]
 * @property {string|null} [last_error]
 * @property {boolean} [firmware_installing]
 * @property {string|null} [firmware_install_error]
 * @property {boolean} [firmware_update_available]
 */

/**
 * @typedef {Object} DeviceStatus
 * @property {boolean} [connected]
 * @property {string} [connection_state]
 * @property {string} [current_page]
 * @property {string} [current_panel] - key of the panel the device shows, empty without one
 * @property {string} [integration_version]
 * @property {boolean|null} [integration_version_mismatch]
 * @property {DeviceInfo} [device_info]
 * @property {UpdateState} [update]
 * @property {string[]} [logs]
 * @property {string|null} [last_disconnect_reason]
 * @property {string|null} [disconnected_since]
 * @property {IdlePageStatus|null} [idle_page]
 */

/**
 * Where the idle page stands: shown (`active`), left open under an overlay
 * (`suspended`), held off by the current page (`held`), due in `idle_in`
 * seconds (`pending`) or switched off (`off`).
 *
 * @typedef {Object} IdlePageStatus
 * @property {"active"|"suspended"|"held"|"pending"|"off"} state
 * @property {number|null} idle_in
 */

/**
 * @typedef {Object} Notification
 * @property {string} id
 * @property {string} device
 * @property {string} [title]
 * @property {string} [message]
 * @property {string} [icon]
 * @property {string} [type]
 * @property {"added"|"removed"} [state]
 */

/**
 * @typedef {Object} TftReleases
 * @property {string[]} releases
 * @property {string|null} required
 * @property {string|null} error
 */

/**
 * @typedef {Object} FirmwareReleases
 * @property {string[]} releases
 * @property {string|null} error
 */

/**
 * @typedef {Object} ThemesResponse
 * @property {number} version
 * @property {Object<string, Theme>} builtins
 * @property {Object<string, Theme>} themes
 */

/**
 * A render of one panel on the hub: `before` is sent before the page switch.
 *
 * @typedef {Object} PanelRender
 * @property {number} page
 * @property {string[]} before
 * @property {string[]} commands
 */

/**
 * @typedef {Object} UpdateResult
 * @property {string} status
 * @property {string[]} [devices_updated]
 * @property {Array<{ name: string, error: string }>} [failed]
 * @property {UpdateState} [update]
 */

/**
 * @typedef {Object} ApiError
 * @property {string} message
 * @property {number} [status]
 */

export {};
