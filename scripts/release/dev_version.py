#!/usr/bin/env python3
"""Derive and write the development firmware and display TFT versions."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from scripts.bump_tft_version import shipped_tft_version

_STABLE_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_DEV_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)\.dev\d+")


def version_kind(version: str) -> str | None:
    """Classify a supported release version as stable, dev, or invalid."""
    if _STABLE_RE.fullmatch(version):
        return "stable"
    if _DEV_RE.fullmatch(version):
        return "dev"
    return None


def derive_dev_version(current_version: str, run_number: str | int) -> str:
    """Derive the PEP 440 dev version from the branch version and run number.

    ``run_number`` is the repository-wide GitHub Actions run counter; it is
    deliberately not reset per development cycle, so a new cycle continues the
    global numbering (e.g. ``0.4.6.dev51``) and every build stays unique and
    monotonic even when a run is canceled or its tag push is retried.
    """
    stable = _STABLE_RE.fullmatch(current_version)
    previous_dev = _DEV_RE.fullmatch(current_version)
    if stable:
        major, minor, patch = map(int, stable.groups())
        base = f"{major}.{minor}.{patch + 1}"
    elif previous_dev:
        base = ".".join(previous_dev.groups())
    else:
        raise ValueError(
            f"Expected a stable X.Y.Z or a previous dev version, got {current_version!r}"
        )

    version = f"{base}.dev{run_number}"
    if not _DEV_RE.fullmatch(version):
        raise ValueError(f"{version!r} is not a publishable PEP 440 development version")
    return version


def write_dev_version(root: Path, run_number: str | int, env_file: Path) -> str:
    """Update the integration/firmware version files and the GitHub env."""
    manifest_file = root / "custom_components/nspanel_haui/manifest.json"
    version_file = root / "esphome/nspanel_haui/version.yaml"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    version = derive_dev_version(manifest["version"], run_number)

    source = version_file.read_text(encoding="utf-8")
    source, count = re.subn(
        r"(?m)^(  yaml_version: )'[^']+'$",
        rf"\g<1>'{version}'",
        source,
    )
    if count != 1:
        raise ValueError(f"Expected one yaml_version in {version_file}, found {count}")

    manifest_source = manifest_file.read_text(encoding="utf-8")
    manifest_source, count = re.subn(
        r'(?m)^(  "version": )"[^"]+"(,?)$',
        lambda match: f'{match.group(1)}"{version}"{match.group(2)}',
        manifest_source,
    )
    if count != 1:
        raise ValueError(f"Expected one version in {manifest_file}, found {count}")

    version_file.write_text(source, encoding="utf-8")
    manifest_file.write_text(manifest_source, encoding="utf-8")
    with env_file.open("a", encoding="utf-8") as env:
        env.write(f"DEV_VERSION={version}\n")
    return version


def write_tft_version(root: Path, version: str, env_file: Path) -> None:
    """Write the display TFT version the build ships to version.yaml and the env.

    A dev release ships the committed TFTs under the ``system.tftVersion`` both
    HMIs carry (``shipped_tft_version`` also checks each TFT embeds it), and the
    firmware requires exactly that TFT (``tft_version``, compiled in as
    ``tft_required_version``), so a dev panel installs it once its display
    reports an older one.
    """
    version_file = root / "esphome/nspanel_haui/version.yaml"
    source, count = re.subn(
        r"(?m)^(  tft_version: )'[^']+'$",
        rf"\g<1>'{version}'",
        version_file.read_text(encoding="utf-8"),
    )
    if count != 1:
        raise ValueError(f"Expected one tft_version in {version_file}, found {count}")
    version_file.write_text(source, encoding="utf-8")
    with env_file.open("a", encoding="utf-8") as env:
        env.write(f"TFT_VERSION={version}\n")


def main(argv: list[str] | None = None) -> int:
    """Update files for a workflow run, or print an actionable validation error."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: dev_version.py RUN_NUMBER", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[2]
    try:
        env_file = Path(os.environ["GITHUB_ENV"])
        sha = os.environ["GITHUB_SHA"]
        version = write_dev_version(root, args[0], env_file)
        tft_version = shipped_tft_version()
        write_tft_version(root, tft_version, env_file)
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"version={version}\nsha={sha[:7]}\n")
    except (KeyError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Building {version} from {sha}, shipping display TFT {tft_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
