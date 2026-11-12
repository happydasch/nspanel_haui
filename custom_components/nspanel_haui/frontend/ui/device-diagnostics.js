// @ts-check
/**
 * NSPanel HAUI - device diagnostics for the Device side stack.
 *
 * The card has two states: a simple one (one status line) and an expanded one
 * (two status tiles, the preview's Show entities switch and tools, and the hub
 * details, which end with Copy report). Both are
 * plain render functions over the status payload the editor already polls; the
 * shell supplies the actions they can trigger.
 */
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { rssiStrengthClass, rssiBarCount, fmtRssi, isOlderVersion } from '../device-info.js';
import { relativeTime, uptimeLabel } from './format.js';
import { button } from './button.js';
import { icon } from './icon.js';
import { infoTile } from './info-tile.js';
import { deviceConnectionState } from '../device-status.js';

const LOG_PROBLEM = /^\[([^\]]*)\]\s+(WARNING|ERROR|CRITICAL)\b/;
// From this many drops in 24 hours the connection counts as an issue.
const UNSTABLE_DROPS = 3;
// Like the drops, a log warning older than a day is history, not an issue.
const LOG_WINDOW_MS = 86_400_000;

/** A WARNING or ERROR line of the last 24 hours; an undated one always counts. */
function recentLogProblem(/** @type {unknown} */ line, /** @type {number} */ now) {
  const match = typeof line === 'string' ? LOG_PROBLEM.exec(line) : null;
  if (!match) return false;
  const time = Date.parse(match[1]);
  return !Number.isFinite(time) || now - time <= LOG_WINDOW_MS;
}

/** "1 log warning" or "3 log warnings". */
function logWarnings(count) {
  return count === 1 ? t('1 log warning') : t('{count} log warnings').replace('{count}', String(count));
}

/** "1 disconnect in 24 h" or "3 disconnects in 24 h". */
function disconnects(count) {
  return count === 1 ? t('1 disconnect in 24 h') : t('{count} disconnects in 24 h').replace('{count}', String(count));
}

