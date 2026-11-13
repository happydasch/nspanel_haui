// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { button, iconButton } from './button.js';
import { actionCard } from './action-card.js';
import { gestureEditor } from './gesture-editor.js';
import { renderNumberInput, renderToggle } from '../form-fields.js';
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
  const themeId = String(config.theme_id || 'dark');
  const themeLabel = customThemes[themeId]?.name
    || (builtinThemes[themeId] ? builtinThemeLabel(themeId) : themeId);
  const schedule = scheduleDraft?.schedule || config.schedule || [];
  const gestures = gestureDraft?.gestures || config.gestures || [];
  const option = (key, label, iconName, summary) => button({
    label, iconName, variant: 'outline', title: summary,
    className: 'haui-device-option', onClick: () => onOpen?.(key),
  });
  return html`<section class="haui-device-option-controls" aria-label=${t('Device settings')}>
    <div class="haui-device-option-buttons">
      ${option('theme', t('Theme'), 'color', themeLabel)}
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
 * The schedule option: the values that apply outside every entry, then the
 * entries themselves. A draft holds the edits until Save.
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
  const scheduleConfig = scheduleDraft || { ...config, schedule: config.schedule || [] };
  const changeSchedule = (schedule, fields = {}) => {
    if (!saving) onScheduleChange?.({ ...scheduleConfig, ...fields, schedule });
  };
  const baseNumber = (id, key, label, hint, min, max, float = false) => html`
    <div class="form-group">
      <label for=${id}>${label}</label>
      ${renderNumberInput(id, scheduleConfig[key], (raw) => {
        const value = float ? parseFloat(raw) : parseInt(raw, 10);
        const next = Number.isNaN(value) ? min : Math.max(min, Math.min(value, max));
        changeSchedule(scheduleConfig.schedule, { [key]: next });
      }, { min, max, ...(float ? { step: 'any' } : {}) })}
      <div class="field-hint">${hint}</div>
    </div>`;
  const baseBrightness = (id, key, label, hint) => {
    // What the panel itself uses, for the brightness no hub setting fixes.
    const panel = deviceBrightness[key === 'brightness' ? 'full' : 'dimmed'];
    return html`<div class="form-group">
      <label for=${id}>${label}</label>
      ${renderNumberInput(id, scheduleConfig[key], (raw) => {
        const value = parseInt(raw, 10);
        const next = Number.isNaN(value) ? null : Math.max(0, Math.min(value, 100));
        changeSchedule(scheduleConfig.schedule, { [key]: next });
      }, {
        min: 0, max: 100,
        placeholder: panel == null
          ? undefined
          : t('Panel: {value}').replace('{value}', String(panel)),
      })}
      <div class="field-hint">${hint}</div>
    </div>`;
  };
  const body = html`
    <p class="config-section-intro">${t('Set display behavior by time of day. Choose fixed times or sunrise and sunset, and leave entry values empty to inherit the settings above.')}</p>
    <div class="haui-field-pair">
      ${baseBrightness('panel-schedule-base-brightness', 'brightness', t('Brightness full (%)'),
        t("Brightness outside the schedule's entries."))}
      ${baseBrightness('panel-schedule-base-brightness_dim', 'brightness_dim', t('Brightness dimmed (%)'),
        t("Dimmed brightness outside the schedule's entries."))}
    </div>
    <div class="haui-field-pair">
      ${baseNumber('panel-schedule-base-timeout_dimming', 'timeout_dimming', t('Dimming timeout (s)'),
        t("Dimming timeout outside the schedule's entries."), 0, 3600)}
      ${baseNumber('panel-schedule-base-duration_dimming', 'duration_dimming', t('Dimming duration (s)'),
        t("Dimming duration outside the schedule's entries."), 0, 5, true)}
    </div>
    <div class="checkbox-wrap">
      <div class="checkbox-row">
        ${renderToggle('panel-schedule-base-use_auto_display_off', Boolean(scheduleConfig.use_auto_display_off), (checked) =>
          changeSchedule(scheduleConfig.schedule, { use_auto_display_off: checked }))}
        <label for="panel-schedule-base-use_auto_display_off">${t('Screen off')}</label>
      </div>
      <div class="field-hint">${t("Turn the display off after the display-off timeout outside the schedule's entries. When off, the display stays on.")}</div>
    </div>
    ${baseNumber('panel-schedule-base-timeout_display_off', 'timeout_display_off', t('Display-off timeout (s)'),
      t("Display-off timeout outside the schedule's entries."), 0, 3600)}
    <div class="checkbox-wrap">
      <div class="checkbox-row">
        ${renderToggle('panel-schedule-base-sound_on_notification', Boolean(scheduleConfig.sound_on_notification), (checked) =>
          changeSchedule(scheduleConfig.schedule, { sound_on_notification: checked }))}
        <label for="panel-schedule-base-sound_on_notification">${t('Notification sound')}</label>
      </div>
      <div class="field-hint">${t("Play sounds for notifications outside the schedule's entries.")}</div>
    </div>
    ${scheduleEditor({
      schedule: scheduleConfig.schedule,
      // A field left empty inherits the value that applies outside the entries:
      // the hub setting, or the panel's own brightness when the hub sets none.
      defaults: {
        ...config,
        ...scheduleConfig,
        brightness: scheduleConfig.brightness ?? deviceBrightness.full ?? null,
        brightness_dim: scheduleConfig.brightness_dim ?? deviceBrightness.dimmed ?? null,
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
        brightness: scheduleConfig.brightness ?? deviceBrightness.full ?? DEFAULT_SCHEDULE_BRIGHTNESS,
        expandedEntryIndex: schedule.length - 1,
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
    <p class="config-section-intro">${t('Define swipe gestures to move between panels or open a specific panel. Multi-swipe gestures must be completed within their time limit.')}</p>
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
