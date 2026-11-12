// @ts-check
import { t } from './localize.js';

/** Whether the device status offers a firmware or display update. */
export function hasUpdateAvailable(update) {
  return Boolean(update?.firmware_update_available || update?.tft_update_available);
}

/** The shared connection state used by device cards, rows and summaries. */
export function deviceConnectionState(status) {
  const connected = status?.connected === true;
  return {
    connected,
    tone: connected ? 'online' : status ? 'offline' : 'unknown',
    label: connected ? t('Connected') : status ? t('Disconnected') : t('Status unavailable'),
  };
}

/**
 * The device's own full and dimmed brightness, read from its ESPHome numbers.
 *
 * These are the values a schedule leaves alone outside its entries, so the
 * editor offers them instead of inventing a brightness the panel never uses.
 * An unreadable entity (missing, unavailable) is `null`, never a made-up value.
 *
 * @param {any} status - the device status payload (`device_info` carries the ids)
 * @param {any} hass - Home Assistant, for the live entity states
 * @returns {{ full: number | null, dimmed: number | null }}
 */
export function deviceBrightness(status, hass) {
  const info = status?.device_info || {};
  const read = (entityId) => {
    const state = entityId ? hass?.states?.[entityId]?.state : undefined;
    const value = parseFloat(state);
    return Number.isFinite(value) ? value : null;
  };
  return {
    full: read(info.brightness_entity_id),
    dimmed: read(info.brightness_dim_entity_id),
  };
}
