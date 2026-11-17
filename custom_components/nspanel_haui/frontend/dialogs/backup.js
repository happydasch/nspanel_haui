/**
 * NSPanel HAUI - the Backups sidebar's body.
 *
 * The device's YAML backup, one card per direction: **Export** writes its
 * settings and panels to a file, **Import** replaces them with a file's. The
 * sidebar frame carries the title and the close control.
 */
import { html } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { backupStyles } from '../styles/backup-styles.js';
import { t } from '../localize.js';
import { button } from '../ui/button.js';
import { surface } from '../ui/surface.js';

class BackupSidebar extends HauiDialog {
  static styles = [...HauiDialog.styles, backupStyles];

  render() {
    if (!this.open) return '';
    return html`<div class="haui-backup-sidebar">${surface({
      title: t('Export'),
      subtitle: t('Save this device’s settings and panels to a YAML file.'),
      body: button({
        label: t('Export'), iconName: 'file',
        onClick: () => this._emit('backup-export'),
      }),
    })}${surface({
      title: t('Import'),
      subtitle: t('Restore a YAML backup on this hub, replacing the settings and panels this device has now.'),
      body: html`<p class="haui-backup-note">${t('There is no undo: export first if you want to keep the current setup.')}</p>${
        button({ label: t('Import'), iconName: 'upload', onClick: () => this._emit('backup-import') })}`,
    })}</div>`;
  }
}

customElements.define('nspanel-backup-sidebar', BackupSidebar);
