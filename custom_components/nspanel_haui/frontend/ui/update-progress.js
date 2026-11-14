// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';

/**
 * @typedef {{ phase: string, phase_started_at: string, started_at: string|null,
 *   expected_seconds: number }} UpdateProgress
 */

/** The steps an install goes through, as the hub names them. */
const STEPS = ['starting', 'transferring', 'verifying', 'done'];

/** @param {string} step */
function stepLabel(step) {
  switch (step) {
    case 'starting': return t('Starting');
    case 'transferring': return t('Transferring');
    case 'verifying': return t('Restarting and checking');
    default: return t('Done');
  }
}

/**
 * Where a running firmware or display install is: its steps with the current
 * one marked, the time it has run and an estimate of what is left. The panel
 * reports no byte progress (the transfer blocks it), so the bar is the elapsed
 * share of the usual duration, held below done until the device confirms.
 *
 * @param {{ progress: UpdateProgress|null|undefined, label: string, now?: number }} options
 */
export function updateProgress({ progress, label, now = Date.now() }) {
  if (!progress || !STEPS.includes(progress.phase) && progress.phase !== 'failed') return nothing;
  if (progress.phase === 'failed') {
    return html`<div class="haui-update-progress is-failed">
      <p class="haui-update-progress-time" role="status">${t('The update failed')}</p>
    </div>`;
  }
  const started = Date.parse(progress.started_at || progress.phase_started_at);
  const elapsed = Math.max(0, Math.round((now - started) / 1000));
  const done = progress.phase === 'done';
  const percent = done ? 100 : Math.min(95, Math.round((elapsed / progress.expected_seconds) * 100));
  const left = progress.expected_seconds - elapsed;
  const estimate = done ? t('Done')
    : left > 0 ? t('About {minutes} min left').replace('{minutes}', String(Math.ceil(left / 60)))
      : t('Taking longer than usual');
  const elapsedText = t('{minutes} min running').replace('{minutes}', String(Math.floor(elapsed / 60)));
  return html`<div class="haui-update-progress" role="progressbar" aria-label=${label}
    aria-valuemin="0" aria-valuemax="100" aria-valuenow=${String(percent)}
    aria-valuetext=${`${stepLabel(progress.phase)}: ${estimate}`}>
    <ol class="haui-update-steps">${STEPS.map((step) => html`<li
      class=${step === progress.phase ? 'is-current' : ''}
      aria-current=${step === progress.phase ? 'step' : nothing}>${stepLabel(step)}</li>`)}</ol>
    <div class="haui-update-progress-bar"><span style=${`--haui-update-progress: ${percent}%`}></span></div>
    <p class="haui-update-progress-time">${done ? estimate : `${elapsedText} · ${estimate}`}</p>
  </div>`;
}
