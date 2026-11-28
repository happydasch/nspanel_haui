import { readFileSync } from 'node:fs';
import { createStore, devicesFromStore } from '../../../custom_components/nspanel_haui/frontend/store/store.js';

export function panels(devices = { kitchen: { config: {}, panels: [] } }) {
  return { devices: structuredClone(devices), system_panels: [], themes: {} };
}

export function deviceStore(panelData = panels()) {
  const store = createStore({ client: {}, storage: { read: (_key, fallback) => fallback, write() {} } });
  store.setState((state) => ({ ...state, devices: devicesFromStore(panelData, state.devices) }));
  return store;
}

export function layout(orientation = 'landscape') {
  if (!['landscape', 'portrait'].includes(orientation)) throw new Error('Unknown display orientation');
  const path = `../../../custom_components/nspanel_haui/frontend/virtual/layout_${orientation}.json`;
  return JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
}

/**
 * The page id a layout gives a page name.
 *
 * The display's page ids follow the HMI's page order, so a fixture that needs
 * one reads it from the layout instead of pinning a number an HMI change would
 * silently break.
 */
export function pageId(name, orientation = 'landscape') {
  const { pages } = layout(orientation);
  const id = Object.keys(pages).find((key) => pages[key].name === name);
  if (id === undefined) throw new Error(`No page named ${name} in the ${orientation} layout`);
  return Number(id);
}
