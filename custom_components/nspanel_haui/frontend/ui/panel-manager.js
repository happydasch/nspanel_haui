// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { button, iconButton } from './button.js';
import { surface } from './surface.js';
import { icon } from './icon.js';
import { valueTile } from './info-tile.js';
import { actionCard } from './action-card.js';
import { gestureEditor } from './gesture-editor.js';
import { builtinThemeLabel } from '../theme-library.js';
import { entryCount } from './entry-list.js';
import { DEFAULT_SCHEDULE_BRIGHTNESS, DEFAULT_SCHEDULE_BRIGHTNESS_DIM, scheduleEditor } from './schedule-editor.js';

/**
 * The lead card of the Panels view: the panel counts, the Add panel action and
 * the device settings.
 *
 * @param {{ panels: any[], onAdd: () => void, onSettings: () => void }} data
 */
export function panelActions({ panels, onAdd, onSettings }) {
  const navigable = panels.filter((panel) => panel.show_in_navigation !== false);
  return actionCard({
    iconName: 'panels',
    title: t('Panels'),
    subtitle: t('{count} panels · {visible} in navigation')
      .replace('{count}', String(panels.length)).replace('{visible}', String(navigable.length)),
    tool: iconButton({ label: t('Settings'), iconName: 'settings', onClick: onSettings }),
    primary: button({ label: t('Add panel'), iconName: 'plus', variant: 'primary', onClick: onAdd }),
  });
}

/**
 * The name of a device's theme: a custom theme's own name, or the predefined
 * theme's label.
 *
 * @param {unknown} themeId
 * @param {Record<string, any>} builtinThemes
 * @param {Record<string, any>} customThemes
 */
function themeLabel(themeId, builtinThemes, customThemes) {
  const id = String(themeId || 'dark');
  return customThemes[id]?.name || (builtinThemes[id] ? builtinThemeLabel(id) : id);
}

/**
 * What the device's theme, schedule, gestures and update settings hold, in a
 * few words: the device settings show it on the row that opens each one.
 *
 * @param {{ config: any, builtinThemes?: Record<string, any>, customThemes?: Record<string, any> }} data
 * @returns {{ theme: string, schedule: string, gestures: string, updates: string }}
 */
export function deviceOptionSummaries({ config, builtinThemes = {}, customThemes = {} }) {
  const { update } = config;
  return {
    theme: themeLabel(config.theme_id, builtinThemes, customThemes),
    schedule: entryCount(config.schedule.length),
    gestures: entryCount(config.gestures.length),
    updates: update.enabled
      ? [
        update.firmware_update_channel === 'dev' ? t('Development') : t('Stable'),
        update.firmware_auto_update ? t('Auto') : t('Manual'),
      ].join(' · ')
      : t('Off'),
  };
}

/**
 * The Device view's settings buttons: Theme, Schedule and Gestures, always three
 * in a row. Theme opens the shared theme editor; the other two open their editor
 * in the modal sidebar (deviceOptionPanel).
 *
 * A button's tooltip carries what its option holds at a glance: the selected
 * theme, the number of schedule entries and gestures.
 *
 * @param {{ config: any, scheduleDraft?: any, gestureDraft?: any,
 *   builtinThemes?: Record<string, any>, customThemes?: Record<string, any>,
 *   onOpen?: (option: string) => void }} data
 */
export function panelManager({
  config, scheduleDraft = null, gestureDraft = null,
  builtinThemes = {}, customThemes = {}, onOpen,
}) {
  const schedule = scheduleDraft?.schedule || config.schedule || [];
  const gestures = gestureDraft?.gestures || config.gestures || [];
  const option = (key, label, iconName, summary) => button({
    label, iconName, variant: 'outline', title: summary,
    className: 'haui-device-option', onClick: () => onOpen?.(key),
  });
  return html`<section class="haui-device-option-controls" aria-label=${t('Device settings')}>
    <div class="haui-device-option-buttons">
      ${option('theme', t('Theme'), 'color', themeLabel(config.theme_id, builtinThemes, customThemes))}
      ${option('schedule', t('Schedule'), 'clock', schedule.length
        ? entryCount(schedule.length)
        : t('Nothing scheduled: the device settings apply all day.'))}
      ${option('gestures', t('Gestures'), 'gesture', gestures.length
        ? entryCount(gestures.length)
        : t('No gestures: swipes do nothing.'))}
    </div>
  </section>`;
}

/**
 * One option's editor in the modal sidebar: the form, which scrolls inside the
 * sidebar, above its action.
 *
 * @param {unknown} body
 * @param {unknown} action - the option's button, in the row below the form
 */
function optionPanel(body, action) {
  return html`<div class="haui-device-option-panel">
    <div class="haui-device-option-panel-body">${body}</div>
    <div class="haui-device-option-panel-actions">${action}</div>
  </div>`;
}

