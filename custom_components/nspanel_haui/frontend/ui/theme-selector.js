// @ts-check
import { html, nothing } from '../lit-import.js';
import { rgb565ToHex } from '../color-utils.js';
import { t } from '../localize.js';

/** The colors the selector's swatch strip shows, in order. */
const SWATCHES = ['background', 'header_background', 'component_active', 'entity_on'];

/**
 * One selector for the whole theme library: predefined and custom themes in a
 * single dropdown, the selected theme's swatches and actions, and the library
 * controls (new theme, export all, import). Shared by the Theme sidebar and
 * the device settings' Theme section.
 *
 * @param {{
 *   builtins?: Record<string, any>,
 *   custom?: Record<string, any>,
 *   selectedId: string,
 *   label?: string,
 *   builtinLabel: (id: string) => string,
 *   onSelect: (id: string) => void,
 *   actions?: { label: string, onClick: () => void }[],
 *   onNew: () => void,
 *   onExportAll: () => void,
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
  onExportAll,
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
  return html`
    <div class="haui-theme-selector">
      <div class="form-group">
        <label for="haui-theme-select">${label}</label>
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
        ${selected
          ? html`<span class="haui-theme-selector-swatches" aria-hidden="true">
              ${SWATCHES.map((key) => html`<i style="background:${rgb565ToHex(selected.colors[key])}"></i>`)}
            </span>`
          : nothing}
      </div>
      ${actions.length
        ? html`<div class="haui-theme-selector-actions">
            ${actions.map(({ label: actionLabel, onClick }) => html`
              <button type="button" @click=${onClick}>${actionLabel}</button>`)}
          </div>`
        : nothing}
      <div class="cp-theme-actions">
        <ha-button variant="neutral" appearance="plain" @click=${onNew}>${t("New theme")}</ha-button>
        <ha-button variant="neutral" appearance="plain" @click=${onExportAll}>${t("Export all")}</ha-button>
        <ha-button
          variant="neutral"
          appearance="plain"
          @click=${(event) => {
            const actionsRow = event.currentTarget.closest(".cp-theme-actions");
            actionsRow?.querySelector("input[type=file]")?.click();
          }}
        >${t("Import")}</ha-button>
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
              <ha-button variant="brand" @click=${onSaveName}>${t("Save")}</ha-button>
              <ha-button variant="neutral" appearance="plain" @click=${onCancelName}>${t("Cancel")}</ha-button>
            </div>
          `
        : nothing}
      ${error ? html`<p class="cp-theme-error" role="alert">${error}</p>` : nothing}
    </div>
  `;
}
