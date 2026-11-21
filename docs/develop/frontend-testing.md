---
title: Tests
description: How the editor's Node tests are written, what to assert, when to add a test and which local checks cover a change
---

# Tests

Frontend tests protect decisions and observable behaviour, not how the markup or styles happen to be written. They run on Node's built-in runner with the vendored Lit bundle, and `happy-dom` supplies the DOM for tests only.

## Conventions

- Import `tests/frontend/support/browser.mjs` before any module that needs browser globals.
- Render through `support/render.mjs` and find controls with `support/queries.mjs` by role, accessible name, label or text.
- Take Home Assistant and panel fixtures from `support/hass.mjs`, `support/fixtures.mjs` and `tests/frontend/fake-host.mjs`.
- `tests/frontend/ui-primitives-preview.html` renders the shipped primitives in their enabled, open, dirty and empty variants for manual review. A new primitive also needs its demo in `tests/frontend/ui-primitives-preview.js` and a semantic assertion in `ui-primitives.test.mjs`.

## Local checks

| Command | Covers |
|---|---|
| `make test-frontend` (`node --test 'tests/frontend/*.test.mjs'`) | Every editor test |
| `make typecheck-frontend` (`npm run typecheck:frontend`) | The modules marked `// @ts-check` |
| `python scripts/check_frontend_styles.py` | The style rules on the [visual foundations](frontend-visuals.md) page |

## When to add a test

| Change | Add a test? | Assert |
|---|---|---|
| Pure formatter, mapper or utility | Yes, one case per branch | Exact return values |
| Store action or selector | Yes | The state transition |
| API client method | Yes | Request shape and returned value |
| New UI primitive or composite | Yes | Semantics, accessible name, callback payload |
| View composition | Only its decision branches | Empty state, disabled action, chosen callback |
| Element lifecycle (dialog, workspace, shell) | Yes for the changed branches | Mount, interact, observed event, state or result |
| Simulator behaviour | Yes | Parsed display state or emitted ESP command |
| Styling, layout, colour or spacing | No | Review in the editor preview or the gallery |
| Copy or translation text | No | A translation mapping only when it is the subject |
| Behaviour-preserving refactor | No new test | Existing behaviour tests stay green without markup-driven edits |

## Assertion boundaries

Prefer return values, emitted events and store state; then real DOM roles, accessible names, text, control presence and meaning-carrying attributes (`aria-*`, `disabled`, `href`, `checked`). Use a functional state class such as `is-*` only when no semantic alternative exists. Do not assert CSS text, pixel geometry, inline style strings, Lit `TemplateResult.strings` or `values`, or private members, and do not fabricate an element with `Object.create(prototype)`: dispatch real DOM events instead of reaching into template callbacks.

One test covers one behaviour and one module; split a file around 300 lines or when it covers more than two modules. Tests never depend on run order and leave no global state patched. Delete an assertion whose subject is presentation or an implementation detail, and when a rename only needs an assertion changed because markup or copy moved, remove it instead of re-pinning it.
