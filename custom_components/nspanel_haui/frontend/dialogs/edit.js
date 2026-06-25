/**
 * NSPanel HAUI - Editor - Edit Panel dialog.
 *
 * Replaces the old renderEditDialog() function with a proper Lit custom element
 * that uses ha-dialog / ha-dialog-header / ha-dialog-footer and communicates
 * via CustomEvent.
 *
 * Maintains its own form state (panel type, title, config options, key, show_in_nav)
 * to avoid polluting the editor's state surface.
 */
import { LitElement, html } from '../lit-import.js';
import { haStyle, haStyleDialog, editorStyles } from '../styles.js';
import { clone } from '../constants.js';
import { formVal } from '../dom-helpers.js';
import { getPanelOptionGroups, renderOptionField } from '../form-fields.js';
import { dialogHeader } from './dialog-header.js';
import { t } from '../localize.js';
import { saveItemEdit, cancelItemEdit } from '../item-editor.js';

/**
 * Compute an auto-generated key for a new panel of the given type, based on
 * the panels already known to this dialog (passed via devicePanels property).
 */
function generateAutoKey(panels, panelType) {
  const usedKeys = new Set(
    (panels || []).filter(p => p.type === panelType).map(p => p.key)
  );
  let idx = 0;
  while (usedKeys.has(`${panelType}_${idx}`)) idx++;
  return `${panelType}_${idx}`;
}

