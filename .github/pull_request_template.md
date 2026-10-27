## What changed

<!-- One or two sentences. Link the issue if there is one: "Closes #123". -->

## Why

<!-- The problem this solves. Skip if the "What changed" line already says it. -->

## How it was tested

<!-- Commands you ran and what you saw. Say plainly if a device passlist item is still unverified. -->

## Checklist

- [ ] Base branch is `dev` (features and fixes) or `master` (hotfix of a released version)
- [ ] Docs in `docs/` updated for behaviour, options or defaults that changed
- [ ] `mkdocs build --strict` passes
- [ ] `pytest tests/` passes
- [ ] `node --test 'tests/frontend/*.test.mjs'` passes (frontend changes only)
- [ ] `ruff check custom_components/` is clean
- [ ] `mypy` is clean
- [ ] Breaking changes documented in `docs/upgrading.md` and the CHANGELOG "Breaking changes" section
- [ ] Screenshot or short recording attached for display/frontend changes
