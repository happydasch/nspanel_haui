# Contributing to NSPanel HAUI

Thanks for helping improve NSPanel HAUI. This page covers the contribution flow; the engineering rules live in
[AGENTS.md](AGENTS.md) and [docs/develop/development.md](docs/develop/development.md).

## Before you start

- Search the existing issues and the [feature wishlist](FEATURE_WISHLIST.md).
- For a large change, open an issue first so the approach can be agreed before the code is written.
- Report security problems privately, as described in [SECURITY.md](SECURITY.md).

## Branches and pull requests

`dev` is the integration branch and the repository's default branch. Commit small changes to `dev` directly,
or branch from `dev` and open the pull request against it.

`master` is release-only. A stable release promotes `dev` into `master` with a pull request; hotfixes of a
released version also branch from `master`. Do not open a pull request against `master` unless you are
promoting or hotfixing a release.

Use a Conventional Commits title, under 100 characters:

```
fix: Keep the notification queue after a display reconnect
feat(climate): Add a fan-only preset
docs: Explain the backup of the stock firmware
```

Fill in the pull request template, including what changed, why, how it was tested, and any device check that
is still unverified. Add a screenshot or recording for frontend or display changes.

## Checks

Run the gates that match your change before pushing:

```bash
make -j4 check          # tests, format, lint, both type checks, docs, version and generated files
make esphome-compile    # firmware change: compile the universal config
```

Backend tests need Python 3.14 and Node 22 or later. Install the environment once with
`pip install -r requirements-dev.txt` and `npm ci`. Frontend and display changes also need the relevant checks
from [docs/develop/development.md](docs/develop/development.md).

Changes to strings need `python -m scripts.translations.extract_translations`. Changes to an HMI or TFT need
both display projects, a `tft_version` bump and `make hmi-check`; see
[docs/develop/nextion-editor.md](docs/develop/nextion-editor.md).

## Documentation

Update `docs/` in the same pull request when behaviour, options, defaults or requirements change. The docs
build strictly with `zensical build --strict`; broken internal links and missing navigation entries fail it.

## AI-assisted contributions

AI-assisted changes are welcome, but you are responsible for understanding, testing and maintaining what you
submit. Do not paste private data from your home into an issue, a pull request or a prompt.
