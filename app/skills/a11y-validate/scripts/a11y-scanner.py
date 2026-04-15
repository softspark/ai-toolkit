#!/usr/bin/env python3
"""Accessibility scanner -- pattern-matching heuristics for WCAG violations.

Stdlib only. No external dependencies.
Scans HTML/JSX/TSX/Vue/Astro/Svelte files for common a11y issues across
10 check categories mapped to WCAG 2.1 success criteria.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FILE_GLOBS = ("*.html", "*.htm", "*.jsx", "*.tsx", "*.vue", "*.astro", "*.svelte")

SKIP_DIRS = {
    "node_modules", "vendor", ".git", "dist", "build", "out", ".next",
    ".nuxt", ".svelte-kit", "__pycache__", ".venv", "venv", "coverage",
    "ios", "android", ".dart_tool", "storybook-static",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
}

# Valid ARIA attributes (subset covering the most common ones)
VALID_ARIA_ATTRS = {
    "aria-activedescendant", "aria-atomic", "aria-autocomplete",
    "aria-busy", "aria-checked", "aria-colcount", "aria-colindex",
    "aria-colspan", "aria-controls", "aria-current", "aria-describedby",
    "aria-details", "aria-disabled", "aria-dropeffect", "aria-errormessage",
    "aria-expanded", "aria-flowto", "aria-grabbed", "aria-haspopup",
    "aria-hidden", "aria-invalid", "aria-keyshortcuts", "aria-label",
    "aria-labelledby", "aria-level", "aria-live", "aria-modal",
    "aria-multiline", "aria-multiselectable", "aria-orientation",
    "aria-owns", "aria-placeholder", "aria-posinset", "aria-pressed",
    "aria-readonly", "aria-relevant", "aria-required", "aria-roledescription",
    "aria-rowcount", "aria-rowindex", "aria-rowspan", "aria-selected",
    "aria-setsize", "aria-sort", "aria-valuemax", "aria-valuemin",
    "aria-valuenow", "aria-valuetext",
}

# Redundant role mappings: element -> implicit role
REDUNDANT_ROLES = {
    "button": "button",
    "a": "link",
    "nav": "navigation",
    "main": "main",
    "header": "banner",
    "footer": "contentinfo",
    "aside": "complementary",
    "form": "form",
    "table": "table",
    "img": "img",
    "input": "textbox",
    "select": "listbox",
    "textarea": "textbox",
}

# Non-interactive elements that need keyboard handling when clickable
NON_INTERACTIVE = {"div", "span", "li", "td", "section", "article", "p"}

# Focusable elements
FOCUSABLE_ELEMENTS = {"a", "button", "input", "select", "textarea", "details", "summary"}


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_files(scan_path: Path) -> list[Path]:
    """Collect all matching source files under scan_path."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(scan_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        for fname in filenames:
            fpath = dp / fname
            if fpath.name in SKIP_FILES:
                continue
            if any(fpath.match(g) for g in FILE_GLOBS):
                files.append(fpath)
    return files


# ---------------------------------------------------------------------------
# Finding helper
# ---------------------------------------------------------------------------

def finding(
    severity: str,
    category: str,
    file: str,
    line: int,
    rule: str,
    message: str,
) -> dict:
    """Create a standardized finding dict."""
    return {
        "severity": severity,
        "category": category,
        "file": file,
        "line": line,
        "rule": rule,
        "message": message,
    }


# ---------------------------------------------------------------------------
# Check 1: Images
# ---------------------------------------------------------------------------

_RE_IMG_TAG = re.compile(r"<(?:img|Image)\b", re.IGNORECASE)
_RE_ALT_ATTR = re.compile(r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)'|\{([^}]*)\})""")
_RE_ROLE_PRES = re.compile(r"""\brole\s*=\s*["'](?:presentation|none)["']""")
_RE_DECORATIVE_ALT = re.compile(r"""\balt\s*=\s*["']\s*["']""")

