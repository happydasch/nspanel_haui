"""Verify the Nextion HMI/TFT is release-ready.

Checks the Nextion2Text dump of ``nextion/nspanel_haui.HMI``:

* ``clock.tTime`` has **Send Component ID** enabled — tapping the time area
  must advance the card (v0.4 regression this gate exists for).
* ``system.tftVersion`` matches the configured display TFT version in
  ``esphome/nspanel_haui/version.yaml`` (or an exact ``--expected-version``),
  in **both** the landscape and the portrait HMI — the two TFTs are always
  updated together, so a stale ``tftVersion`` in either fails the gate.  The
  integration/firmware version is independent and reported only for reference:
  a firmware-only release ships the previous TFT unchanged.
* ``nextion/nspanel_haui_portrait.HMI`` / ``.tft`` exist when
  ``--require-portrait`` is given — the US portrait release asset — and the
  portrait HMI reports touches exactly like the landscape one (``clock.tTime``
  enabled there too, every widget's **Send Component ID** identical).

Exit code 0 when every check passes, 1 otherwise.  The release workflow
(`.github/workflows/release.yml`) runs this before cutting a tag, so a release
cannot be published until the Nextion Editor tasks landed.

Usage:
    python -m scripts.verify_nextion.verify_nextion [--hmi PATH] [--dump DIR] \\
        [--expected-version X.Y.Z] [--require-portrait]

The parser/checks live in importable functions so tests can drive fake dumps.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HMI = ROOT / "nextion" / "nspanel_haui.HMI"
DEFAULT_DUMP = ROOT / "ref_src" / "nextion-out-visual"
MANIFEST = ROOT / "custom_components" / "nspanel_haui" / "manifest.json"
VERSION_YAML = ROOT / "esphome" / "nspanel_haui" / "version.yaml"

SENDME_RE = re.compile(r"Send Component ID\s*:\s*(.+)")
DECL_RE = re.compile(r"^Variable \(string\) tftVersion\b")
TEXT_FIELD_RE = re.compile(r"^\s*Text\s*:\s*([0-9][\w.\-]*)\s*$")
# Nextion writes widget declarations as "<Type> <Name>" at column 0 (e.g.
# ``Text tTime``, ``Picture pGrid``), each followed by its attribute block.
WIDGET_HEADER_RE = re.compile(r"^[A-Z][\w ]*\s+[\w]+\s*$")


def parse_dump(dump_dir: Path) -> dict[str, dict]:
    """Return {page_name: {text: str}} for every page dump in *dump_dir*."""
    pages: dict[str, dict] = {}
    for path in sorted(dump_dir.glob("*.txt")):
        pages[path.stem] = {"text": path.read_text(encoding="utf-8", errors="replace")}
    return pages


def _widget_block(page_text: str, header_line: str) -> list[str]:
    """Return the attribute-block lines of the widget whose declaration is
    ``<header_line>`` (e.g. ``Text tTime``), or [] when absent.

    The dump runs the page's event code first and places each widget
    declaration at column 0; scanning per-line and stopping at the next
    widget header keeps the search scoped to the requested widget.
    """
    lines = page_text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == header_line), None)
    if start is None:
        return []
    for i in range(start + 1, len(lines)):
        if WIDGET_HEADER_RE.match(lines[i]):
            return lines[start:i]
    return lines[start:]


def check_t_time_sendme(page: dict | None) -> tuple[bool, str]:
    """clock.tTime must report taps (Send Component ID enabled).

    Nextion's dump uses the IDE's actual states: ``disabled``, ``on press``,
    ``on release`` or ``on press and release`` — a tap tick is reported in any
    of the enabled modes.  The check is scoped to the ``Text tTime`` widget;
    other widgets' settings are ignored.
    """
    if page is None:
        return False, "clock page dump missing"
    block = _widget_block(page["text"], "Text tTime")
    if not block:
        return False, "clock.tTime widget block not found in the dump"
    match = SENDME_RE.search("\n".join(block))
    if not match:
        return False, "clock.tTime Send Component ID attribute not found"
    state = match.group(1).strip().lower()
    if state in ("on press", "on release", "on press and release"):
        return True, f"clock.tTime Send Component ID is {state!r}"
    return False, f"clock.tTime Send Component ID is {state!r}, expected an enabled mode"


def check_tft_version(page: dict | None, expected: str) -> tuple[bool, str]:
    """system.tftVersion must match the configured display TFT version.

    The dump contains event code referencing ``system.tftVersion.txt`` before
    the declaration, so scan for the ``Variable (string) tftVersion`` block
    and read its ``Text`` attribute instead of the first textual mention.
    """
    if page is None:
        return False, "system page dump missing"
    lines = page["text"].splitlines()
    start = next((i for i, line in enumerate(lines) if DECL_RE.match(line)), None)
    if start is None:
        return False, "system.tftVersion declaration not found in the dump"
    for line in lines[start + 1 :]:
        if re.match(r"^Variable ", line):
            break
        match = TEXT_FIELD_RE.match(line)
        if match:
            actual = match.group(1).strip()
            if actual != expected:
                return False, f"system.tftVersion is {actual!r}, expected {expected!r}"
            return True, f"system.tftVersion is {actual!r}"
    return False, "system.tftVersion Text attribute not found"


# A dumped page declares each widget as "<Type> <Name>" at column 0; the
# type may contain spaces or a dash ("Dual-state Button btMode1").
WIDGET_DECL_RE = re.compile(r"^(\S.*?)\s+(\S+)$")


def _sendme_states(page_text: str) -> dict[str, str]:
    """Return {widget name: Send Component ID state} for every widget on a dumped page."""
    states: dict[str, str] = {}
    current = None
    for line in page_text.splitlines():
        decl = WIDGET_DECL_RE.match(line)
        if decl:
            current = decl.group(2)
            continue
        match = SENDME_RE.search(line)
        if match and current:
            states[current] = match.group(1).strip().lower()
    return states


def check_sendme_parity(
    landscape_pages: dict[str, dict], portrait_pages: dict[str, dict]
) -> tuple[bool, str]:
    """Every widget must report touches the same way on both layouts.

    The portrait HMI is a sibling of the landscape project — only geometry may
    differ — so a Send Component ID toggled in one file and not the other
    leaves one TFT without that touch (``scripts/hmi_layout`` copies the
    setting; this catches edits made in the editor afterwards).
    """
    mismatches = []
    for page in sorted(set(landscape_pages) & set(portrait_pages)):
        landscape = _sendme_states(landscape_pages[page]["text"])
        portrait = _sendme_states(portrait_pages[page]["text"])
        for name in sorted(set(landscape) & set(portrait)):
            if landscape[name] != portrait[name]:
                mismatches.append(f"{page}.{name} ({landscape[name]!r} vs {portrait[name]!r})")
    if mismatches:
        return False, "Send Component ID differs between the layouts: " + ", ".join(mismatches)
    return True, "Send Component ID identical on every widget of both layouts"


WIDGET_LOC_RE = re.compile(
    r"^(?:Text|Button|Picture|Bar|Number|Gauge|Slider|Progressbar|Multiline "
    r"Text|Multimedia|Variable|String|Timer|qrcode|Div|Crop)\b"
)


def _layout_signature(page_text: str) -> list[tuple[int, int, int, int]]:
    """Return the (x, y, width, height) of every widget on a dumped page.

    Used to tell a real rotation (coordinates change) from an edited copy
    (coordinates identical to the landscape even after version/sendme edits).
    """
    import re as _re

    pat = _re.compile(
        r"x coordinate\s*:\s*(\d+)\s*\n\s*y coordinate\s*:\s*(\d+)\s*\n"
        r"\s*Width\s*:\s*(\d+)\s*\n\s*Height\s*:\s*(\d+)"
    )
    return [(int(x), int(y), int(w), int(h)) for x, y, w, h in pat.findall(page_text)]


def check_portrait(hmi: Path, landscape_dump: Path) -> tuple[bool, str]:
    """Portrait HMI/TFT must exist and be a real rotation, not an edited copy.

    Requires: the portrait HMI/TFT files exist, are not byte-identical to the
    landscape files, and at least one page's widget geometry changed (a true
    portrait rotation re-layouts the widgets).  A copy with only the version
    text / sendme changed keeps the coordinates and is rejected.
    """
    portrait_hmi = hmi.with_name(hmi.stem.replace("_haui", "_haui_portrait") + ".HMI")
    portrait_tft = portrait_hmi.with_suffix(".tft")

    def _display(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    missing = [p for p in (portrait_hmi, portrait_tft) if not p.exists()]
    if missing:
        return False, f"missing portrait asset(s): {', '.join(_display(p) for p in missing)}"
    landscape_tft = hmi.with_suffix(".tft")
    for name, portrait, landscape in (
        ("HMI", portrait_hmi, hmi),
        ("TFT", portrait_tft, landscape_tft),
    ):
        try:
            same = portrait.read_bytes() == landscape.read_bytes()
        except OSError as exc:
            return False, f"cannot read {_display(portrait)}: {exc}"
        if same:
            return (
                False,
                f"portrait {name} is a byte-identical copy of the landscape file — "
                "rotate/re-layout it in the Nextion Editor instead of copying",
            )

    # Geometry check against the landscape dump: with fake portrait copies the
    # coordinates never change, even after version/sendme edits.
    if landscape_dump is not None:
        landscape_pages = parse_dump(landscape_dump)
        portrait_dump = landscape_dump.with_name(landscape_dump.name + "-portrait")
        if portrait_dump.exists():
            portrait_pages = parse_dump(portrait_dump)
            # only pages present in both
            common = set(landscape_pages) & set(portrait_pages)
            if common:
                changed = any(
                    _layout_signature(landscape_pages[p]["text"])
                    != _layout_signature(portrait_pages[p]["text"])
                    for p in common
                )
                if not changed:
                    return (
                        False,
                        "portrait layout is a copy — all widget coordinates match the "
                        "landscape; rotate and re-layout every page in the Nextion Editor",
                    )
    return True, "portrait HMI and TFT present, distinct and rotated"


def gate_tft_version(ok: bool, msg: str) -> tuple[str, bool]:
    """Verdict for a ``system.tftVersion`` gate check (an exact match).

    Allowing the firmware version to stand in for the TFT version is no longer
    tolerated: the HMIs must report exactly the configured TFT version in both
    layouts.

    Returns:
        ``(label, fail)``: ``label`` is ``PASS`` or ``FAIL``; ``fail`` is True
        when the check must fail the gate.
    """
    if ok:
        return "PASS", False
    return "FAIL", True


VERSION_ATTR_RE = re.compile(r"^\s*tft_version:\s*'?([^'\s]+)'?", re.MULTILINE)


def read_tft_version(version_yaml: Path) -> str:
    """Read the configured display TFT version from ``version.yaml``."""
    if not version_yaml.exists():
        return ""
    match = VERSION_ATTR_RE.search(version_yaml.read_text())
    return match.group(1) if match else ""


def read_integration_version(manifest: Path) -> str:
    """Read the integration/firmware version from ``manifest.json``."""
    if not manifest.exists():
        return ""
    try:
        value = json.loads(manifest.read_text()).get("version", "")
    except ValueError:
        return ""
    return str(value)


def resolve_expected_version(explicit: str | None, version_yaml: Path) -> str:
    """The exact TFT version the HMIs must report: an explicit pin, else ``version.yaml``.

    The configured TFT version is the source of truth (not ``manifest.json``):
    the integration/firmware version advances with every release while
    ``tft_version`` only advances on a ``--tft-update`` release.
    """
    if explicit:
        return explicit.strip()
    return read_tft_version(version_yaml)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hmi", type=Path, default=DEFAULT_HMI)
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    parser.add_argument(
        "--expected-version",
        default=None,
        help=(
            "exact TFT version both HMIs must report (default: the tft_version "
            "configured in esphome/nspanel_haui/version.yaml)"
        ),
    )
    parser.add_argument("--require-portrait", action="store_true")
    args = parser.parse_args()

    expected = resolve_expected_version(args.expected_version, VERSION_YAML)
    if not expected:
        print(
            "error: cannot determine the expected TFT version (pass "
            "--expected-version or set tft_version in version.yaml)",
            file=sys.stderr,
        )
        return 2

    print(f"Expected tftVersion: {expected}")
    integration = read_integration_version(MANIFEST)
    if integration and integration != expected:
        print(
            f"note: integration firmware version is {integration} — a firmware-only "
            "release ships the previous TFT unchanged"
        )
    if not args.hmi.exists():
        print(f"error: HMI not found: {args.hmi}", file=sys.stderr)
        return 2

    # Regenerate the dump so the checks always run against the current HMI.
    portrait_hmi = args.hmi.with_name(args.hmi.stem.replace("_haui", "_haui_portrait") + ".HMI")
    portrait_dump = args.dump.with_name(args.dump.name + "-portrait")

    def _dump(hmi_path: Path, out_dir: Path) -> None:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.nextion2text.Nextion2Text",
                "-i",
                str(hmi_path),
                "-o",
                str(out_dir),
                "-d",
                "-s",
                "-p",
                "visual",
            ],
            check=True,
            # Keep the dump's noisy stdout out of the log, but let stderr through
            # so a Nextion2Text crash reports its reason instead of only
            # "returned non-zero exit status 1".
            stdout=subprocess.DEVNULL,
            cwd=ROOT,
        )

    _dump(args.hmi, args.dump)
    pages = parse_dump(args.dump)

    # Both TFTs must be updated together, so the portrait dump is always
    # regenerated too; --require-portrait remains for the portrait asset/touch
    # checks, not for the TFT version gate.
    portrait_pages: dict[str, dict] = {}
    if portrait_hmi.exists():
        _dump(portrait_hmi, portrait_dump)
        portrait_pages = parse_dump(portrait_dump)

    failures = []
    ok, msg = check_t_time_sendme(pages.get("clock"))
    print(f"[{'PASS' if ok else 'FAIL'}] clock.tTime: {msg}")
    if not ok:
        failures.append(msg)

    # The HMIs must report exactly the configured TFT version, in both the
    # landscape and the portrait HMI (a stale tftVersion in either fails).
    ok, msg = check_tft_version(pages.get("system"), expected)
    label, fail = gate_tft_version(ok, msg)
    print(f"[{label}] system.tftVersion (landscape): {msg}")
    if fail:
        failures.append(msg)
    if portrait_hmi.exists():
        ok, msg = check_tft_version(portrait_pages.get("system"), expected)
        label, fail = gate_tft_version(ok, msg)
        print(f"[{label}] system.tftVersion (portrait): {msg}")
        if fail:
            failures.append(f"portrait: {msg}")

    if args.require_portrait:
        ok, msg = check_portrait(args.hmi, args.dump)
        print(f"[{'PASS' if ok else 'FAIL'}] portrait asset: {msg}")
        if not ok:
            failures.append(msg)
        if portrait_hmi.exists():
            ok, msg = check_t_time_sendme(portrait_pages.get("clock"))
            print(f"[{'PASS' if ok else 'FAIL'}] portrait clock.tTime: {msg}")
            if not ok:
                failures.append(f"portrait: {msg}")
            ok, msg = check_sendme_parity(pages, portrait_pages)
            print(f"[{'PASS' if ok else 'FAIL'}] portrait touch parity: {msg}")
            if not ok:
                failures.append(msg)

    if failures:
        print("\nNextion gate FAILED — fix in the Nextion Editor before releasing:")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("\nAll Nextion checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
