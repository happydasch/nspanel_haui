/** Panel editor layout and preview-specific rules. */
import { css } from '../lit-import.js';

export const panelEditorStyles = css`
  .haui-panel-editor-sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .haui-panel-editor-sidebar > #panel-edit-form {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    box-sizing: border-box;
    overscroll-behavior: contain;
  }
  /* The padding is the body's, not the scroll container's: a sticky bar pins to the very top. */
  .haui-panel-editor-sidebar .haui-dialog-body { padding: 16px; }
  .haui-panel-editor-preview { margin-bottom: 16px; }
  .haui-panel-editor-preview nspanel-simulator-frame {
    display: block;
    max-width: min(100%, 480px);
    margin: 0 auto;
    overflow: hidden;
    border: 1px solid var(--divider-color);
    border-radius: var(--haui-radius-control);
    box-sizing: border-box;
  }
  .haui-panel-editor-preview nspanel-simulator-frame[portrait] { max-width: 180px; }
  /* Once the preview has scrolled away, a small copy with the panel's name
     and type stays pinned above the form. It overlays the form from a
     zero-height sticky anchor, so showing it moves nothing. */
  .haui-panel-editor-pin { position: sticky; z-index: 2; top: 0; height: 0; }
  .haui-panel-editor-pin-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--divider-color);
    background: var(--card-background-color);
    box-shadow: var(--haui-shadow-card);
    opacity: 0;
    transform: translateY(-6px);
    visibility: hidden;
    transition: opacity 140ms ease, transform 140ms ease, visibility 0s linear 140ms;
  }
  .haui-panel-editor-pin-bar.is-shown { opacity: 1; transform: none; visibility: visible; transition-delay: 0s; }
  .haui-panel-editor-pin-thumb { flex: 0 0 auto; width: 84px; }
  .haui-panel-editor-pin-thumb.is-portrait { width: 40px; }
  .haui-panel-editor-pin-thumb nspanel-simulator-frame {
    display: block;
    overflow: hidden;
    border: 1px solid var(--divider-color);
    border-radius: var(--haui-radius-control);
  }
  .haui-panel-editor-pin-text { display: grid; min-width: 0; gap: 4px; }
  .haui-panel-editor-pin-text > * { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .haui-panel-editor-pin-text strong { font-size: var(--haui-text-body); font-weight: 600; }
  .haui-panel-editor-pin-text span { color: var(--secondary-text-color); font-size: var(--haui-text-caption); }
  @media (prefers-reduced-motion: reduce) { .haui-panel-editor-pin-bar { transition: none; } }
  .haui-panel-editor-alert { margin-top: 12px; }
`;
