// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { button } from '../ui/button.js';
import { renderField, renderNumberInput, renderSelect, renderToggleField } from '../form-fields.js';
import { durationLabel } from '../ui/format.js';

/**
 * @typedef {{ firmware_auto_update: boolean, auto_install: boolean, install_delay: number,
 *   max_attempts: number, retry_interval: number }} UpdatePolicy
 */

/** The waits the policy offers before an automatic firmware install, in seconds. */
export const INSTALL_DELAY_CHOICES = [0, 300, 600, 1800, 3600];
/** The waits the policy offers between two automatic attempts, in seconds. */
export const RETRY_INTERVAL_CHOICES = [900, 3600, 21600, 86400];

/**
 * A select of waits in seconds; a stored value outside the choices stays selectable.
 * @param {string} id
 * @param {number} value
 * @param {number[]} choices
 * @param {(seconds: number) => void} onChange
 * @param {string} [zeroLabel]
 */
function waitSelect(id, value, choices, onChange, zeroLabel = '') {
  const values = choices.includes(value) ? choices : [...choices, value].sort((a, b) => a - b);
  return renderSelect(id, value,
    values.map((seconds) => ({ value: seconds, label: seconds === 0 && zeroLabel ? zeroLabel : durationLabel(seconds) })),
    (next) => onChange(Number(next)));
}

/**
 * The policy's fields, shared by the hub policy and a device's override.
 * @param {{ policy: UpdatePolicy, idPrefix: string, onChange: (policy: UpdatePolicy) => void }} options
 */
export function updatePolicyFields({ policy, idPrefix, onChange }) {
  /** @param {Partial<UpdatePolicy>} change */
  const set = (change) => onChange({ ...policy, ...change });
  return html`
    ${renderToggleField({
      id: `${idPrefix}-firmware-auto`,
      checked: policy.firmware_auto_update,
      label: t('Install firmware updates automatically'),
      hint: t('A newer firmware installs by itself; the display update it needs follows after the restart.'),
      onChange: (checked) => set({ firmware_auto_update: checked }),
    })}
    ${renderField({
      id: `${idPrefix}-install-delay`,
      label: t('Wait before an automatic firmware install'),
      control: waitSelect(`${idPrefix}-install-delay`, policy.install_delay, INSTALL_DELAY_CHOICES,
        (seconds) => set({ install_delay: seconds }), t('Start right away')),
      hint: t('Time to install it now, put it off or skip the version in Updates.'),
    })}
    ${renderToggleField({
      id: `${idPrefix}-tft-auto`,
      checked: policy.auto_install,
      label: t('Install display updates automatically'),
      hint: t('When off, the display asks before it installs the update the firmware needs.'),
      onChange: (checked) => set({ auto_install: checked }),
    })}
    ${renderField({
      id: `${idPrefix}-max-attempts`,
      label: t('Failed attempts before it stops'),
      control: renderNumberInput(`${idPrefix}-max-attempts`, policy.max_attempts, (raw) => {
        const attempts = parseInt(raw, 10);
        if (attempts >= 1 && attempts <= 10) set({ max_attempts: attempts });
      }, { min: 1, max: 10 }),
      hint: t('After this many failed automatic attempts at one version, the install waits for you or a newer version.'),
    })}
    ${renderField({
      id: `${idPrefix}-retry-interval`,
      label: t('Wait between attempts'),
      control: waitSelect(`${idPrefix}-retry-interval`, policy.retry_interval, RETRY_INTERVAL_CHOICES,
        (seconds) => set({ retry_interval: seconds })),
    })}`;
}

/**
 * The hub's automatic update policy: what every device does with a new
 * firmware or display update unless the device overrides it.
 *
 * @param {{ policy: UpdatePolicy, dirty?: boolean, saving?: boolean,
 *   onChange: (policy: UpdatePolicy) => void, onSave: () => void }} options
 */
export function updatePolicyView({ policy, dirty = false, saving = false, onChange, onSave }) {
  return html`<div class="haui-device-option-panel">
    <div class="haui-device-option-panel-body">
      <p class="haui-config-section-intro">${t('How every device installs firmware and display updates by itself. A device can override this in its Updates sidebar.')}</p>
      ${updatePolicyFields({ policy, idPrefix: 'policy', onChange })}
    </div>
    <div class="haui-device-option-panel-actions">${button({
      label: saving ? t('Saving...') : t('Save'), iconName: 'check', variant: 'primary',
      disabled: saving || !dirty, onClick: onSave,
    })}</div>
  </div>`;
}
