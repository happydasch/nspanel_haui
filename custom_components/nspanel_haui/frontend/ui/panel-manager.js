// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { button, iconButton } from './button.js';
import { actionCard } from './action-card.js';
import { gestureEditor } from './gesture-editor.js';
import { builtinThemeLabel } from '../theme-library.js';
import { entryCount } from './entry-list.js';
import { DEFAULT_SCHEDULE_BRIGHTNESS, scheduleEditor } from './schedule-editor.js';

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
 * The schedule option: its entries. Outside them the device settings apply,
 * and an entry field left empty inherits the device setting. A draft holds the
 * edits until Save.
 *
 * @param {{ config: any, saving?: boolean, scheduleDraft?: any,
 *   deviceBrightness?: { full?: number|null, dimmed?: number|null },
 *   onScheduleChange?: (draft: any) => void, onScheduleSave?: () => void,
 *   onScheduleEntryToggle?: (index: number, open: boolean) => void }} data
 */
function scheduleOption({
  config, saving = false, scheduleDraft = null, deviceBrightness = {},
  onScheduleChange, onScheduleSave, onScheduleEntryToggle,
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
  const body = html`
    <p class="haui-config-section-intro">${t('Set display behavior by time of day. Choose fixed times or sunrise and sunset. Outside the entries the device settings apply, and entry values left empty inherit them.')}</p>
    ${addedBrightness == null ? nothing : html`<p class="haui-field-hint is-persistent">${
      t("Saving also sets the device's full brightness to {value}%: a schedule needs it outside its entries.")
        .replace('{value}', String(addedBrightness))}</p>`}
    ${scheduleEditor({
      schedule: scheduleConfig.schedule,
      // A field left empty inherits the device setting, or the panel's own
      // brightness when the hub sets none.
      defaults: {
        ...config,
        brightness: config.brightness ?? addedBrightness ?? deviceBrightness.full ?? null,
        brightness_dim: config.brightness_dim ?? deviceBrightness.dimmed ?? null,
      },
      idPrefix: 'panel-schedule',
      expandedEntryIndex: scheduleConfig.expandedEntryIndex,
      onEntryToggle: (index, isOpen) => {
        if (!isOpen && scheduleConfig.expandedEntryIndex === index) {
          onScheduleEntryToggle?.(index, isOpen);
        }
      },
      onChange: (schedule) => changeSchedule(schedule),
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
