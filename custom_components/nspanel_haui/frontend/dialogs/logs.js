/**
 * NSPanel HAUI - the Logs sidebar's body.
 *
 * The hub's recent log lines of every device or of the one its device selector
 * names, newest first and grouped by day, with a level filter, a search and Copy.
 * The same on Fleet and on a device, which only preselects itself. The sidebar
 * frame carries the title and the close control.
 */
import { html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { logsStyles } from '../styles/logs-styles.js';
import { currentLanguage, t } from '../localize.js';
import { icon } from '../ui/icon.js';
import { iconButton } from '../ui/button.js';
import { segmented } from '../ui/segmented.js';
import { parseEvent } from '../ui/event-list.js';
import { emptyState } from '../ui/empty-state.js';

/**
 * @typedef {{ line: string, device: string, deviceName: string, timestamp: string,
 *   level: string, message: string, time: Date|null }} LogEntry
 */

/**
 * Parse the hub's lines, newest first.
 * @param {Array<string|{ line: string, device?: string, deviceName?: string }>} logs - oldest
 *   first; `device` is the device's node name, `deviceName` the name shown
 * @returns {LogEntry[]}
 */
export function logEntries(logs) {
  return logs.map((entry) => {
    const { line, device = '', deviceName = '' } = typeof entry === 'string' ? { line: entry } : entry;
    const parsed = parseEvent(line);
    const time = parsed.timestamp ? new Date(parsed.timestamp) : null;
    return {
      ...parsed,
      line,
      device,
      deviceName,
      level: parsed.level === 'warn' ? 'warning' : parsed.level,
      time: time && !Number.isNaN(time.getTime()) ? time : null,
    };
  }).reverse();
}

/**
 * The entries of the selected device, without its name on every line, or every
 * device's with theirs.
 * @param {LogEntry[]} entries
 * @param {string} device - a device's node name, or '' for every device
 */
export function deviceLogEntries(entries, device) {
  if (!device) return entries;
  return entries.filter((entry) => entry.device === device).map((entry) => ({ ...entry, deviceName: '' }));
}

/**
 * The entries a level and a search leave; the search also matches the device.
 * @param {LogEntry[]} entries
 * @param {string} level - 'all' or a level name
 * @param {string} query
 */
export function filterLogEntries(entries, level, query) {
  const needle = query.trim().toLowerCase();
  return entries.filter((entry) => (level === 'all' || entry.level === level)
    && (!needle || `${entry.deviceName} ${entry.message}`.toLowerCase().includes(needle)));
}

/**
 * The entries as Copy writes them: oldest first, each the hub's own line with
 * its full timestamp, and the device in front of the message when several are listed.
 * @param {LogEntry[]} entries - newest first
 */
export function logText(entries) {
  return entries.slice().reverse().map((entry) => {
    const message = entry.deviceName ? `${entry.deviceName}: ${entry.message}` : entry.message;
    return entry.timestamp ? `[${entry.timestamp}] ${entry.level.toUpperCase()} ${message}` : message;
  }).join('\n');
}

/** @param {LogEntry[]} entries - consecutive entries of one calendar day form a group */
function byDay(entries) {
  /** @type {Array<{ key: string, time: Date|null, entries: LogEntry[] }>} */
  const groups = [];
  for (const entry of entries) {
    const key = entry.time ? entry.time.toDateString() : '';
    if (groups.at(-1)?.key !== key) groups.push({ key, time: entry.time, entries: [] });
    groups.at(-1).entries.push(entry);
  }
  return groups;
}

const LEVEL_TAGS = () => ({ warning: t('Warning'), error: t('Error'), debug: t('Debug') });

class LogsSidebar extends HauiDialog {
  static styles = [...HauiDialog.styles, logsStyles];

  static get properties() {
    return {
      // Every device's hub log lines, oldest first: `{ line, device, deviceName }`.
      logs: { type: Array },
      // The devices to choose from: `{ name, label }`.
      devices: { type: Array },
      // The selected device's node name, or '' for every device.
      device: { type: String },
      _level: { state: true },
      _query: { state: true },
    };
  }

  constructor() {
    super();
    this.logs = [];
    this.devices = [];
    this.device = '';
    this._level = 'all';
    this._query = '';
  }

  /** @param {LogEntry[]} entries */
  _copy(entries) {
    this._emit('copy-logs', { text: logText(entries) });
  }

  /** Escape clears a search first; the sidebar closes on the next one. */
  _onSearchKey(event) {
    if (event.key !== 'Escape' || !this._query) return;
    event.preventDefault();
    this._query = '';
  }

  /**
   * An icon in front of the search; the native select lies invisibly over it,
   * so the browser's own list opens. The icon and its tint change when one
   * device is selected, and the title names it.
   */
  _renderDevices() {
    const selected = this.devices.find((device) => device.name === this.device);
    return html`<label class=${`haui-logs-device ${selected ? 'is-filtered' : ''}`.trim()}
      title=${selected ? selected.label : t('All devices')}>
      ${icon(selected ? 'screen' : 'devices')}
      <select aria-label=${t('Device')} .value=${this.device}
        @change=${(event) => this._emit('device-selected', { device: event.currentTarget.value })}>
        <option value="" ?selected=${!this.device}>${t('All devices')}</option>
        ${this.devices.map((device) => html`<option value=${device.name}
          ?selected=${device.name === this.device}>${device.label}</option>`)}
      </select>
    </label>`;
  }

  _renderFilter(entries) {
    const count = (level) => entries.filter((entry) => entry.level === level).length;
    const warnings = count('warning');
    const errors = count('error');
    return segmented({
      label: t('Log level'),
      value: this._level,
      options: [
        { value: 'all', label: t('All'), count: entries.length },
        { value: 'warning', label: t('Warnings'), count: warnings, tone: warnings ? 'warning' : 'neutral' },
        { value: 'error', label: t('Errors'), count: errors, tone: errors ? 'danger' : 'neutral' },
      ],
      onSelect: (level) => { this._level = level; },
    });
  }

  /** @param {LogEntry} entry */
  _renderEntry(entry) {
    const language = currentLanguage();
    const tag = LEVEL_TAGS()[entry.level];
    return html`<li class=${`haui-log haui-log-${entry.level}`}>
      <time datetime=${entry.timestamp || nothing}
        title=${entry.time ? entry.time.toLocaleString(language) : nothing}>${entry.time
          ? entry.time.toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : '--:--:--'}</time>
      <p>${tag ? html`<span class="haui-log-tag">${tag}</span>` : nothing}${entry.deviceName ? html`<span class="haui-log-device">${entry.deviceName}</span>` : nothing}<span class="haui-log-text">${entry.message}</span></p>
    </li>`;
  }

  _renderList(entries, visible) {
    if (!entries.length) return emptyState({ message: t('No log entries yet.'), iconName: null, className: 'haui-empty-state-compact' });
    if (!visible.length) return emptyState({ message: t('No log entries match.'), iconName: null, className: 'haui-empty-state-compact' });
    const language = currentLanguage();
    return byDay(visible).map((group) => html`<section>
      ${group.time ? html`<h3>${group.time.toLocaleDateString(language, { weekday: 'long', day: 'numeric', month: 'long' })}</h3>` : nothing}
      <ol>${group.entries.map((entry) => this._renderEntry(entry))}</ol>
    </section>`);
  }

  render() {
    if (!this.open) return nothing;
    const entries = deviceLogEntries(logEntries(this.logs), this.device);
    const visible = filterLogEntries(entries, this._level, this._query);
    return html`<div class="haui-logs-tools">
        <div class="haui-logs-search-row">
          ${this._renderDevices()}
          <label class="haui-search-field haui-logs-search">
            ${icon('search')}
            <input type="search" .value=${this._query} placeholder=${t('Search logs')}
              aria-label=${t('Search logs')}
              @input=${(event) => { this._query = event.currentTarget.value; }}
              @keydown=${this._onSearchKey}>
          </label>
          ${iconButton({
            label: t('Copy logs'), iconName: 'content-copy', disabled: !visible.length,
            onClick: () => this._copy(visible),
          })}
        </div>
        ${this._renderFilter(entries)}
      </div>
      <div class="haui-logs-list">${this._renderList(entries, visible)}</div>`;
  }
}

customElements.define("nspanel-logs-sidebar", LogsSidebar);
