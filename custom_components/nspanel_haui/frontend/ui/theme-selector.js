// @ts-check
import { html, nothing } from '../lit-import.js';
import { rgb565ToHex } from '../color-utils.js';
import { t } from '../localize.js';
import { button, iconButton } from './button.js';

/** The colors the selector's palette chip shows, in order. */
const SWATCHES = ['background', 'header_background', 'component_active', 'entity_on'];

/**
 * One selector for the whole theme library: predefined and custom themes in a
 * single dropdown over the selected palette, and the library controls (new
 * theme, export selected, import, plus the selected theme's own actions) in one
 * row underneath. Used by the Theme sidebar.
 *
 * @param {{
 *   builtins?: Record<string, any>,
 *   custom?: Record<string, any>,
 *   selectedId: string,
 *   label?: string,
 *   builtinLabel: (id: string) => string,
 *   onSelect: (id: string) => void,
 *   actions?: { label: string, iconName: string, onClick: () => void, danger?: boolean }[],
 *   onNew: () => void,
 *   onExport: () => void,
 *   onImport: (event: Event) => void,
 *   notice?: string,
 *   error?: string,
 *   nameAction?: string,
 *   themeName?: string,
 *   onNameInput?: (value: string) => void,
 *   onSaveName?: () => void,
 *   onCancelName?: () => void,
 * }} options
 */
export function themeSelector({
  builtins = {},
  custom = {},
  selectedId,
  label = t("Theme"),
  builtinLabel,
  onSelect,
  actions = [],
  onNew,
  onExport,
  onImport,
  notice = "",
  error = "",
  nameAction = "",
  themeName = "",
  onNameInput,
  onSaveName,
  onCancelName,
}) {
  const customIds = Object.keys(custom);
  const selected = custom[selectedId] || builtins[selectedId];
  /* The file input sits in the action row, so Import opens the picker next to it. */
  const openFilePicker = (event) => {
    event.currentTarget
      .closest(".haui-theme-selector-actions")
      ?.querySelector("input[type=file]")
      ?.click();
  };
  return html`
    <div class="haui-theme-selector">
      <div class="form-group">
        <label for="haui-theme-select">${label}</label>
        <div class="haui-theme-selector-field">
          ${selected
            ? html`<span class="haui-theme-selector-chip" aria-hidden="true">
                ${SWATCHES.map((key) => html`<i style="background:${rgb565ToHex(selected.colors[key])}"></i>`)}
              </span>`
            : nothing}
          <select
            id="haui-theme-select"
            class="native-select"
            .value=${selectedId}
            @change=${(event) => onSelect(event.target.value)}
          >
            <optgroup label=${t("Predefined themes")}>
              ${Object.keys(builtins).map((id) => html`
                <option value=${id} ?selected=${id === selectedId}>${builtinLabel(id)}</option>`)}
            </optgroup>
            ${customIds.length
              ? html`<optgroup label=${t("Custom themes")}>
                  ${customIds.map((id) => html`
                    <option value=${id} ?selected=${id === selectedId}>${custom[id].name}</option>`)}
                </optgroup>`
              : nothing}
          </select>
        </div>
      </div>
      <div class="haui-theme-selector-actions">
        ${button({ label: t("New"), variant: "quiet", onClick: onNew, className: "haui-theme-selector-action" })}
        ${button({ label: t("Export"), variant: "quiet", onClick: onExport, className: "haui-theme-selector-action" })}
        ${button({
          label: t("Import"),
          variant: "quiet",
          onClick: openFilePicker,
          className: "haui-theme-selector-action",
        })}
        ${actions.length
          ? html`<span class="haui-theme-selector-divider" aria-hidden="true"></span>
              ${actions.map(({ label: actionLabel, iconName, onClick, danger }) =>
                iconButton({
                  label: actionLabel,
                  iconName,
                  onClick,
                  className: `haui-row-action${danger ? " is-danger" : ""}`,
                }))}`
          : nothing}
        <input type="file" accept="application/json,.json" hidden @change=${onImport} />
      </div>
      ${notice ? html`<p class="config-section-intro" role="status">${notice}</p>` : nothing}
      ${nameAction
        ? html`
            <div class="cp-theme-name">
              <input
                type="text"
                maxlength="64"
                class="native-input"
                .value=${themeName}
                @input=${(event) => onNameInput?.(event.target.value)}
                aria-label=${t("Color theme name")}
              />
              <ha-button size="s" variant="brand" @click=${onSaveName}>${t("Save")}</ha-button>
              <ha-button size="s" variant="neutral" appearance="plain" @click=${onCancelName}>${t("Cancel")}</ha-button>
            </div>
          `
        : nothing}
      ${error ? html`<p class="cp-theme-error" role="alert">${error}</p>` : nothing}
    </div>
  `;
}
