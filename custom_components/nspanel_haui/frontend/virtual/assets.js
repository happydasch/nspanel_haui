/**
 * NSPanel HAUI - the simulated display's assets: layouts, icon map, pictures.
 *
 * Shared by the panel cards and the live preview; layouts and the icon map are
 * fetched once and kept.
 */

const MODULE_URL = import.meta.url;
const LAYOUT_CACHE = new Map();
let ICON_MAP_PROMISE = null;

function loadJson(url, loader) {
  if (loader) return Promise.resolve(loader(url));
  return fetch(url).then((response) => {
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  });
}

/** Memoised virtual-panel layout loader. */
export function loadLayout(orientation, loader) {
  let promise = LAYOUT_CACHE.get(orientation);
  if (!promise) {
    promise = loadJson(new URL(`layout_${orientation}.json`, MODULE_URL), loader)
      .catch((error) => {
        LAYOUT_CACHE.delete(orientation);
        throw error;
      });
    LAYOUT_CACHE.set(orientation, promise);
  }
  return promise;
}

/** Memoised icon map ({character: icon name}) used by the display renderer. */
export function loadIconMap(loader) {
  if (!ICON_MAP_PROMISE) {
    ICON_MAP_PROMISE = loadJson(new URL('icon_map.json', MODULE_URL), loader)
      .catch((error) => {
        ICON_MAP_PROMISE = null;
        throw error;
      });
  }
  return ICON_MAP_PROMISE;
}

/** URL of a virtual-panel picture asset. */
export function pictureUrlFor(orientation, id) {
  return new URL(`pictures/${orientation}/${id}.webp`, MODULE_URL).href;
}
