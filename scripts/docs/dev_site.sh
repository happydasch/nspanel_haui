#!/usr/bin/env bash
# Point mkdocs.yml at the dev site, published under /dev/ (the editor footer
# links prerelease versions there): its own site_url, repo link and edit links.
# CI runs it in a dev checkout before `zensical build` (ci.yml: docs and
# deploy-docs). Run from the repository root; needs GNU sed.
set -euo pipefail

sed -i \
  -e 's#^site_url: .*#site_url: https://happydasch.github.io/nspanel_haui/dev/#' \
  -e 's#^repo_url: .*#repo_url: https://github.com/happydasch/nspanel_haui/tree/dev#' \
  -e 's#^edit_uri: edit/master/#edit_uri: edit/dev/#' \
  mkdocs.yml

# sed succeeds even when a line moved or changed shape; a dev site that still
# points at master is a silent failure, so check every rewrite landed.
for line in \
  'site_url: https://happydasch.github.io/nspanel_haui/dev/' \
  'repo_url: https://github.com/happydasch/nspanel_haui/tree/dev' \
  'edit_uri: edit/dev/docs/'; do
  grep -qxF "$line" mkdocs.yml || { echo "mkdocs.yml: missing '$line'" >&2; exit 1; }
done
