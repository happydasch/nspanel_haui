// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';
import { deviceConnectionState } from '../device-status.js';

/** The connection tone of one device, as the summary strip paints it. */
function deviceTone(status) {
  return deviceConnectionState(status).tone;
}

/** A labelled figure on the strip's right: updates pending, hub version. */
function fact(label, value) {
  return html`<div><dt>${label}</dt><dd>${value}</dd></div>`;
}

/**
 * Render health and update figures from device status; until the first status
 * arrives (`pending`) the values are placeholders.
 * @param {{ total: number, online: number, updates: number, version: string, pending?: boolean }} stats
 */
export function fleetSummary({ total, online, updates, version, pending = false }) {
  const value = (text) => (pending ? html`<span class="haui-stat-placeholder"></span>` : text);
  const tone = pending ? 'neutral' : online === total ? 'success' : online ? 'warning' : 'danger';
  const health = pending ? ''
    : online === total ? t('All devices connected')
      : online ? t('{count} offline').replace('{count}', String(total - online))
        : t('No device connected');
  return html`<section class=${`haui-fleet-summary haui-fleet-band-${tone} ${
    pending ? 'haui-fleet-summary-pending' : ''}`}
    aria-label=${t('Fleet overview')} aria-busy=${pending ? 'true' : 'false'}>
    <div class="haui-fleet-band-top">
      <span class="haui-fleet-orb">${icon('lan-connect')}</span>
      <div class="haui-fleet-lead">
        <strong>${pending ? html`<span class="haui-stat-placeholder"></span>` : `${online} / ${total}`}</strong>
        <span>${health}</span>
      </div>
      <dl class="haui-fleet-facts">
        ${fact(t('Updates'), value(String(updates)))}
        ${fact(t('Hub version'), value(version))}
      </dl>
    </div>
  </section>`;
}

/** Render the connection bar independently from the inventory summary. */
export function fleetBar({ devices, total, online }) {
  return total ? html`<div class="haui-inventory-bar">
    <div class="haui-fleet-bar" role="img"
      aria-label=${t('{online} of {total} devices connected')
    .replace('{online}', String(online)).replace('{total}', String(total))}>
      ${devices.map(({ name, status }) => html`<span class=${deviceTone(status)} title=${name}></span>`)}
    </div>
  </div>` : '';
}
