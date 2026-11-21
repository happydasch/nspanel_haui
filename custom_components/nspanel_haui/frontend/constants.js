/**
 * NSPanel HAUI - constants & helpers.
 * Shared constants and small helpers for the editor.
 */
import { t } from './localize.js';

/** Deep-clone a JSON-serializable value. */
export function clone(v) {
  return JSON.parse(JSON.stringify(v));
}

/** Default panel template for a given type. */
export function defaultPanel(type = "clock") {
  return {
    type,
    title: "",
    key: "",
  };
}

/**
 * Default values for per-device configuration (matching const.py DEVICE_CONFIG).
 * These serve as UI initialization placeholders - the backend always provides
 * complete config at runtime. Do NOT rely on these for runtime behavior.
 */
export const DEVICE_CONFIG_DEFAULTS = {
  locale: "en_US",
  display_model: "eu",
  enabled: true,
  button_left_entity: "",
  button_right_entity: "",
  show_home_button: false,
  show_idle_button: false,
  show_notifications_button: true,
  log_level: "INFO",
  stale_data_seconds: 0,
  reset_interaction_on_button: true,
  snapshot_max_age_seconds: -1,
  sound_on_startup: false,
  use_relay_left: true,
  use_relay_right: true,
  use_auto_dimming: true,
  use_auto_page: true,
  use_auto_display_off: true,
  timeout_dimming: 10,
  timeout_page: 30,
  timeout_display_off: 120,
  duration_dimming: 2,
  brightness: null,
  brightness_dim: null,
  schedule: [],
  sound_on_notification: false,
  persistent_sound_interval: 5,
  home_panel: "",
  idle_panel: "",
  idle_panel_extra: "",
  auto_navigate_home_timeout: 0,
  time_format: "",
  date_format: "",
  date_format_locale: "",
  theme_id: "dark",
  gestures: [
    { swipes: ["swipe_left"], action: "next_panel", timeframe: 3 },
    { swipes: ["swipe_right"], action: "prev_panel", timeframe: 3 },
    { swipes: ["swipe_up"], action: "sys_about", timeframe: 3 },
    { swipes: ["swipe_down"], action: "sys_settings", timeframe: 3 },
  ],
  // Mirrors DEFAULT_CONFIG["update"] in Python. Checks run by default so update
  // offers are found even when a device is never opened in the editor.
  update: {
    enabled: true,
    check_on_connect: true,
    update_interval: 3600,
    firmware_auto_update: false,
    firmware_update_channel: "stable",
    auto_install: true,
    install_delay: 600,
    max_attempts: 3,
    retry_interval: 3600,
  },
};

// Mirrors DEFAULT_CONFIG["update"]["firmware_manifest_url"] in Python (the
// stable channel's manifest).  It is not part of DEVICE_CONFIG_DEFAULTS: the
// store holds the URL only when a device overrides it (a test panel following
// a local test release).
export const DEFAULT_FIRMWARE_MANIFEST_URL =
  "https://github.com/happydasch/nspanel_haui/releases/latest/download/firmware-manifest.json";

// Mirrors FirmwareUpdateChannel in Python — the channel the HAUI Firmware
// entity follows when firmware_manifest_url is left empty.
export const FIRMWARE_UPDATE_CHANNELS = ["stable", "dev"];

/**
 * Supported locale options for the device config locale dropdown.
 * Labels are endonyms (each language in its own name) on purpose, so a user can
 * find their language even when the UI is currently in one they cannot read.
 */
export const LOCALE_OPTIONS = [
  { value: "en_US", label: "English" },
  { value: "de_DE", label: "Deutsch" },
  { value: "nl_NL", label: "Nederlands" },
  { value: "pl_PL", label: "Polski" },
  { value: "fr_FR", label: "Français" },
  { value: "sk_SK", label: "Slovenčina" },
];

/**
 * Supported log levels for the device config "Log Level" dropdown (mirrors
 * LOG_LEVEL_OPTIONS in device_config.py).  The value is the threshold at which
 * this device's app messages are emitted; DEBUG adds detailed diagnostics
 * (entity state changes, display commands) on top of routine INFO messages.
 * Built per call, so the labels follow the language the editor loaded.
 * @returns {{value: string, label: string}[]}
 */
export function logLevelOptions() {
  return [
    { value: "CRITICAL", label: t("Critical") },
    { value: "ERROR", label: t("Error") },
    { value: "WARNING", label: t("Warning") },
    { value: "INFO", label: t("Info") },
    { value: "DEBUG", label: t("Debug") },
  ];
}

/**
 * The display models that run the rotated portrait TFT layout: a US panel
 * mounted portrait. Every other model, including a US panel mounted landscape,
 * uses the default landscape layout.
 */
const PORTRAIT_MODELS = ["us"];

/**
 * The display model choices the device settings show. Their labels are built
 * per call: the editor fetches its translations after this module loaded, so a
 * list built at import time would keep the English labels for the whole
 * session.
 * @returns {{value: string, label: string}[]}
 */
export function displayModelOptions() {
  return [
    { value: "eu", label: t("European (standard)") },
    { value: "us", label: t("US (portrait)") },
  ];
}

/** Swipes the display reports — the steps of a gesture (mirrors `GESTURES` in Python). */
export const GESTURE_NAMES = ["swipe_left", "swipe_right", "swipe_up", "swipe_down"];

/** Values of a gesture's `action` that are not a panel key (mirrors `GestureAction` in Python). */
export const GESTURE_ACTIONS = ["", "next_panel", "prev_panel"];

/**
 * Whether a device's `display_model` uses the rotated 320x480 TFT layout
 * (mirrors `is_portrait_model` in Python; unknown models count as landscape).
 * @param {string|undefined} displayModel
 * @returns {boolean}
 */
export function isPortraitModel(displayModel) {
  const value = String(displayModel || "").toLowerCase();
  return PORTRAIT_MODELS.includes(value);
}

/**
 * Time format presets for the device config dialog.  An empty string value
 * means "inherit the hub-level default" (matching DEVICE_CONFIG).  Built per
 * call, so the labels follow the language the editor loaded.
 * @returns {{value: string, label: string}[]}
 */
export function timeFormatOptions() {
  return [
    { value: "", label: t("Default (24-hour)") },
    { value: "%H:%M", label: t("24-hour (14:30)") },
    { value: "%I:%M %p", label: t("US 12-hour (2:30 PM)") },
    { value: "%I:%M", label: t("12-hour no AM/PM (2:30)") },
  ];
}

/**
 * Date format presets for the device config dialog.  An empty string value
 * means "inherit the hub-level default".  Built per call, so the labels follow
 * the language the editor loaded.
 * @returns {{value: string, label: string}[]}
 */
export function dateFormatOptions() {
  return [
    { value: "", label: t("Default (locale-based)") },
    { value: "%m/%d/%Y", label: t("US numeric (03/14/2026)") },
    { value: "%B %d, %Y", label: t("US long (March 14, 2026)") },
    { value: "%d.%m.%Y", label: t("European numeric (14.03.2026)") },
    { value: "%Y-%m-%d", label: t("ISO (2026-03-14)") },
  ];
}

/**
 * Map entity popup types to the user panel type whose form edits them; an
 * edited popup is saved as that type under the popup's key. Other system
 * panels are edited with their own type.
 */
export const POPUP_TO_USER_TYPE = {
  popup_light: "light",
  popup_climate: "climate",
  popup_media_player: "media",
  popup_cover: "cover",
  popup_vacuum: "vacuum",
  popup_timer: "timer",
  popup_alarm: "alarm",
};