class EditPanelDialog extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      open: { type: Boolean, reflect: true },
      panel: { type: Object },
      panelTypes: { type: Array },
      saving: { type: Boolean },
      error: { type: String },
      entryId: { type: String },
      devicePanels: { type: Array },
      dialogVersion: { type: Number },
    };
  }

  static styles = [haStyle, haStyleDialog, editorStyles];

  constructor() {
    super();
    this.open = false;
    this.panel = null;
    this.panelTypes = [];
    this.saving = false;
    this.error = null;
    this.entryId = null;
    this.devicePanels = [];
    this._editingPanelType = null;
    this._editingPanel = null;
    this._itemListData = {};
    this._userSelectedType = false;
    this._dialogVersion = 0;
  }

  willUpdate(changed) {
    if ((changed.has("open") && this.open) || changed.has("dialogVersion")) {
      // Reset user type selection each time the dialog opens or a new panel
      // session starts. The dialogVersion counter is incremented by the parent
      // for every open/close/open cycle, ensuring the reset fires even when
      // open doesn't change (e.g. close + reopen in separate microtasks
      // before Lit renders the intermediate null state).
      this._userSelectedType = false;
    }
    if (changed.has("panel") && this.panel) {
      // Don't overwrite the user's explicit type selection when the parent
      // re-renders due to status polling or other reactive updates.
      if (!this._userSelectedType) {
        this._editingPanelType = this.panel.data?.type || "clock";
        // Only sync _editingPanel from the parent prop when the user hasn't
        // made an explicit type change — otherwise the parent's stale
        // _editingPanel (never updated on type change) would overwrite
        // the user's in-progress edits.
        this._editingPanel = this.panel;
        this._itemListData = {};
      }
    }
  }

  render() {
    if (!this.panel) return "";
    // Always prefer the dialog's own _editingPanel over the parent's panel prop.
    // The parent's _editingPanel reference is never updated on type change, so
    // relying on "this._editingPanel || this.panel" means the parent's stale
    // data would overwrite the user's type selection on re-render.
    // Instead, once _userSelectedType is true, ALWAYS use _editingPanel.
    const ep = (this._userSelectedType && this._editingPanel) ? this._editingPanel : (this._editingPanel || this.panel);
    const isAdd = ep.index < 0;
    const panelType = this._editingPanelType || ep.data?.type || "clock";
    const descriptor = this.panelTypes.find((pt) => pt.type_key === panelType);
    const typeLabel = descriptor ? descriptor.label : panelType;
    const headerTitle = isAdd ? t('Add Panel') : `${t('Edit Panel')} — ${typeLabel}`;
    const saveLabel = this.saving ? t('Saving...') : isAdd ? t('Add') : t('Save');

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        .preventScrimClose=${true}
      >
        ${dialogHeader(headerTitle, this._dispatchClose)}

        <form id="panel-edit-form" @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">

          ${isAdd ? html`
            <div class="form-group">
              <label for="fld-type">${t('Panel type')}</label>
              <div style="display:flex;align-items:center;gap:8px;">
                ${descriptor?.icon ? html`<ha-icon .icon=${descriptor.icon}></ha-icon>` : ""}
                <ha-select
                  id="fld-type"
                  name="type"
                  style="flex:1"
                  .value=${panelType}
                  .options=${this.panelTypes.map((pt) => ({ value: pt.type_key, label: pt.label }))}
                  @selected=${this._onTypeChange}
                ></ha-select>
              </div>
              ${descriptor ? html`<span class="field-hint">${descriptor.description}</span>` : ""}
            </div>
          ` : ""}

          <div class="form-group">
            <label for="fld-title">${t('Panel title')}</label>
            <ha-input
              id="fld-title"
              name="title"
              .value=${ep.data.title || ""}
              style="width: 100%"
              @input=${(e) => {
                this._editingPanel = {
                  ...this._editingPanel,
                  data: { ...this._editingPanel.data, title: e.target.value },
                };
                this.requestUpdate();
              }}
            ></ha-input>
            <span class="field-hint">${t('Title shown on the panel header. Falls back to unnamed if left empty.')}</span>
          </div>

          ${getPanelOptionGroups(descriptor).map(group => {
            const sectionLabel = group.section ? group.section : t('Configuration');
            return html`
              <details class="config-section">
                <summary>${sectionLabel}</summary>
                <div class="config-section-body">
                  ${group.options.map(opt => renderOptionField(this, opt, ep.data[opt.key], descriptor))}
                </div>
              </details>
            `;
          })}

          <details class="config-section">
            <summary>${t('Advanced')}</summary>
            <div class="config-section-body">

              <div class="form-group">
                <label for="fld-key">${t('Panel key')}</label>
                <ha-input
                  id="fld-key"
                  name="key"
                  .value=${ep.data.key || ""}
                  style="width: 100%"
                  @input=${(e) => {
                    this._editingPanel = {
                      ...this._editingPanel,
                      data: { ...this._editingPanel.data, key: e.target.value },
                    };
                    this.requestUpdate();
                  }}
                ></ha-input>
                <span class="field-hint">${t('Used to reference this panel in actions and gestures')}</span>
              </div>

              <div class="form-group">
                <label for="fld-unlock-code">${t('Panel pin')}</label>
                <ha-input
                  id="fld-unlock-code"
                  name="unlock_code"
                  type="password"
                  .value=${ep.data.unlock_code || ""}
                  style="width: 100%"
                  @input=${(e) => {
                    this._editingPanel = {
                      ...this._editingPanel,
                      data: { ...this._editingPanel.data, unlock_code: e.target.value },
                    };
                    this.requestUpdate();
                  }}
                ></ha-input>
                <span class="field-hint">${t('Set a PIN code to lock this panel. Users must enter this code before accessing the panel.')}</span>
              </div>

              <div class="form-group">
                <div class="checkbox-row">
                  <ha-switch
                    id="fld-show-in-nav"
                    ?checked=${ep.data.show_in_navigation !== false}
                    @change=${(e) => {
                      this._editingPanel = {
                        ...this._editingPanel,
                        data: { ...this._editingPanel.data, show_in_navigation: e.target.checked },
                      };
                      this.requestUpdate();
                    }}
                  ></ha-switch>
                  <label for="fld-show-in-nav">${t('Show in navigation')}</label>
                </div>
                <span class="field-hint">${t("When unchecked, panel is only reachable via stack (item actions, gestures, or as home/sleep/wakeup panel)")}</span>
              </div>
            </div>
          </details>

          ${this.error
            ? html`<ha-alert alert-type="error" style="margin-top:12px">${this.error}</ha-alert>`
            : ""}

          </div>
        </form>

        <div slot="footer" class="footer-wrapper">
          <ha-dialog-footer>
            <ha-button
              slot="secondaryAction"
              variant="neutral"
              appearance="plain"
              @click=${this._dispatchClose}
            >
              ${t('Cancel')}
            </ha-button>
            <ha-button
              slot="primaryAction"
              variant="brand"
              @click=${this._dispatchSave}
              ?disabled=${this.saving}
            >
              ${saveLabel}
            </ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }

  _onTypeChange(e) {
    const newType = e.detail.value;
    // Idempotency guard: ha-select fires @selected synchronously on user
    // interaction only, but a re-rendered ha-select may fire the event again
    // with its restored .value.  Skip if the type hasn't actually changed.
    if (newType === this._editingPanelType) return;

    this._editingPanelType = newType;
    this._userSelectedType = true;
    this._itemListData = {};
    if (this.panel) {
      // Preserve live-edited fields from _editingPanel.data when changing type.
      const liveData = this._editingPanel?.data || this.panel.data;
      this._editingPanel = {
        ...this.panel,
        data: {
          ...liveData,
          type: newType,
          key: generateAutoKey(this.devicePanels, newType),
        },
      };
    }
    this.requestUpdate();
  }

  _dispatchClose() {
    this.dispatchEvent(new CustomEvent("dialog-closed"));
  }

  _dispatchSave() {
    // Read form data from this dialog's own shadow DOM and pass via event detail.
    const form = this.renderRoot.querySelector("#panel-edit-form");
    if (!form) return;
    const ep = this.panel;
    if (!ep) return;

    // Use _editingPanel.data (the live version mutated by renderOptionField's
    // @input/@selected handlers) instead of ep.data (the original prop) so that
    // all user edits (int, float, select, etc.) are captured.
    const liveData = this._editingPanel?.data || ep.data;

    const panelType = this._editingPanelType || liveData?.type || "clock";
    const panel = clone(liveData);
    panel.type = panelType;
    panel.key = formVal(form, "fld-key") || panel.key || "";
    const titleVal = formVal(form, "fld-title");
    if (titleVal) {
      panel.title = titleVal;
    } else {
      delete panel.title;
    }

    const showInNavEl = form.querySelector("#fld-show-in-nav");
    panel.show_in_navigation = showInNavEl ? showInNavEl.checked : true;

    // Defensive fallback: if key is still empty, auto-generate one
    if (!panel.key) {
      panel.key = generateAutoKey(this.devicePanels, panelType);
    }

    // Item/item_list data lives in _itemListData; remove from panel so
    // saveFromData handles them exclusively via serializeItem.
    const descriptor = this.panelTypes.find((pt) => pt.type_key === panelType);
    if (descriptor?.options) {
      for (const opt of descriptor.options) {
        if (opt.kind === "item" || opt.kind === "item_list") {
          delete panel[opt.key];
        }
      }
    }

    this.dispatchEvent(new CustomEvent("dialog-save", {
      detail: { panel, panelType, index: ep.index, itemListData: this._itemListData },
    }));
  }

  /* ── item inline editor (renderOptionField calls these on dialog host) ─ */

  _saveItemEdit() {
    saveItemEdit(this);
  }

  _cancelItemEdit() {
    cancelItemEdit(this);
  }
}

customElements.define("ha-dialog-edit-panel", EditPanelDialog);
export { EditPanelDialog };
