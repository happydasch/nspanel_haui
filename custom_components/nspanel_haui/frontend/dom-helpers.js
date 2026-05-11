/**
 * NSPanel HAUI - Editor - DOM helper utilities.
 *
 * Tiny helpers used across the editor to reduce repeated querySelector patterns.
 */

/**
 * Read the value of a form field by its id attribute.
 * @param {HTMLElement} form - the form (or any ancestor) DOM element
 * @param {string} id - the element id (without #)
 * @param {string} [fallback=""] - value to return if element not found
 * @returns {string}
 */
export function formVal(form, id, fallback = "") {
  const el = form.querySelector(`#${id}`);
  return el ? el.value : fallback;
}
