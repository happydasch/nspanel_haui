// @ts-check
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { countBadge } from './badge.js';
import { relativeTime } from './format.js';
import { icon } from './icon.js';
import { button } from './button.js';
import { emptyState } from './empty-state.js';
import { sectionHeading } from './surface.js';

/** Parse a hub log record without assuming it has a timestamp or level. */
export function parseEvent(line) {
  // `s`: a message can span lines (an exception, a template error).
  const match = /^\[(.*?)\]\s+(INFO|WARNING|WARN|ERROR|DEBUG)\s+(.*)$/is.exec(String(line || ''));
  return match
    ? { timestamp: match[1], level: match[2].toLowerCase(), message: match[3] }
    : { timestamp: '', level: 'info', message: String(line || '') };
}

/**
 * Order the log lines of several devices by time, oldest first; a line
 * without a readable timestamp sorts before every dated one.
 * @template {{ line: string }} T
 * @param {T[]} events
 * @returns {T[]}
 */
export function eventsByTime(events) {
  return events
    .map((event) => ({ event, time: Date.parse(parseEvent(event.line).timestamp) || 0 }))
    .sort((a, b) => a.time - b.time)
    .map(({ event }) => event);
}

/**
 * What Latest events lists: newest first, without debug lines, and a message
 * a device repeats once, with its count and its newest time. The hub writes some
 * warnings on every render (an entity that does not exist), which would
 * otherwise fill the list with one line.
 * @template {{ line: string, deviceName?: string }} T
 * @param {T[]} events - in any order
 * @param {number} [limit] - how many different events to keep
 * @returns {Array<T & { count: number }>}
 */
export function latestEvents(events, limit = 8) {
  /** @type {Map<string, T & { count: number }>} */
  const latest = new Map();
  for (const event of eventsByTime(events).reverse()) {
    const { level, message } = parseEvent(event.line);
    if (level === 'debug') continue;
    const key = `${event.deviceName || ''}\n${level}\n${message}`;
    const seen = latest.get(key);
    if (seen) seen.count += 1;
    else if (latest.size < limit) latest.set(key, { ...event, count: 1 });
  }
  return [...latest.values()];
}

const LEVEL_ICONS = Object.freeze({
  error: 'alert', warning: 'alert', warn: 'alert', debug: 'bug-outline',
});

/** Render the latest real device log entries as a timeline. */
/** @param {{ events: Array<{ line: string, deviceName?: string, count?: number }>, deviceName?: string, onOpenLogs?: () => void }} data */
export function eventList({ events, deviceName, onOpenLogs }) {
  return html`<section class="haui-event-list">
    <header>${sectionHeading({
      title: t('Latest events'),
      className: 'haui-section-heading',
      badge: events.length ? countBadge(events.length) : nothing,
    })}
      ${onOpenLogs ? button({
        label: t('Logs'), variant: 'quiet', className: 'haui-event-logs', onClick: onOpenLogs,
      }) : nothing}
    </header>
    ${events.length ? html`<ol>
      ${events.map((event) => {
        const parsed = parseEvent(event.line);
        const level = parsed.level === 'warning' ? 'warn' : parsed.level;
        const device = event.deviceName || deviceName || '';
        const count = event.count || 1;
        // An exception's traceback belongs in Logs; the timeline keeps its first line.
        return html`<li class=${`haui-event-${level}`}>
          <span class="haui-event-node">${icon(LEVEL_ICONS[level] || 'info')}</span>
          <div class="haui-event-copy"><p>${parsed.message.split('\n')[0]}</p>
            <div class="haui-event-meta">${device ? html`<span class="haui-event-device">${device}</span>` : nothing}<time datetime=${parsed.timestamp || ''}>${
              parsed.timestamp ? relativeTime(parsed.timestamp) : t('Unknown')}</time>${count > 1
              ? html`<span class="haui-event-repeat" title=${t('Repeated {count} times').replace('{count}', String(count))}>×${count}</span>`
              : nothing}</div></div>
        </li>`;
      })}
    </ol>` : emptyState({ title: t('No events yet'), iconName: 'check', className: 'haui-empty-state-horizontal' })}
  </section>`;
}
