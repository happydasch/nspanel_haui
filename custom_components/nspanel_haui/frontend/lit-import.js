/**
 * NSPanel HAUI - Editor - shared Lit re-export.
 *
 * Every module that needs Lit imports from here instead of the raw CDN URL.
 * This gives us a single place to change the Lit version or switch to a
 * bundled copy without touching every file.
 */
export { LitElement, html, css } from "https://unpkg.com/lit@3?module";
