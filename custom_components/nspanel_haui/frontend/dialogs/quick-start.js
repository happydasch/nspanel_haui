// @ts-check
/**
 * NSPanel HAUI - the quick start of a device without panels.
 *
 * A device's configuration is more than one page: it needs a home screen, an
 * idle panel and whatever further pages the user reaches from the header.
 * This dialog sets one up in two steps - choose a configuration for a use case
 * (`presets.js`), then the few choices that configuration offers: the theme the
 * device draws in, the area it resolves against, the optional pages, the Wi-Fi
 * name. What its pages are is the configuration's own decision - whether the
 * home page is a grid of tiles or a row of entities is not a choice here. The
 * second step reads top to bottom: the chosen configuration's name and sentence,
 * the controls that fill it in, the pages it creates with the hub's render of
 * each and their role markers, and the banner under them with what it still
 * needs.
 *
 * The dialog is a chooser only. It resolves nothing: the flow
 * (`quick-start-flow.js`) resolves every preset against the user's Home
 * Assistant and hands the results in, and it writes the pages and the device
 * settings when the user creates them.
 */
import { html, nothing } from '../lit-import.js';
import { t } from '../localize.js';
import { dialogHeader } from './dialog-header.js';
import { HauiDialog } from './haui-dialog.js';
import { renderField, renderSelect, renderToggleField } from '../form-fields.js';
import { emptyState } from '../ui/empty-state.js';
import { icon } from '../ui/icon.js';
import { panelRoleMarker } from '../ui/panel-role.js';

class QuickStartDialog extends HauiDialog {
  /** @returns {any} */
  static get properties() {
    return {
      ...super.properties,
      deviceName: { type: String },
      /** The preset catalog, each with the hub's render of its home page. */
      presets: { type: Array },
      /** The selected preset resolved with the current choices. */
      resolution: { type: Object },
      /** `{ preset, areaId, themeId, toggles, essid, password }` */
      choices: { type: Object },
      /** `[{ area_id, name }]` */
      areas: { type: Array },
      /** The theme choices, `[{ value, label }]` of the hub's themes. */
      themeOptions: { type: Array },
      saving: { type: Boolean },
      error: { type: String },
    };
  }

  constructor() {
    super();
    this.deviceName = '';
    this.presets = [];
    this.resolution = null;
    this.choices = null;
    this.areas = [];
    this.themeOptions = [];
    this.saving = false;
    this.error = '';
  }

  /** @param {Object<string, any>} choices */
  _choose(choices) {
    this._emit('quick-start-choose', choices);
  }

  /* ── step 1: the configurations ───────────────────────────────────────── */

  /**
   * One configuration: its name, the hub's render of the home page it creates,
   * and what it is for. How big it is and what it still needs belong to the
   * second step, which resolves it again with the choices made there.
   * @param {any} preset
   */
  _presetCard(preset) {
    return html`<button type="button" class="haui-quick-start-card" data-preset=${preset.key}
      aria-label=${t('Set up {name}').replace('{name}', preset.label)}
      ?disabled=${this.saving}
      @click=${() => this._choose({ preset: preset.key })}>
      <div class="haui-quick-start-preview">
        ${preset.preview || html`<span class="haui-quick-start-preview-empty">${icon(preset.icon)}</span>`}
      </div>
      <div class="haui-quick-start-copy">
        <p class="haui-quick-start-title">${icon(preset.icon)}${preset.label}</p>
        <p class="haui-quick-start-description">${preset.description}</p>
        ${preset.error
          ? html`<p class="haui-quick-start-error" role="alert">${preset.error}</p>`
          : nothing}
      </div>
    </button>`;
  }

  _chooseStep() {
    return html`
      <p class="haui-quick-start-intro">${t('Start from a configuration for how you use the panel. Its entities are filled in from your Home Assistant, and you can change everything in the editor afterwards.')}</p>
      ${this.presets.length
        ? html`<div class="haui-quick-start-list">
            ${this.presets.map((preset) => this._presetCard(preset))}
          </div>`
        : emptyState({ message: t('This hub offers no configurations.'), iconName: null })}
    `;
  }

  /* ── step 2: the choices ──────────────────────────────────────────────── */

  /** @param {string} key @param {boolean} on */
  _toggle(key, on) {
    this._choose({ toggles: { ...(this.choices?.toggles || {}), [key]: on } });
  }

  /**
   * A count with its unit: "1 entity", "4 entities".
   * @param {number} count
   * @param {string} one
   * @param {string} many - a string with a `{count}` placeholder
   */
  _count(count, one, many) {
    return count === 1 ? one : many.replace('{count}', String(count));
  }

