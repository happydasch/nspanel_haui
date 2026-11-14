#!/usr/bin/env python3
"""Check frontend CSS against the shared design tokens and scale."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "nspanel_haui" / "frontend"
CSS_TEMPLATE = re.compile(r"\bcss\s*`([^`]*)`", re.DOTALL)
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
DECLARATION = re.compile(r"(?<![\w-])([\w-]+)\s*:\s*([^;{}]+);")
HEX_COLOR = re.compile(r"#[\da-fA-F]{3,8}\b")
COLOR_FUNCTION = re.compile(r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\s*\(", re.IGNORECASE)
PX = re.compile(r"(?<![\w.-])(-?(?:\d+(?:\.\d*)?|\.\d+))px\b")
NON_PX_LENGTH = re.compile(r"(?<![\w.-])(-?(?:\d+(?:\.\d*)?|\.\d+))(?:rem|em)\b")
FONT_SIZES = {"10", "12", "13", "14", "16", "20", "24"}
FONT_WEIGHTS = {"400", "500", "600"}
SPACING = {"0", "4", "8", "12", "16", "20", "24", "28", "32", "40"}
SPACING_PROPERTIES = {
    "padding",
    "padding-block",
    "padding-inline",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin",
    "margin-block",
    "margin-inline",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "gap",
    "row-gap",
    "column-gap",
}
ALLOWED_BARE_COLORS = {"#fff", "#ffffff", "#000", "#000000", "#0003"}
REDUCED_MOTION = re.compile(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{")
ACTIVE_MOTION = re.compile(
    r"\b(?:transition|animation)(?:-(?:property|duration|name))?\s*:\s*(?!none\b)[^;{}]+;"
)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def css_sources(frontend: Path = FRONTEND) -> list[tuple[Path, str]]:
    """Return CSS template contents with comments removed."""
    sources = []
    for path in frontend.rglob("*.js"):
        if "vendor" in path.parts:
            continue
        for match in CSS_TEMPLATE.finditer(path.read_text(encoding="utf-8")):
            sources.append((path, COMMENT.sub("", match.group(1))))
    return sources


def _inside_var_fallback(value: str, position: int) -> bool:
    """Whether a character is in the fallback argument of a CSS var()."""
    cursor = 0
    while True:
        start = value.find("var(", cursor)
        if start < 0 or start >= position:
            return False
        depth = 1
        comma = -1
        index = start + 4
        while index < len(value) and depth:
            char = value[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 1 and comma < 0:
                comma = index
            index += 1
        if comma >= 0 and comma < position < index - 1:
            return True
        cursor = index


def _selector_duplicates(
    sources: list[tuple[Path, str]], frontend: Path = FRONTEND
) -> dict[str, set[str]]:
    """Find class selectors declared in more than one CSS source file."""
    files_by_selector: dict[str, set[str]] = defaultdict(set)
    for path, css in sources:
        for match in re.finditer(r"([^{}]+)\{", css):
            prelude = match.group(1).rsplit("}", 1)[-1].rsplit(";", 1)[-1].strip()
            if not prelude or prelude.startswith("@"):
                continue
            for selector in prelude.split(","):
                selector = " ".join(selector.split())
                if "." in selector and not selector.startswith(":host"):
                    files_by_selector[selector].add(path.relative_to(frontend).as_posix())
    return {selector: files for selector, files in files_by_selector.items() if len(files) > 1}


def _duplicate_style_adoptions(frontend: Path = FRONTEND, root: Path = ROOT) -> list[str]:
    """Find repeated style identifiers in a component's static style array."""
    failures = []
    array_patterns = (
        re.compile(r"static\s+styles\s*=\s*\[([^\]]*)\]", re.DOTALL),
        re.compile(r"static\s+get\s+styles\s*\(\)\s*\{.*?return\s*\[([^\]]*)\]", re.DOTALL),
    )
    imported_names = re.compile(r"\b[A-Za-z_$][\w$]*(?:Styles|Style)\b")
    for path in frontend.rglob("*.js"):
        if "vendor" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in array_patterns:
            for match in pattern.finditer(text):
                names = imported_names.findall(match.group(1))
                repeated = sorted({name for name in names if names.count(name) > 1})
                for name in repeated:
                    failures.append(
                        f"{path.relative_to(root)}: style {name} is adopted more than once"
                    )
    return failures


def _split_reduced_motion(css: str) -> tuple[str, str]:
    """Split CSS into the text outside and inside prefers-reduced-motion blocks."""
    outside, inside, cursor = [], [], 0
    for match in REDUCED_MOTION.finditer(css):
        if match.start() < cursor:
            continue
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(css[end], 0)
            end += 1
        outside.append(css[cursor : match.start()])
        inside.append(css[match.end() : end - 1])
        cursor = end
    outside.append(css[cursor:])
    return "".join(outside), "".join(inside)


def _rule_selectors(css: str) -> list[tuple[list[str], str]]:
    """Return each innermost rule's selectors and body."""
    return [
        ([" ".join(selector.split()) for selector in prelude.split(",")], body)
        for prelude, body in RULE.findall(css)
    ]


