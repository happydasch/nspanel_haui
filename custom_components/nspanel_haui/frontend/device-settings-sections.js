// @ts-check
/**
 * The groups of the device settings: one tile each on the landing, one page
 * each behind it. The shell reads a group's label for the strip and the
 * element reads its tile from the same table, so the two cannot drift apart.
 */
import { t } from './localize.js';
import { GESTURE_NAMES, LOCALE_OPTIONS } from './constants.js';
import { panelName } from './panel-utils.js';
import { idlePanelKeys, unknownPanelRef } from './panel-roles.js';
import { entryCount } from './ui/entry-list.js';
import { themeLabel } from './ui/panel-manager.js';

/**
 * What a group holds, as far as its tile needs it: the stored config plus the
 * names only the hub knows (`panels` and their types, the theme library).
 * @typedef {{ panels?: any[], panelTypes?: any[], builtinThemes?: Record<string, any>,
 *   customThemes?: Record<string, any> }} SectionContext
 */

/** @param {unknown} value */
const percent = (value) => (value == null || value === '' ? t('Not set') : `${value}%`);

/** A switch and the timeout behind it; 0 seconds turns it off too. */
const after = (/** @type {unknown} */ enabled, /** @type {unknown} */ seconds) =>
  (enabled && Number(seconds) > 0 ? String(seconds) : null);

/** The direction word of one swipe step. */
const DIRECTIONS = Object.freeze({
  swipe_left: () => t('left'),
  swipe_right: () => t('right'),
  swipe_up: () => t('up'),
  swipe_down: () => t('down'),
});

/** @param {any} cfg @param {SectionContext} ctx */
function generalSummary(cfg, ctx) {
  const locale = LOCALE_OPTIONS.find((option) => option.value === cfg.locale);
  // The model's own short name: `eu` reads as EU beside the language and theme.
  const model = String(cfg.display_model ?? '').toUpperCase();
  return [
    model,
    locale?.label,
    themeLabel(cfg.theme_id, ctx.builtinThemes || {}, ctx.customThemes || {}),
  ].filter(Boolean).join(' · ');
}

/** @param {any} cfg */
function screenSummary(cfg) {
  const seconds = after(cfg.use_auto_display_off, cfg.timeout_display_off);
  // Only the brightness values that are set, then how the display turns off.
  const parts = [
    percent(cfg.brightness),
    cfg.brightness_dim == null || cfg.brightness_dim === ''
      ? null
      : t('dimmed {value}').replace('{value}', `${cfg.brightness_dim}%`),
  ].filter((part) => part && part !== t('Not set'));
  parts.push(seconds ? t('off after {seconds} s').replace('{seconds}', seconds) : t('display stays on'));
  // The schedule lives in this group: its entry count closes the tile.
  const entries = Array.isArray(cfg.schedule) ? cfg.schedule.length : 0;
  parts.push(entries ? entryCount(entries) : t('No entries'));
  return parts.join(' · ');
}

/** @param {any} cfg */
function soundsSummary(cfg) {
  return [
    cfg.sound_on_startup ? t('Startup on') : t('Startup off'),
    cfg.sound_on_notification ? t('Notifications on') : t('Notifications off'),
  ].join(' · ');
}

/** @param {any} cfg @param {SectionContext} ctx */
function homeSummary(cfg, ctx) {
  const home = String(cfg.home_panel ?? '');
  const panel = (ctx.panels || []).find((entry) => entry.key === home);
  const idle = idlePanelKeys(cfg.idle_panel, cfg.idle_panel_extra).length;
  return [
    home ? panelName(panel, ctx.panelTypes) || unknownPanelRef(home) : t('No home panel'),
    idle === 1 ? t('1 idle panel') : t('{count} idle panels').replace('{count}', String(idle)),
  ].join(' · ');
}

/** @param {any} cfg */
function gesturesSummary(cfg) {
  const gestures = Array.isArray(cfg.gestures) ? cfg.gestures : [];
  if (!gestures.length) return t('No gestures');
  const swipes = [...new Set(gestures.flatMap((gesture) => gesture.swipes || []))]
    .filter((swipe) => GESTURE_NAMES.includes(swipe));
  return [
    gestures.length === 1 ? t('1 gesture') : t('{count} gestures').replace('{count}', String(gestures.length)),
    swipes.length ? swipes.map((swipe) => DIRECTIONS[swipe]()).join(', ') : t('no swipes'),
  ].join(' · ');
}

/** @param {any} cfg */
function buttonsSummary(cfg) {
  const shown = [
    cfg.show_home_button ? t('Home') : null,
    cfg.show_idle_button ? t('Idle') : null,
    cfg.show_notifications_button ? t('Notifications') : null,
  ].filter(Boolean);
  return shown.length ? shown.join(' · ') : t('No buttons');
}

/** @param {any} cfg */
function hardwareSummary(cfg) {
  const side = (/** @type {unknown} */ relay, /** @type {unknown} */ entity) =>
    (relay ? t('relay') : String(entity ?? '') || t('no entity'));
  return [
    t('Left: {value}').replace('{value}', side(cfg.use_relay_left, cfg.button_left_entity)),
    t('Right: {value}').replace('{value}', side(cfg.use_relay_right, cfg.button_right_entity)),
  ].join(' · ');
}

/** @param {any} cfg */
function advancedSummary(cfg) {
  return [
    t('Log level: {level}').replace('{level}', String(cfg.log_level ?? '')),
    t('page settle {seconds} s').replace('{seconds}', String(cfg.page_settle_delay ?? 0)),
  ].join(' · ');
}

/** Every group of the device settings, in the order the landing shows them. */
export const SETTINGS_SECTIONS = Object.freeze([
  { key: 'general', label: () => t('General'), iconName: 'settings', summary: generalSummary },
  { key: 'home', label: () => t('Home & idle'), iconName: 'homeOutline', summary: homeSummary },
  { key: 'hardware', label: () => t('Hardware buttons'), iconName: 'dialpad', summary: hardwareSummary },
  { key: 'buttons', label: () => t('Screen buttons'), iconName: 'toggleSwitch', summary: buttonsSummary },
  // Brightness, dimming, display off and the schedule that sets them by time of day.
  { key: 'screen', label: () => t('Screen'), iconName: 'dimming', summary: screenSummary },
  { key: 'sounds', label: () => t('Sounds'), iconName: 'sound', summary: soundsSummary },
  { key: 'gestures', label: () => t('Gestures'), iconName: 'gesture', summary: gesturesSummary },
  // The log level, the stale-data threshold and the page settle delay.
  { key: 'advanced', label: () => t('Advanced'), iconName: 'tuneVariant', summary: advancedSummary },
]);

/**
 * One group by key; an unknown key is a bug, not an empty page.
 * @param {string} key
 */
export function settingsSection(key) {
  const section = SETTINGS_SECTIONS.find((entry) => entry.key === key);
  if (!section) throw new Error(`Unknown device settings section: ${key}`);
  return section;
}
