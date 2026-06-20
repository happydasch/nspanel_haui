/**
 * NSPanel HAUI - Shared network/WiFi info helpers.
 *
 * Reads WiFi/network info directly from HA sensor/text_sensor entities
 * instead of relying on JSON payload from the backend status endpoint.
 * This data persists in HA state even after brief disconnections.
 */
import { t } from './localize.js';

/**
 * Simple slugify matching Python's homeassistant.util.slugify.
 * Lowercases, replaces runs of non-alphanumeric with '_', strips leading/trailing '_'.
 */
export function slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
}

/**
 * Read WiFi/network info from HA entity states for a given device name.
 *
 * ESPHome text_sensor entities (wifi_info ip_address, ssid) are
 * registered under the sensor domain in HA (Platform.SENSOR), so
 * lookup uses `sensor.{slug}_ip` etc.
 *
 * @param {Object} hass - The HA hass object (provides hass.states)
 * @param {string} deviceName - The device name (ESPHome node name)
 * @returns {{ ip: string|null, ssid: string|null, rssi: number|null }}
 */
export function readNetworkInfo(hass, deviceName) {
  if (!hass || !deviceName) return { ip: null, ssid: null, rssi: null };
  const slug = slugify(deviceName);
  const states = hass.states;

  function val(entityId) {
    const s = states[entityId];
    if (s && s.state && !['unknown', 'unavailable', ''].includes(s.state)) {
      return s.state;
    }
    return null;
  }

  const ip = val(`sensor.${slug}_ip`);
  const ssid = val(`sensor.${slug}_ssid`);
  const rssiRaw = val(`sensor.${slug}_rssi`);
  const rssi = rssiRaw != null ? parseFloat(rssiRaw) : null;

  return { ip, ssid, rssi };
}

/* ── RSSI display helpers ─────────────────────────────────────────── */

/**
 * Map RSSI value (dBm) to a CSS class for colouring.
 * Shared across device-info dialog and device-manager rows.
 */
export function rssiStrengthClass(rssi) {
  if (rssi == null || rssi === "") return "wifi-off";
  if (rssi >= -50) return "wifi-excellent";
  if (rssi >= -60) return "wifi-good";
  if (rssi >= -70) return "wifi-fair";
  if (rssi >= -80) return "wifi-weak";
  return "wifi-off";
}

/**
 * Map RSSI value (dBm) to a wifi icon name.
 */
export function rssiIcon(rssi) {
  if (rssi == null || rssi === "") return "mdi:wifi-off";
  if (rssi >= -50) return "mdi:wifi-strength-4";
  if (rssi >= -60) return "mdi:wifi-strength-3";
  if (rssi >= -70) return "mdi:wifi-strength-2";
  if (rssi >= -80) return "mdi:wifi-strength-1";
  return "mdi:wifi-off";
}

/**
 * How many bars to show for a given RSSI value (0-4).
 */
export function rssiBarCount(rssi) {
  if (rssi == null || rssi === "") return 0;
  if (rssi >= -50) return 4;
  if (rssi >= -60) return 3;
  if (rssi >= -70) return 2;
  if (rssi >= -80) return 1;
  return 0;
}

/**
 * Format RSSI value for display (e.g. "-65 dBm").
 */
export function fmtRssi(rssi) {
  if (rssi == null || rssi === "") return t("No signal");
  return `${rssi} dBm`;
}