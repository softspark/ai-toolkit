#!/usr/bin/env python3
"""SEO scanner -- pattern-matching heuristics for common SEO issues.

Stdlib only. No external dependencies.
Scans HTML/JSX/TSX/Vue/Astro/Svelte files for SEO problems across 9 categories.
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

SCAN_EXTENSIONS = {
    ".html", ".htm", ".jsx", ".tsx", ".vue", ".astro", ".svelte",
}

SKIP_DIRS = {
    "node_modules", "vendor", ".git", "dist", "build", "out", ".next",
    ".nuxt", ".svelte-kit", "__pycache__", ".venv", "venv", ".tox",
    "public/build", "coverage", ".turbo", ".vercel",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
}

# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def collect_files(scan_path: Path) -> list[Path]:
    """Collect scannable files under the given path, respecting skip rules."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(scan_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in SCAN_EXTENSIONS and fname not in SKIP_FILES:
                files.append(fpath)
    return sorted(files)


def find_project_root(start: Path) -> Path:
    """Walk up to find .git or package.json as project root indicator."""
    current = start if start.is_dir() else start.parent
    while current != current.parent:
        if (current / ".git").exists() or (current / "package.json").exists():
            return current
        current = current.parent
    return start if start.is_dir() else start.parent


# ---------------------------------------------------------------------------
# Finding accumulator
# ---------------------------------------------------------------------------

Findings = list[dict]


def add_finding(
    findings: Findings,
    severity: str,
    category: str,
    file_path: str,
    line: int,
    message: str,
) -> None:
    """Append a finding to the list."""
    findings.append({
        "severity": severity,
        "category": category,
        "file": file_path,
        "line": line,
        "message": message,
    })


# ---------------------------------------------------------------------------
# Category 1: Meta tags
# ---------------------------------------------------------------------------

_RE_TITLE = re.compile(r"<title[\s>]", re.IGNORECASE)
_RE_META_DESC = re.compile(
    r"""<meta\s[^>]*name\s*=\s*["']description["']""", re.IGNORECASE,
)
_RE_OG_TITLE = re.compile(
    r"""<meta\s[^>]*property\s*=\s*["']og:title["']""", re.IGNORECASE,
)
_RE_OG_DESC = re.compile(
    r"""<meta\s[^>]*property\s*=\s*["']og:description["']""", re.IGNORECASE,
)
_RE_OG_IMAGE = re.compile(
    r"""<meta\s[^>]*property\s*=\s*["']og:image["']""", re.IGNORECASE,
)
_RE_CANONICAL = re.compile(
    r"""<link\s[^>]*rel\s*=\s*["']canonical["']""", re.IGNORECASE,
)
# Framework metadata exports (Next.js App Router)
_RE_METADATA_EXPORT = re.compile(r"export\s+(const\s+metadata|async\s+function\s+generateMetadata)")


def check_meta_tags(content: str, rel_path: str, findings: Findings) -> None:
    """Check for missing meta tags in a file."""
    has_head = re.search(r"<head[\s>]|<Head[\s>]", content) is not None
    has_metadata_export = _RE_METADATA_EXPORT.search(content) is not None

    # Only check files that define a head section or are page-level components
    is_page = (
        has_head
        or has_metadata_export
        or "layout" in rel_path.lower()
        or "/page." in rel_path.lower()
        or "/index." in rel_path.lower()
        or rel_path.lower().endswith("index.html")
    )
    if not is_page:
        return

    # Skip if using framework metadata API
    if has_metadata_export:
        return

    checks = [
        (_RE_TITLE, "HIGH", "Missing <title> tag"),
        (_RE_META_DESC, "HIGH", "Missing meta description"),
        (_RE_CANONICAL, "HIGH", "Missing canonical link"),
        (_RE_OG_TITLE, "WARN", "Missing og:title meta tag"),
        (_RE_OG_DESC, "WARN", "Missing og:description meta tag"),
        (_RE_OG_IMAGE, "WARN", "Missing og:image meta tag"),
    ]
    for pattern, severity, message in checks:
        if not pattern.search(content):
            add_finding(findings, severity, "meta", rel_path, 1, message)


