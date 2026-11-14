import { currentLanguage, t } from '../localize.js';

const TIME_UNITS = [
  ['year', 31_557_600], ['month', 2_629_800], ['week', 604_800], ['day', 86_400],
  ['hour', 3_600], ['minute', 60], ['second', 1],
];

/** Format an ISO timestamp relative to `now`; missing or invalid dates are explicit. */
export function relativeTime(value, { now = Date.now(), locale = currentLanguage() } = {}) {
  const timestamp = typeof value === 'number' ? value : Date.parse(value || '');
  if (!Number.isFinite(timestamp)) return t('Unknown');
  let seconds = Math.round((timestamp - now) / 1000);
  // The hub stamps its events: a browser clock a little behind the hub's must
  // not read a moment ago as "in 3 seconds".
  if (seconds > 0 && seconds < 60) seconds = 0;
  // Half away from zero both ways (Math.round takes -1.5 to -1).
  const inUnit = (/** @type {number} */ size) => Math.sign(seconds) * Math.round(Math.abs(seconds) / size);
  let index = TIME_UNITS.findIndex(([, size]) => Math.abs(seconds) >= size);
  if (index < 0) index = TIME_UNITS.length - 1;
  let amount = inUnit(TIME_UNITS[index][1]);
  // 3599 s is "1 hour ago", not "60 minutes ago": an amount that rounds up to
  // the next unit is told in that unit.
  if (index > 0 && Math.abs(amount) * TIME_UNITS[index][1] >= TIME_UNITS[index - 1][1]) {
    index -= 1;
    amount = inUnit(TIME_UNITS[index][1]);
  }
  return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(amount, TIME_UNITS[index][0]);
}

/** Keep versions as supplied; represent absent device reports honestly. */
export function versionLabel(version) {
  return typeof version === 'string' && version.trim() ? version : t('Unknown');
}

/**
 * The update a device is offered, in a sentence; the firmware leads when both are offered.
 * @param {{ firmware_update_available?: boolean, firmware_update_version?: string|null }} update
 */
export function updateOfferLabel(update) {
  if (!update.firmware_update_available) return t('A display update is ready to install.');
  return update.firmware_update_version
    ? t('Firmware {version} is ready to install.').replace('{version}', update.firmware_update_version)
    : t('A firmware update is ready to install.');
}

/** Convert seconds into the compact uptime labels used in status surfaces. */
export function uptimeLabel(value) {
  if (!Number.isFinite(value) || value < 0) return t('Unknown');
  const days = Math.floor(value / 86_400);
  const hours = Math.floor((value % 86_400) / 3_600);
  const minutes = Math.floor((value % 3_600) / 60);
  if (days) return t('{days}d {hours}h').replace('{days}', String(days)).replace('{hours}', String(hours));
  if (hours) return t('{hours}h {minutes}m').replace('{hours}', String(hours)).replace('{minutes}', String(minutes));
  if (minutes) return t('{minutes}m').replace('{minutes}', String(minutes));
  return t('{seconds}s').replace('{seconds}', String(Math.floor(value)));
}

/**
 * A wait in seconds as a short duration: `10 minutes`, `1 hour`, `1 day`.
 * @param {number} seconds
 */
export function durationLabel(seconds) {
  if (seconds % 86400 === 0) {
    const days = seconds / 86400;
    return days === 1 ? t('1 day') : t('{count} days').replace('{count}', String(days));
  }
  if (seconds % 3600 === 0) {
    const hours = seconds / 3600;
    return hours === 1 ? t('1 hour') : t('{count} hours').replace('{count}', String(hours));
  }
  const minutes = Math.round(seconds / 60);
  return minutes === 1 ? t('1 minute') : t('{count} minutes').replace('{count}', String(minutes));
}
