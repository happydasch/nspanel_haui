/**
 * NSPanel HAUI - device version and Wi-Fi signal helpers.
 */
import { t } from './localize.js';

/**
 * Whether PEP 440 version ``a`` is older than ``b``.
 *
 * Device firmware and TFT releases use PEP 440 versions, including development
 * suffixes such as ``0.4.5.dev29``. Invalid or missing versions are not treated
 * as evidence that an update is pending.
 *
 * @param {string} a
 * @param {string} b
 * @returns {boolean}
 */
export function isOlderVersion(a, b) {
  const left = parseVersion(a);
  const right = parseVersion(b);
  if (!left || !right) return false;

  for (let i = 0; i < Math.max(left.release.length, right.release.length); i++) {
    const diff = (left.release[i] || 0) - (right.release[i] || 0);
    if (diff !== 0) return diff < 0;
  }

  const preRank = (version) => version.preType
    ? ({ a: 0, b: 1, rc: 2 })[version.preType]
    : version.dev != null && version.post == null ? -1 : 3;
  const preDiff = preRank(left) - preRank(right);
  if (preDiff !== 0) return preDiff < 0;

  if (left.preType && right.preType) {
    const preDiffNum = left.preNumber - right.preNumber;
    if (preDiffNum !== 0) return preDiffNum < 0;
  }
  const postDiff = (left.post ?? -1) - (right.post ?? -1);
  if (postDiff !== 0) return postDiff < 0;
  const devDiff = (left.dev ?? Infinity) - (right.dev ?? Infinity);
  if (devDiff !== 0) return devDiff < 0;
  return compareLocal(left.local, right.local) < 0;
}

const VERSION_RE = /^v?(\d+(?:\.\d+)*)(?:\.?(alpha|beta|preview|pre|rc|a|b)(\d*))?(?:\.post(\d+))?(?:\.dev(\d+))?(?:\+([a-z0-9]+(?:[._-][a-z0-9]+)*))?$/i;

function parseVersion(value) {
  const match = String(value ?? "").trim().match(VERSION_RE);
  if (!match) return null;
  const preType = match[2]?.toLowerCase();
  return {
    release: match[1].split(".").map(Number),
    preType: preType ? (preType.startsWith("a") ? "a" : preType.startsWith("b") ? "b" : "rc") : null,
    preNumber: Number(match[3] || 0),
    post: match[4] == null ? null : Number(match[4]),
    dev: match[5] == null ? null : Number(match[5]),
    local: match[6]?.toLowerCase().split(/[._-]/).map((part) => /^\d+$/.test(part) ? Number(part) : part) || null,
  };
}

function compareLocal(left, right) {
  if (left == null || right == null) return left == null ? (right == null ? 0 : -1) : 1;
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    if (left[i] == null) return -1;
    if (right[i] == null) return 1;
    if (left[i] === right[i]) continue;
    if (typeof left[i] === "number" && typeof right[i] !== "number") return 1;
    if (typeof left[i] !== "number" && typeof right[i] === "number") return -1;
    return left[i] < right[i] ? -1 : 1;
  }
  return 0;
}

function rssiValue(rssi) {
  if ((typeof rssi !== "number" && typeof rssi !== "string") || rssi === "") return null;
  const value = Number(rssi);
  return Number.isFinite(value) ? value : null;
}

function rssiLevel(rssi) {
  const value = rssiValue(rssi);
  if (value == null) return 0;
  if (value >= -50) return 4;
  if (value >= -60) return 3;
  if (value >= -70) return 2;
  return 1;
}

export function rssiStrengthClass(rssi) {
  const classes = ["wifi-unknown", "wifi-weak", "wifi-fair", "wifi-good", "wifi-excellent"];
  return classes[rssiLevel(rssi)];
}

export function rssiBarCount(rssi) {
  return rssiLevel(rssi);
}

export function fmtRssi(rssi) {
  const value = rssiValue(rssi);
  return value == null ? t('Unknown') : `${value} dBm`;
}
