/**
 * NSPanel HAUI - Custom icon set.
 *
 * Registers a "haui:home-assistant" icon via window.customIcons for use in
 * Home Assistant dashboards and the HAUI Editor itself.  The icon depicts a
 * square panel (rounded rect) with two rounded-square buttons protruding
 * from the bottom - the NSPanel silhouette.
 *
 * Pattern follows the HACS customIcons convention so the icon works with
 * standard <ha-icon> and <ha-svg-icon> components.
 */

/* eslint-disable max-len */
const nspanelHauiIcons = {
  "home-assistant": {
    /*
     * Three non-overlapping filled shapes - panel body + two button "feet".
     * No compound paths, no overlap - each renders as a distinct element.
     * Exact path data from the 24×24 SVG.
     */
    path:
      /* Panel body (inverted-U, rounded top corners) */
      "M4 16 L20 16 L20 7 C20 5.343145 18.656855 4 17 4 L7 4 C5.343146 4 4 5.343145 4 7 Z " +
      /* Left foot (bottom-left, rounded outer corner) */
      "M4 20 C4 21.104568 4.895431 22 6 22 L11 22 L11 18 L4 18 Z " +
      /* Right foot (bottom-right, rounded outer corner) */
      "M13 22 L18 22 C19.104568 22 20 21.104568 20 20 L20 18 L13 18 Z",
    keywords: ["home assistant", "nspanel", "haui", "panel"],
  },
};
/* eslint-enable max-len */

const registerIcons = () => {
  const iconSet = {
    getIcon: async (iconName) => {
      const icon = nspanelHauiIcons[iconName];
      return icon ? { path: icon.path } : {};
    },
    getIconList: async () =>
      Object.entries(nspanelHauiIcons).map(([name, content]) => ({
        name,
        keywords: content.keywords,
      })),
  };
  // Merge into the existing objects instead of replacing them: the frontend
  // may have already captured the object reference when it resolves custom
  // icons, so a replacement would leave its lookups reading an empty set.
  window.customIcons = Object.assign(window.customIcons || {}, {
    haui: iconSet,
  });
  window.customIconsets = Object.assign(window.customIconsets || {}, {
    haui: iconSet.getIcon,
  });
};

const observedRoots = new WeakSet();

const watchRoot = (root) => {
  if (observedRoots.has(root)) {
    return;
  }
  observedRoots.add(root);
  new MutationObserver(() => healRoot(root)).observe(root, {
    childList: true,
    subtree: true,
  });
};

const healRoot = (root) => {
  root.querySelectorAll("ha-icon").forEach((element) => {
    const icon = element.icon;
    if (
      typeof icon === "string" &&
      icon.startsWith("haui:") &&
      element._legacy
    ) {
      // HA keeps its legacy fallback after the icon set becomes available.
      element._legacy = false;
      element.icon = undefined;
      element.icon = icon;
    }
  });
  root.querySelectorAll("*").forEach((element) => {
    if (element.shadowRoot) {
      healRoot(element.shadowRoot);
      watchRoot(element.shadowRoot);
    }
  });
};

const healHauiIcons = () => healRoot(document);

registerIcons();
healHauiIcons();
watchRoot(document);
window.addEventListener("hass-panel-ready", healHauiIcons);