def _catch_all_fragments(
    covered_by_file: dict[Path, set[str]], frontend: Path = FRONTEND
) -> set[Path]:
    """Fragments that styles.js composes into one sheet with a universal reduced-motion rule.

    A `*` rule in a reduced-motion block (styles/content.js) turns motion off for the
    whole shadow root, so the fragments sharing its sheet need no overrides of their own.
    """
    composition = frontend / "styles.js"
    if not composition.exists():
        return set()
    text = composition.read_text(encoding="utf-8")
    imports = {
        name.strip(): (composition.parent / module).resolve()
        for names, module in re.findall(r"import\s*\{([^}]*)\}\s*from\s*'([^']+)'", text)
        for name in names.split(",")
    }
    templates = {
        name: re.findall(r"\$\{(\w+)\}", body)
        for name, body in re.findall(r"export\s+const\s+(\w+)\s*=\s*css`([^`]*)`", text)
    }

    def expand(name: str) -> set[str]:
        return {name}.union(*(expand(part) for part in templates.get(name, [])))

    universal = {
        path.resolve()
        for path, selectors in covered_by_file.items()
        if any("*" in selector for selector in selectors)
    }
    covered: set[Path] = set()
    for name in templates:
        paths = {imports[part] for part in expand(name) if part in imports}
        if paths & universal:
            covered |= paths
    return covered


def _motion_errors(css_by_path: dict[Path, str], frontend: Path, root: Path) -> list[str]:
    """Every selector with motion needs a reduced-motion override in its own file."""
    motion_by_file: dict[Path, list[str]] = {}
    covered_by_file: dict[Path, set[str]] = {}
    for path, css in css_by_path.items():
        outside, inside = _split_reduced_motion(css)
        covered_by_file[path] = {
            selector for selectors, _ in _rule_selectors(inside) for selector in selectors
        }
        motion_by_file[path] = [
            selector
            for selectors, body in _rule_selectors(outside)
            if ACTIVE_MOTION.search(body)
            for selector in selectors
        ]
    catch_all = _catch_all_fragments(covered_by_file, frontend)
    errors = []
    for path, selectors in motion_by_file.items():
        covered = covered_by_file[path]
        if path.resolve() in catch_all or any("*" in selector for selector in covered):
            continue
        for selector in selectors:
            if selector not in covered:
                errors.append(
                    f"{path.relative_to(root)}: motion on {selector!r} must respect "
                    "prefers-reduced-motion"
                )
    return errors


def _normalise_number(number: str) -> str:
    value = abs(float(number))
    return str(int(value)) if value.is_integer() else format(value, "g")


def check_css_sources(
    sources: list[tuple[Path, str]], frontend: Path = FRONTEND, root: Path = ROOT
) -> list[str]:
    """Check CSS values and cross-file selector ownership."""
    errors: list[str] = []
    for path, css in sources:
        relative = path.relative_to(root).as_posix()
        for match in DECLARATION.finditer(css):
            prop, value = match.groups()
            line = css.count("\n", 0, match.start()) + 1
            where = f"{relative}:{line}"
            pixels = [_normalise_number(number) for number in PX.findall(value)]
            if prop == "font-size" and any(number not in FONT_SIZES for number in pixels):
                errors.append(f"{where}: off-scale font-size {value.strip()!r}")
            elif prop == "font-size" and not pixels and not ("var(" in value or "calc(" in value):
                errors.append(f"{where}: font-size must use a typography token or scale step")
            elif prop == "font-weight":
                weights = re.findall(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w.-])", value)
                if any(weight not in FONT_WEIGHTS for weight in weights):
                    errors.append(f"{where}: off-scale font-weight {value.strip()!r}")
            elif prop == "border-radius":
                if any(number not in {"0", "8", "12", "999", "9999"} for number in pixels):
                    errors.append(f"{where}: off-scale border-radius {value.strip()!r}")
                elif value.strip() not in {"0", "0px"} and not any(
                    token in value for token in ("var(", "calc(", "50%")
                ):
                    errors.append(
                        f"{where}: border-radius must use a radius token or standard shape"
                    )
            elif prop in SPACING_PROPERTIES and (
                any(number not in SPACING for number in pixels)
                or any(float(number) != 0 for number in NON_PX_LENGTH.findall(value))
            ):
                errors.append(f"{where}: off-scale {prop} {value.strip()!r}")

            if path.name != "tokens.js":
                for color in HEX_COLOR.finditer(value):
                    if color.group(
                        0
                    ).lower() not in ALLOWED_BARE_COLORS and not _inside_var_fallback(
                        value, color.start()
                    ):
                        errors.append(
                            f"{where}: raw color {color.group(0)} must use a design token"
                        )
                for color in COLOR_FUNCTION.finditer(value):
                    if not _inside_var_fallback(value, color.start()):
                        errors.append(
                            f"{where}: raw color function {color.group(0)[:-1]} "
                            "must use a design token"
                        )

    css_by_path: dict[Path, str] = defaultdict(str)
    for path, css in sources:
        css_by_path[path] += css
    errors.extend(_motion_errors(css_by_path, frontend, root))

    for path, css in sources:
        if path.name != "tokens.js":
            for match in re.finditer(r"--haui-[\w-]+\s*:", css):
                line = css.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(root)}:{line}: define --haui-* aliases in styles/tokens.js"
                )

    for selector, files in sorted(_selector_duplicates(sources, frontend).items()):
        errors.append(f"duplicate selector {selector!r} in {', '.join(sorted(files))}")
    return errors


def check(frontend: Path = FRONTEND, root: Path = ROOT) -> list[str]:
    errors = check_css_sources(css_sources(frontend), frontend, root)
    for path in frontend.rglob("*.js"):
        if "vendor" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "--code-font-family" in text:
            errors.append(f"{path.relative_to(root)}: obsolete --code-font-family token")

    errors.extend(_duplicate_style_adoptions(frontend, root))
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("Frontend style checks failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Frontend styles follow the shared token scale and composition rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
