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
import { encodeItemValue } from '../haui-item.js';
import { ENTITY_OVERRIDE_FIELDS } from '../haui-entity.js';
import { getPanelOptionGroups, renderOptionField } from '../form-fields.js';

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
  }

  willUpdate(changed) {
    if (changed.has("panel") && this.panel) {
      this._editingPanelType = this.panel.data?.type || "clock";
      // Forward _editingPanel and _itemListData for renderOptionField's host access pattern
      this._editingPanel = this.panel;
      this._itemListData = {};
    }
  }

  render() {
    if (!this.panel) return "";
    const ep = this.panel;
    const isAdd = ep.index < 0;
    const panelType = this._editingPanelType || ep.data?.type || "clock";
    const descriptor = this.panelTypes.find((pt) => pt.type_key === panelType);
    const typeLabel = (descriptor ? descriptor.label : panelType);
    const headerTitle = isAdd ? "Add Panel" : `Edit Panel — ${typeLabel}`;
    const saveLabel = this.saving ? "Saving…" : isAdd ? "Add" : "Save";

    return html`
      <ha-dialog
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title=${headerTitle}
        .preventScrimClose=${this.saving}
      >

        <form id="panel-edit-form" @submit=${(e) => e.preventDefault()}>
          <div class="dialog-body">

          ${isAdd ? html`
            <div class="form-group">
              <label for="fld-type">Panel Type</label>
              <ha-select
                id="fld-type"
                name="type"
                .value=${panelType}
                .options=${this.panelTypes.map((pt) => ({ value: pt.type_key, label: pt.label }))}
                @selected=${this._onTypeChange}
              ></ha-select>
              ${descriptor ? html`<span class="field-hint">${descriptor.description}</span>` : ""}
            </div>
          ` : ""}

          <div class="form-group">
            <label for="fld-title">Panel Title</label>
            <ha-input
              id="fld-title"
              name="title"
              .value=${ep.data.title || ""}
              style="width: 100%"
            ></ha-input>
            <span class="field-hint">Optional display name shown on the panel header. Falls back to panel type if left empty.</span>
          </div>

          ${getPanelOptionGroups(descriptor).map(group => {
            const sectionLabel = group.section || "Configuration";
            return html`
              <details class="config-section">
                <summary>${sectionLabel}</summary>
                <div class="config-section-body">
                  ${group.options.map(opt => renderOptionField(this, opt, ep.data[opt.key]))}
                </div>
              </details>
            `;
          })}

          <details class="config-section">
            <summary>Advanced</summary>
            <div class="config-section-body">
              <div class="form-group">
                <label for="fld-key">Key</label>
                <ha-input
                  id="fld-key"
                  name="key"
                  .value=${ep.data.key || ""}
                  style="width: 100%"
                ></ha-input>
                <span class="field-hint">Used to reference this panel in actions and gestures</span>
              </div>

              <div class="checkbox-row">
                <ha-checkbox
                  id="fld-show-in-nav"
                  ?checked=${ep.data.show_in_navigation !== false}
                ></ha-checkbox>
                <label for="fld-show-in-nav">Show in navigation</label>
              </div>
              <span class="field-hint">When unchecked, panel is only reachable via stack (item actions, gestures, or as home/sleep/wakeup panel)</span>
            </div>
          </details>

          ${this.error
            ? html`<ha-alert alert-type="error" style="margin-top:12px">${this.error}</ha-alert>`
            : ""}

          </div>
        </form>

        <ha-dialog-footer slot="footer">
          <ha-button
            slot="secondaryAction"
            appearance="plain"
            @click=${this._dispatchClose}
          >
            Cancel
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
      </ha-dialog>
    `;
  }

  _onTypeChange(e) {
    const newType = e.detail.value;
    this._editingPanelType = newType;
    this._itemListData = {};
    if (this.panel) {
      // Preserve live-edited fields from _editingPanel.data when changing type.
      const liveData = this._editingPanel?.data || this.panel.data;
      this.panel = {
        ...this.panel,
        data: {
          ...liveData,
          type: newType,
          key: generateAutoKey(this.devicePanels, newType),
        },
      };
      // Keep _editingPanel in sync for renderOptionField's host access pattern
      this._editingPanel = this.panel;
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
    // all user edits (color_seed, color_mode, int, float, select, etc.) are captured.
    const liveData = this._editingPanel?.data || ep.data;

    const panelType = this._editingPanelType || liveData?.type || "clock";
    const panel = clone(liveData);
    panel.type = panelType;
    panel.key = formVal(form, "fld-key") || panel.key || "";
    panel.title = formVal(form, "fld-title") || "";

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
    const ee = this._editingItem;
    if (!ee) return;
    const { optKey, index } = ee;

    const uid = `item-edit-${optKey}-${index}`;
    const inline = this.renderRoot.querySelector(`#${uid}`);
    if (!inline) return;

    const typeVal = this._editingItemType || inline.querySelector("#item-type")?.value || "entity_id";

    // Encode item value based on type
    const inputVal = formVal(inline, "item-entity");
    const config = { item: encodeItemValue(inputVal, typeVal) };

    // Read standard entity override fields
    for (const f of ENTITY_OVERRIDE_FIELDS) {
      const fv = formVal(inline, `item-${f}`);
      if (fv) config[f] = fv;
    }

    // Read per-item appearance overrides (declared by the panel type descriptor).
    // Read from ee.config (not DOM) — renderItemOptionField mutates ee.config via
    // setVal, which correctly handles bool checkboxes that formVal cannot.
    const savePt = this._editingPanelType || this._editingPanel?.data?.type;
    const descriptor = (savePt && this.panelTypes)
      ? this.panelTypes.find(d => d.type_key === savePt) || null
      : null;
    if (descriptor?.item_options) {
      for (const f of descriptor.item_options) {
        const fv = ee.config?.[f];
        if (fv !== null && fv !== undefined && fv !== '') config[f] = fv;
      }
    }

    if (!this._itemListData) this._itemListData = {};
    if (!this._itemListData[optKey]) this._itemListData[optKey] = [];

    if (index >= 0) {
      const updated = [...this._itemListData[optKey]];
      updated[index] = config;
      this._itemListData[optKey] = updated;
    } else {
      this._itemListData[optKey] = [...this._itemListData[optKey], config];
    }

    this._editingItem = null;
    this._editingItemType = null;
    this.requestUpdate();
  }

  _cancelItemEdit() {
    this._editingItem = null;
    this._editingItemType = null;
    this.requestUpdate();
  }
}

customElements.define("ha-dialog-edit-panel", EditPanelDialog);
export { EditPanelDialog };
