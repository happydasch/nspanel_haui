/**
 * NSPanel HAUI - Home Assistant elements the editor renders but does not own.
 *
 * HA does not load these at startup. It imports them with its more-info
 * dialog, which it preloads after its own first render
 * (src/state/more-info-mixin.ts in the HA frontend). After a reload on the
 * panel URL the editor can render first, and an undefined <ha-dialog> shows
 * its content inline, so the editor waits until they are defined.
 */

export const HA_ELEMENTS = ['ha-dialog', 'ha-dialog-footer', 'ha-card', 'ha-alert'];

/** How long to wait before telling the user which elements are missing. */
export const HA_ELEMENTS_TIMEOUT_MS = 10000;

/** @returns {string[]} the HA elements not defined yet */
export function undefinedHaElements() {
  return HA_ELEMENTS.filter((tag) => !customElements.get(tag));
}

/** @returns {Promise<void>} resolves once every HA element is defined */
export async function whenHaElementsDefined() {
  await Promise.all(HA_ELEMENTS.map((tag) => customElements.whenDefined(tag)));
}
