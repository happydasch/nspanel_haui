// @ts-check
import { t } from '../localize.js';
import { button, iconButton } from './button.js';
import { actionCard } from './action-card.js';
import { builtinThemeLabel } from '../theme-library.js';

/**
 * The lead card of the Panels view: the panel counts, the Add panel action and
 * the device settings.
 *
 * @param {{ panels: any[], onAdd: () => void, onSettings: () => void }} data
 */
export function panelActions({ panels, onAdd, onSettings }) {
  const navigable = panels.filter((panel) => panel.show_in_navigation !== false);
  return actionCard({
    iconName: 'panels',
    title: t('Panels'),
    subtitle: t('{count} panels · {visible} in navigation')
      .replace('{count}', String(panels.length)).replace('{visible}', String(navigable.length)),
    tool: iconButton({ label: t('Settings'), iconName: 'settings', onClick: onSettings }),
    primary: button({ label: t('Add panel'), iconName: 'plus', variant: 'primary', onClick: onAdd }),
  });
}

/**
 * The name of a device's theme: a custom theme's own name, or the predefined
 * theme's label.
 *
 * @param {unknown} themeId
 * @param {Record<string, any>} builtinThemes
 * @param {Record<string, any>} customThemes
 */
export function themeLabel(themeId, builtinThemes, customThemes) {
  const id = String(themeId || 'dark');
  return customThemes[id]?.name || (builtinThemes[id] ? builtinThemeLabel(id) : id);
}

/**
 * What a device's update settings hold, in a few words: the Updates button below
 * the side stack shows it on its trailing edge.
 *
 * @param {any} config - the device's config
 */
export function updatesSummary(config) {
  const { update } = config;
  if (!update.enabled) return t('Off');
  return [
    update.firmware_update_channel === 'dev' ? t('Development') : t('Stable'),
    update.firmware_auto_update ? t('Auto') : t('Manual'),
  ].join(' · ');
}