/** A duration in seconds as 45s / 12m / 1.5h; a missing value stays a dash. */
function fmtInterval(seconds) {
  if (seconds == null) return '-';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Number((seconds / 3600).toFixed(1))}h`;
}

/**
 * The readings both states show, derived once from the status payload.
 *
 * @param {any} status
 * @param {number} [now]
 */
export function diagnosticsModel(status, now = Date.now()) {
  const info = status?.device_info || {};
  const update = status?.update || {};
  const { connected } = deviceConnectionState(status);
  const logs = Array.isArray(status?.logs) ? status.logs : [];
  const logProblems = logs.filter((line) => recentLogProblem(line, now)).length;
  const requiredTft = info.tft_required_version;
  const tftPending = Boolean(info.tft_version && requiredTft && isOlderVersion(info.tft_version, requiredTft));
  const weakSignal = connected && rssiBarCount(info.rssi) === 1;
  const mismatch = status?.haui_version_mismatch === true;
  const updateFailed = update.state === 'error';
  const health = status?.connection_health || null;
  const drops = Number.isFinite(health?.drops_24h) ? health.drops_24h : 0;
  const unstable = drops >= UNSTABLE_DROPS;
  /** @type {{ key: string, label: string }[]} */
  const issues = [];
  if (!connected) issues.push({ key: 'offline', label: t('Offline') });
  if (mismatch) issues.push({ key: 'mismatch', label: t('Firmware does not match the hub') });
  if (updateFailed) issues.push({ key: 'update', label: t('Display update failed') });
  else if (tftPending) issues.push({ key: 'tft', label: t('Display update pending') });
  if (weakSignal) issues.push({ key: 'wifi', label: t('Weak Wi-Fi signal') });
  if (unstable) issues.push({ key: 'unstable', label: disconnects(drops) });
  if (logProblems) {
    issues.push({ key: 'logs', label: logWarnings(logProblems) });
  }
  return {
    info, update, connected, logs, logProblems, tftPending, weakSignal, mismatch, updateFailed, issues,
    health, drops, unstable,
    uptime: connected && Number.isFinite(info.connection_uptime) ? info.connection_uptime : null,
  };
}

/** The header icon: a check for "All good", or an alert with the issue count and the issues as its tooltip. */
export function diagnosticsIcon(/** @type {ReturnType<typeof diagnosticsModel>} */ model) {
  const count = model.issues.length;
  if (count === 0) {
    return html`<span class="haui-diag-status good" role="img" title=${t('All good')} aria-label=${t('All good')}>
      ${icon('check-circle-outline')}</span>`;
  }
  const summary = count === 1 ? t('1 issue') : t('{count} issues').replace('{count}', String(count));
  // The issues are the icon's accessible name too: a tooltip alone reaches
  // neither the keyboard, touch nor a screen reader.
  return html`<span class="haui-diag-status warn" role="img"
    title=${`${summary}\n${model.issues.map((issue) => issue.label).join('\n')}`}
    aria-label=${`${summary}: ${model.issues.map((issue) => issue.label).join(', ')}`}>
    ${icon('alert-circle-outline')}<span class="haui-diag-status-count" aria-hidden="true">${count}</span></span>`;
}

export function diagnosticsSubtitle(model) {
  if (model.connected) {
    return model.uptime != null
      ? t('Online for {uptime}').replace('{uptime}', uptimeLabel(model.uptime))
      : t('Online');
  }
  return model.info.disconnected_since
    ? `${t('Offline')} · ${t('Last seen {time}').replace('{time}', relativeTime(model.info.disconnected_since))}`
    : t('Offline');
}

function signalBars(rssi) {
  const bars = rssiBarCount(rssi);
  const cls = rssiStrengthClass(rssi);
  return html`<span class="rssi-bars" aria-hidden="true">
    ${[1, 2, 3, 4].map((index) => html`<span class=${`rssi-bar ${bars >= index ? cls : ''}`}></span>`)}
  </span>`;
}

function displayState(model) {
  const { info, update } = model;
  const version = info.tft_version || t('Unknown');
  if (model.updateFailed) return html`${version} · <span class="bad">${t('update failed')}</span>`;
  if (update.state === 'installing') return html`${version} · <span class="warn">${t('installing')}</span>`;
  if (model.tftPending) return html`${version} · <span class="warn">${t('update pending')}</span>`;
  return version;
}

/**
 * The connection readings of the Connection & device card: how long the device
 * has been online (or that it is offline) and its Wi-Fi signal.
 */
export function connectionTiles(/** @type {ReturnType<typeof diagnosticsModel>} */ model) {
  const { info } = model;
  const unknown = t('Unknown');
  const latest = model.health?.recent_drops?.[0];
  // Offline, the drop that is going on; online, the latest the hub saw today.
  const dropReason = model.connected ? latest?.reason : info.last_disconnect_reason;
  const uptimeFacts = [
    model.connected
      ? [t('Last connected'), info.last_connection ? relativeTime(info.last_connection) : unknown]
      : [t('Disconnected'), info.disconnected_since ? relativeTime(info.disconnected_since) : unknown],
    ...(model.health ? [[t('Disconnects (24 h)'),
      model.drops ? `${model.drops} · ${relativeTime(latest?.time)}` : t('None'), model.unstable ? 'warn' : '']] : []),
    ...(dropReason ? [[t('Last drop'), dropReason]] : []),
  ];
  return [
    infoTile({
      key: 'uptime',
      label: model.connected ? t('Online for') : t('Status'),
      value: model.connected ? (model.uptime != null ? uptimeLabel(model.uptime) : t('Online')) : t('Offline'),
      tone: !model.connected ? 'bad' : model.unstable ? 'warn' : '',
      facts: uptimeFacts,
    }),
    infoTile({
      key: 'wifi', label: t('Wi-Fi'),
      value: html`${fmtRssi(info.rssi)}${signalBars(info.rssi)}`, heading: fmtRssi(info.rssi),
      tone: model.weakSignal ? 'warn' : '',
      facts: [[t('SSID'), info.ssid || unknown], [t('IP address'), info.ip || unknown]],
    }),
  ];
}

/** The expanded state's two readings; the firmware tile's details open on hover, focus or a tap. */
function tiles(model, status, onLogs) {
  const { info } = model;
  const unknown = t('Unknown');
  const logValue = model.logProblems === 1 ? t('1 warning')
    : model.logProblems ? t('{count} warnings').replace('{count}', String(model.logProblems)) : t('No warnings');
  return html`<div class="haui-diag-tiles">
    ${infoTile({
      key: 'diag-firmware', label: t('Firmware'),
      value: model.mismatch ? t('Mismatch') : info.yaml_version ? t('Matches') : unknown,
      tone: model.mismatch ? 'bad' : '',
      facts: [
        [t('Firmware'), status?.haui_version || unknown],
        [t('YAML version'), info.yaml_version || unknown, model.mismatch ? 'bad' : ''],
        [t('Display'), displayState(model)],
      ],
    })}
    ${infoTile({
      key: 'diag-log', label: t('Hub log'), value: logValue, tone: model.logProblems ? 'warn' : '',
      note: t('in the last 24 h'), onClick: onLogs,
    })}
  </div>`;
}

function displayLabel(state) {
  if (state === 'on') return t('On');
  if (state === 'dim') return t('Dimmed');
  if (state === 'off') return t('Off');
  return t('Unknown');
}

function idlePageLabel(idlePage) {
  switch (idlePage?.state) {
    case 'active': return t('Shown');
    case 'suspended': return t('Paused by an overlay');
    case 'offline': return t('Paused while offline');
    case 'held': return t('Held by the current page');
    case 'pending': return t('In {time}').replace('{time}', uptimeLabel(idlePage.idle_in));
    case 'off': return t('Off');
    default: return t('Unknown');
  }
}

/**
 * The entities the current page listens to, one entry per entity with the
 * attributes it reads, and their live state from Home Assistant.
 *
 * @param {any[]} listeners
 * @param {any} hass
 */
export function watchedEntities(listeners, hass) {
  /** @type {Map<string, string[]>} */
  const byEntity = new Map();
  for (const listener of listeners) {
    const attributes = byEntity.get(listener.item_id) || [];
    if (listener.attribute && !attributes.includes(listener.attribute)) attributes.push(listener.attribute);
    byEntity.set(listener.item_id, attributes);
  }
  return [...byEntity].map(([entityId, attributes]) => {
    const stateObj = hass?.states?.[entityId];
    const missing = Boolean(hass) && !stateObj;
    return {
      entityId,
      attributes,
      stateObj,
      name: stateObj?.attributes?.friendly_name || entityId,
      value: !hass ? '' : missing ? t('Not found') : hass.formatEntityState(stateObj),
      problem: missing || stateObj?.state === 'unavailable',
    };
  });
}

/** Opens Home Assistant's own entity dialog. */
function openMoreInfo(/** @type {Event} */ event, /** @type {string} */ entityId) {
  /** @type {HTMLElement} */ (event.currentTarget).dispatchEvent(new CustomEvent('hass-more-info', {
    detail: { entityId }, bubbles: true, composed: true,
  }));
}

function entityRow(/** @type {ReturnType<typeof watchedEntities>[number]} */ entity) {
  const body = html`<span class="haui-diag-entity-name">${entity.name}</span>
    <span class=${`haui-diag-entity-state${entity.problem ? ' warn' : ''}`}>${entity.value}</span>
    <span class="haui-diag-entity-id">${[entity.entityId, entity.attributes.join(', ')].filter(Boolean).join(' · ')}</span>`;
  return entity.stateObj
    ? html`<button type="button" class="haui-diag-entity" title=${entity.entityId}
        @click=${(/** @type {Event} */ event) => openMoreInfo(event, entity.entityId)}>${body}</button>`
    : html`<div class="haui-diag-entity" title=${entity.entityId}>${body}</div>`;
}

/** The drops of the last 24 hours: the count and the latest, every one in the tooltip. */
function dropsRow(model) {
  const drops = model.health.recent_drops || [];
  const latest = drops[0];
  return {
    label: t('Disconnects (24 h)'),
    value: latest ? `${model.drops} · ${latest.reason} · ${relativeTime(latest.time)}` : t('None'),
    title: drops.map((drop) => `${relativeTime(drop.time)}: ${drop.reason}`).join('\n'),
    tone: model.unstable ? 'warn' : '',
  };
}

/** Device heartbeats that came late: the count and the longest gap. */
function lateHeartbeatsRow(health) {
  const count = health.late_heartbeats_24h || 0;
  return {
    label: t('Late heartbeats (24 h)'),
    value: count
      ? `${count} · ${t('longest {time}').replace('{time}', uptimeLabel(health.longest_heartbeat_gap))}`
      : t('None'),
    title: t('A heartbeat is late when it comes more than 1.5 intervals after the previous one'),
    tone: '',
  };
}

/**
 * What the hub is doing with the panel: the display, the idle page, how
 * steady the connection was and the entities the current page watches. The
 * raw listener and timer lists are developer detail and go into the report,
 * copied from the end of the section.
 */
function hubDetails(model, status, hass, onCopyReport) {
  const { connected } = model;
  const listeners = status?.active_listeners || [];
  const listenerCount = status?.active_listener_count ?? listeners.length;
  const timerCount = status?.active_timer_count ?? (status?.active_timers || []).length;
  const entities = watchedEntities(listeners, hass);
  const problems = entities.filter((entity) => entity.problem).length;
  const rows = [
    // Offline, the hub's display and idle readings are stale; the connection history is not.
    ...(connected ? [
      { label: t('Display'), value: displayLabel(status?.device_info?.display_state), title: '', tone: '' },
      { label: t('Idle page'), value: idlePageLabel(status?.idle_page), title: '', tone: '' },
    ] : []),
    ...(model.health ? [dropsRow(model), lateHeartbeatsRow(model.health)] : []),
  ];
  return html`<details class="haui-details-more haui-diag-internals">
    <summary>${t('Hub details')} · ${entities.length === 1 ? t('1 watched entity')
      : t('{count} watched entities').replace('{count}', String(entities.length))}${problems
      ? html` · <span class="warn">${problems === 1 ? t('1 unavailable')
        : t('{count} unavailable').replace('{count}', String(problems))}</span>` : nothing}</summary>
    ${rows.length ? html`<dl>${rows.map((row) => html`<div>
      <dt>${row.label}</dt><dd class=${row.tone} title=${row.title || nothing}>${row.value}</dd>
    </div>`)}</dl>` : nothing}
    ${entities.length ? html`<div class="haui-diag-entities" role="group" aria-label=${t('Watched entities')}>
      ${entities.map(entityRow)}
    </div>` : nothing}
    <p class="haui-diag-internals-note">${t('Listeners')} ${listenerCount} · ${t('Timers')} ${timerCount} · ${t('the report lists them')}</p>
    ${button({ label: t('Copy report'), iconName: 'content-copy', onClick: onCopyReport, disabled: !onCopyReport })}
  </details>`;
}

/** The preview's entity hover switch; the hover itself is mouse-only. */
function showEntitiesCheck(/** @type {boolean} */ checked, /** @type {(show: boolean) => void} */ onChange) {
  return html`<label class="haui-diag-check">
    <input type="checkbox" .checked=${checked} aria-describedby="haui-diag-check-hint"
      @change=${(/** @type {Event} */ event) => onChange(/** @type {HTMLInputElement} */ (event.currentTarget).checked)}>
    <span class="haui-diag-check-copy">
      <span>${t('Show entities in the preview')}</span>
      <span class="haui-diag-check-hint" id="haui-diag-check-hint">${t('Hover over a widget in the preview to see the Home Assistant entity it shows')}</span>
    </span>
  </label>`;
}

/**
 * @typedef {{ live: boolean, ready: boolean, canInteract: boolean, sandboxChanged: boolean,
 *   onReset: () => void, onRedraw: () => void }} PreviewTools
 */

/**
 * The preview's tools: in Simulated, the sandbox reset once an entity has a
 * simulated state; in Live, the interaction reset and the redraw, which wait
 * for the connected panel.
 */
function previewToolButtons(/** @type {PreviewTools} */ tools) {
  const { live, ready, canInteract, sandboxChanged, onReset, onRedraw } = tools;
  if (!live && !sandboxChanged) return nothing;
  return html`<div class="haui-diag-tools" role="group" aria-label=${t('Preview tools')}>
    ${live
      ? html`${button({ label: t('Reset interaction'), iconName: 'timer-refresh', onClick: onReset, disabled: !canInteract })}
        ${button({ label: t('Redraw display'), iconName: 'refresh', onClick: onRedraw, disabled: !canInteract })}`
      : button({ label: t('Reset sandbox'), iconName: 'refresh', onClick: onReset, disabled: !ready })}
  </div>`;
}

/**
 * The diagnostics card body for one device.
 *
 * @param {{ status: any, hass?: any, expanded?: boolean, onLogs?: () => void, onCopyReport?: () => void,
 *   showEntities?: boolean, onShowEntities?: (show: boolean) => void, previewTools?: PreviewTools|null }} options
 */
export function deviceDiagnostics({
  status, hass, expanded = false, onLogs, onCopyReport, showEntities = false, onShowEntities,
  previewTools = null,
}) {
  if (!status || !expanded) return '';
  const model = diagnosticsModel(status);
  return html`<section class="haui-device-diagnostics expanded" aria-label=${t('Diagnostics')}>
    ${tiles(model, status, onLogs)}
    ${onShowEntities ? showEntitiesCheck(showEntities, onShowEntities) : nothing}
    ${previewTools ? previewToolButtons(previewTools) : nothing}
    ${hubDetails(model, status, hass, onCopyReport)}
  </section>`;
}

const ENTITY_ID = /\b([a-z_]+)\.[a-z0-9_]+\b/g;
const IPV4 = /\b\d{1,3}(?:\.\d{1,3}){3}\b/g;

/** Hub log lines name entities and addresses: keep only an entity's domain. */
function scrubLogLine(/** @type {string} */ line) {
  return line.replace(IPV4, '<ip>').replace(ENTITY_ID, '$1.<entity>');
}

/**
 * A plain-text report for a bug report. It stays in English on purpose (it is
 * read by maintainers) and leaves out the SSID, the IP and the entity ids,
 * since it is meant to be pasted into a public issue.
 *
 * @param {string} name
 * @param {any} status
 * @param {Date} [now]
 */
export function diagnosticsReport(name, status, now = new Date()) {
  const model = diagnosticsModel(status, now.getTime());
  const { info, update, health } = model;
  const idlePage = status?.idle_page;
  const listeners = status?.active_listeners || [];
  const timers = status?.active_timers || [];
  const yesNo = (value) => (value ? 'yes' : 'no');
  const lines = [
    'NSPanel HAUI diagnostics',
    `Device: ${name}`,
    `Generated: ${now.toISOString()}`,
    `Integration: ${status?.haui_version || 'unknown'}`,
    `Firmware (YAML): ${info.yaml_version || 'unknown'} (matches hub: ${yesNo(!model.mismatch)})`,
    `Display (TFT): ${info.tft_version || 'unknown'}${info.tft_required_version ? ` (required ${info.tft_required_version})` : ''}`,
    `Display update: ${update.state || 'idle'}${update.version ? ` ${update.version}` : ''}${update.last_error ? ` (${update.last_error})` : ''}`,
    `Connection: ${status?.connection_state || (model.connected ? 'connected' : 'disconnected')}`
      + (model.uptime != null ? `, up ${model.uptime}s` : ''),
    `Last disconnect: ${info.last_disconnect_reason || 'none'}${info.disconnected_since ? ` (${info.disconnected_since})` : ''}`,
    `Disconnects (24 h): ${health ? health.drops_24h : 'unknown'}`,
    ...(health?.recent_drops || []).map((drop) => `  ${drop.time} ${drop.reason}`),
    `Late heartbeats (24 h): ${health ? health.late_heartbeats_24h : 'unknown'}`
      + (health?.longest_heartbeat_gap != null ? `, longest ${health.longest_heartbeat_gap}s` : ''),
    `Wi-Fi signal: ${info.rssi != null && info.rssi !== '' ? `${info.rssi} dBm` : 'unknown'}`,
    `Current page: ${status?.current_page || 'unknown'}`,
    `Display: ${info.display_state || 'unknown'}`,
    `Idle page: ${idlePage?.state || 'unknown'}${idlePage?.idle_in != null ? ` (in ${idlePage.idle_in}s)` : ''}`,
    `Issues: ${model.issues.map((issue) => issue.key).join(', ') || 'none'}`,
    '',
    `Listeners (${status?.active_listener_count ?? listeners.length}):`,
    // Only the domain: entity ids carry room and people names.
    ...listeners.map((listener) => `  ${String(listener.item_id).split('.')[0]} [${listener.attribute || 'state'}] -> ${listener.callback_name}`),
    `Timers (${status?.active_timer_count ?? timers.length}):`,
    ...timers.map((timer) => `  ${timer.callback_name} (${timer.type} ${fmtInterval(timer.interval)})`),
    '',
    `Recent hub log (${model.logs.length} lines):`,
    ...model.logs.map(scrubLogLine),
  ];
  return `${lines.join('\n')}\n`;
}

