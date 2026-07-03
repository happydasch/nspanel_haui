/**
 * NSPanel HAUI - System panel override editing.
 *
 * Each exported function takes the component instance (`host`) as its first
 * parameter.
 */
import { clone, POPUP_TO_USER_TYPE } from './constants.js';
import { t } from './localize.js';

export function openSysPanelEdit(host, sysPanel) {
  host._dialogVersion = (host._dialogVersion || 0) + 1;
  const panels = host._devicePanels();
  const existingIdx = panels.findIndex(p => p.key === sysPanel.key);
  const resolvedType = POPUP_TO_USER_TYPE[sysPanel.type] || sysPanel.type;

  if (existingIdx >= 0) {
    const existingData = clone(panels[existingIdx]);
    existingData.type = resolvedType;
    host._itemListData = {};
    host._editingPanel = { index: existingIdx, data: existingData };
    host._editingPanelType = resolvedType;
    host._error = null;
    host._deleteTarget = null;
    host.requestUpdate();
    return;
  }

  const data = {
    type: resolvedType,
    key: sysPanel.key,
    show_in_navigation: false,
  };
  host._itemListData = {};
  host._editingPanelType = resolvedType;
  host._editingPanel = { index: -1, data };
  host._error = null;
  host._deleteTarget = null;
  host.requestUpdate();
}

export async function resetSysPanelOverride(host, key) {
  const panels = host._devicePanels();
  const newPanels = panels.filter(p => p.key !== key);
  await host._savePanels(newPanels, t('System panel reset to default'));
}