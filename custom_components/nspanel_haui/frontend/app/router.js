// @ts-check

/** @typedef {{ view: 'fleet'|'device', device: string|null, panel: string|null, panelView: 'preview'|'panels' }} Route */

const FLEET_ROUTE = Object.freeze({ view: 'fleet', device: null, panel: null, panelView: 'preview' });

/** Parse the editor hash into a route; malformed or unknown shapes resolve to Fleet. */
export function parseRoute(hash) {
  const raw = String(hash || '').replace(/^#/, '').replace(/^\//, '');
  if (!raw) return { ...FLEET_ROUTE };
  try {
    const parts = raw.split('/').map(decodeURIComponent);
    if (parts[0] !== 'device' || !parts[1]) return { ...FLEET_ROUTE };
    if (parts.length === 2) {
      return { view: 'device', device: parts[1], panel: null, panelView: 'preview' };
    }
    if (parts.length === 3 && parts[2] === 'panels') {
      return { view: 'device', device: parts[1], panel: null, panelView: 'panels' };
    }
    if (parts.length === 4 && parts[2] === 'panel' && parts[3]) {
      return { view: 'device', device: parts[1], panel: parts[3], panelView: 'panels' };
    }
  } catch {
    return { ...FLEET_ROUTE };
  }
  return { ...FLEET_ROUTE };
}

/** Serialize a route to a canonical hash. */
export function formatRoute(route) {
  if (route?.view !== 'device' || !route.device) return '#/';
  const device = encodeURIComponent(route.device);
  if (route.panel) return `#/device/${device}/panel/${encodeURIComponent(route.panel)}`;
  if (route.panelView === 'panels') return `#/device/${device}/panels`;
  return `#/device/${device}`;
}

/** Bind store route state to browser history; the router owns URL side effects. */
export function createRouter(store, win = window) {
  const syncFromUrl = () => store.actions.setRoute(parseRoute(win.location.hash));
  const onPopState = () => syncFromUrl();
  const onHashChange = () => syncFromUrl();
  win.addEventListener('popstate', onPopState);
  win.addEventListener('hashchange', onHashChange);
  syncFromUrl();

  return {
    navigate(route, { replace = false } = {}) {
      const hash = formatRoute(route);
      const url = `${win.location.pathname}${win.location.search}${hash}`;
      if (replace) win.history.replaceState(null, '', url);
      else win.history.pushState(null, '', url);
      store.actions.setRoute(parseRoute(hash));
    },
    destroy() {
      win.removeEventListener('popstate', onPopState);
      win.removeEventListener('hashchange', onHashChange);
    },
  };
}
