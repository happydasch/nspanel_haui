## What changed

<!-- One or two sentences. Link the issue if there is one: "Closes #123". -->

## Why

<!-- The problem this solves. Skip if the "What changed" line already says it. -->

## How it was tested

<!-- Commands you ran and what you saw. Say plainly if a device passlist item is still unverified. -->

## Checklist

- [ ] Base branch is `dev` (features and fixes) or `master` (hotfix of a released version)
- [ ] Docs in `docs/` updated for behaviour, options or defaults that changed
- [ ] `zensical build --strict` passes
- [ ] `pytest tests/` passes
- [ ] `npm ci` (once per clone), then `node --test 'tests/frontend/*.test.mjs'` and `npm run typecheck:frontend` pass (frontend changes only)
- [ ] `ruff format --check custom_components/ scripts/ tests/` and `ruff check custom_components/ scripts/` are clean
- [ ] `mypy` is clean
- [ ] Breaking changes documented in `docs/user/update.md` and the CHANGELOG "Breaking changes" section
- [ ] Screenshot or short recording attached for display/frontend changes
