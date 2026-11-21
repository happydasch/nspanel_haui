// @ts-check
import { html } from '../lit-import.js';
import { t } from '../localize.js';
import { gestureEditor } from './gesture-editor.js';

/**
 * The Gestures group of the device settings: the swipes and the panel each one
 * opens. Every edit goes into the settings draft through `onChange`/`onAdd`, so
 * the sidebar's one Save applies it.
 *
 * @param {{ panels?: any[], systemPanels?: any[], panelTypes?: any[], gestures: any[],
 *   expandedEntryIndex?: number|null,
 *   onEntryToggle?: (index: number, open: boolean) => void,
 *   onChange?: (gestures: any[]) => void,
 *   onAdd?: (gestures: any[]) => void }} data
 */
export function gestureSection({
  panels = [], systemPanels = [], panelTypes = [], gestures, expandedEntryIndex = null,
  onEntryToggle, onChange, onAdd,
}) {
  return html`
    <p class="haui-config-section-intro">${t('Define swipe gestures to move between panels or open a specific panel. Multi-swipe gestures must be completed within their time limit.')}</p>
    ${gestureEditor({
      gestures,
      panels,
      systemPanels,
      panelTypes,
      expandedEntryIndex,
      onEntryToggle: (index, isOpen) => {
        if (!isOpen && expandedEntryIndex === index) onEntryToggle?.(index, isOpen);
      },
      onChange: (next) => onChange?.(next),
      onAdd: (next) => onAdd?.(next),
    })}`;
}
