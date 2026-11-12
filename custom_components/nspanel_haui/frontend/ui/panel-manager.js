// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { button, expandToggle, iconButton } from './button.js';
import { icon } from './icon.js';
import { surface } from './surface.js';
import { actionCard } from './action-card.js';
import { gestureEditor, gestureSummary } from './gesture-editor.js';
import { idlePanelKeys, panelPills } from './panel-pills.js';
import { renderNumberInput, renderToggle } from '../form-fields.js';
import { badge } from './badge.js';
import { entryCount } from './entry-list.js';
import { DEFAULT_SCHEDULE_BRIGHTNESS, scheduleEditor, scheduleSummary } from './schedule-editor.js';

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
 * The Device side stack of the Panels view: home and idle role assignments,
 * schedule editing and gesture configuration. The Add panel action is the
 * view's lead card (`panelActions`).
 *
 * Each card is collapsed to its heading unless `expanded` lists it (`roles`, `gestures`, `schedule`).
 *
 * The schedule and the gestures are edited in a draft (`scheduleDraft`,
 * `gestureDraft`) that their card's Save writes to the device config.
 *
 * @param {{ panels: any[], systemPanels?: any[], config: any, saving?: boolean, scheduleDraft?: any,
 *   gestureDraft?: any, deviceBrightness?: { full?: number|null, dimmed?: number|null },
 *   onSetRole: (field: string, panelKey: string) => void,
 *   onScheduleChange?: (draft: any) => void, onScheduleSave?: () => void,
 *   onScheduleEntryToggle?: (index: number, open: boolean) => void,
 *   onGestureChange?: (draft: any) => void, onGestureSave?: () => void,
 *   onGestureEntryToggle?: (index: number, open: boolean) => void,
 *   expanded?: string[], onToggle?: (card: string) => void }} data
 */
export function panelManager({
  panels, systemPanels = [], config, saving = false, scheduleDraft = null, gestureDraft = null,
  deviceBrightness = {}, onSetRole, onScheduleChange, onScheduleSave, onScheduleEntryToggle,
  onGestureChange, onGestureSave, onGestureEntryToggle, expanded = [], onToggle,
}) {
  const open = (card) => expanded.includes(card);
  // The chevron and a click on the heading both fold the card.
  const toggle = (card) => {
    const flip = onToggle && (() => onToggle(card));
    return { actions: expandToggle(open(card), flip), onToggle: flip };
  };
  // The visually hidden label names the field; the icon only shows it on hover. Giving the icon
  // role="img" would read the name twice and hide the idle count bubble inside it.
  /** @param {string} id @param {string} label @param {string} iconName @param {unknown} count */
  const roleHeading = (id, label, iconName, count = nothing) => html`<div class="haui-role-heading">
    <span class="haui-role-field-icon" title=${label}>${icon(iconName)}${count}</span>
    <label class="haui-role-field-label" for=${id}>${label}</label>
  </div>`;
  const homeKey = String(config.home_panel ?? '').trim();
  const homeField = html`<div class="haui-role-field haui-role-field-home">
    ${roleHeading('haui-home-panel', t('Home panel'), 'home')}
    <div class="haui-role-content">
      ${panelPills({
        id: 'haui-home-panel', panels, keys: homeKey ? [homeKey] : [], single: true,
        addLabel: t('Set panel'), disabled: saving,
        onChange: (keys) => onSetRole('home_panel', keys[0] || ''),
      })}
    </div>
  </div>`;
  const idle = idlePanelKeys(config.idle_panel, config.idle_panel_extra);
  const idleField = html`<div class="haui-role-field haui-role-extra haui-role-field-idle">
    ${roleHeading('haui-idle-panels', t('Idle panels'), 'clock', idle.length
      ? html`<span class="haui-role-icon-count" role="img"
        aria-label=${t('{count} panels').replace('{count}', String(idle.length))}>${idle.length}</span>`
      : nothing)}
    <div class="haui-role-content">
      ${panelPills({
        id: 'haui-idle-panels', panels, keys: idle, numbered: true, reorderable: true, disabled: saving,
        onChange: (keys) => onSetRole('idle_panels', keys.join(', ')),
      })}
      ${idle.length ? nothing : html`<span class="haui-role-hint">
        ${t('Nothing opens automatically until you add a panel.')}
      </span>`}
    </div>
  </div>`;
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
  const scheduleBody = html`
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
    })}
    <div class="haui-card-actions haui-schedule-actions">
      ${button({
        label: t('Save'), iconName: 'check', variant: 'primary',
        disabled: saving || !scheduleDraft, onClick: onScheduleSave,
      })}
    </div>`;
  const gestureConfig = gestureDraft || { gestures: config.gestures || [] };
  const changeGestures = (gestures, fields = {}) => {
    if (!saving) onGestureChange?.({ ...gestureConfig, ...fields, gestures });
  };
  const gestureBody = html`
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
    })}
    <div class="haui-card-actions haui-gesture-actions">
      ${button({
        label: t('Save'), iconName: 'check', variant: 'primary',
        disabled: saving || !gestureDraft, onClick: onGestureSave,
      })}
    </div>`;
  return html`${surface({
    title: t('Home & idle panels'),
    subtitle: t('Choose what opens when you go home and what appears automatically while idle.'),
    className: 'haui-panel-roles',
    ...toggle('roles'),
    body: open('roles') ? html`
      ${homeField}
      ${idleField}` : undefined,
  })}${surface({
    title: t('Schedule'),
    // The folded card already says what is scheduled, so the entries do not
    // have to be expanded to be reminded of them.
    subtitle: scheduleSummary(scheduleConfig.schedule),
    badge: scheduleConfig.schedule.length
      ? badge(entryCount(scheduleConfig.schedule.length), 'primary')
      : nothing,
    className: 'haui-schedule-card',
    ...toggle('schedule'),
    body: open('schedule') ? scheduleBody : undefined,
  })}${surface({
    title: t('Gestures'),
    // Like the schedule: the folded card says what each gesture does.
    subtitle: gestureSummary(gestureConfig.gestures, panels, systemPanels),
    badge: gestureConfig.gestures.length
      ? badge(entryCount(gestureConfig.gestures.length), 'primary')
      : nothing,
    className: 'haui-gesture-card',
    ...toggle('gestures'),
    body: open('gestures') ? gestureBody : undefined,
  })}`;
}
