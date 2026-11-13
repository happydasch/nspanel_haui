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
