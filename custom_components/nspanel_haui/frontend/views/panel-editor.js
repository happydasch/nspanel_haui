/**
 * NSPanel HAUI - panel editor view.
 *
 * Renders the shared panel form in the Device sidebar and preserves its
 * existing modal presentation for routes that still use the legacy shell.
 *
 * Maintains its own form state (panel type, title, config options, key, show_in_nav)
 * to avoid polluting the editor's state surface.
 */
import { html, nothing } from '../lit-import.js';
import { clone, isPortraitModel } from '../constants.js';
import { formVal } from '../dom-helpers.js';
import {
  getPanelOptionGroups, renderField, renderNumberInput, renderOptionField, renderSelect,
  renderToggleField,
} from '../form-fields.js';
import { dialogHeader } from '../dialogs/dialog-header.js';
import { HauiDialog } from '../dialogs/haui-dialog.js';
import { t } from '../localize.js';
import { buildPanelConfig, generateAutoKey, panelKeyError } from '../crud.js';
import { renderSimulatorPreview } from '../previews/simulator-frame.js';
import { sidebarFooterStyles } from '../styles/sidebar-footer.js';
import { panelEditorStyles } from '../styles/panel-editor-styles.js';

// Options that hold the panel's list of items.
const ITEM_LIST_KINDS = ['item_list', 'list_items', 'list_entities'];
// The pinned preview bar's height: it takes over as the full preview's last part scrolls under it.
const PIN_BAR_HEIGHT = 77;

/**
 * A random entity of the domain, preferring one with a state: an unavailable
 * entity still shows the popup's layout.
 * @param {Record<string, {state: string}>} states
 * @param {string} domain
 * @returns {string|null}
 */
function randomEntity(states, domain) {
  const ids = Object.keys(states).filter((id) => id.startsWith(`${domain}.`));
  const known = ids.filter((id) => !['unavailable', 'unknown'].includes(states[id].state));
  const pool = known.length ? known : ids;
  return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
}

class PanelEditor extends HauiDialog {

  static styles = [...HauiDialog.styles, sidebarFooterStyles, panelEditorStyles];
  static get properties() {
    return {
      api: { type: Object },
      inline: { type: Boolean },
      panel: { type: Object },
      panelTypes: { type: Array },
      saving: { type: Boolean },
      error: { type: String },
      entryId: { type: String },
      devicePanels: { type: Array },
      systemPanels: { type: Array },
      dialogVersion: { type: Number },
      // What the hub renders the panel with: { entryId, device, deviceConfig, panels, deviceInfo, api }.
      previewContext: { type: Object },
      _previewPanel: { state: true },
      _previewPinned: { state: true },
    };
  }

  constructor() {
    super();
    this.inline = false;
    this.api = null;
    this.panel = null;
    this.panelTypes = [];
    this.saving = false;
    this.error = null;
    this.entryId = null;
    this.devicePanels = [];
    this.systemPanels = [];
    this._editingPanelType = null;
    this._editingPanel = null;
    this._itemListData = {};
    this._userSelectedType = false;
    this._dialogVersion = 0;
    this.previewContext = null;
    this._previewPanel = null;
    this._previewPinned = false;
  }

