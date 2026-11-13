/**
 * NSPanel HAUI - the Logs sidebar's body.
 *
 * The hub's recent log lines of one device, or of every device (Fleet), newest
 * first and grouped by day, with a level filter, a search and Copy. The sidebar
 * frame carries the title and the close control.
 */
import { css, html, nothing } from '../lit-import.js';
import { HauiDialog } from './haui-dialog.js';
import { currentLanguage, t } from '../localize.js';
import { icon } from '../ui/icon.js';
import { iconButton } from '../ui/button.js';
import { parseEvent } from '../ui/event-list.js';
import { emptyState } from '../ui/empty-state.js';

/**
 * @typedef {{ line: string, deviceName: string, timestamp: string, level: string,
 *   message: string, time: Date|null }} LogEntry
 */

/**
 * Parse the hub's lines, newest first.
 * @param {Array<string|{ line: string, deviceName?: string }>} logs - oldest first
 * @returns {LogEntry[]}
 */
export function logEntries(logs) {
  return logs.map((entry) => {
    const { line, deviceName = '' } = typeof entry === 'string' ? { line: entry } : entry;
    const parsed = parseEvent(line);
    const time = parsed.timestamp ? new Date(parsed.timestamp) : null;
    return {
      ...parsed,
      line,
      deviceName,
      level: parsed.level === 'warn' ? 'warning' : parsed.level,
      time: time && !Number.isNaN(time.getTime()) ? time : null,
    };
  }).reverse();
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
  static styles = [...HauiDialog.styles, css`
    :host { display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
    .haui-logs-tools { display: grid; flex: 0 0 auto; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
    .haui-logs-search-row { display: flex; align-items: center; gap: 4px; }
    .haui-logs-search {
      display: flex; flex: 1 1 auto; align-items: center; gap: 8px; min-width: 0; min-height: 38px;
      padding: 0 12px; border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill);
      background: var(--haui-surface-soft); color: var(--secondary-text-color); --mdc-icon-size: 18px;
    }
    .haui-logs-search:focus-within { border-color: var(--primary-color); }
    .haui-logs-search input {
      flex: 1 1 auto; min-width: 0; border: 0; outline: 0; background: transparent;
      color: var(--primary-text-color); font: inherit; font-size: var(--haui-text-label);
    }
    .haui-logs-search-row .haui-icon-button { flex: 0 0 auto; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
    .haui-logs-filter { display: flex; flex-wrap: wrap; gap: 4px; }
    .haui-logs-filter button {
      display: inline-flex; align-items: center; gap: 4px; min-height: 30px; padding: 0 4px 0 12px;
      border: 1px solid var(--divider-color); border-radius: var(--haui-radius-pill); background: transparent;
      color: var(--secondary-text-color); font: inherit; font-size: var(--haui-text-caption); cursor: pointer;
    }
    .haui-logs-filter button:hover { background: var(--haui-surface-soft); }
    .haui-logs-filter button[aria-pressed="true"] {
      border-color: var(--primary-color); color: var(--primary-text-color);
      background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color));
    }
    .haui-logs-count {
      min-width: 18px; padding: 4px 4px; border-radius: var(--haui-radius-pill); background: var(--haui-surface-soft);
      font-size: var(--haui-text-caption); font-variant-numeric: tabular-nums; text-align: center;
    }
    .haui-logs-count.is-warning { background: var(--haui-warn-soft); color: var(--haui-warn); }
    .haui-logs-count.is-error { background: var(--haui-bad-soft); color: var(--haui-bad); }
    .haui-logs-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding-bottom: 12px; }
    .haui-logs-list h3 {
      position: sticky; top: 0; z-index: 1; margin: 0; padding: 8px 16px 4px;
      border-bottom: 1px solid var(--divider-color); background: var(--card-background-color);
      color: var(--secondary-text-color); font-size: var(--haui-text-caption); font-weight: 600;
    }
    .haui-logs-list ol { margin: 0; padding: 0; list-style: none; }
    .haui-log {
      display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px;
      padding: 8px 16px 8px 12px; border-inline-start: 3px solid transparent;
      font-size: var(--haui-text-label); line-height: 1.45;
    }
    .haui-log + .haui-log { border-top: 1px solid color-mix(in srgb, var(--divider-color) 55%, transparent); }
    .haui-log time {
      color: var(--secondary-text-color); font-family: var(--haui-mono); font-size: var(--haui-text-caption);
      font-variant-numeric: tabular-nums; line-height: 1.65;
    }
    .haui-log p { min-width: 0; margin: 0; overflow-wrap: anywhere; }
    .haui-log-text { white-space: pre-wrap; }
    .haui-log-tag {
      display: inline-block; margin-inline-end: 4px; padding: 0 4px; border-radius: var(--haui-radius-control);
      font-size: var(--haui-text-eyebrow); font-weight: 600; letter-spacing: .03em; line-height: 1.6;
      text-transform: uppercase; vertical-align: 1px;
    }
    .haui-log-device { margin-inline-end: 4px; color: var(--secondary-text-color); font-weight: 500; }
    .haui-log-warning { border-inline-start-color: var(--haui-warn); background: color-mix(in srgb, var(--haui-warn) 7%, transparent); }
    .haui-log-warning .haui-log-tag { background: var(--haui-warn-soft); color: var(--haui-warn); }
    .haui-log-error { border-inline-start-color: var(--haui-bad); background: color-mix(in srgb, var(--haui-bad) 8%, transparent); }
    .haui-log-error .haui-log-tag { background: var(--haui-bad-soft); color: var(--haui-bad); }
    .haui-log-debug .haui-log-text { color: var(--secondary-text-color); }
    .haui-log-debug .haui-log-tag { background: var(--haui-surface-soft); color: var(--secondary-text-color); }
  `];

  static get properties() {
    return {
      // Hub log lines, oldest first, or `{ line, deviceName }` when several devices are listed.
      logs: { type: Array },
      _level: { state: true },
      _query: { state: true },
    };
  }

  constructor() {
    super();
    this.logs = [];
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

  _renderFilter(entries) {
    const count = (level) => entries.filter((entry) => entry.level === level).length;
    const options = [
      { value: 'all', label: t('All'), count: entries.length, tone: '' },
      { value: 'warning', label: t('Warnings'), count: count('warning'), tone: 'is-warning' },
      { value: 'error', label: t('Errors'), count: count('error'), tone: 'is-error' },
    ];
    return html`<div class="haui-logs-filter" role="group" aria-label=${t('Log level')}>
      ${options.map((option) => html`<button type="button" aria-pressed=${String(this._level === option.value)}
        @click=${() => { this._level = option.value; }}>
        <span>${option.label}</span>
        <span class=${`haui-logs-count ${option.count ? option.tone : ''}`}>${option.count}</span>
      </button>`)}
    </div>`;
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
    const entries = logEntries(this.logs);
    const visible = filterLogEntries(entries, this._level, this._query);
    return html`<div class="haui-logs-tools">
        <div class="haui-logs-search-row">
          <label class="haui-logs-search">
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
