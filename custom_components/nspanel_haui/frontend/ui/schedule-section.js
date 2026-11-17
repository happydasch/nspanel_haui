// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import {
  DEFAULT_SCHEDULE_BRIGHTNESS, DEFAULT_SCHEDULE_BRIGHTNESS_DIM, scheduleEditor,
} from './schedule-editor.js';

/**
 * The schedule of the Screen group: the display settings by time of day. It sits
 * below the brightness, dimming and display-off fields it fills the entries'
 * empty fields from, so those values are shown once, as the fields themselves.
 * Every edit goes into the settings draft through `onChange`/`onAdd`, so the
 * sidebar's one Save applies it.
 *
 * @param {{ config: any, schedule: any[], deviceBrightness?: { full?: number|null, dimmed?: number|null },
 *   addedBrightness?: number|null, addedBrightnessDim?: number|null,
 *   expandedEntryIndex?: number|null,
 *   onEntryToggle?: (index: number, open: boolean) => void,
 *   onChange?: (schedule: any[], fields?: Record<string, unknown>) => void,
 *   onAdd?: (schedule: any[], fields?: Record<string, unknown>) => void }} data
 */
export function scheduleSection({
  config, schedule, deviceBrightness = {}, addedBrightness = null, addedBrightnessDim = null,
  expandedEntryIndex = null, onEntryToggle, onChange, onAdd,
}) {
  const dims = (/** @type {any[]} */ entries) => entries.some((entry) => entry.brightness_dim != null);
  // A field left empty inherits the device setting, or the panel's own
  // brightness when the hub sets none.
  const defaults = {
    ...config,
    brightness: config.brightness ?? deviceBrightness.full ?? null,
    brightness_dim: config.brightness_dim ?? deviceBrightness.dimmed ?? null,
  };
  // An entry that dims needs a dimmed brightness to restore when it ends; the
  // panel's own comes along with the first entry that dims.
  const dimmedBrightness = (/** @type {any[]} */ entries) => (
    config.brightness_dim == null && dims(entries)
      ? { brightness_dim: deviceBrightness.dimmed ?? DEFAULT_SCHEDULE_BRIGHTNESS_DIM }
      : {});
  return html`
    <h2 class="haui-settings-block-title">${t('Schedule')}</h2>
    <p class="haui-config-section-intro">${t('Set the display by time of day, with fixed times or sunrise and sunset. An entry fills the fields it leaves empty from the values above.')}</p>
    ${addedBrightness == null ? nothing : html`<p class="haui-field-hint is-persistent">${
      t("Saving also sets the device's full brightness to {value}%: a schedule needs it outside its entries.")
        .replace('{value}', String(addedBrightness))}</p>`}
    ${addedBrightnessDim == null ? nothing : html`<p class="haui-field-hint is-persistent">${
      t("Saving also sets the device's dimmed brightness to {value}%: an entry that dims needs it outside the entry.")
        .replace('{value}', String(addedBrightnessDim))}</p>`}
    ${scheduleEditor({
      schedule,
      defaults,
      idPrefix: 'panel-schedule',
      expandedEntryIndex,
      onEntryToggle: (index, isOpen) => {
        if (!isOpen && expandedEntryIndex === index) onEntryToggle?.(index, isOpen);
      },
      onChange: (entries) => onChange?.(entries, dimmedBrightness(entries)),
      onAdd: (entries) => onAdd?.(entries, {
        ...(config.brightness == null ? { brightness: deviceBrightness.full ?? DEFAULT_SCHEDULE_BRIGHTNESS } : {}),
        ...dimmedBrightness(entries),
      }),
    })}`;
}
