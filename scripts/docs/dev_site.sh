#!/usr/bin/env bash
# Point mkdocs.yml at the dev site (published under /dev/, where the editor's footer
# links prerelease versions): its own site_url, repo link and edit links. CI runs it
# before `zensical build`; run it from the repository root. Needs GNU sed.
set -euo pipefail

sed -i \
  -e 's#^site_url: .*#site_url: https://happydasch.github.io/nspanel_haui/dev/#' \
  -e 's#^repo_url: .*#repo_url: https://github.com/happydasch/nspanel_haui/tree/dev#' \
  -e 's#^edit_uri: edit/master/#edit_uri: edit/dev/#' \
  mkdocs.yml

# sed succeeds even when a line moved or changed shape, so check every rewrite landed.
for line in \
  'site_url: https://happydasch.github.io/nspanel_haui/dev/' \
  'repo_url: https://github.com/happydasch/nspanel_haui/tree/dev' \
  'edit_uri: edit/dev/docs/'; do
  grep -qxF "$line" mkdocs.yml || { echo "mkdocs.yml: missing '$line'" >&2; exit 1; }
done