# ---------------------------------------------------------------------------
# Category 2: Heading hierarchy
# ---------------------------------------------------------------------------

_RE_HEADING = re.compile(r"<[hH]([1-6])[\s>]")


def check_headings(content: str, rel_path: str, findings: Findings) -> None:
    """Check for multiple H1 tags and skipped heading levels."""
    h1_lines: list[int] = []
    heading_levels: list[tuple[int, int]] = []  # (level, line_number)

    for line_num, line in enumerate(content.splitlines(), 1):
        for match in _RE_HEADING.finditer(line):
            level = int(match.group(1))
            heading_levels.append((level, line_num))
            if level == 1:
                h1_lines.append(line_num)

    if len(h1_lines) > 1:
        for line_num in h1_lines[1:]:
            add_finding(
                findings, "WARN", "headings", rel_path, line_num,
                f"Multiple <h1> tags found (also at line {h1_lines[0]})",
            )

    # Check for skipped levels
    for i in range(1, len(heading_levels)):
        prev_level, _ = heading_levels[i - 1]
        curr_level, curr_line = heading_levels[i]
        if curr_level > prev_level + 1:
            add_finding(
                findings, "WARN", "headings", rel_path, curr_line,
                f"Heading level skipped: h{prev_level} -> h{curr_level}",
            )


# ---------------------------------------------------------------------------
# Category 3: Image alt text
# ---------------------------------------------------------------------------

_RE_IMG_TAG = re.compile(r"<(?:img|Image)\b([^>]*)>", re.IGNORECASE | re.DOTALL)
_RE_ALT_ATTR = re.compile(r"""\balt\s*=\s*["'{]""", re.IGNORECASE)


def check_image_alt(content: str, rel_path: str, findings: Findings) -> None:
    """Check for images missing alt attributes."""
    for line_num, line in enumerate(content.splitlines(), 1):
        for match in re.finditer(r"<(?:img|Image)\b([^>]*)/?/?>", line, re.IGNORECASE):
            attrs = match.group(1)
            if not _RE_ALT_ATTR.search(attrs):
                add_finding(
                    findings, "WARN", "images", rel_path, line_num,
                    "Image missing alt attribute",
                )


# ---------------------------------------------------------------------------
# Category 4: Structured data (JSON-LD)
# ---------------------------------------------------------------------------

_RE_JSON_LD = re.compile(
    r"""<script\s[^>]*type\s*=\s*["']application/ld\+json["']""", re.IGNORECASE,
)


def check_structured_data(content: str, rel_path: str, findings: Findings) -> None:
    """Check for presence of JSON-LD structured data."""
    is_page = (
        "layout" in rel_path.lower()
        or "/page." in rel_path.lower()
        or "/index." in rel_path.lower()
        or rel_path.lower().endswith("index.html")
    )
    if not is_page:
        return

    if not _RE_JSON_LD.search(content):
        add_finding(
            findings, "INFO", "structured-data", rel_path, 1,
            "No JSON-LD structured data found",
        )


# ---------------------------------------------------------------------------
# Category 5: Hreflang
# ---------------------------------------------------------------------------

_RE_HREFLANG = re.compile(r"""hreflang\s*=\s*["'][^"']*["']""", re.IGNORECASE)


def check_hreflang(project_root: Path, findings: Findings) -> None:
    """Check for hreflang tags if i18n directories exist."""
    i18n_indicators = [
        "locales", "i18n", "translations", "lang", "messages",
    ]
    has_i18n = False
    for indicator in i18n_indicators:
        if (project_root / indicator).is_dir():
            has_i18n = True
            break

    # Also check for next-i18next, nuxt i18n modules, etc.
    pkg_path = project_root / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(errors="replace"))
            all_deps = {}
            all_deps.update(pkg.get("dependencies", {}))
            all_deps.update(pkg.get("devDependencies", {}))
            i18n_deps = ["next-i18next", "@nuxtjs/i18n", "i18next", "vue-i18n", "react-intl"]
            for dep in i18n_deps:
                if dep in all_deps:
                    has_i18n = True
                    break
        except (json.JSONDecodeError, OSError):
            pass

    if not has_i18n:
        return

    # If i18n is detected, check for hreflang in HTML files
    found_hreflang = False
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in SCAN_EXTENSIONS:
                continue
            try:
                content = fpath.read_text(errors="replace")
            except (OSError, PermissionError):
                continue
            if _RE_HREFLANG.search(content):
                found_hreflang = True
                break
        if found_hreflang:
            break

    if not found_hreflang:
        add_finding(
            findings, "WARN", "hreflang", "project", 0,
            "i18n detected but no hreflang tags found in any template",
        )


