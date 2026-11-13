/**
 * NSPanel HAUI - the firmware/display update surface.
 *
 * The Updates sidebar's body; it owns every update concern: version rows, the
 * check action and the install picker (release / URL / local file). The sidebar
 * frame carries the title and the close control. Device facts and diagnostics
 * live in the Device side stack.
 */
import { html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { t } from '../localize.js';
import { hasUpdateAvailable } from '../device-status.js';
import { DEFAULT_FIRMWARE_MANIFEST_URL, FIRMWARE_UPDATE_CHANNELS } from '../constants.js';
import { renderNumberInput, renderSelect, renderToggle } from '../form-fields.js';
import { badge } from '../ui/badge.js';
import { segmented } from '../ui/segmented.js';
import { updateOfferLabel, versionLabel } from '../ui/format.js';
import { icon } from '../ui/icon.js';
const UPDATE_INTERVAL_PRESETS = [900, 1800, 3600, 7200, 21600, 43200, 86400, 604800];
function updateIntervalLabel(value) {
  switch (value) {
    case 900: return t('Every 15 minutes');
    case 1800: return t('Every 30 minutes');
    case 3600: return t('Every hour');
    case 7200: return t('Every 2 hours');
    case 21600: return t('Every 6 hours');
    case 43200: return t('Every 12 hours');
    case 86400: return t('Every day');
    case 604800: return t('Every week');
    default: throw new Error(`Unknown update interval preset: ${value}`);
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
function versionRow({ iconName, label, version, note, offered, disabled, onInstall }) {
  return html`<div class="haui-firmware-row">
    <dt>
      <span class="haui-firmware-row-icon">${icon(iconName)}</span>
      <span class="haui-firmware-row-name">${label}${offered
        ? badge(t('Update available'), 'warning') : nothing}${note ? html`<small>${note}</small>` : nothing}</span>
    </dt>
    <dd>
      <span class="haui-firmware-row-version">${versionLabel(version)}</span>
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

/** Read a stored update option while preserving the UI's display defaults. */
function settingValue(settings, key, fallback) {
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
 * One update preference: what it does on the left, its switch on the right.
 * `checked` stands in for the stored value where a control maps onto it (an
 * interval of 0 reads as "periodic checks off").
 */
function updateRow(host, { id, key, settings, label, hint = '', fallback = true, checked, mapValue }) {
  return html`<div class="haui-update-row">
    <div class="haui-update-row-copy">
      <label class="haui-update-row-label" for=${id}>${label}</label>
      ${hint ? html`<p class="haui-update-row-hint">${hint}</p>` : nothing}
    </div>
    ${renderToggle(id, checked ?? Boolean(settingValue(settings, key, fallback)),
      (next) => setSetting(host, key, mapValue ? mapValue(next) : next))}
  </div>`;
}

class FirmwarePopover extends HauiDialog {
  static get properties() {
    return {
      deviceStatus: { type: Object },
      deviceName: { type: String },
      entryId: { type: String },
      api: { type: Object },
      config: { type: Object },
      _settingsDraft: { type: Object, state: true },
      _customIntervalSelected: { type: Boolean, state: true },
      _picker: { type: Object, state: true },
      _popoverError: { type: String, state: true },
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
    this._customIntervalSelected = false;
    this._settingsInitial = null;
    this._settingsDevice = null;
    this._settingsSaveTimer = null;
    this._picker = null;
    this._popoverError = null;
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
    if (deviceChanged) this._customIntervalSelected = false;
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
    this._popoverError = null;
    try {
      await this.api.updates.check(this.entryId, this.deviceName);
      this._emit('update-check');
    } catch (error) {
      this._popoverError = error.message || t('Failed to check for updates');
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
      return html`<div class="device-update-picker">${t('Updates are disabled for this device.')}</div>`;
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
      <div class="device-update-picker" @click=${(e) => e.stopPropagation()}>
        <div class="form-group">
          <label for="di-install-source">${tft ? t('TFT to install') : t('Firmware to install')}</label>
          ${renderSelect(
            'di-install-source',
            choice,
            options,
            (value) => this._updatePicker({ choice: value, file: null, error: '' }),
            { disabled: uploading },
          )}
          ${releases === null ? html`<div class="field-hint">${t('Loading releases…')}</div>` : ''}
          ${releasesError
            ? html`<div class="field-hint">${t('Releases unavailable: {error}').replace('{error}', releasesError)}</div>`
            : ''}
        </div>
        ${choice === 'url' ? html`
          <div class="form-group">
            <label for="di-install-url">${tft ? t('TFT file URL') : t('Firmware OTA image URL')}</label>
            <input
              id="di-install-url"
              class="native-input"
              type="url"
              .value=${url}
              @input=${(e) => this._updatePicker({ url: e.target.value, error: '' })}
            />
          </div>
        ` : ''}
        ${choice === 'file' ? html`
          <div class="form-group">
            <label for="di-install-file">${tft ? t('Local TFT file') : t('Local firmware OTA image')}</label>
            <input
              id="di-install-file"
              class="native-input"
              type="file"
              accept=${tft ? '.tft' : '.bin'}
              ?disabled=${uploading}
              @change=${(e) => this._updatePicker({ file: e.target.files?.[0] || null, error: '' })}
            />
            <div class="field-hint">
              ${t('The file is uploaded to Home Assistant and must be reachable by the device.')}
            </div>
          </div>
        ` : ''}
        ${uploading ? html`<div class="field-hint">${t('Uploading local update file…')}</div>` : ''}
        <div class="field-hint">${tft
          ? t('Another release, URL or local file stays on the display until the firmware version changes or Home Assistant restarts.')
          : t('Another release, URL or local file pauses automatic firmware updates until Home Assistant restarts. Use the OTA image (nspanel_haui_ota.bin), not the factory image.')}</div>
        ${error ? html`<p class="device-update-error">${error}</p>` : ''}
        <div class="device-update-actions">
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

  /** The lead card: what the device's updates are doing, and the check action. */
  _renderStatus(summary, updatesEnabled) {
    return html`<section class=${`haui-firmware-hero haui-firmware-status-${summary.tone}`}>
      <div class="haui-firmware-hero-body" role="status">
        <span class="haui-firmware-status-icon">${icon(summary.iconName)}</span>
        <div class="haui-firmware-hero-copy">
          <strong>${summary.title}</strong>
          ${summary.detail ? html`<p>${summary.detail}</p>` : nothing}
        </div>
      </div>
      ${updatesEnabled ? html`<button type="button" class="haui-firmware-hero-action"
        ?disabled=${this._actionBusy} @click=${this._checkForUpdates}>
        ${icon('refresh')}<span>${this._actionBusy ? t('Checking…') : t('Check for updates')}</span>
      </button>` : nothing}
    </section>`;
  }

  /** The installed versions, one row each, with what the release offers. */
  _renderVersions({ status, info, update, requiredTft, updatesEnabled, installDisabled }) {
    return html`<dl class="haui-surface haui-firmware-versions">
      ${versionRow({
        iconName: 'info', label: t('Integration'), version: status.integration_version,
      })}
      ${versionRow({
        iconName: 'chip', label: t('Firmware'), version: info.yaml_version,
        note: update.firmware_update_version
          ? t('Latest release: {version}').replace('{version}', update.firmware_update_version) : '',
        offered: update.firmware_update_available,
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

  /** The master switch, on its own strip under the card's heading. */
  _renderMaster(settings) {
    return html`<div class="haui-update-master">
      <div class="haui-update-row-copy">
        <label class="haui-update-row-label" for="update-enabled">${t('Enable updates')}</label>
        <p class="haui-update-row-hint">${t('When off, checks, update entities, and manual firmware/display installs are disabled. An update already in progress will finish.')}</p>
      </div>
      ${renderToggle('update-enabled', Boolean(settingValue(settings, 'enabled', true)),
        (checked) => setSetting(this, 'enabled', checked))}
    </div>`;
  }

  /** When the hub checks for releases, and how often. */
  _renderReleaseChecks(settings, interval) {
    return html`<section class="haui-update-group">
      <h3 class="haui-update-group-title">${icon('refresh')}${t('Release checks')}</h3>
      ${updateRow(this, {
        id: 'update-check-on-connect', key: 'check_on_connect', settings,
        label: t('Check for updates on connect'),
        hint: t('Run a release check after the device connects to Home Assistant.'),
      })}
      ${updateRow(this, {
        id: 'update-periodic-checks', key: 'update_interval', settings,
        label: t('Enable periodic update checks'),
        checked: interval > 0,
        mapValue: (checked) => {
          if (!checked) this._customIntervalSelected = false;
          return checked ? (interval > 0 ? interval : 3600) : 0;
        },
      })}
      ${interval > 0 ? html`<div class="haui-update-field">
        <label for="update-interval">${t('Check every')}</label>
        ${renderSelect('update-interval', this._customIntervalSelected
          || !UPDATE_INTERVAL_PRESETS.includes(interval)
          ? 'custom' : String(interval), [
          ...UPDATE_INTERVAL_PRESETS.map((value) => ({ value, label: updateIntervalLabel(value) })),
          { value: 'custom', label: t('Custom interval…') },
        ], (value) => {
          if (value === 'custom') {
            this._customIntervalSelected = true;
            this.requestUpdate();
            return;
          }
          this._customIntervalSelected = false;
          setSetting(this, 'update_interval', Number(value));
        })}
        ${this._customIntervalSelected
          || !UPDATE_INTERVAL_PRESETS.includes(interval)
          ? html`<div class="haui-update-field-control">
            <label for="update-custom-interval">${t('Custom interval (seconds)')}</label>
            ${renderNumberInput('update-custom-interval', interval, (raw) => {
              const value = parseInt(raw, 10);
              setSetting(this, 'update_interval', Number.isNaN(value) || value < 1 ? 1 : value, true);
            }, { min: 1, max: 604800 })}
          </div>` : nothing}
        <p class="haui-update-row-hint">${t('Choose how often to check for a newer release.')}</p>
      </div>` : nothing}
    </section>`;
  }

  /** The shared release channel used for firmware and display updates. */
  _renderUpdateChannel(settings, channel) {
    const manualUrl = Boolean(settings.firmware_manifest_url);
    return html`<div class="haui-update-channel">
      <h3 class="haui-update-group-title">${icon('download')}${t('Update channel')}</h3>
      <div class="haui-update-field">
        ${segmented({
          label: t('Update channel'),
          options: FIRMWARE_UPDATE_CHANNELS.map((value) => ({
            value, label: value === 'dev' ? t('Development') : t('Stable'),
          })),
          value: channel,
          onSelect: (value) => setSetting(this, 'firmware_update_channel', value),
        })}
        <p class="haui-update-row-hint">${t('Choose stable releases or published development builds. This channel applies to both firmware and display updates.')}</p>
      </div>
      <details class="haui-update-advanced" ?open=${manualUrl}>
        <summary>${t('Custom manifest URL')}${manualUrl ? html`<span class="haui-update-set">${t('Set')}</span>` : nothing}</summary>
        <div class="haui-update-field">
          <label for="update-firmware-manifest-url">${t('Firmware manifest URL')}</label>
          <input
            id="update-firmware-manifest-url"
            class="native-input"
            type="url"
            placeholder=${channel === 'dev' ? '' : DEFAULT_FIRMWARE_MANIFEST_URL}
            .value=${String(settingValue(settings, 'firmware_manifest_url', ''))}
            @input=${(event) => setSetting(this, 'firmware_manifest_url', event.target.value.trim() || undefined, true)}
          />
          <p class="haui-update-row-hint">${t('The manifest names the firmware the HAUI Firmware entity offers. Leave empty to follow the channel above; a URL here overrides it (e.g. point a test panel at the manifest of a local test release to follow test builds).')}</p>
        </div>
      </details>
    </div>`;
  }

  /** Groups the master switch with the release source it enables. */
  _renderUpdateSettings(settings, channel, enabled) {
    return html`<section class="haui-update-group haui-update-settings-group">
      ${this._renderMaster(settings)}
      ${enabled ? this._renderUpdateChannel(settings, channel)
        : html`<p class="haui-update-off-note">${t('Updates are disabled for this device.')}</p>`}
    </section>`;
  }

  /** Which firmware the hub follows, and whether it installs it by itself. */
  _renderFirmwareSettings(settings) {
    return html`<section class="haui-update-group">
      <h3 class="haui-update-group-title">${icon('chip')}${t('Firmware')}</h3>
      ${updateRow(this, {
        id: 'update-firmware-auto', key: 'firmware_auto_update', settings, fallback: false,
        label: t('Auto-install firmware updates'),
        hint: t('Install a newer firmware when the release ships one. The matching TFT follows after the device reboots.'),
      })}
    </section>`;
  }

  /** The display's TFT follows the firmware; this decides whether it asks. */
  _renderDisplaySettings(settings) {
    return html`<section class="haui-update-group">
      <h3 class="haui-update-group-title">${icon('monitor')}${t('Display')}</h3>
      ${updateRow(this, {
        id: 'update-auto-install-tft', key: 'auto_install', settings,
        label: t('Auto-install TFT updates'),
        hint: t('Replace an outdated display TFT automatically when the firmware needs a newer one. When off, the display asks first.'),
      })}
    </section>`;
  }

  _renderSettings() {
    if (!this.config) return nothing;
    const settings = this._settingsDraft || this.config.update || {};
    const enabled = Boolean(settingValue(settings, 'enabled', true));
    const interval = Number(settingValue(settings, 'update_interval', 3600));
    const channel = String(settingValue(settings, 'firmware_update_channel', 'stable'));
    return html`<section class="haui-surface haui-firmware-settings" aria-label=${t('Update settings')}>
      <header class="haui-update-header">
        <span class="haui-firmware-settings-icon">${icon('tune-variant')}</span>
        <div class="haui-update-header-copy">
          <h2>${t('Update settings')}</h2>
          <p>${t('Controls release checks and firmware/display updates for this device.')}</p>
        </div>
      </header>
      ${this._renderUpdateSettings(settings, channel, enabled)}
      ${enabled ? html`${this._renderReleaseChecks(settings, interval)}${
        this._renderFirmwareSettings(settings)}${this._renderDisplaySettings(settings)}`
      : nothing}
    </section>`;
  }

  render() {
    if (!this.open) return '';
    const status = this.deviceStatus;
    if (!status) {
      return html`<div class="haui-firmware-sidebar">${this._renderSettings()}</div>`;
    }
    const info = status.device_info || {};
    const update = status.update || {};
    const requiredTft = info.tft_required_version;
    const updatesEnabled = update.enabled !== false;
    const installing = update.firmware_installing || update.state === 'checking' || update.state === 'installing';
    return html`<div class="haui-firmware-sidebar">
      ${this._renderStatus(updateSummary(update), updatesEnabled)}
      ${this._renderVersions({
        status, info, update, requiredTft, updatesEnabled,
        installDisabled: installing || this._actionBusy,
      })}
      ${this._popoverError ? html`<p class="device-update-error">${this._popoverError}</p>` : nothing}
      ${this._renderSettings()}
      ${this._picker ? this._renderPicker(this.deviceName, requiredTft, update) : nothing}
    </div>`;
  }
}

customElements.define('nspanel-firmware-popover', FirmwarePopover);