  willUpdate(changed) {
    if ((changed.has("open") && this.open) || changed.has("dialogVersion")) {
      // Reset user type selection each time the dialog opens or a new panel
      // session starts. The dialogVersion counter is incremented by the parent
      // for every open/close/open cycle, ensuring the reset fires even when
      // open doesn't change (e.g. close + reopen in separate microtasks
      // before Lit renders the intermediate null state).
      this._userSelectedType = false;
      // An item left open in the previous session would keep Save disabled.
      this._editingItem = null;
      this._editingItemType = null;
      this._previewPanel = null;
      this.__previewJson = null;
      this.__sample = null;
      this._previewPinned = false;
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


  /** Update one panel field without duplicating the immutable edit-state write. */
  _setPanelValue(key, value) {
    this._editingPanel = {
      ...this._editingPanel,
      data: { ...this._editingPanel.data, [key]: value },
    };
    this.requestUpdate();
  }
  render() {
    if (!this.panel) return "";
    // Always prefer the dialog's own _editingPanel over the parent's panel prop.
    // The parent's _editingPanel reference is never updated on type change, so
    // relying on "this._editingPanel || this.panel" means the parent's stale
    // data would overwrite the user's type selection on re-render.
    // Instead, once _userSelectedType is true, ALWAYS use _editingPanel.
    const ep = (this._userSelectedType && this._editingPanel) ? this._editingPanel : (this._editingPanel || this.panel);
    const sysPanel = this._sysPanel();
    // A system panel's first edit has no index yet, but it is not a new panel.
    const isAdd = ep.index < 0 && !sysPanel;
    const panelType = this._editingPanelType || ep.data?.type || "clock";
    const descriptor = this.panelTypes.find((pt) => pt.type_key === panelType);
    const typeLabel = sysPanel ? sysPanel.label : descriptor ? descriptor.label : panelType;
    const headerTitle = isAdd ? t('Add Panel') : `${t('Edit Panel')} — ${typeLabel}`;
    const saveLabel = this.saving ? t('Saving...') : isAdd ? t('Add') : t('Save');
    const errors = this._fieldErrors();
    // The rich item list is edited in _itemListData; the panel data is its saved state.
    const itemCount = (options) => options.reduce((count, opt) => {
      const list = this._itemListData?.[opt.key] ?? ep.data[opt.key];
      return count + (Array.isArray(list) ? list.length : 0);
    }, 0);

    const content = html`
        ${this._renderHeader(headerTitle)}

        <form id="panel-edit-form" @submit=${(e) => e.preventDefault()}
          @scroll=${this.inline ? this._onFormScroll : null}>
          ${this.inline
            ? this._renderPinnedPreview(sysPanel, ep.data.title || typeLabel,
                [typeLabel, ep.data.key].filter(Boolean).join(' · '))
            : nothing}
          <div class="haui-dialog-body">

          ${this._renderPreview(sysPanel)}

          ${isAdd ? renderField({
            id: 'fld-type',
            label: t('Panel type'),
            control: html`<div class="haui-field-row">
              ${descriptor?.icon ? html`<ha-icon .icon=${descriptor.icon}></ha-icon>` : nothing}
              ${renderSelect('fld-type', panelType,
                this.panelTypes.map((pt) => ({ value: pt.type_key, label: pt.label })),
                (value) => this._onTypeChange(value))}
            </div>`,
            hint: descriptor?.description || '',
          }) : nothing}

          ${renderField({
            id: 'fld-title',
            label: t('Panel title'),
            control: html`<input id="fld-title" name="title" class="haui-input"
              .value=${ep.data.title || ''}
              @input=${(event) => this._setPanelValue('title', event.target.value)} />`,
            hint: t('Title shown on the panel header. Falls back to the panel type name if left empty.'),
          })}

          ${getPanelOptionGroups(descriptor).map(group => {
            const sectionLabel = group.section ? group.section : t('Configuration');
            // A section holding lists counts their entries; the one with the panel's items opens with the form.
            const lists = group.options.filter((opt) => ITEM_LIST_KINDS.includes(opt.kind));
            return html`
              <details class="haui-config-section" ?open=${lists.some((opt) => opt.kind === 'item_list')}>
                <summary>
                  ${sectionLabel}
                  ${lists.length ? html`<span class="haui-config-section-count"
                    title=${t('{count} items').replace('{count}', String(itemCount(lists)))}
                  >${itemCount(lists)}</span>` : nothing}
                </summary>
                <div class="haui-config-section-body">
                  ${group.options.map(opt => renderOptionField(this, opt, ep.data[opt.key]))}
                </div>
              </details>
            `;
          })}

          ${sysPanel?.hub_driven ? "" : html`
          <details class="haui-config-section">
            <summary>${t('Advanced')}</summary>
            <div class="haui-config-section-body">

              ${sysPanel ? nothing : renderField({
                id: 'fld-key',
                label: t('Panel key'),
                control: html`<input id="fld-key" name="key" class="haui-input"
                  aria-invalid=${errors.has('fld-key') ? 'true' : nothing}
                  aria-describedby=${errors.has('fld-key') ? 'fld-key-error' : nothing}
                  .value=${ep.data.key || ''}
                  @input=${(event) => this._setPanelValue('key', event.target.value)} />`,
                hint: t('Used to reference this panel in actions and gestures'),
                extra: errors.has('fld-key')
                  ? html`<span class="haui-field-error" id="fld-key-error" role="alert">${errors.get('fld-key')}</span>`
                  : nothing,
              })}

              ${renderField({
                id: 'fld-unlock-code',
                label: t('Panel pin'),
                control: html`<input id="fld-unlock-code" name="unlock_code" type="password"
                  inputmode="numeric" class="haui-input"
                  aria-invalid=${errors.has('fld-unlock-code') ? 'true' : nothing}
                  aria-describedby=${errors.has('fld-unlock-code') ? 'fld-unlock-code-error' : nothing}
                  .value=${ep.data.unlock_code || ''}
                  @input=${(event) => this._setPanelValue('unlock_code', event.target.value)} />`,
                hint: t('Set a PIN code to lock this panel. Users must enter this code before accessing the panel.'),
                extra: errors.has('fld-unlock-code')
                  ? html`<span class="haui-field-error" id="fld-unlock-code-error" role="alert">${errors.get('fld-unlock-code')}</span>`
                  : nothing,
              })}

              ${sysPanel ? nothing : renderToggleField({
                id: 'fld-show-in-nav',
                checked: ep.data.show_in_navigation !== false,
                label: t('Show in navigation'),
                hint: t("When unchecked, panel is only reachable via stack (item actions, gestures, or as the home/idle panel)"),
                onChange: (checked) => this._setPanelValue('show_in_navigation', checked),
              })}

              ${descriptor?.has_header === false ? renderToggleField({
                id: 'fld-long-press-back',
                checked: ep.data.long_press_back === true,
                label: t('Long press to go back'),
                hint: t('This page has no navigation buttons. Hold anywhere for about a second to go back to the panel it was opened from, or to the home panel.'),
                onChange: (checked) => this._setPanelValue('long_press_back', checked),
              }) : nothing}

              ${renderField({
                id: 'fld-close-timeout',
                label: t('Close automatically after (seconds)'),
                control: renderNumberInput('fld-close-timeout', ep.data.close_timeout ?? 0, (raw) => {
                  const value = parseInt(raw, 10);
                  this._setPanelValue('close_timeout', isNaN(value) || value < 0 ? 0 : value);
                }, { min: 0 }),
                hint: t('Close the panel and go back after this many seconds. 0 = stay open.'),
              })}
            </div>
          </details>
          `}

          ${this.error
            ? html`<ha-alert class="haui-panel-editor-alert" alert-type="error">${this.error}</ha-alert>`
            : ""}

          </div>
        </form>

        <div slot="footer" class="haui-footer-wrapper">
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
              ?disabled=${this.saving || this._editingItem != null || errors.size > 0}
              title=${this._editingItem != null ? t('Apply or cancel the open item first')
                : errors.size ? t('Fix the marked fields first') : ''}
            >
              ${saveLabel}
            </ha-button>
          </ha-dialog-footer>
        </div>
    `;
    if (this.inline) {
      return html`<aside class="haui-panel-editor-sidebar" aria-label=${headerTitle}>
        ${content}
      </aside>`;
    }
    return html`<ha-dialog .open=${this.open} @closed=${this._dispatchClose}>${content}</ha-dialog>`;
  }

  /**
   * The panel as the hub draws it: a user panel with the form's unsaved edits,
   * a popup as the device has it configured (its sample context is the hub's).
   */
  _renderPreview(sysPanel) {
    const frame = this._previewFrame(sysPanel);
    if (frame === nothing) return nothing;
    return html`<div class="haui-panel-editor-preview" aria-label=${t('Panel preview')}>${frame}</div>`;
  }

  /**
   * The preview's small copy with the panel's name, type and key, pinned above the
   * form once the preview has scrolled away (`_onFormScroll`).
   */
  _renderPinnedPreview(sysPanel, name, detail) {
    const frame = this._previewFrame(sysPanel);
    if (frame === nothing) return nothing;
    const portrait = isPortraitModel(this.previewContext?.deviceConfig?.display_model);
    return html`<div class="haui-panel-editor-pin" aria-hidden="true">
      <div class=${`haui-panel-editor-pin-bar${this._previewPinned ? ' is-shown' : ''}`}>
        <span class=${`haui-panel-editor-pin-thumb${portrait ? ' is-portrait' : ''}`}>${frame}</span>
        <span class="haui-panel-editor-pin-text"><strong>${name}</strong><span>${detail}</span></span>
      </div>
    </div>`;
  }

  /** The hub's render of the panel; both frames share it (the previewer keeps one render per key). */
  _previewFrame(sysPanel) {
    const context = this.previewContext;
    const panel = sysPanel ? this.panel?.data : this._previewPanel;
    if (!context || !panel) return nothing;
    const kwargs = sysPanel ? this._popupSample() : null;
    return renderSimulatorPreview(kwargs ? { ...context, kwargs } : context, panel, sysPanel ? -1 : 0);
  }

  /** Pin the small preview once the full one has all but scrolled out of the form. */
  _onFormScroll(event) {
    const preview = this.renderRoot.querySelector('.haui-panel-editor-preview');
    if (!preview) return;
    const top = event.currentTarget.getBoundingClientRect().top;
    const pinned = preview.getBoundingClientRect().bottom < top + PIN_BAR_HEIGHT;
    if (pinned !== this._previewPinned) this._previewPinned = pinned;
  }

  /**
   * What an entity popup's preview opens for while the popup names no entity
   * itself: one of its domain, picked at random once per editing session.
   * @returns {{ item: string, item_id: string }|null}
   */
  _popupSample() {
    const data = this.panel?.data || {};
    const configured = data.item && typeof data.item === 'object' ? data.item.item : data.item;
    if (configured || data.item_id || !this.hass) return null;
    const descriptor = this.panelTypes.find((pt) => pt.type_key === data.type);
    const domain = descriptor?.options?.find((opt) => opt.key === 'item' && opt.kind === 'item')?.domain;
    if (!domain) return null;
    if (this.__sample?.domain !== domain) {
      this.__sample = { domain, entityId: randomEntity(this.hass.states, domain) };
    }
    const { entityId } = this.__sample;
    return entityId ? { item: entityId, item_id: entityId } : null;
  }

  /** The dialog's header; in the sidebar the frame's strip carries the title and the close control. */
  _renderHeader(title) {
    return this.inline ? nothing : dialogHeader(title, this._dispatchClose);
  }

  _onTypeChange(newType) {
    // Idempotency guard: skip if the type hasn't actually changed.
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

  /**
   * The panel the form holds right now, as the save would send it.
   * @returns {{ panel: any, panelType: string, index: number }|null}
   */
  _collectPanel() {
    // Read form data from this dialog's own shadow DOM.
    const form = this.renderRoot?.querySelector?.("#panel-edit-form");
    if (!form) return null;
    const ep = this.panel;
    if (!ep) return null;

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

    const sysPanel = this._sysPanel();
    const showInNavEl = form.querySelector("#fld-show-in-nav");
    panel.show_in_navigation = sysPanel ? false : showInNavEl ? showInNavEl.checked : true;
    // The hub ignores both on the panels it drives (see HUB_DRIVEN_PANELS).
    if (sysPanel?.hub_driven) {
      delete panel.unlock_code;
      delete panel.close_timeout;
    }

    // Defensive fallback: if key is still empty, auto-generate one
    if (!panel.key) {
      panel.key = generateAutoKey(this.devicePanels, panelType);
    }
    return { panel, panelType, index: ep.index };
  }

  _dispatchSave() {
    const collected = this._collectPanel();
    if (!collected || this._fieldErrors().size) return;
    const { panel, panelType, index } = collected;

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

    this._emit("dialog-save", {
      panel, panelType, index, itemListData: this._itemListData,
    });
  }

  /**
   * What is wrong with the form right now, by field id. Save stays disabled
   * while a field is listed.
   * @returns {Map<string, string>}
   */
  _fieldErrors() {
    const errors = new Map();
    const data = this._editingPanel?.data || this.panel?.data || {};
    if (!this._sysPanel()) {
      const keyError = panelKeyError(data.key, {
        panels: this.devicePanels, index: this.panel?.index ?? -1, systemPanels: this.systemPanels,
      });
      if (keyError) errors.set('fld-key', keyError);
      else if (/\s/.test(data.key || '')) errors.set('fld-key', t('A panel key cannot contain spaces'));
    }
    // The unlock keypad on the display only has digits.
    if (data.unlock_code && !/^\d+$/.test(String(data.unlock_code))) {
      errors.set('fld-unlock-code', t('The PIN can only contain digits'));
    }
    return errors;
  }

  /** The hub's render of the form's current state, a moment after the last edit. */
  _schedulePreview() {
    if (!this.previewContext || this._sysPanel()) return;
    const collected = this._collectPanel();
    if (!collected) return;
    const descriptor = this.panelTypes.find((pt) => pt.type_key === collected.panelType);
    const existing = collected.index >= 0 ? this.devicePanels[collected.index] : null;
    const draft = buildPanelConfig(collected.panel, descriptor, this._itemListData, existing);
    const json = JSON.stringify(draft);
    if (json === this.__previewJson) return;
    this.__previewJson = json;
    clearTimeout(this.__previewTimer);
    // Each change asks the hub for a render: wait until the typing pauses.
    this.__previewTimer = setTimeout(() => { this._previewPanel = draft; }, this._previewPanel ? 400 : 0);
  }

  updated(changed) {
    super.updated?.(changed);
    this._schedulePreview();
    // A marked field may sit in a collapsed section: open it once, when the
    // error appears, so the reason Save is disabled is on screen. Later
    // updates leave the section as the user set it.
    const shown = new Set();
    for (const id of this._fieldErrors().keys()) {
      const field = this.renderRoot?.querySelector?.(`#${id}`);
      if (!field) continue;
      shown.add(id);
      if (this.__shownErrors?.has(id)) continue;
      const section = field.closest?.('details');
      if (section && !section.open) section.open = true;
    }
    this.__shownErrors = shown;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this.__previewTimer);
  }

  /**
   * The system panel being edited, found by the key the dialog was opened
   * with — never the live key field, so typing a system key into a user
   * panel does not turn its form into a system panel's.
   * @returns {object|undefined}
   */
  _sysPanel() {
    const key = this.panel?.data?.key;
    return key ? this.systemPanels.find((sp) => sp.key === key) : undefined;
  }
}

customElements.define("nspanel-panel-editor", PanelEditor);