def check_images(lines: list[str], rel: str) -> list[dict]:
    """Check images for missing/empty alt, decorative without role."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        if not _RE_IMG_TAG.search(line):
            continue
        alt_match = _RE_ALT_ATTR.search(line)
        if not alt_match:
            results.append(finding(
                "HIGH", "images", rel, i, "1.1.1",
                "Image missing alt attribute",
            ))
            continue
        alt_value = alt_match.group(1) or alt_match.group(2) or ""
        if alt_value.strip() == "" and not _RE_ROLE_PRES.search(line):
            if _RE_DECORATIVE_ALT.search(line):
                results.append(finding(
                    "WARN", "images", rel, i, "1.1.1",
                    "Empty alt on image without role=\"presentation\" -- "
                    "add role if decorative, or provide descriptive alt",
                ))
    return results


# ---------------------------------------------------------------------------
# Check 2: ARIA
# ---------------------------------------------------------------------------

_RE_ARIA_ATTR = re.compile(r"\b(aria-[\w-]+)\s*=")
_RE_ARIA_HIDDEN_TRUE = re.compile(r"""aria-hidden\s*=\s*["']true["']""")
_RE_ROLE_ATTR = re.compile(r"""\brole\s*=\s*["'](\w+)["']""")
_RE_OPEN_TAG = re.compile(r"<(\w+)\b")

def check_aria(lines: list[str], rel: str) -> list[dict]:
    """Check for invalid ARIA attrs, aria-hidden on focusable, redundant roles."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        # Invalid aria-* attributes
        for m in _RE_ARIA_ATTR.finditer(line):
            attr = m.group(1).lower()
            if attr.startswith("aria-") and attr not in VALID_ARIA_ATTRS:
                results.append(finding(
                    "WARN", "aria", rel, i, "4.1.2",
                    f"Possibly invalid ARIA attribute: {attr}",
                ))

        # aria-hidden="true" on focusable elements
        if _RE_ARIA_HIDDEN_TRUE.search(line):
            tag_match = _RE_OPEN_TAG.search(line)
            if tag_match and tag_match.group(1).lower() in FOCUSABLE_ELEMENTS:
                results.append(finding(
                    "HIGH", "aria", rel, i, "4.1.2",
                    "aria-hidden=\"true\" on focusable element creates "
                    "orphaned focus",
                ))

        # Redundant ARIA roles
        role_match = _RE_ROLE_ATTR.search(line)
        tag_match = _RE_OPEN_TAG.search(line)
        if role_match and tag_match:
            tag = tag_match.group(1).lower()
            role = role_match.group(1).lower()
            if REDUNDANT_ROLES.get(tag) == role:
                results.append(finding(
                    "WARN", "aria", rel, i, "4.1.2",
                    f"Redundant ARIA role=\"{role}\" on <{tag}> "
                    f"(implicit role is already \"{role}\")",
                ))
    return results


# ---------------------------------------------------------------------------
# Check 3: Headings
# ---------------------------------------------------------------------------

_RE_HEADING = re.compile(r"<[hH]([1-6])\b")

def check_headings(lines: list[str], rel: str) -> list[dict]:
    """Check for skipped heading levels, missing h1, multiple h1."""
    results: list[dict] = []
    headings: list[tuple[int, int]] = []  # (level, line_number)

    for i, line in enumerate(lines, 1):
        for m in _RE_HEADING.finditer(line):
            headings.append((int(m.group(1)), i))

    if not headings:
        return results

    # Multiple h1
    h1_lines = [ln for lvl, ln in headings if lvl == 1]
    if len(h1_lines) > 1:
        for ln in h1_lines[1:]:
            results.append(finding(
                "WARN", "headings", rel, ln, "1.3.1",
                "Multiple <h1> elements detected -- page should have one",
            ))

    # Missing h1
    if not h1_lines:
        results.append(finding(
            "WARN", "headings", rel, headings[0][1], "1.3.1",
            "No <h1> element found in file",
        ))

    # Skipped heading levels
    prev_level = 0
    for level, ln in headings:
        if prev_level > 0 and level > prev_level + 1:
            results.append(finding(
                "WARN", "headings", rel, ln, "1.3.1",
                f"Heading level skipped: h{prev_level} -> h{level}",
            ))
        prev_level = level

    return results


# ---------------------------------------------------------------------------
# Check 4: Forms
# ---------------------------------------------------------------------------

_RE_INPUT = re.compile(
    r"<(?:input|select|textarea)\b(?![^>]*type\s*=\s*[\"'](?:hidden|submit|button|reset|image)[\"'])",
    re.IGNORECASE,
)
_RE_LABEL_ASSOC = re.compile(
    r"""(?:\baria-label\s*=|\baria-labelledby\s*=|\bid\s*=)""",
)
_RE_RADIO = re.compile(r"""type\s*=\s*["']radio["']""", re.IGNORECASE)
_RE_FIELDSET = re.compile(r"<fieldset\b", re.IGNORECASE)

def check_forms(lines: list[str], rel: str) -> list[dict]:
    """Check inputs without labels, radio groups without fieldset/legend."""
    results: list[dict] = []
    has_radio = False
    has_fieldset = False

    for i, line in enumerate(lines, 1):
        if _RE_INPUT.search(line):
            if not _RE_LABEL_ASSOC.search(line):
                results.append(finding(
                    "HIGH", "forms", rel, i, "3.3.2",
                    "Form input without associated label "
                    "(no id+for, no aria-label, no aria-labelledby)",
                ))
        if _RE_RADIO.search(line):
            has_radio = True
        if _RE_FIELDSET.search(line):
            has_fieldset = True

    if has_radio and not has_fieldset:
        results.append(finding(
            "WARN", "forms", rel, 1, "1.3.1",
            "Radio group detected without <fieldset>/<legend>",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 5: Keyboard
# ---------------------------------------------------------------------------

_RE_ONCLICK = re.compile(r"\bonClick\s*=", re.IGNORECASE)
_RE_ONKEY = re.compile(r"\bon(?:KeyDown|KeyPress|KeyUp)\s*=", re.IGNORECASE)
_RE_TABINDEX_POS = re.compile(r"""\btabindex\s*=\s*["']?(\d+)["']?""", re.IGNORECASE)

def check_keyboard(lines: list[str], rel: str) -> list[dict]:
    """Check onClick without onKeyDown on non-interactive, tabIndex > 0."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        tag_match = _RE_OPEN_TAG.search(line)
        tag_name = tag_match.group(1).lower() if tag_match else ""

        # onClick on non-interactive without keyboard handler
        if tag_name in NON_INTERACTIVE and _RE_ONCLICK.search(line):
            if not _RE_ONKEY.search(line):
                results.append(finding(
                    "HIGH", "keyboard", rel, i, "2.1.1",
                    f"onClick on <{tag_name}> without onKeyDown/onKeyPress "
                    f"-- not keyboard-accessible",
                ))

        # tabIndex > 0
        tabindex_match = _RE_TABINDEX_POS.search(line)
        if tabindex_match:
            val = int(tabindex_match.group(1))
            if val > 0:
                results.append(finding(
                    "HIGH", "keyboard", rel, i, "2.4.3",
                    f"tabIndex={val} breaks natural tab order -- use 0 or -1",
                ))
    return results


# ---------------------------------------------------------------------------
# Check 6: Color/contrast (basic heuristic)
# ---------------------------------------------------------------------------

_RE_INLINE_COLOR = re.compile(
    r"""style\s*=\s*["'][^"']*color\s*:\s*#([0-9a-fA-F]{3,8})[^"']*"""
    r"""background(?:-color)?\s*:\s*#([0-9a-fA-F]{3,8})""",
)

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    """Convert 3/6-char hex to RGB tuple."""
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    h = h[:6]
    return int(h[0:2], 16), int(h[1:4][:2], 16), int(h[2:6][:2], 16)


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG formula."""
    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(hex_fg: str, hex_bg: str) -> float:
    """Compute contrast ratio between two hex colors."""
    l1 = _relative_luminance(*_hex_to_rgb(hex_fg))
    l2 = _relative_luminance(*_hex_to_rgb(hex_bg))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_color_contrast(lines: list[str], rel: str) -> list[dict]:
    """Detect inline color styles with insufficient contrast (heuristic)."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        m = _RE_INLINE_COLOR.search(line)
        if m:
            fg_hex, bg_hex = m.group(1), m.group(2)
            try:
                ratio = _contrast_ratio(fg_hex, bg_hex)
                if ratio < 4.5:
                    results.append(finding(
                        "WARN", "color-contrast", rel, i, "1.4.3",
                        f"Inline color contrast ratio ~{ratio:.1f}:1 "
                        f"(minimum 4.5:1 for normal text)",
                    ))
            except (ValueError, IndexError):
                pass
    return results


# ---------------------------------------------------------------------------
# Check 7: Focus
# ---------------------------------------------------------------------------

_RE_OUTLINE_NONE = re.compile(
    r"outline\s*:\s*(?:none|0)\b", re.IGNORECASE,
)
_RE_FOCUS_VISIBLE = re.compile(r":focus-visible", re.IGNORECASE)

def check_focus(lines: list[str], rel: str) -> list[dict]:
    """Detect outline:none/0 without alternative focus indicator."""
    results: list[dict] = []
    content = "\n".join(lines)
    has_focus_visible = bool(_RE_FOCUS_VISIBLE.search(content))

    for i, line in enumerate(lines, 1):
        if _RE_OUTLINE_NONE.search(line) and not has_focus_visible:
            results.append(finding(
                "HIGH", "focus", rel, i, "2.4.7",
                "outline:none/0 without :focus-visible alternative "
                "-- removes visible focus indicator",
            ))
    return results


# ---------------------------------------------------------------------------
# Check 8: Media
# ---------------------------------------------------------------------------

_RE_VIDEO = re.compile(r"<video\b", re.IGNORECASE)
_RE_AUDIO = re.compile(r"<audio\b", re.IGNORECASE)
_RE_TRACK = re.compile(r"<track\b", re.IGNORECASE)
_RE_AUTOPLAY = re.compile(r"\bautoplay\b", re.IGNORECASE)
_RE_MUTED = re.compile(r"\bmuted\b", re.IGNORECASE)

def check_media(lines: list[str], rel: str) -> list[dict]:
    """Check video/audio for missing tracks and autoplay without muted."""
    results: list[dict] = []
    content = "\n".join(lines)
    has_track = bool(_RE_TRACK.search(content))

    for i, line in enumerate(lines, 1):
        if _RE_VIDEO.search(line):
            if not has_track:
                results.append(finding(
                    "HIGH", "media", rel, i, "1.2.2",
                    "Video element without <track> for captions",
                ))
            if _RE_AUTOPLAY.search(line) and not _RE_MUTED.search(line):
                results.append(finding(
                    "HIGH", "media", rel, i, "1.4.2",
                    "Video autoplay without muted attribute",
                ))
        if _RE_AUDIO.search(line):
            if not has_track:
                results.append(finding(
                    "HIGH", "media", rel, i, "1.2.1",
                    "Audio element without <track> for captions/transcript",
                ))
            if _RE_AUTOPLAY.search(line) and not _RE_MUTED.search(line):
                results.append(finding(
                    "HIGH", "media", rel, i, "1.4.2",
                    "Audio autoplay without muted attribute",
                ))
    return results


# ---------------------------------------------------------------------------
# Check 9: Target size
# ---------------------------------------------------------------------------

_RE_WH_INLINE = re.compile(
    r"""style\s*=\s*["'][^"']*(?:width|height)\s*:\s*(\d+)px""",
    re.IGNORECASE,
)
_RE_CLICKABLE_TAG = re.compile(r"<(?:a|button|input)\b", re.IGNORECASE)

def check_target_size(lines: list[str], rel: str) -> list[dict]:
    """Detect very small clickable areas from inline styles."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        if not _RE_CLICKABLE_TAG.search(line):
            continue
        sizes = _RE_WH_INLINE.findall(line)
        for size_str in sizes:
            px = int(size_str)
            if 0 < px < 24:
                results.append(finding(
                    "WARN", "target-size", rel, i, "2.5.8",
                    f"Clickable element with {px}px dimension "
                    f"(minimum 24x24px recommended)",
                ))
                break
    return results


# ---------------------------------------------------------------------------
# Check 10: Language
# ---------------------------------------------------------------------------

_RE_HTML_TAG = re.compile(r"<html\b", re.IGNORECASE)
_RE_LANG_ATTR = re.compile(r"""\blang\s*=\s*["']""", re.IGNORECASE)

def check_language(lines: list[str], rel: str) -> list[dict]:
    """Check for missing lang attribute on <html> element."""
    results: list[dict] = []
    for i, line in enumerate(lines, 1):
        if _RE_HTML_TAG.search(line) and not _RE_LANG_ATTR.search(line):
            results.append(finding(
                "HIGH", "language", rel, i, "3.1.1",
                "Missing lang attribute on <html> element",
            ))
    return results


# ---------------------------------------------------------------------------
# Scan orchestrator
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_images,
    check_aria,
    check_headings,
    check_forms,
    check_keyboard,
    check_color_contrast,
    check_focus,
    check_media,
    check_target_size,
    check_language,
]


def scan_file(fpath: Path, root: Path) -> list[dict]:
    """Run all checks against a single file."""
    try:
        content = fpath.read_text(errors="replace")
    except (OSError, PermissionError):
        return []

    lines = content.splitlines()
    rel = str(fpath.relative_to(root))
    results: list[dict] = []

    for check_fn in ALL_CHECKS:
        results.extend(check_fn(lines, rel))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Accessibility scanner -- detect common a11y issues",
    )
    parser.add_argument(
        "path", nargs="?", default=".",
        help="Directory or file to scan (default: current directory)",
    )
    parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--severity", choices=["high", "warn", "info", "all"], default="all",
        help="Minimum severity to report (default: all)",
    )
    args = parser.parse_args()

    scan_path = Path(args.path).resolve()
    if not scan_path.exists():
        print(json.dumps({"error": f"Path does not exist: {args.path}"}))
        sys.exit(2)

    # Determine root for relative paths
    root = scan_path if scan_path.is_dir() else scan_path.parent

    # Collect files
    if scan_path.is_file():
        files = [scan_path] if any(scan_path.match(g) for g in FILE_GLOBS) else []
    else:
        files = collect_files(scan_path)

    if not files:
        report = {
            "scan_path": str(args.path),
            "files_scanned": 0,
            "findings": [],
            "summary": {"HIGH": 0, "WARN": 0, "INFO": 0},
        }
        print(json.dumps(report, indent=2))
        sys.exit(0)

    # Scan
    all_findings: list[dict] = []
    for fpath in files:
        all_findings.extend(scan_file(fpath, root))

    # Severity filter
    if args.severity == "high":
        all_findings = [f for f in all_findings if f["severity"] == "HIGH"]
    elif args.severity == "warn":
        all_findings = [f for f in all_findings if f["severity"] in ("HIGH", "WARN")]

    # Deduplicate (same file+line+rule+message)
    seen: set[tuple[str, int, str, str]] = set()
    deduped: list[dict] = []
    for f in all_findings:
        key = (f["file"], f["line"], f["rule"], f["message"])
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    all_findings = deduped

    # Sort: HIGH first, then WARN, then INFO
    sev_order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    all_findings.sort(key=lambda f: (sev_order.get(f["severity"], 9), f["file"], f["line"]))

    # Summary counts
    summary = {"HIGH": 0, "WARN": 0, "INFO": 0}
    for f in all_findings:
        sev = f["severity"]
        summary[sev] = summary.get(sev, 0) + 1

    report = {
        "scan_path": str(args.path),
        "files_scanned": len(files),
        "findings": all_findings,
        "summary": summary,
    }

    if args.output == "json":
        print(json.dumps(report, indent=2))
    else:
        _print_text_report(report)

    # Exit code: 1 if HIGH findings
    sys.exit(1 if summary["HIGH"] > 0 else 0)


def _print_text_report(report: dict) -> None:
    """Print a terminal-friendly text report."""
    print(f"\n=== Accessibility Scan Report ===\n")
    print(f"Path:    {report['scan_path']}")
    print(f"Files:   {report['files_scanned']}")
    s = report["summary"]
    print(f"HIGH:    {s['HIGH']}  |  WARN: {s['WARN']}  |  INFO: {s['INFO']}")
    print()

    if not report["findings"]:
        print("No accessibility issues found.")
        return

    for f in report["findings"]:
        print(f"[{f['severity']}] {f['file']}:{f['line']}")
        print(f"  Category: {f['category']}")
        print(f"  WCAG:     {f['rule']}")
        print(f"  {f['message']}")
        print()


if __name__ == "__main__":
    main()