  /**
   * The area the preset resolves against, as a native select.
   *
   * The explanation is the shared floating hint only, never a native `title`
   * beside it: the browser would draw its own tooltip and the hint at the same
   * time. The hint is an always-visible line where a pointer cannot hover, so a
   * touch device loses nothing.
   */
  _areaField() {
    const options = this.areas.map((area) => ({ value: area.area_id, label: area.name }));
    const hint = t('The entities this setup fills come from this area.');
    return renderField({
      id: 'quick-start-area',
      label: t('Area'),
      hint,
      control: renderSelect(
        'quick-start-area',
        this.choices?.areaId || '',
        options,
        (areaId) => this._choose({ areaId }),
        { placeholder: t('Choose an area') },
      ),
    });
  }

  /**
   * The theme the device draws in. It is a device setting, not a choice of the
   * configuration, but the setup writes it: the pages it creates are coloured
   * from it and the gallery renders in it.
   */
  _themeField() {
    return renderField({
      id: 'quick-start-theme',
      label: t('Theme'),
      hint: t('The colors this panel draws with. The pages this setup creates take them too.'),
      control: renderSelect(
        'quick-start-theme',
        this.choices?.themeId || '',
        this.themeOptions || [],
        (themeId) => this._choose({ themeId }),
      ),
    });
  }

  /** @param {any} toggle */
  _toggleField(toggle) {
    return renderToggleField({
      id: `quick-start-toggle-${toggle.key}`,
      checked: toggle.on,
      label: toggle.label,
      hint: toggle.description,
      onChange: (on) => this._toggle(toggle.key, on),
    });
  }

  _wifiFields() {
    const network = t('The network the code joins.');
    const example = t('The preview uses an example network.');
    return html`
      ${renderField({
        id: 'quick-start-essid',
        label: t('Network name'),
        hint: network,
        control: html`<input id="quick-start-essid" class="haui-input" type="text"
          .value=${this.choices?.essid || ''}
          placeholder=${t('Your Wi-Fi network')}
          @input=${(event) => this._choose({ essid: event.target.value })} />`,
      })}
      ${renderField({
        id: 'quick-start-password',
        label: t('Password'),
        hint: example,
        control: html`<input id="quick-start-password" class="haui-input" type="password"
          .value=${this.choices?.password || ''}
          @input=${(event) => this._choose({ password: event.target.value })} />`,
      })}`;
  }

  /**
   * Where a page sits on the device, drawn as the panel list draws it on a row:
   * the role's icon, with the role's own name on the marker.
   * @param {any} page
   */
  _roleMarker(page) {
    return panelRoleMarker({ role: page.node, extra: page.role === 'idle_extra' });
  }

  /**
   * One page of the setup: the hub's render of it, what it is for, and the
   * panel type behind it with how many entities it holds.
   * @param {any} page
   */
  _pageCard(page) {
    const count = this._count(page.entityCount || 0, t('1 entity'), t('{count} entities'));
    return html`<div class="haui-quick-start-page" data-page=${page.id}
      title=${page.typeDescription || nothing}>
      <div class="haui-quick-start-page-preview">
        ${page.preview || html`<span class="haui-quick-start-preview-empty">${icon('panels')}</span>`}
      </div>
      <div class="haui-quick-start-page-copy">
        <div class="haui-quick-start-page-head">
          <span class="haui-quick-start-page-title">${page.label}</span>
          ${this._roleMarker(page)}
        </div>
        <p class="haui-quick-start-page-meta">${page.typeLabel} · ${count}</p>
      </div>
    </div>`;
  }

  /**
   * The pages the setup creates, each with the hub's render of it, under a
   * heading that counts them: how many pages, and what they hold.
   * @param {any} resolution
   */
  _pageGallery(resolution) {
    const pages = this._count(resolution.pages.length, t('1 page'), t('{count} pages'));
    const entities = this._count(
      resolution.entityCount || 0, t('1 entity'), t('{count} entities'),
    );
    return html`<div class="haui-quick-start-pages">
      <div class="haui-quick-start-pages-head">
        <h3 class="haui-quick-start-section-title">${t('Pages')}</h3>
        <p class="haui-quick-start-pages-meta">${pages} · ${entities}</p>
      </div>
      <div class="haui-quick-start-page-list">
        ${resolution.pages.map((page) => this._pageCard(page))}
      </div>
    </div>`;
  }

  /** Why the setup cannot be created yet, as it is resolved. */
  _readiness(resolution) {
    if (resolution.blocked.length) {
      return t('Needs a {domains} entity, and Home Assistant has none')
        .replace('{domains}', resolution.blocked.join(', '));
    }
    if (resolution.needsInput.length) {
      return t('Needs {fields}')
        .replace('{fields}', resolution.needsInput.map((input) => input.label).join(', '));
    }
    return '';
  }