/**
 * The device settings that apply outside the schedule's entries and fill the
 * entry fields left empty: brightness, auto dimming, auto display off and the
 * notification sound. They are read-only here; the button below them opens the
 * device settings, where they are edited.
 *
 * @param {any} defaults - the values the entries inherit
 * @param {(() => void)|undefined} onOpenDeviceSettings
 */
function scheduleDefaults(defaults, onOpenDeviceSettings) {
  const percent = (/** @type {unknown} */ value) => (value == null || value === '' ? t('Not set') : `${value}%`);
  /** A timeout behind its switch; a timeout of 0 turns it off too. */
  const after = (/** @type {unknown} */ enabled, /** @type {unknown} */ seconds) => (enabled && Number(seconds) > 0
    ? t('After {seconds} s').replace('{seconds}', String(seconds))
    : null);
  const dimming = after(defaults.use_auto_dimming, defaults.timeout_dimming);
  const displayOff = after(defaults.use_auto_display_off, defaults.timeout_display_off);
  const sound = Boolean(defaults.sound_on_notification);
  return surface({
    title: t('Outside the entries'),
    subtitle: t('Entries inherit the values they leave empty.'),
    leading: html`<span class="haui-schedule-defaults-icon" aria-hidden="true">${icon('screen')}</span>`,
    className: 'haui-schedule-defaults',
    body: html`<dl class="haui-diag-tiles">
        ${valueTile({
          label: t('Brightness'), iconName: 'brightness', value: percent(defaults.brightness),
          detail: t('Dimmed: {value}').replace('{value}', percent(defaults.brightness_dim)),
        })}
        ${valueTile({
          label: t('Auto dimming'), iconName: 'dimming', value: dimming ?? t('Off'), muted: !dimming,
          detail: dimming && defaults.duration_dimming != null
            ? t('{seconds} s fade').replace('{seconds}', String(defaults.duration_dimming)) : '',
        })}
        ${valueTile({
          label: t('Auto display off'), iconName: 'displayOff', value: displayOff ?? t('Off'), muted: !displayOff,
        })}
        ${valueTile({
          label: t('Notification sound'), iconName: sound ? 'sound' : 'mute', value: sound ? t('On') : t('Off'),
          muted: !sound,
        })}
      </dl>
      ${button({
        label: t('Edit in device settings'), iconName: 'settings', className: 'haui-schedule-defaults-edit',
        disabled: !onOpenDeviceSettings, onClick: onOpenDeviceSettings,
      })}`,
  });
}

/**
 * The schedule option: its entries. Outside them the device settings apply,
 * and an entry field left empty inherits the device setting; the sidebar shows
 * those settings read-only above the entries. A draft holds the edits until
 * Save.
 *
 * @param {{ config: any, saving?: boolean, scheduleDraft?: any,
 *   deviceBrightness?: { full?: number|null, dimmed?: number|null },
 *   onScheduleChange?: (draft: any) => void, onScheduleSave?: () => void,
 *   onScheduleEntryToggle?: (index: number, open: boolean) => void,
 *   onOpenDeviceSettings?: () => void }} data
 */
