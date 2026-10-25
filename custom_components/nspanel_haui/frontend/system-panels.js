/**
 * NSPanel HAUI - System panel override editing.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, POPUP_TO_USER_TYPE } from './constants.js';
import { t } from './localize.js';
import { openPanelDialog } from './crud.js';

export function openSysPanelEdit(host, sysPanel) {
  const panels = host._devicePanels();
  const existingIdx = panels.findIndex(p => p.key === sysPanel.key);
  const resolvedType = POPUP_TO_USER_TYPE[sysPanel.type] || sysPanel.type;

  if (existingIdx >= 0) {
    const existingData = clone(panels[existingIdx]);
    existingData.type = resolvedType;
    openPanelDialog(host, existingIdx, existingData, resolvedType);
  } else {
    openPanelDialog(
      host, -1, { type: resolvedType, key: sysPanel.key, show_in_navigation: false }, resolvedType
    );
  }
  host.requestUpdate();
}

export async function resetSysPanelOverride(host, key) {
  const panels = host._devicePanels();
  const newPanels = panels.filter(p => p.key !== key);
  await host._savePanels(newPanels, t('System panel reset to default'));
}