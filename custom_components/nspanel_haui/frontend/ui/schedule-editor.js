// @ts-check
import { html, nothing } from '../lit-import.js';
import { renderNumberInput, renderSelect, renderToggle } from '../form-fields.js';
import { t } from '../localize.js';
import { entryList } from './entry-list.js';

/** The schedule entry "Add entry" starts with. */
export const NEW_SCHEDULE_ENTRY = {
  start: '22:00', start_offset: 0, end: '07:00', end_offset: 0,
  sound: true, brightness: 20, brightness_dim: null, display_off: true,
  timeout_dimming: null, timeout_display_off: 30, duration_dimming: null,
};

export const DEFAULT_SCHEDULE_BRIGHTNESS = 100;

/** One schedule entry's window as text, e.g. "Sunset −30 min → 22:00". */
export function scheduleWindowLabel(entry) {
  const boundary = (value, offset) => {
    if (value !== 'sunrise' && value !== 'sunset') return String(value ?? '');
    const minutes = Number(offset) || 0;
    const name = value === 'sunrise' ? t('Sunrise') : t('Sunset');
    if (!minutes) return name;
    return `${name} ${minutes > 0 ? '+' : '−'}${Math.abs(minutes)} min`;
  };
  return `${boundary(entry.start, entry.start_offset)} → ${boundary(entry.end, entry.end_offset)}`;
}

/**
 * Render the schedule entries of the Panels side stack as an `entryList`: each
 * entry folds to its window and what it turns off; only `expandedEntryIndex`
 * (the entry just added) opens by state.
 *
 * Every value an entry leaves empty is inherited from the device settings, so
 * `defaults` (the device config) supplies the placeholders that say what an
 * empty field means.
 *
 * @param {{ schedule?: any[], defaults?: any, idPrefix?: string, expandedEntryIndex?: number|null,
 *   onChange: (schedule: any[]) => void, onAdd?: (schedule: any[]) => void,
 *   onEntryToggle?: (index: number, open: boolean) => void }} options
 */
export function scheduleEditor({
  schedule = [], defaults = {}, idPrefix = 'dc-schedule', expandedEntryIndex = null,
  onChange, onAdd, onEntryToggle,
}) {
  const update = (index, fields) => {
    const next = [...schedule];
    next[index] = { ...next[index], ...fields };
    onChange(next);
  };
  /** A typed number, or null (inherit) when the field is emptied. */
  const number = (raw, min, max, float = false) => {
    if (raw === '' || raw == null) return null;
    const value = float ? parseFloat(raw) : parseInt(raw, 10);
    if (Number.isNaN(value)) return null;
    return Math.max(min, Math.min(value, max));
  };
  /** What an empty field falls back to, as the input's placeholder. */
  const inherit = (key) => {
    const value = defaults?.[key];
    return value == null || value === ''
      ? t('Inherit')
      : t('Inherit ({value})').replace('{value}', String(value));
  };
  const boundary = (id, label, value, offset, fallbackTime, onChangeBoundary) => {
    const isSun = value === 'sunrise' || value === 'sunset';
    return html`<div class="haui-field">
      <label for=${id}>${label}</label>
      <div class="haui-schedule-boundary">
        ${renderSelect(id, isSun ? value : 'time', [
          { value: 'time', label: t('Time') },
          { value: 'sunrise', label: t('Sunrise') },
          { value: 'sunset', label: t('Sunset') },
        ], (v) => onChangeBoundary(v === 'time' ? fallbackTime : v, v === 'time' ? 0 : (offset ?? 0)))}
        ${isSun ? renderNumberInput(`${id}_offset`, offset ?? 0, (raw) => {
          const v = parseInt(raw, 10);
          onChangeBoundary(value, Number.isNaN(v) ? 0 : Math.max(-720, Math.min(v, 720)));
        }, { min: -720, max: 720, placeholder: t('Offset (min)') }) : html`<input
          id=${`${id}_time`} type="time" class="haui-input" .value=${String(value ?? '')}
          @input=${(event) => onChangeBoundary(event.target.value, 0)}>`}
      </div>
      ${isSun ? html`<div class="haui-field-hint">${t('Offset in minutes: negative is earlier, positive is later.')}</div>` : nothing}
    </div>`;
  };
  const body = (item, index) => {
    const id = (name) => `${idPrefix}_${index}_${name}`;
    const setField = (key, value) => update(index, { [key]: value });
    const setBoundary = (key, offsetKey, value, offset) => update(index, { [key]: value, [offsetKey]: offset });
    /** @param {{ min: number, max: number, step?: string }} opts */
    const numberField = (name, label, value, opts) => {
      const { min, max, step } = opts;
      return html`<div class="haui-field">
        <label for=${id(name)}>${label}</label>
        ${renderNumberInput(id(name), value, (raw) => setField(name, number(raw, min, max, step === 'any')), {
          min, max, step, placeholder: inherit(name),
        })}
      </div>`;
    };
    return html`
      ${boundary(id('start'), t('From'), item.start, item.start_offset, '22:00',
        (start, start_offset) => setBoundary('start', 'start_offset', start, start_offset))}
      ${boundary(id('end'), t('To'), item.end, item.end_offset, '07:00',
        (end, end_offset) => setBoundary('end', 'end_offset', end, end_offset))}
      <div class="haui-field-pair">
        ${numberField('brightness', t('Brightness full (%)'), item.brightness, { min: 0, max: 100 })}
        ${numberField('brightness_dim', t('Brightness dimmed (%)'), item.brightness_dim, { min: 0, max: 100 })}
      </div>
      <div class="haui-field-pair">
        ${numberField('timeout_dimming', t('Dimming timeout (s)'), item.timeout_dimming, { min: 0, max: 3600 })}
        ${numberField('duration_dimming', t('Dimming duration (s)'), item.duration_dimming,
          { min: 0, max: 5, step: 'any' })}
      </div>
      <div class="haui-checkbox-wrap">
        <div class="haui-checkbox-row">
          ${renderToggle(id('display_off'), Boolean(item.display_off), (checked) => setField('display_off', checked))}
          <label for=${id('display_off')}>${t('Screen off')}</label>
        </div>
        <div class="haui-field-hint">${t('Turn the display off after the display-off timeout. When off, the display stays on.')}</div>
      </div>
      ${item.display_off ? numberField('timeout_display_off', t('Display-off timeout (s)'),
        item.timeout_display_off, { min: 0, max: 3600 }) : nothing}
      <div class="haui-checkbox-wrap">
        <div class="haui-checkbox-row">
          ${renderToggle(id('sound'), Boolean(item.sound), (checked) => setField('sound', checked))}
          <label for=${id('sound')}>${t('Notification sound')}</label>
        </div>
        <div class="haui-field-hint">${t('When off, no sounds are played and a notification does not wake the display.')}</div>
      </div>`;
  };
  return entryList({
    entries: schedule,
    className: 'haui-schedule-editor',
    addId: `${idPrefix}_add`,
    addLabel: t('Add entry'),
    removeLabel: t('Remove entry'),
    expandedIndex: expandedEntryIndex,
    onAdd: () => (onAdd || onChange)([...schedule, { ...NEW_SCHEDULE_ENTRY }]),
    onRemove: (index) => onChange(schedule.filter((_, i) => i !== index)),
    onToggle: onEntryToggle,
    summary: scheduleWindowLabel,
    note: (item) => [item.sound ? '' : t('Silent'), item.display_off ? t('Screen off') : '']
      .filter(Boolean).join(' · '),
    body,
  });
}