  /**
   * What the setup still needs and what it leaves out, as a banner under the
   * pages and the switches for the optional ones: an error while it cannot be
   * created, a warning for the remarks it carries while it can, and nothing
   * when it is neither.
   * @param {any} resolution
   * @param {string} readiness - why it cannot be created yet, '' when it can
   */
  _outcome(resolution, readiness) {
    const warnings = resolution.warnings || [];
    if (!readiness && !warnings.length) return nothing;
    return html`<ha-alert class="haui-quick-start-outcome"
      alert-type=${readiness ? 'error' : 'warning'}
      .title=${readiness}>
      ${warnings.length
        ? html`<ul class="haui-quick-start-warnings">
            ${warnings.map((warning) => html`<li>${warning}</li>`)}
          </ul>`
        : nothing}
    </ha-alert>`;
  }

  /**
   * The chosen configuration's name and what it is for, as the dialog's intro:
   * the first thing the second step says, above its controls.
   * @param {any} preset
   */
  _heading(preset) {
    return html`<div class="haui-quick-start-heading">
      <h2 class="haui-quick-start-heading-title">${icon(preset.icon)}${preset.label}</h2>
      <p class="haui-quick-start-heading-copy">${preset.description}</p>
    </div>`;
  }

  /** @param {any} preset */
  _optionsStep(preset) {
    const resolution = this.resolution;
    const wifi = resolution?.pages.some((page) => page.panel.type === 'qr') === true;
    const readiness = resolution && !resolution.ready
      ? this._readiness(resolution) || (preset.needsArea && !this.choices?.areaId
        ? t('Choose an area to fill this in') : '')
      : '';
    const toggles = (resolution?.toggles || [])
      .filter((toggle) => toggle.available !== false);
    // The switches add optional pages to the gallery, so they sit under it and
    // above the banner that says what the setup leaves out.
    return html`
      ${this._heading(preset)}
      <div class="haui-quick-start-setup">
        <section class="haui-quick-start-form" aria-label=${preset.label}>
          <div class="haui-field-pair">${this._themeField()}</div>
          ${preset.needsArea ? html`<div class="haui-field-pair">${this._areaField()}</div>` : nothing}
          ${wifi ? html`<div class="haui-field-pair">${this._wifiFields()}</div>` : nothing}
        </section>
        <section class="haui-quick-start-result" aria-label=${t('Pages')}>
          ${resolution ? this._pageGallery(resolution) : nothing}
        </section>
        ${toggles.length
          ? html`<div class="haui-quick-start-toggles">
              ${toggles.map((toggle) => this._toggleField(toggle))}
            </div>`
          : nothing}
        ${resolution ? this._outcome(resolution, readiness) : nothing}
      </div>
    `;
  }

  /** @param {any} preset */
  _footer(preset) {
    if (!preset) return html`
      <ha-button slot="primaryAction" variant="neutral" appearance="plain"
        @click=${this._dispatchClose}>${t('Done')}</ha-button>
    `;
    const create = t('Create {count} pages')
      .replace('{count}', String(this.resolution?.pages.length ?? 0));
    return html`
      <ha-button slot="secondaryAction" variant="neutral" appearance="plain"
        ?disabled=${this.saving}
        @click=${() => this._choose({ preset: null })}>${t('Back')}</ha-button>
      <ha-button slot="primaryAction" variant="brand"
        .disabled=${this.saving || this.resolution?.ready !== true}
        @click=${() => this._emit('quick-start-create')}>${create}</ha-button>
    `;
  }

  _title() {
    return t('Set up {device}').replace('{device}', this.deviceName);
  }

  render() {
    if (!this.deviceName) return nothing;
    const preset = this.choices?.preset
      ? (this.presets || []).find((entry) => entry.key === this.choices.preset)
      : null;
    // Keep HA's modal mounted: removing an open dialog can dismiss its replacement.
    return html`
      <ha-dialog
        class="haui-quick-start-dialog"
        .open=${this.open}
        @closed=${this._dispatchClose}
        header-title=${this._title()}>
        ${dialogHeader(this._title(), this._dispatchClose)}
        <div class="haui-dialog-body haui-quick-start">
          ${this.error
            ? html`<ha-alert class="haui-quick-start-save-error" alert-type="error">${this.error}</ha-alert>`
            : nothing}
          ${preset ? this._optionsStep(preset) : this._chooseStep()}
        </div>
        <div slot="footer" class="haui-footer-wrapper">
          <ha-dialog-footer>${this._footer(preset)}</ha-dialog-footer>
        </div>
      </ha-dialog>
    `;
  }
}

customElements.define('nspanel-dialog-quick-start', QuickStartDialog);
