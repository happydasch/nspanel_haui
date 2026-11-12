// @ts-check
import { t } from '../localize.js';
import { button, iconButton } from './button.js';
import { actionCard } from './action-card.js';
import { updateOfferLabel } from './format.js';
import { hasUpdateAvailable } from '../device-status.js';

/**
 * The lead card of the Preview view: the device's next actions, with the
 * settings as a cog beside the title. An offered update leads while there is
 * one; otherwise adding a panel does. Checking for updates belongs to the
 * Connection & device card.
 *
 * @param {{ status: any, onSettings: () => void, onFirmware: () => void, onAdd: () => void, onTheme: () => void }} data
 */
export function deviceActions({ status, onSettings, onFirmware, onAdd, onTheme }) {
  const update = status?.update || {};
  const tool = iconButton({ label: t('Settings'), iconName: 'settings', onClick: onSettings });
  const addPanel = (variant) => button({ label: t('Add panel'), iconName: 'plus', variant, onClick: onAdd });
  const themeButton = button({ label: t('Theme'), iconName: 'palette', variant: 'outline', onClick: onTheme });
  if (hasUpdateAvailable(update)) {
    return actionCard({
      iconName: 'update',
      title: t('Update available'),
      subtitle: updateOfferLabel(update),
      tool,
      primary: button({ label: t('Install update'), iconName: 'update', variant: 'primary', onClick: onFirmware }),
      secondary: [addPanel(), themeButton],
      stacked: true,
    });
  }
  return actionCard({
    iconName: 'tablet-dashboard',
    title: t('Manage this device'),
    subtitle: t('Add a panel or change the settings.'),
    tool,
    primary: addPanel('primary'),
    secondary: [themeButton],
    stacked: true,
    inlineActions: true,
  });
}
