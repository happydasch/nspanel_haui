#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
git config core.hooksPath scripts/git_hooks
printf 'Installed repository hooks from %s\n' scripts/git_hooks
