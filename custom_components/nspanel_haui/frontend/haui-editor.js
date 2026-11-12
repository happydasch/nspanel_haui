// The registered frontend entry point; the editor element lives in app/shell.js.
//
// A page left open across a Home Assistant restart keeps the editor it loaded,
// but when the frontend changed, HA imports this entry again from its new URL
// (the asset digest is part of it, `web/editor.py`). Loading the editor's
// modules a second time would define every element again ("has already been
// used with this registry"), and the editor already in the page fetches its
// assets from the old path, which no longer exists. Only a reload recovers, and
// HA has already removed the old editor, so it loses nothing.
if (globalThis.customElements?.get('nspanel-haui-editor')) {
  globalThis.location.reload();
  await new Promise(() => {});
}

export const { NSPanelEditor } = await import('./app/shell.js');
