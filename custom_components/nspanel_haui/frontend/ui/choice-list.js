// @ts-check
/**
 * NSPanel HAUI - a labelled group of checkbox rows.
 *
 * One boxed row per choice (an icon, its name and an optional hint), tinted
 * while it is picked, with the group's name, an optional count badge and one
 * group action in the heading. The rows own no state: the caller keeps the
 * selection and gets every change back as `(key, checked)`.
 */
import { html, nothing } from '../lit-import.js';
import { icon } from './icon.js';

/**
 * @typedef {{ key: string, label: string, hint?: string, iconName?: string,
 *   checked: boolean, disabled?: boolean }} Choice
 * @typedef {{ id: string, label: string, choices: Choice[],
 *   onToggle: (key: string, checked: boolean) => void,
 *   badge?: unknown, actions?: unknown, emptyText?: string,
 *   className?: string }} ChoiceListOptions
 */

/**
 * A labelled group of checkbox rows. `badge` and `actions` are prepared
 * templates (a `countBadge`, a `button`), not text: the primitive formats
 * nothing. The group is named by `aria-label`, not a `<fieldset>/<legend>`, so
 * the heading row can carry those controls without joining the group's name.
 *
 * @param {ChoiceListOptions} options
 */
export function choiceList({
  id, label, choices, onToggle, badge, actions, emptyText, className = '',
}) {
  return html`<div class=${`haui-choice-group ${className}`.trim()}>
    <div class="haui-choice-head">
      <span class="haui-eyebrow">${label}</span>
      <span class="haui-choice-head-extra">${badge ?? nothing}${actions ?? nothing}</span>
    </div>
    ${choices.length ? html`<div class="haui-choice-list" id=${id} role="group" aria-label=${label}>
      ${choices.map((choice) => html`<label class=${`haui-choice ${choice.checked ? 'is-checked' : ''}`.trim()}>
        <input type="checkbox" .checked=${choice.checked} ?disabled=${choice.disabled === true}
          @change=${(/** @type {Event} */ event) => onToggle(
            choice.key, /** @type {HTMLInputElement} */ (event.currentTarget).checked,
          )}>
        <span class="haui-choice-copy">
          <span class="haui-choice-name">${choice.iconName ? icon(choice.iconName) : nothing}<span>${choice.label}</span></span>
          ${choice.hint ? html`<span class="haui-choice-hint">${choice.hint}</span>` : nothing}
        </span>
      </label>`)}
    </div>` : nothing}
    ${emptyText ? html`<p class="haui-choice-empty">${emptyText}</p>` : nothing}
  </div>`;
}
