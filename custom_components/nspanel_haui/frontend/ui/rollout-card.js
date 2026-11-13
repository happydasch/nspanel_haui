// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { badge } from './badge.js';
import { button, iconButton } from './button.js';
import { surface } from './surface.js';
import { updateProgress } from './update-progress.js';

/**
 * @typedef {{ name: string, kind: 'firmware'|'tft', state: string, error: string|null }} RolloutDevice
 * @typedef {{ id: number, state: string, started_at?: string|null, devices: RolloutDevice[] }} Rollout
 */

/** @param {string} state @returns {[string, string]} label and badge tone */
function deviceState(state) {
  switch (state) {
    case 'queued': return [t('Queued'), 'neutral'];
    case 'installing': return [t('Installing'), 'primary'];
    case 'done': return [t('Done'), 'success'];
    case 'failed': return [t('Failed'), 'danger'];
    case 'cancelled': return [t('Cancelled'), 'neutral'];
    default: return [t('Not started'), 'neutral'];
  }
}

/** @param {string} state */
function rolloutSummary(state) {
  switch (state) {
    case 'running': return t('Installing one device at a time; a failure stops the devices after it.');
    case 'done': return t('Every update of this rollout is installed.');
    case 'stopped': return t('Stopped at the first failure; the devices after it were not started.');
    default: return t('Cancelled; the device that was installing finished its update.');
  }
}

/**
 * Fleet's update rollout: each device with its state, the one installing with
 * its progress, and cancel controls for the devices still queued (the one
 * installing cannot be stopped).
 *
 * @param {{ rollout: Rollout|null|undefined,
 *   devices: Array<{ name: string, device?: { friendlyName?: string }, status?: any }>,
 *   onCancel?: (device: string|null) => void }} options
 */
export function rolloutCard({ rollout, devices, onCancel }) {
  if (!rollout || rollout.state === 'idle' || !rollout.devices.length) return nothing;
  const running = rollout.state === 'running';
  /** @param {string} name */
  const deviceOf = (name) => devices.find((device) => device.name === name);
  /** @param {string} name */
  const nameOf = (name) => deviceOf(name)?.device?.friendlyName || name;
  const queued = rollout.devices.some((entry) => entry.state === 'queued');
  const body = html`<p class="haui-rollout-summary">${rolloutSummary(rollout.state)}</p>
    <ol class="haui-rollout-list">${rollout.devices.map((entry) => {
      const [label, tone] = deviceState(entry.state);
      const update = deviceOf(entry.name)?.status?.update || {};
      const name = nameOf(entry.name);
      return html`<li class="haui-rollout-row">
        <div class="haui-rollout-row-head">
          <strong>${name}</strong>
          <span class="haui-rollout-kind">${entry.kind === 'firmware' ? t('Firmware') : t('Display')}</span>
          ${badge(label, tone)}
          ${running && entry.state === 'queued' && onCancel ? iconButton({
            label: t('Cancel {name}').replace('{name}', name),
            iconName: 'close',
            className: 'haui-rollout-cancel',
            onClick: () => onCancel(entry.name),
          }) : nothing}
        </div>
        ${entry.state === 'installing' ? updateProgress({
          progress: entry.kind === 'firmware' ? update.firmware_progress : update.tft_progress,
          label: t('{name} update').replace('{name}', name),
        }) : nothing}
        ${entry.error ? html`<p class="haui-rollout-error" role="alert">${entry.error}</p>` : nothing}
      </li>`;
    })}</ol>
    ${running && queued && onCancel ? html`<div class="haui-rollout-actions">${button({
      label: t('Cancel remaining'), iconName: 'close', onClick: () => onCancel(null),
    })}</div>` : nothing}`;
  return surface({ title: t('Update rollout'), body, className: 'haui-rollout' });
}
