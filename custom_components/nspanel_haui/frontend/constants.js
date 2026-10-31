/**
 * NSPanel HAUI - constants & helpers.
 * Shared constants and small helpers for the editor.
 */

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
  sound_on_notification: false,
  persistent_sound_interval: 5,
  use_do_not_disturb: false,
  quiet_hours_start: '',
  quiet_hours_end: '',
  use_sleep_schedule: false,
  sleep_schedule_start: '',
  sleep_schedule_end: '',
  use_night_mode: false,
  night_mode_start: '',
  night_mode_end: '',
  brightness_full: 50,
  brightness_dimmed: 20,
  night_brightness_full: 5,
  night_brightness_dimmed: 5,
  night_timeout_page: 15,
  night_timeout_display_off: 30,
  home_panel: "",
  idle_panel: "",
  idle_panel_extra: "",
  hub_idle_timeout: 0,
  auto_navigate_home_timeout: 0,
  time_format: "",
  date_format: "",
  date_format_locale: "",
  color_overrides: {},
  // Mirrors DEFAULT_CONFIG["update"] in Python.  Checks run by default so a
  // device that is never opened in the editor still receives updates.
  update: {
    check_on_connect: true,
    update_interval: 3600,
    firmware_auto_update: true,
    auto_install: true,
  },
};

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
];

/**
 * Supported log levels for the device config "Log Level" dropdown (mirrors
 * LOG_LEVEL_OPTIONS in device_config.py).  The value is the threshold at which
 * this device's app messages are emitted; DEBUG adds detailed diagnostics
 * (entity state changes, display commands) on top of routine INFO messages.
 */
export const LOG_LEVEL_OPTIONS = [
  { value: "CRITICAL", label: "Critical" },
  { value: "ERROR", label: "Error" },
  { value: "WARNING", label: "Warning" },
  { value: "INFO", label: "Info" },
  { value: "DEBUG", label: "Debug" },
];

/**
 * Display model options for the device config dialog.
 * The model selects which TFT layout the display needs: the default landscape
 * layout (EU standard and US panels mounted landscape) or the rotated
 * portrait layout for a US panel mounted portrait.  The update controller
 * uses it to pick the release asset.
 */
export const DISPLAY_MODEL_OPTIONS = [
  { value: "eu", label: "European (standard)", portrait: false },
  { value: "us", label: "US (portrait)", portrait: true },
];

/** Touch gestures the display reports — the steps of a gesture sequence (mirrors `GESTURES` in Python). */
export const GESTURE_NAMES = ["swipe_left", "swipe_right", "swipe_up", "swipe_down"];

/**
 * Whether a device's `display_model` uses the rotated 320x480 TFT layout
 * (mirrors `is_portrait_model` in Python; unknown models count as landscape).
 * @param {string|undefined} displayModel
 * @returns {boolean}
 */
export function isPortraitModel(displayModel) {
  const value = String(displayModel || "").toLowerCase();
  return DISPLAY_MODEL_OPTIONS.some((o) => o.value === value && o.portrait);
}

/**
 * Time format presets for the device config dialog.  An empty string value
 * means "inherit the hub-level default" (matching DEVICE_CONFIG).
 */
export const TIME_FORMAT_OPTIONS = [
  { value: "", label: "Default (24-hour)" },
  { value: "%H:%M", label: "24-hour (14:30)" },
  { value: "%I:%M %p", label: "US 12-hour (2:30 PM)" },
  { value: "%I:%M", label: "12-hour no AM/PM (2:30)" },
];

/**
 * Date format presets for the device config dialog.  An empty string value
 * means "inherit the hub-level default".
 */
export const DATE_FORMAT_OPTIONS = [
  { value: "", label: "Default (locale-based)" },
  { value: "%m/%d/%Y", label: "US numeric (03/14/2026)" },
  { value: "%B %d, %Y", label: "US long (March 14, 2026)" },
  { value: "%d.%m.%Y", label: "European numeric (14.03.2026)" },
  { value: "%Y-%m-%d", label: "ISO (2026-03-14)" },
];

/**
 * Map popup system type keys to their underlying user-facing type keys.
 * Only panels in this map are editable via the Edit dropdown.
 */
export const POPUP_TO_USER_TYPE = {
  popup_light: "light",
  popup_climate: "climate",
  popup_media_player: "media",
  popup_cover: "cover",
  popup_vacuum: "vacuum",
  popup_timer: "timer",
};
