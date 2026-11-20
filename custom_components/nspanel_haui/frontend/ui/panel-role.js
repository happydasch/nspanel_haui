// @ts-check
/**
 * NSPanel HAUI - a page's role on the device, as a marker.
 *
 * The home panel, the idle panels and the navigation and hidden pages are one
 * kind of fact, so the panel list and the quick start draw them the same way:
 * the role's icon in a small circle, with its name for a screen reader.
 */
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { icon } from './icon.js';

/** The icon of each place a page can sit on the device. */
const ROLE_ICONS = {
  home: 'home',
  idle: 'sleep',
  navigation: 'panels',
  hidden: 'eye-off-outline',
};

// The names are read when the marker is drawn: translations load after this module.
const ROLE_LABELS = {
  home: () => t('Home panel'),
  idle: () => t('Idle panel'),
  navigation: () => t('Navigation'),
  hidden: () => t('Hidden'),
};

/**
 * The marker of one role: its icon in the role's own tone, the role's name on
 * the marker itself. An unknown role draws nothing.
 *
 * @param {{ role: string, label?: string, extra?: boolean }} options - `label`
 *   replaces the role's name (a numbered idle panel); `extra` dims a marker
 *   that continues the idle cycle
 */
export function panelRoleMarker({ role, label, extra = false }) {
  const iconName = ROLE_ICONS[role];
  const name = ROLE_LABELS[role];
  if (!iconName || !name) return nothing;
  return html`<span class=${`haui-panel-role haui-panel-role-${role}${extra ? ' is-extra' : ''}`}
    role="img" aria-label=${label || name()}>${icon(iconName)}</span>`;
}