function scheduleOption({
  config, saving = false, scheduleDraft = null, deviceBrightness = {},
  onScheduleChange, onScheduleSave, onScheduleEntryToggle, onOpenDeviceSettings,
}) {
  const scheduleConfig = scheduleDraft || { schedule: config.schedule || [] };
  const changeSchedule = (schedule, fields = {}) => {
    if (!saving) onScheduleChange?.({ ...scheduleConfig, ...fields, schedule });
  };
  // A schedule needs a full brightness to restore when an entry ends. Without a
  // hub setting, the first entry brings the panel's own along, saved with it.
  const addedBrightness = config.brightness == null && scheduleConfig.schedule.length
    ? scheduleConfig.brightness ?? null
    : null;
  // Likewise an entry's dimmed brightness: the panel's own comes along with it.
  const dims = (schedule) => schedule.some((entry) => entry.brightness_dim != null);
  const addedBrightnessDim = config.brightness_dim == null && dims(scheduleConfig.schedule)
    ? scheduleConfig.brightness_dim ?? null
    : null;
  const brightnessDimFields = (schedule) => (
    config.brightness_dim == null && scheduleConfig.brightness_dim == null && dims(schedule)
      ? { brightness_dim: deviceBrightness.dimmed ?? DEFAULT_SCHEDULE_BRIGHTNESS_DIM }
      : {});
  // A field left empty inherits the device setting, or the panel's own
  // brightness when the hub sets none.
  const defaults = {
    ...config,
    brightness: config.brightness ?? addedBrightness ?? deviceBrightness.full ?? null,
    brightness_dim: config.brightness_dim ?? addedBrightnessDim ?? deviceBrightness.dimmed ?? null,
  };
  const body = html`
    <p class="haui-config-section-intro">${t('Set display behavior by time of day. Choose fixed times or sunrise and sunset.')}</p>
    ${scheduleDefaults(defaults, onOpenDeviceSettings)}
    ${addedBrightness == null ? nothing : html`<p class="haui-field-hint is-persistent">${
      t("Saving also sets the device's full brightness to {value}%: a schedule needs it outside its entries.")
        .replace('{value}', String(addedBrightness))}</p>`}
    ${addedBrightnessDim == null ? nothing : html`<p class="haui-field-hint is-persistent">${
      t("Saving also sets the device's dimmed brightness to {value}%: an entry that dims needs it outside the entry.")
        .replace('{value}', String(addedBrightnessDim))}</p>`}
    ${scheduleEditor({
      schedule: scheduleConfig.schedule,
      defaults,
      idPrefix: 'panel-schedule',
      expandedEntryIndex: scheduleConfig.expandedEntryIndex,
      onEntryToggle: (index, isOpen) => {
        if (!isOpen && scheduleConfig.expandedEntryIndex === index) {
          onScheduleEntryToggle?.(index, isOpen);
        }
      },
      onChange: (schedule) => changeSchedule(schedule, brightnessDimFields(schedule)),
      onAdd: (schedule) => changeSchedule(schedule, {
        expandedEntryIndex: schedule.length - 1,
        ...(config.brightness == null && scheduleConfig.brightness == null
          ? { brightness: deviceBrightness.full ?? DEFAULT_SCHEDULE_BRIGHTNESS }
          : {}),
      }),
    })}`;
  return optionPanel(body, button({
    label: t('Save'), iconName: 'check', variant: 'primary',
    disabled: saving || !scheduleDraft, onClick: onScheduleSave,
  }));
}

/**
 * The gestures option: the swipes and the panel each one opens. A draft holds
 * the edits until Save.
 *
 * @param {{ panels?: any[], systemPanels?: any[], config: any, saving?: boolean,
 *   gestureDraft?: any, onGestureChange?: (draft: any) => void, onGestureSave?: () => void,
 *   onGestureEntryToggle?: (index: number, open: boolean) => void }} data
 */
function gestureOption({
  panels = [], systemPanels = [], config, saving = false, gestureDraft = null,
  onGestureChange, onGestureSave, onGestureEntryToggle,
}) {
  const gestureConfig = gestureDraft || { gestures: config.gestures || [] };
  const changeGestures = (gestures, fields = {}) => {
    if (!saving) onGestureChange?.({ ...gestureConfig, ...fields, gestures });
  };
  const body = html`
    <p class="haui-config-section-intro">${t('Define swipe gestures to move between panels or open a specific panel. Multi-swipe gestures must be completed within their time limit.')}</p>
    ${gestureEditor({
      gestures: gestureConfig.gestures,
      panels,
      systemPanels,
      expandedEntryIndex: gestureConfig.expandedEntryIndex,
      onEntryToggle: (index, isOpen) => {
        if (!isOpen && gestureConfig.expandedEntryIndex === index) {
          onGestureEntryToggle?.(index, isOpen);
        }
      },
      onChange: (gestures) => changeGestures(gestures),
      onAdd: (gestures) => changeGestures(gestures, { expandedEntryIndex: gestures.length - 1 }),
    })}`;
  return optionPanel(body, button({
    label: t('Save'), iconName: 'check', variant: 'primary',
    disabled: saving || !gestureDraft, onClick: onGestureSave,
  }));
}

/**
 * The editor one device option opens in the modal sidebar: the schedule or the
 * gestures. The theme has no separate editor — its button opens the shared
 * theme sidebar.
 *
 * @param {string} kind - schedule or gestures
 * @param {{ panels?: any[], systemPanels?: any[], config: any, saving?: boolean,
 *   scheduleDraft?: any, gestureDraft?: any,
 *   deviceBrightness?: { full?: number|null, dimmed?: number|null },
 *   onScheduleChange?: (draft: any) => void, onScheduleSave?: () => void,
 *   onScheduleEntryToggle?: (index: number, open: boolean) => void,
 *   onOpenDeviceSettings?: () => void,
 *   onGestureChange?: (draft: any) => void, onGestureSave?: () => void,
 *   onGestureEntryToggle?: (index: number, open: boolean) => void }} data
 */
export function deviceOptionPanel(kind, data) {
  /** @type {Record<string, (data: any) => unknown>} */
  const options = { schedule: scheduleOption, gestures: gestureOption };
  const render = options[kind];
  if (!render) throw new Error(`Unknown device option: ${kind}`);
  return render(data);
}
