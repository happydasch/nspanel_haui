/**
 * NSPanel HAUI - the Backups sidebar's body.
 *
 * The device's backup and its copies: **Backup file** keeps the device's
 * settings and panels in one YAML file, one card holding **Export** and
 * **Import** as a single pair of buttons with one note under them, because both
 * work on the same file; **Copy to other devices** is a card of its own, writing
 * the parts picked onto other devices of the hub. Both directions replace what
 * is there, so each card says so in a warning banner. The sidebar frame carries
 * the title and the close control.
 */
import { html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { backupStyles } from '../styles/backup-styles.js';
import { t } from '../localize.js';
import { countBadge } from '../ui/badge.js';
import { button } from '../ui/button.js';
import { choiceList } from '../ui/choice-list.js';
import { emptyState } from '../ui/empty-state.js';
import { surface } from '../ui/surface.js';

/** The parts of a device a copy can take. */
const COPY_SECTIONS = () => [
  {
    key: 'settings',
    label: t('Device settings'),
    hint: t('Language, screen, sounds, buttons, gestures and the theme'),
    iconName: 'settings',
  },
  {
    key: 'panels',
    label: t('Panels'),
    hint: t('Every panel of this device, in its order'),
    iconName: 'panels',
  },
  {
    key: 'update',
    label: t('Update settings'),
    hint: t('The update channel and its automatic installs'),
    iconName: 'refresh',
  },
];

/** A copy starts with what makes a device look like this one. */
const DEFAULT_SECTIONS = Object.freeze(['settings', 'panels']);

/**
 * The warning both directions carry: what an import or a copy replaces, as the
 * banner Home Assistant shows its warnings in, so a destructive direction is
 * read as a warning rather than as another line of the card.
 * @param {string} message
 * @param {string} [id] - the id a control points at with aria-describedby
 */
function warningBanner(message, id) {
  return html`<ha-alert alert-type="warning" id=${id || nothing}>${message}</ha-alert>`;
}

class BackupSidebar extends HauiDialog {
  static styles = [...HauiDialog.styles, backupStyles];

  static get properties() {
    return {
      // The device the sidebar belongs to, which a copy reads.
      deviceName: { type: String },
      // That device's friendly name, which the copy card names.
      sourceLabel: { type: String },
      // The hub's other devices, which a copy writes: `{ name, label }`.
      devices: { type: Array },
      entryId: { type: String },
      api: { type: Object },
      _sections: { type: Array, state: true },
      _targets: { type: Array, state: true },
      _busy: { type: Boolean, state: true },
      _error: { type: String, state: true },
    };
  }

  constructor() {
    super();
    this.deviceName = '';
    this.sourceLabel = '';
    this.devices = [];
    this.entryId = null;
    this.api = null;
    this._sections = [...DEFAULT_SECTIONS];
    this._targets = [];
    this._busy = false;
    this._error = '';
  }

  /** A sidebar left open while the screen changes device copies the new one. */
  willUpdate(changed) {
    if (!changed.has('deviceName')) return;
    this._targets = [];
    this._error = '';
  }

  /**
   * A section or a device joins or leaves the copy.
   * @param {'_sections'|'_targets'} field
   * @param {string} value
   * @param {boolean} picked
   */
  _pick(field, value, picked) {
    const kept = this[field].filter((entry) => entry !== value);
    this[field] = picked ? [...kept, value] : kept;
  }

  /** Pick every other device at once, or clear the pick again. */
  _pickAll(pick) {
    this._targets = pick ? this.devices.map((device) => device.name) : [];
  }

  async _copy() {
    if (this._busy || !this._sections.length || !this._targets.length) return;
    if (!this.api || !this.entryId || !this.deviceName) return;
    this._busy = true;
    this._error = '';
    try {
      const result = await this.api.devices.copy(
        this.entryId, this.deviceName, this._targets, this._sections,
      );
      this._targets = [];
      this._emit('backup-copied', { devices: result?.devices || [] });
    } catch (error) {
      this._error = error.message || t('Copy failed');
    } finally {
      this._busy = false;
    }
  }

  /** The YAML file: Export and Import as one pair of buttons, one banner below. */
  _renderFile() {
    return surface({
      title: t('Backup file'),
      subtitle: t('Downloads this device’s settings and panels as a YAML file.'),
      body: html`<div class="haui-backup-actions">
        ${button({ label: t('Export'), iconName: 'file', onClick: () => this._emit('backup-export') })}
        ${button({
          label: t('Import'),
          iconName: 'upload',
          id: 'backup-import',
          describedBy: 'backup-import-hint',
          onClick: () => this._emit('backup-import'),
        })}
      </div>
      ${warningBanner(t('Replaces what this device has now. There is no undo.'), 'backup-import-hint')}`,
    });
  }

  /** The parts a copy takes, each with what it carries. */
  _renderSections() {
    return choiceList({
      id: 'backup-sections',
      label: t('What to copy'),
      badge: countBadge(this._sections.length, { title: t('Parts to copy') }),
      choices: COPY_SECTIONS().map((section) => ({
        ...section, checked: this._sections.includes(section.key),
      })),
      onToggle: (key, picked) => this._pick('_sections', key, picked),
    });
  }

  /** The devices a copy writes; one action picks them all or clears them. */
  _renderTargets() {
    const all = this.devices.length > 0 && this._targets.length === this.devices.length;
    return choiceList({
      id: 'backup-targets',
      label: t('To devices'),
      badge: countBadge(this._targets.length, { title: t('Devices to copy to') }),
      actions: this.devices.length > 1
        ? button({
          label: all ? t('Clear') : t('Select all'),
          variant: 'quiet',
          onClick: () => this._pickAll(!all),
        })
        : nothing,
      choices: this.devices.map((device) => ({
        key: device.name, label: device.label, checked: this._targets.includes(device.name),
      })),
      onToggle: (key, picked) => this._pick('_targets', key, picked),
    });
  }

  /** What the pick will do, and the reason Copy is off while it cannot run. */
  _renderSummary() {
    if (!this._sections.length) return t('Pick at least one part to copy.');
    if (!this._targets.length) return t('Pick at least one device to copy to.');
    const parts = COPY_SECTIONS()
      .filter((section) => this._sections.includes(section.key))
      .map((section) => section.label)
      .join(' + ');
    return t('Copied to the devices below: {parts}').replace('{parts}', parts);
  }

  /** The card's subtitle: whose copy this is, when the sidebar knows it. */
  _copySubtitle() {
    if (!this.sourceLabel) return nothing;
    return t('Writes {source}’s settings and panels onto other devices on this hub.')
      .replace('{source}', this.sourceLabel);
  }

  /** The copy's own card: what it takes, where it goes, what the pick does. */
  _renderCopy() {
    return surface({
      title: t('Copy to other devices'),
      subtitle: this._copySubtitle(),
      body: this.devices.length
        ? html`${this._renderSections()}${this._renderTargets()}
            <p class="haui-backup-note" role="status">${this._renderSummary()}</p>
            ${warningBanner(t('What you pick replaces it on every device you choose; there is no undo.'))}
            ${this._error ? html`<p class="haui-backup-error" role="alert">${this._error}</p>` : nothing}
            ${button({
              label: t('Copy'),
              iconName: 'content-copy',
              variant: 'primary',
              disabled: !this._sections.length || !this._targets.length,
              busy: this._busy,
              onClick: () => this._copy(),
            })}`
        : emptyState({
          iconName: 'devices',
          title: t('No other device'),
          message: t('This hub has no other device to copy to.'),
        }),
    });
  }

  render() {
    if (!this.open) return nothing;
    return html`<div class="haui-backup-sidebar">${this._renderFile()}${this._renderCopy()}</div>`;
  }
}

customElements.define('nspanel-backup-sidebar', BackupSidebar);
