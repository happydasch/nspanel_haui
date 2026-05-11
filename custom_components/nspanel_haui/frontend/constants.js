/**
 * NSPanel HAUI - Editor - constants & helpers.
 * Extracted from panel-editor.js; see that file for the class that delegates to these helpers.
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
  enabled: true,
  button_left_entity: "",
  button_right_entity: "",
  show_home_button: false,
  show_sleep_button: false,
  show_notifications_button: true,
  debug_level: 0,
  home_on_wakeup: false,
  home_on_first_touch: true,
  home_only_when_on: false,
  home_on_button_toggle: false,
  return_to_home_after_seconds: 0,
  always_return_to_home: false,
  sound_on_startup: true,
  use_relay_left: true,
  use_relay_right: true,
  sound_on_notification: true,
  home_panel: "",
  sleep_panel: "",
  wakeup_panel: "",
  friendly_name: "",
};

/** Supported locale options for the device config locale dropdown. */
export const LOCALE_OPTIONS = [
  { value: "en_US", label: "English" },
  { value: "de_DE", label: "Deutsch" },
  { value: "nl_NL", label: "Nederlands" },
  { value: "pl_PL", label: "Polski" },
];

/** Debug level options for the device config debug_level dropdown. */
export const DEBUG_LEVELS = [
  { value: "0", label: "Off" },
  { value: "1", label: "Basic" },
  { value: "2", label: "Verbose" },
];
