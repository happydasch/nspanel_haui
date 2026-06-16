/**
 * NSPanel HAUI - Editor - shared Lit re-export.
 *
 * Every module that needs Lit imports from here instead of the raw CDN URL.
 * Lit is vendored locally so the panel works without internet access to
 * unpkg / jsdelivr.  The bundle was created with esbuild from lit@3.
 */
export { LitElement, html, css, nothing } from "./vendor/lit/index.js";