# ---------------------------------------------------------------------------
# Category 6: robots.txt
# ---------------------------------------------------------------------------


def check_robots(project_root: Path, findings: Findings) -> None:
    """Check for robots.txt at project root or public directory."""
    candidates = [
        project_root / "robots.txt",
        project_root / "public" / "robots.txt",
        project_root / "static" / "robots.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return

    add_finding(
        findings, "HIGH", "robots", "project", 0,
        "No robots.txt found at project root or public/",
    )


# ---------------------------------------------------------------------------
# Category 7: Sitemap
# ---------------------------------------------------------------------------


def check_sitemap(project_root: Path, findings: Findings) -> None:
    """Check for sitemap.xml or sitemap configuration."""
    # Direct file check
    sitemap_paths = [
        project_root / "sitemap.xml",
        project_root / "public" / "sitemap.xml",
        project_root / "static" / "sitemap.xml",
    ]
    for candidate in sitemap_paths:
        if candidate.exists():
            return

    # Check for sitemap generation in package.json deps
    pkg_path = project_root / "package.json"
    if pkg_path.exists():
        try:
            pkg_content = pkg_path.read_text(errors="replace")
            sitemap_deps = [
                "next-sitemap", "gatsby-plugin-sitemap", "@nuxtjs/sitemap",
                "sitemap", "vite-plugin-sitemap", "astro-sitemap",
            ]
            for dep in sitemap_deps:
                if dep in pkg_content:
                    return
        except (OSError, PermissionError):
            pass

    # Check for sitemap reference in robots.txt
    for robots_path in [
        project_root / "robots.txt",
        project_root / "public" / "robots.txt",
    ]:
        if robots_path.exists():
            try:
                robots_content = robots_path.read_text(errors="replace").lower()
                if "sitemap:" in robots_content:
                    return
            except (OSError, PermissionError):
                pass

    add_finding(
        findings, "HIGH", "sitemap", "project", 0,
        "No sitemap.xml or sitemap generator detected",
    )


# ---------------------------------------------------------------------------
# Category 8: Core Web Vitals static signals
# ---------------------------------------------------------------------------

_RE_LAZY_IMG = re.compile(
    r"""<(?:img|Image)\b[^>]*loading\s*=\s*["']lazy["']""", re.IGNORECASE,
)
_RE_HERO_COMPONENT = re.compile(
    r"(?:Hero|Banner|Masthead|Jumbotron|HeroSection|CoverImage)", re.IGNORECASE,
)


def check_cwv_signals(content: str, rel_path: str, findings: Findings) -> None:
    """Detect lazy loading on above-fold images and other CWV issues."""
    lines = content.splitlines()
    in_hero_section = False

    for line_num, line in enumerate(lines, 1):
        # Track hero/banner context
        if _RE_HERO_COMPONENT.search(line):
            in_hero_section = True

        # Reset hero context after closing tags or significant gaps
        if in_hero_section and re.search(r"</(?:section|div|header)>", line, re.IGNORECASE):
            in_hero_section = False

        # Lazy loading on first/hero images is harmful for LCP
        if _RE_LAZY_IMG.search(line) and (in_hero_section or line_num <= 30):
            add_finding(
                findings, "HIGH", "cwv", rel_path, line_num,
                "Lazy loading on above-the-fold image delays LCP",
            )

        # Script in head without async/defer
        if re.search(r"<script\b", line, re.IGNORECASE):
            has_async_defer = re.search(r"\b(async|defer|type\s*=\s*[\"']module[\"'])\b", line, re.IGNORECASE)
            has_json_ld = re.search(r"""type\s*=\s*["']application/ld\+json["']""", line, re.IGNORECASE)
            if not has_async_defer and not has_json_ld:
                # Only flag if in head section
                head_start = content.lower().find("<head")
                head_end = content.lower().find("</head>")
                line_offset = sum(len(l) + 1 for l in lines[:line_num - 1])
                if head_start != -1 and head_end != -1 and head_start < line_offset < head_end:
                    add_finding(
                        findings, "WARN", "cwv", rel_path, line_num,
                        "Script in <head> without async/defer blocks rendering",
                    )


# ---------------------------------------------------------------------------
# Category 9: llms.txt (GEO signal)
# ---------------------------------------------------------------------------


def check_llms_txt(project_root: Path, findings: Findings) -> None:
    """Check for llms.txt file (Generative Engine Optimization signal)."""
    candidates = [
        project_root / "llms.txt",
        project_root / "public" / "llms.txt",
        project_root / "static" / "llms.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return

    add_finding(
        findings, "INFO", "geo", "project", 0,
        "No llms.txt found (recommended for Generative Engine Optimization)",
    )


# ---------------------------------------------------------------------------
# Main scan orchestrator
# ---------------------------------------------------------------------------


def scan(scan_path: Path, project_root: Path) -> dict:
    """Run all SEO checks and return structured results."""
    files = collect_files(scan_path)
    findings: Findings = []

    # Per-file checks
    for fpath in files:
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        rel_path = str(fpath.relative_to(project_root))

        check_meta_tags(content, rel_path, findings)
        check_headings(content, rel_path, findings)
        check_image_alt(content, rel_path, findings)
        check_structured_data(content, rel_path, findings)
        check_cwv_signals(content, rel_path, findings)

    # Project-level checks
    check_hreflang(project_root, findings)
    check_robots(project_root, findings)
    check_sitemap(project_root, findings)
    check_llms_txt(project_root, findings)

    # Deduplicate
    seen: set[tuple[str, int, str]] = set()
    deduped: Findings = []
    for f in findings:
        key = (f["file"], f["line"], f["message"])
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    findings = deduped

    # Sort by severity (HIGH -> WARN -> INFO), then file, then line
    sev_order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (sev_order.get(f["severity"], 9), f["file"], f["line"]))

    # Build summary
    summary = {"HIGH": 0, "WARN": 0, "INFO": 0}
    for f in findings:
        sev = f["severity"]
        summary[sev] = summary.get(sev, 0) + 1

    rel_scan = str(scan_path.relative_to(project_root)) if scan_path != project_root else "."

    return {
        "scan_path": rel_scan,
        "files_scanned": len(files),
        "findings": findings,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SEO scanner -- detect common SEO issues in HTML/JSX/TSX/Vue/Astro/Svelte files",
    )
    parser.add_argument(
        "path", nargs="?", default=".",
        help="Directory or file to scan (default: current directory)",
    )
    parser.add_argument(
        "--output", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.exists():
        print(json.dumps({"error": f"Path does not exist: {target}"}), file=sys.stderr)
        sys.exit(2)

    scan_path = target if target.is_dir() else target.parent
    project_root = find_project_root(scan_path)

    result = scan(scan_path, project_root)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_text_report(result)

    # Exit code: non-zero if HIGH findings exist
    if result["summary"].get("HIGH", 0) > 0:
        sys.exit(1)


def _print_text_report(result: dict) -> None:
    """Print a human-readable text report."""
    summary = result["summary"]
    print(f"\nSEO Scan: {result['scan_path']}")
    print(f"Files scanned: {result['files_scanned']}")
    print(f"HIGH: {summary.get('HIGH', 0)}  WARN: {summary.get('WARN', 0)}  INFO: {summary.get('INFO', 0)}")
    print()

    for f in result["findings"]:
        line_str = f":{f['line']}" if f["line"] > 0 else ""
        print(f"[{f['severity']}] {f['category']} | {f['file']}{line_str}")
        print(f"  {f['message']}")
        print()


if __name__ == "__main__":
    main()
