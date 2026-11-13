import { html } from '../lit-import.js';

const ICONS = Object.freeze({
  home: 'home', bell: 'bell-outline', tune: 'tune', settings: 'cog-outline',
  devices: 'devices', grid: 'view-grid-outline', plus: 'plus', check: 'check',
  back: 'arrow-left', up: 'arrow-up', down: 'arrow-down', grip: 'drag',
  more: 'dots-horizontal', edit: 'pencil-outline', list: 'format-list-bulleted',
  chevronLeft: 'chevron-left', chevronRight: 'chevron-right', close: 'close',
  wifi: 'wifi', signal: 'signal', panels: 'view-dashboard-outline', screen: 'monitor',
  refresh: 'refresh', download: 'download', clock: 'clock-outline', sleep: 'sleep',
  info: 'information-outline', activity: 'pulse', alert: 'alert-outline', light: 'lightbulb-outline',
  thermo: 'thermometer', cover: 'window-shutter', media: 'play-outline', cloud: 'cloud-outline',
  network: 'lan', search: 'magnify', log: 'text-box-outline', lightning: 'lightning-bolt-outline',
  upload: 'upload', file: 'file-document-outline', github: 'github', help: 'help-circle-outline',
  notification: 'bell-outline', menu: 'menu', color: 'palette-outline',
  duplicate: 'content-duplicate', delete: 'delete-outline',
});

/** Render a Home Assistant icon; icon-only controls own their accessible name. */
export function icon(name, className = '', decorative = true) {
  const mdiName = ICONS[name] || name;
  return html`<ha-icon class=${className}
    icon=${mdiName.includes(':') ? mdiName : `mdi:${mdiName}`}
    aria-hidden=${decorative ? 'true' : 'false'}></ha-icon>`;
}
