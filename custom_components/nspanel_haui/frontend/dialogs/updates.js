/**
 * NSPanel HAUI - the firmware/display update surface.
 *
 * The Updates sidebar's body; it owns every update concern: version rows, the
 * check action, the install picker (release / URL / local file) and the
 * device's update settings. The sidebar frame carries the title and the close
 * control. Device facts and diagnostics live in the Device side stack.
 */
import { html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';
import { hasUpdateAvailable } from '../device-status.js';
import {
  DEFAULT_FIRMWARE_MANIFEST_URL, DEVICE_CONFIG_DEFAULTS, FIRMWARE_UPDATE_CHANNELS,
} from '../constants.js';
import { renderField, renderNumberInput, renderSelect, renderToggle } from '../form-fields.js';
import { badge } from '../ui/badge.js';
import { button } from '../ui/button.js';
import { segmented } from '../ui/segmented.js';
import { durationLabel, relativeTime, updateOfferLabel, versionLabel } from '../ui/format.js';
import { updateProgress } from '../ui/update-progress.js';
import { icon } from '../ui/icon.js';
import { sectionHeading } from '../ui/surface.js';
/** How often the hub can look for a new version, in seconds; 0 never does. */
const UPDATE_INTERVAL_CHOICES = [0, 900, 1800, 3600, 7200, 21600, 43200, 86400, 604800];
/** The waits offered before an automatic firmware install, in seconds. */
const INSTALL_DELAY_CHOICES = [0, 300, 600, 1800, 3600];
/** The waits offered between two automatic attempts, in seconds. */
const RETRY_INTERVAL_CHOICES = [900, 3600, 21600, 86400];

function updateIntervalLabel(value) {
  switch (value) {
    case 0: return t('Never');
    case 900: return t('Every 15 minutes');
    case 1800: return t('Every 30 minutes');
    case 3600: return t('Every hour');
    case 7200: return t('Every 2 hours');
    case 21600: return t('Every 6 hours');
    case 43200: return t('Every 12 hours');
    case 86400: return t('Every day');
    case 604800: return t('Every week');
    default: return t('Every {duration}').replace('{duration}', durationLabel(value));
  }
}


/**
 * A running or finished display (TFT) update the hub reports, in words.
 * @param {string} state
 */
export function updateStateLabel(state) {
  switch (state) {
    case 'checking': return t('Checking for a display update…');
    case 'installing': return t('Installing the display update…');
    case 'done': return t('Display update installed');
    case 'error': return t('Display update failed');
    default:
      console.warn(`NSPanel HAUI: unknown display update state ${state}`);
      return t('Update status unavailable');
  }
}

/**
 * What the Updates sidebar leads with: the one thing to know about the
 * device's updates. A running install outranks a failure, a failure an offer.
 *
 * @param {import('../api/types.js').UpdateState & Record<string, any>} update
 * @returns {{ tone: 'neutral'|'busy'|'danger'|'warning'|'success', iconName: string, title: string, detail?: string|null }}
 */
export function updateSummary(update) {
  const { state } = update;
  if (update.enabled === false) {
    return { tone: 'neutral', iconName: 'sync-off', title: t('Updates are disabled for this device.') };
  }
  if (update.firmware_installing) {
    return { tone: 'busy', iconName: 'loading', title: t('Installing the firmware…') };
  }
  if (state === 'checking' || state === 'installing') {
    return { tone: 'busy', iconName: 'loading', title: updateStateLabel(state) };
  }
  if (state === 'error') {
    return { tone: 'danger', iconName: 'alert-circle-outline', title: updateStateLabel(state), detail: update.last_error };
  }
  if (update.firmware_install_error) {
    return {
      tone: 'danger', iconName: 'alert-circle-outline',
      title: t('Firmware update failed'), detail: update.firmware_install_error,
    };
  }
  if (hasUpdateAvailable(update)) {
    return { tone: 'warning', iconName: 'update', title: t('Update available'), detail: updateOfferLabel(update) };
  }
  if (state === 'done') {
    return { tone: 'success', iconName: 'check-circle-outline', title: updateStateLabel(state) };
  }
  if (state === 'idle') {
    // The hub's reason why the release cannot serve this device.
    const reason = update.firmware_update_reason || update.tft_update_reason;
    return reason
      ? { tone: 'neutral', iconName: 'information-outline', title: t('No update available'), detail: reason }
      : { tone: 'success', iconName: 'check-circle-outline', title: t('Up to date') };
  }
  return {
    tone: 'neutral', iconName: 'help-circle-outline',
    title: state ? updateStateLabel(state) : t('Update status unavailable'),
  };
}

/** One row of the version list: what is installed, and what the release has for it. */
function versionRow({ iconName, label, version, note, offered, skipped = false, disabled, onInstall }) {
  return html`<div class="haui-update-version">
    <dt>
      <span class="haui-update-version-icon">${icon(iconName)}</span>
      <span class="haui-update-version-name">${label}${offered
        ? badge(t('Update available'), 'warning') : nothing}${skipped
        ? html`<span title=${t('Skipped: it installs only by hand.')}>${badge(t('Skipped'), 'neutral')}</span>`
        : nothing}${note ? html`<small>${note}</small>` : nothing}</span>
    </dt>
    <dd>
      <span class="haui-update-version-number">${versionLabel(version)}</span>
      ${onInstall ? html`<ha-button
        size="s"
        appearance=${offered ? 'outlined' : 'plain'}
        variant=${offered ? 'brand' : 'neutral'}
        ?disabled=${disabled}
        aria-label=${`${t('Install')} ${label}`}
        @click=${onInstall}
      >
        <ha-icon slot="start" icon="mdi:download"></ha-icon>
        ${t('Install')}
      </ha-button>` : nothing}
    </dd>
  </div>`;
}

/** Read a stored update option; one the device never stored takes its default. */
function settingValue(settings, key, fallback = DEVICE_CONFIG_DEFAULTS.update[key]) {
  return settings?.[key] ?? fallback;
}

/** Update the draft and persist it once the user pauses while editing a field. */
function setSetting(host, key, value, debounce = false) {
  host._settingsDraft = { ...(host._settingsDraft || {}), [key]: value };
  host.requestUpdate();
  if (debounce) host._scheduleSettingsSave();
  else host._saveSettings();
}

/**
 * One update preference: what it does on the left, its switch on the right,
 * and its hint as a field hint that floats under the row on hover or focus.
 */
function updateRow(host, { id, key, settings, label, hint = '' }) {
  return html`<div class="haui-field haui-update-field haui-update-choice">
    <label for=${id}>${label}</label>
    ${renderToggle(id, Boolean(settingValue(settings, key)), (next) => setSetting(host, key, next))}
    ${hint ? html`<div class="haui-field-hint">${hint}</div>` : nothing}
  </div>`;
}

/**
 * A setting counted in seconds, as a list of choices; a stored value outside
 * them stays selectable.
 * @param {any} host
 * @param {{ id: string, key: string, settings: Record<string, any>, choices: number[],
 *   label: (seconds: number) => string }} options
 */
function secondsSelect(host, { id, key, settings, choices, label }) {
  const value = Number(settingValue(settings, key));
  const values = choices.includes(value) ? choices : [...choices, value].sort((a, b) => a - b);
  return renderSelect(id, value, values.map((seconds) => ({ value: seconds, label: label(seconds) })),
    (next) => setSetting(host, key, Number(next)));
}

class UpdatesSidebar extends HauiDialog {
  static get properties() {
    return {
      deviceStatus: { type: Object },
      deviceName: { type: String },
      entryId: { type: String },
      api: { type: Object },
      config: { type: Object },
      _settingsDraft: { type: Object, state: true },
      _picker: { type: Object, state: true },
      _checkError: { type: String, state: true },
      _actionBusy: { type: Boolean, state: true },
    };
  }

  constructor() {
    super();
    this.deviceStatus = null;
    this.deviceName = null;
    this.entryId = null;
    this.config = null;
    this._settingsDraft = null;
    this._settingsInitial = null;
    this._settingsDevice = null;
    this._settingsSaveTimer = null;
    this._picker = null;
    this._checkError = null;
    this._actionBusy = false;
  }

  /**
   * Adopt persisted settings without discarding newer local edits. A save can
   * finish while another control is being changed, so rebase those edits onto
   * the config that just landed.
   */
  willUpdate(changed) {
    if (!changed.has('config') && !changed.has('deviceName')) return;
    const stored = this.config?.update || {};
    if (this.deviceName === this._settingsDevice
      && JSON.stringify(stored) === JSON.stringify(this._settingsInitial)) return;

    const previous = this._settingsInitial || {};
    const draft = this._settingsDraft || previous;
    const deviceChanged = this.deviceName !== this._settingsDevice;
    const rebased = { ...stored };
    if (!deviceChanged) {
      for (const key of new Set([...Object.keys(previous), ...Object.keys(draft)])) {
        if (JSON.stringify(draft[key]) === JSON.stringify(previous[key])) continue;
        if (draft[key] === undefined) delete rebased[key];
        else rebased[key] = draft[key];
      }
    }
    this._settingsDevice = this.deviceName;
    this._settingsInitial = { ...stored };
    this._settingsDraft = rebased;
  }


  updated(changed) {
    if (changed.has('open') && !this.open) this._picker = null;
  }
  _settingsChanged() {
    return JSON.stringify(this._settingsDraft || {}) !== JSON.stringify(this._settingsInitial || {});
  }

  _scheduleSettingsSave() {
    clearTimeout(this._settingsSaveTimer);
    this._settingsSaveTimer = setTimeout(() => {
      this._settingsSaveTimer = null;
      this._saveSettings();
    }, 300);
  }

  _saveSettings() {
    clearTimeout(this._settingsSaveTimer);
    this._settingsSaveTimer = null;
    if (!this._settingsChanged()) return;
    this._emit('save-update-settings', { update: { ...this._settingsDraft } });
  }

  async _checkForUpdates() {
    if (!this.deviceName || !this.entryId || this._actionBusy) return;
    this._actionBusy = true;
    this._checkError = null;
    try {
      await this.api.updates.check(this.entryId, this.deviceName);
      this._emit('update-check');
    } catch (error) {
      this._checkError = error.message || t('Failed to check for updates');
    } finally {
      this._actionBusy = false;
    }
  }

  /* ── TFT / firmware install picker ────────────────────────────────── */

  async _openPicker(kind, name, choice = '') {
    const updateStatus = this.deviceStatus?.update;
    if (
      updateStatus?.enabled === false || this._actionBusy || updateStatus?.firmware_installing ||
      updateStatus?.state === 'checking' || updateStatus?.state === 'installing'
    ) return;
    this._picker = { kind, device: name, releases: null, releasesError: '', choice, url: '', file: null, error: '' };
    const load = kind === 'tft'
      ? () => this.api.updates.tftReleases(this.entryId, name)
      : () => this.api.updates.firmwareReleases(this.entryId, name);
    let result;
    try {
      result = await load();
    } catch (e) {
      result = {
        releases: [],
        error: e.message || (kind === 'tft' ? t('Failed to load the TFT releases') : t('Failed to load the firmware releases')),
      };
    }
    // The picker may have been closed or opened for another install meanwhile.
    if (this._picker?.kind !== kind || this._picker.device !== name) return;
    const releases = result.releases;
    const pending = this._picker.choice === null;
    const required = result.required;
    const tftNeedsExplicitChoice = kind === 'tft'
      && this._picker.choice === ''
      && (!required || releases.length === 0);
    const defaultChoice = pending || tftNeedsExplicitChoice
      ? (releases[0] ?? 'url')
      : this._picker.choice;
    this._picker = {
      ...this._picker,
      releases,
      releasesError: result.error || '',
      choice: defaultChoice,
    };
  }

  _updatePicker(changes) { this._picker = { ...this._picker, ...changes }; }

  _finishLocalUpload(error = '') {
    if (!this._picker?.uploading) return;
    this._picker = error ? { ...this._picker, uploading: false, error } : null;
  }

  _installFromPicker() {
    const { kind, device: name, choice } = this._picker;
    if (this.deviceStatus?.update?.enabled === false) return;
    if (choice === null) return;
    const event = kind === 'tft' ? 'update-tft' : 'update-firmware';
    if (choice === 'url') {
      const url = this._picker.url.trim();
      if (!/^https?:\/\/\S+$/i.test(url)) {
        this._updatePicker({
          error: kind === 'tft'
            ? t('Enter the http(s) URL of a .tft file')
            : t('Enter the http(s) URL of a firmware OTA image (.bin)'),
        });
        return;
      }
      this._emit(event, { name, url });
    } else if (choice === 'file') {
      const file = this._picker.file;
      if (!file) {
        this._updatePicker({ error: t('Choose a local update file') });
        return;
      }
      const extension = kind === 'tft' ? '.tft' : '.bin';
      if (!file.name.toLowerCase().endsWith(extension)) {
        this._updatePicker({
          error: kind === 'tft'
            ? t('Choose a Nextion TFT file (.tft)')
            : t('Choose an ESPHome OTA image (.bin)'),
        });
        return;
      }
      this._updatePicker({ uploading: true, error: '' });
      this._emit(event, { name, file });
      return;
    } else if (choice) {
      this._emit(event, { name, version: choice });
    } else {
      this._emit(event, { name });
    }
    this._picker = null;
  }

  _renderPicker(name, required, updateStatus) {
    if (updateStatus?.enabled === false) {
      return html`<div class="haui-update-picker">${t('Updates are disabled for this device.')}</div>`;
    }
    const { kind, releases, releasesError, choice, url, file, error, uploading } = this._picker;
    const tft = kind === 'tft';
    let defaults = [];
    if (tft) {
      defaults = [['', required
        ? t('Version the firmware needs ({version})').replace('{version}', required)
        : t('Version the firmware needs')]];
    } else if (updateStatus?.firmware_update_available) {
      defaults = [['', t('Offered update ({version})').replace('{version}', updateStatus.firmware_update_version || '')]];
    }
    // The manifest's TFT is normally the required one, which the default
    // already installs; list it only when it differs.
    const listed = (releases || []).filter((tag) => !(tft && required && tag === required));
    const options = [
      ...defaults,
      ...listed.map((tag) => [tag, tag]),
      ['url', t('From URL')],
      ['file', t('From local file')],
    ];
    return html`
      <div class="haui-update-picker" @click=${(e) => e.stopPropagation()}>
        <div class="haui-field">
          <label for="di-install-source">${tft ? t('TFT to install') : t('Firmware to install')}</label>
          ${renderSelect(
            'di-install-source',
            choice,
            options,
            (value) => this._updatePicker({ choice: value, file: null, error: '' }),
            { disabled: uploading },
          )}
          ${releases === null ? html`<div class="haui-field-hint is-persistent">${t('Loading releases…')}</div>` : ''}
          ${releasesError
            ? html`<div class="haui-field-hint is-persistent">${t('Releases unavailable: {error}').replace('{error}', releasesError)}</div>`
            : ''}
        </div>
        ${choice === 'url' ? html`
          <div class="haui-field">
            <label for="di-install-url">${tft ? t('TFT file URL') : t('Firmware OTA image URL')}</label>
            <input
              id="di-install-url"
              class="haui-input"
              type="url"
              .value=${url}
              @input=${(e) => this._updatePicker({ url: e.target.value, error: '' })}
            />
          </div>
        ` : ''}
        ${choice === 'file' ? html`
          <div class="haui-field">
            <label for="di-install-file">${tft ? t('Local TFT file') : t('Local firmware OTA image')}</label>
            <input
              id="di-install-file"
              class="haui-input"
              type="file"
              accept=${tft ? '.tft' : '.bin'}
              ?disabled=${uploading}
              @change=${(e) => this._updatePicker({ file: e.target.files?.[0] || null, error: '' })}
            />
            <div class="haui-field-hint">
              ${t('The file is uploaded to Home Assistant and must be reachable by the device.')}
            </div>
          </div>
        ` : ''}
        ${uploading ? html`<div class="haui-field-hint">${t('Uploading local update file…')}</div>` : ''}
        <div class="haui-field-hint">${tft
          ? t('Another release, URL or local file stays on the display until the firmware version changes or Home Assistant restarts.')
          : t('Another release, URL or local file pauses automatic firmware updates until Home Assistant restarts. Use the OTA image (nspanel_haui_ota.bin), not the factory image.')}</div>
        ${error ? html`<p class="haui-update-error">${error}</p>` : ''}
        <div class="haui-update-actions">
          <ha-button
            variant="neutral"
            appearance="plain"
            ?disabled=${uploading}
            @click=${() => { this._picker = null; }}
          >
            ${t('Cancel')}
          </ha-button>
          <ha-button
            ?disabled=${uploading || choice === null || (choice === 'file' && !file)}
            @click=${() => this._installFromPicker()}
          >
            ${uploading ? t('Uploading…') : t('Install')}
          </ha-button>
        </div>
      </div>
    `;
  }

  /* ── the sidebar's cards ──────────────────────────────────────────── */

  /** The compact status line above the installed versions. */
  _renderStatus(summary) {
    return html`<div class="haui-update-summary">
      <div class=${`haui-update-summary-status haui-update-status-${summary.tone}`} role="status">
        <span class="haui-update-status-icon">${icon(summary.iconName)}</span>
        <div class="haui-update-summary-copy">
          <strong>${summary.title}</strong>
          ${summary.detail ? html`<p>${summary.detail}</p>` : nothing}
        </div>
      </div>
    </div>`;
  }

  /** The installed versions, one row each, with what the release offers. */
  _renderVersions({ status, info, update, requiredTft, updatesEnabled, installDisabled }) {
    return html`<dl class="haui-update-versions">
      ${versionRow({
        iconName: 'info', label: t('Integration'), version: status.integration_version,
      })}
      ${versionRow({
        iconName: 'chip', label: t('Firmware (YAML)'), version: info.yaml_version,
        note: update.firmware_update_version
          ? t('Latest release: {version}').replace('{version}', update.firmware_update_version) : '',
        offered: update.firmware_update_available,
        skipped: Boolean(update.firmware_update_version)
          && update.firmware_skipped_version === update.firmware_update_version,
        disabled: installDisabled,
        onInstall: updatesEnabled
          ? () => this._openPicker('firmware', this.deviceName, update.firmware_update_available ? '' : null)
          : null,
      })}
      ${versionRow({
        iconName: 'monitor', label: t('Display (TFT)'), version: info.tft_version,
        note: requiredTft ? t('The firmware needs {version}').replace('{version}', requiredTft) : '',
        offered: update.tft_update_available,
        disabled: installDisabled,
        onInstall: updatesEnabled ? () => this._openPicker('tft', this.deviceName) : null,
      })}
    </dl>`;
  }

  /** The check action sits after the installed version rows. */
  _renderCheckAction(updatesEnabled) {
    return updatesEnabled ? html`<div class="haui-update-check-action">
      <ha-button
        size="s"
        appearance="plain"
        ?disabled=${this._actionBusy}
        aria-busy=${this._actionBusy ? 'true' : nothing}
        @click=${this._checkForUpdates}
      >
        <ha-icon slot="start" icon="mdi:refresh"></ha-icon>
        ${this._actionBusy ? t('Checking…') : t('Check for updates')}
      </ha-button>
    </div>` : nothing;
  }

  /** What an update needs decided: where versions come from, what to do with a find, how often to look. */
  _renderDecisions(settings) {
    const automatic = Boolean(settingValue(settings, 'firmware_auto_update'));
    return html`<section class="haui-update-group">
      <div class="haui-field haui-update-field haui-update-choice">
        <span class="haui-update-choice-label">${t('Update channel')}</span>
        ${segmented({
          label: t('Update channel'),
          options: FIRMWARE_UPDATE_CHANNELS.map((value) => ({
            value, label: value === 'dev' ? t('Development') : t('Stable'),
          })),
          value: String(settingValue(settings, 'firmware_update_channel')),
          onSelect: (value) => setSetting(this, 'firmware_update_channel', value),
        })}
        ${settings.firmware_manifest_url
          ? html`<div class="haui-field-hint is-persistent">${t('The custom manifest URL under Advanced overrides the channel for firmware.')}</div>`
          : html`<div class="haui-field-hint">${t('Stable releases, or published development builds, for firmware and display.')}</div>`}
      </div>
      <div class="haui-field haui-update-field haui-update-choice">
        <span class="haui-update-choice-label">${t('When a new version is found')}</span>
        ${segmented({
          label: t('When a new version is found'),
          options: [{ value: false, label: t('Manual') }, { value: true, label: t('Auto') }],
          value: automatic,
          onSelect: (value) => setSetting(this, 'firmware_auto_update', value),
        })}
        <div class="haui-field-hint">${automatic
          ? t('A newer firmware installs by itself; the display file it needs follows after the restart.')
          : t('A newer firmware waits until you press Install.')}</div>
      </div>
      ${renderField({
        id: 'update-interval',
        label: t('Check for a new version'),
        className: 'haui-update-field',
        control: secondsSelect(this, {
          id: 'update-interval', key: 'update_interval', settings,
          choices: UPDATE_INTERVAL_CHOICES, label: updateIntervalLabel,
        }),
      })}
    </section>`;
  }

  /** The settings most devices leave alone, folded away until a manifest URL is set. */
  _renderAdvanced(settings) {
    const automatic = Boolean(settingValue(settings, 'firmware_auto_update'));
    return html`<section class="haui-update-group">
      <details class="haui-update-advanced" ?open=${Boolean(settings.firmware_manifest_url)}>
        <summary>${t('Advanced')}</summary>
        <div class="haui-update-advanced-body">
          ${renderField({
            id: 'update-firmware-manifest-url',
            label: t('Custom manifest URL'),
            className: 'haui-update-field',
            control: html`<input id="update-firmware-manifest-url" class="haui-input" type="url"
              placeholder=${settingValue(settings, 'firmware_update_channel') === 'dev' ? '' : DEFAULT_FIRMWARE_MANIFEST_URL}
              .value=${String(settingValue(settings, 'firmware_manifest_url', ''))}
              @input=${(event) => setSetting(this, 'firmware_manifest_url', event.target.value.trim() || undefined, true)} />`,
            hint: t('The manifest names the firmware the HAUI Firmware entity offers. Leave empty to follow the channel above; a URL here overrides it (e.g. point a test panel at the manifest of a local test release to follow test builds).'),
          })}
          ${updateRow(this, {
            id: 'update-check-on-connect', key: 'check_on_connect', settings,
            label: t('Check for updates on connect'),
            hint: t('Run a release check after the device connects to Home Assistant.'),
          })}
          ${automatic ? renderField({
            id: 'update-install-delay',
            label: t('Wait before an automatic firmware install'),
            className: 'haui-update-field',
            control: secondsSelect(this, {
              id: 'update-install-delay', key: 'install_delay', settings, choices: INSTALL_DELAY_CHOICES,
              label: (seconds) => (seconds === 0 ? t('Start right away') : durationLabel(seconds)),
            }),
            hint: t('Time to install it now, put it off or skip the version in Updates.'),
          }) : nothing}
          ${updateRow(this, {
            id: 'update-tft-auto', key: 'auto_install', settings,
            label: t('Install display updates automatically'),
            hint: t('A firmware update restarts the device, which then needs a matching display file. When off, the display asks before it installs it.'),
          })}
          ${automatic || settingValue(settings, 'auto_install') ? html`${renderField({
            id: 'update-max-attempts',
            label: t('Failed attempts before it stops'),
            className: 'haui-update-field',
            control: renderNumberInput('update-max-attempts', settingValue(settings, 'max_attempts'), (raw) => {
              const attempts = parseInt(raw, 10);
              if (attempts >= 1 && attempts <= 10) setSetting(this, 'max_attempts', attempts, true);
            }, { min: 1, max: 10 }),
            hint: t('After this many failed automatic attempts at one version, the install waits for you or a newer version.'),
          })}${renderField({
            id: 'update-retry-interval',
            label: t('Wait between attempts'),
            className: 'haui-update-field',
            control: secondsSelect(this, {
              id: 'update-retry-interval', key: 'retry_interval', settings,
              choices: RETRY_INTERVAL_CHOICES, label: durationLabel,
            }),
          })}` : nothing}
        </div>
      </details>
    </section>`;
  }

  /**
   * The automatic firmware install waiting to start: when it starts, and the
   * choice to start it now, put it off or skip its version.
   */
  _renderScheduled(update) {
    const scheduled = update.firmware_scheduled;
    if (!scheduled) return nothing;
    const control = (action, seconds) => () => this._emit('update-control',
      seconds === undefined ? { action } : { action, seconds });
    return html`<section class="haui-surface haui-update-scheduled" role="status">
      <p>${t('Firmware {version} installs automatically {when}.')
        .replace('{version}', scheduled.version)
        .replace('{when}', relativeTime(scheduled.starts_at))}</p>
      <div class="haui-update-scheduled-actions">
        ${button({ label: t('Install now'), iconName: 'download', variant: 'primary', onClick: control('install_now') })}
        ${button({ label: t('In 1 hour'), iconName: 'clock-outline', onClick: control('defer', 3600) })}
        ${button({ label: t('In 1 day'), iconName: 'calendar', onClick: control('defer', 86400) })}
        ${button({ label: t('Skip this version'), iconName: 'skip-next', variant: 'quiet', onClick: control('skip') })}
      </div>
    </section>`;
  }

  /** When the automatic install tries again, or that it stopped trying. */
  _renderRetry(update) {
    /** @type {Array<[string, string]>} */
    const kinds = [['firmware_auto', t('Firmware')], ['tft_auto', t('Display')]];
    return kinds.map(([key, label]) => {
      const auto = update[key];
      if (auto?.stopped_reason) {
        return html`<p class="haui-update-retry is-stopped" role="status">${label}: ${
          t('Automatic install stopped after {count} failed attempts. Install it by hand or wait for a newer version.')
            .replace('{count}', String(auto.attempts))}</p>`;
      }
      if (auto?.next_attempt_at) {
        return html`<p class="haui-update-retry" role="status">${label}: ${
          t('Attempt {count} of {max} failed; the next try is {when}.')
            .replace('{count}', String(auto.attempts))
            .replace('{max}', String(auto.max_attempts))
            .replace('{when}', relativeTime(auto.next_attempt_at))}</p>`;
      }
      return nothing;
    });
  }

  _renderSettings() {
    if (!this.config) return nothing;
    const settings = this._settingsDraft || this.config.update || {};
    return html`<section class="haui-surface haui-update-settings" aria-label=${t('Update settings')}>
      ${sectionHeading({
        title: t('Update settings'),
        subtitle: t('How this device finds and installs updates.'),
        leading: html`<span class="haui-update-settings-icon">${icon('tune-variant')}</span>`,
        actions: renderToggle('update-enabled', Boolean(settingValue(settings, 'enabled')),
          (checked) => setSetting(this, 'enabled', checked), { label: t('Enable updates') }),
        className: 'haui-update-header',
      })}
      ${settingValue(settings, 'enabled')
        ? html`${this._renderDecisions(settings)}${this._renderAdvanced(settings)}`
        : html`<p class="haui-update-off-note">${t('Updates are disabled for this device.')}</p>`}
    </section>`;
  }

  render() {
    if (!this.open) return '';
    const status = this.deviceStatus;
    if (!status) {
      return html`<div class="haui-update-sidebar">${this._renderSettings()}</div>`;
    }
    const info = status.device_info || {};
    const update = status.update || {};
    const requiredTft = info.tft_required_version;
    const updatesEnabled = update.enabled !== false;
    const installing = update.firmware_installing || update.state === 'checking' || update.state === 'installing';
    return html`<div class="haui-update-sidebar">
      <section class="haui-surface haui-update-overview">
        ${this._renderStatus(updateSummary(update))}
        ${this._renderVersions({
          status, info, update, requiredTft, updatesEnabled,
          installDisabled: installing || this._actionBusy,
        })}
        ${this._renderCheckAction(updatesEnabled)}
      </section>
      ${this._renderScheduled(update)}
      ${updateProgress({ progress: update.firmware_progress, label: t('Firmware update') })}
      ${updateProgress({ progress: update.tft_progress, label: t('Display update') })}
      ${this._renderRetry(update)}
      ${this._checkError ? html`<p class="haui-update-error">${this._checkError}</p>` : nothing}
      ${this._renderSettings()}
      ${this._picker ? this._renderPicker(this.deviceName, requiredTft, update) : nothing}
    </div>`;
  }
}

customElements.define('nspanel-updates-sidebar', UpdatesSidebar);
