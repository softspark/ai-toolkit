#!/usr/bin/env python3
"""Ecosystem Doctor — detects upstream drift across supported tools.

Reads scripts/ecosystem_tools.json, probes each tool's documentation page
and (when configured) its CLI version, diffs against benchmarks/ecosystem-doctor-snapshot.json,
and reports what changed since the last run.

Stdlib-only. JSON output by default; `--format text` for human view.
Non-zero exit in --check mode when drift is detected.

Usage:
    ecosystem_doctor.py                        # check all tools, JSON to stdout
    ecosystem_doctor.py --format text          # human-readable
    ecosystem_doctor.py --tool cursor          # single tool
    ecosystem_doctor.py --offline              # skip network probes
    ecosystem_doctor.py --update               # refresh snapshot (overwrite)
    ecosystem_doctor.py --check                # exit 1 on any drift

Exit codes:
    0  no drift, or --update mode
    1  drift detected (in --check mode) or script error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir

REGISTRY_PATH = toolkit_dir / "scripts" / "ecosystem_tools.json"
SNAPSHOT_PATH = toolkit_dir / "benchmarks" / "ecosystem-doctor-snapshot.json"

USER_AGENT = "ai-toolkit-ecosystem-doctor/1.0 (+https://github.com/softspark/ai-toolkit)"
HTTP_TIMEOUT = 15

HEADING_RE = re.compile(r"<h([1-3])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def load_registry() -> dict:
    """Read tool registry JSON."""
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError(f"Registry not found: {REGISTRY_PATH}")
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_snapshot() -> dict:
    """Read last-seen snapshot or empty dict."""
    if not SNAPSHOT_PATH.is_file():
        return {"schema_version": 1, "tools": {}}
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def save_snapshot(snapshot: dict) -> None:
    """Write snapshot atomically."""
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(SNAPSHOT_PATH)


def fetch_url(url: str) -> tuple[str, str | None]:
    """Fetch a URL. Returns (content, error). On failure, content is empty and error is set."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html, text/plain, */*"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace"), None
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return "", f"URL error: {e.reason}"
    except TimeoutError:
        return "", f"timeout after {HTTP_TIMEOUT}s"
    except Exception as e:  # noqa: BLE001 — single-point error capture, safe degradation
        return "", f"{type(e).__name__}: {e}"


def strip_html(s: str) -> str:
    """Remove tags, collapse whitespace."""
    return WHITESPACE_RE.sub(" ", TAG_RE.sub("", s)).strip()


def extract_headings(content: str) -> list[str]:
    """Extract unique H1-H3 headings from HTML or Markdown.

    Returns a sorted list (stable for diff).
    """
    found: set[str] = set()
    for match in HEADING_RE.finditer(content):
        text = strip_html(match.group(2))
        if text:
            found.add(text)
    for match in MARKDOWN_HEADING_RE.finditer(content):
        text = match.group(2).strip()
        if text:
            found.add(text)
    return sorted(found)


def detect_markers(content: str, markers: list[str]) -> dict[str, bool]:
    """For each expected marker, record whether it appears in content (case-insensitive)."""
    lower = content.lower()
    return {m: (m.lower() in lower) for m in markers}


def content_hash(content: str) -> str:
    """SHA-256 of fetched content (hex, truncated)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def probe_version(probe: dict | None) -> str | None:
    """Run the tool's version command. Returns None if not configured or command missing."""
    if not probe or probe.get("kind") != "command":
        return None
    cmd = probe.get("command", "")
    if not cmd:
        return None
    binary = cmd.split()[0]
    if shutil.which(binary) is None:
        return None
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
        return (result.stdout or result.stderr).strip().splitlines()[0] if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


def diff_lists(old: list[str], new: list[str]) -> tuple[list[str], list[str]]:
    """Return (added, removed) between two sorted lists."""
    old_set, new_set = set(old), set(new)
    return sorted(new_set - old_set), sorted(old_set - new_set)


def check_tool(tool: dict, last_seen: dict, offline: bool) -> dict:
    """Probe one tool and compare against its last-seen state. Returns a report dict.

    `last_seen` is the per-tool state dict (keys: docs_hash, headings, markers, version).
    """
    tool_id = tool["id"]
    previous = last_seen
    report: dict = {
        "id": tool_id,
        "display_name": tool["display_name"],
        "kind": tool.get("kind", "editor"),
        "docs_url": tool["urls"].get("docs"),
        "drift": [],
        "current": {},
        "errors": [],
    }

    # --- Static checks (offline-safe) -----------------------------------------
    generators = tool.get("our_generators", [])
    report["current"]["generator_count"] = len(generators)
    missing_generators = [g for g in generators if not (toolkit_dir / g).is_file()]
    if missing_generators:
        report["errors"].append(f"Declared generators missing on disk: {missing_generators}")

    # --- Dynamic checks (network) ---------------------------------------------
    if not offline and tool["urls"].get("docs"):
        content, err = fetch_url(tool["urls"]["docs"])
        if err:
            report["errors"].append(f"docs fetch: {err}")
        else:
            report["current"]["docs_hash"] = content_hash(content)
            headings = extract_headings(content)
            report["current"]["heading_count"] = len(headings)

            # Diff headings vs previous run
            prev_headings = previous.get("headings", [])
            added, removed = diff_lists(prev_headings, headings)
            if added:
                report["drift"].append({"kind": "headings_added", "items": added[:20]})
            if removed:
                report["drift"].append({"kind": "headings_removed", "items": removed[:20]})

            report["_headings_snapshot"] = headings  # consumed by --update

            # Marker presence check
            markers_seen = detect_markers(content, tool.get("capability_markers", []))
            report["current"]["markers"] = markers_seen
            prev_markers = previous.get("markers", {})
            marker_changes: list[str] = []
            for m, seen in markers_seen.items():
                if m in prev_markers and prev_markers[m] != seen:
                    marker_changes.append(f"{m}: {'+' if seen else '-'}")
            if marker_changes:
                report["drift"].append({"kind": "marker_flips", "items": marker_changes})

            # Content hash diff (any change at all)
            if previous.get("docs_hash") and previous["docs_hash"] != report["current"]["docs_hash"]:
                if not added and not removed and not marker_changes:
                    report["drift"].append({"kind": "content_changed_no_heading_delta"})

    # --- Version probe --------------------------------------------------------
    if not offline:
        version = probe_version(tool.get("version_probe"))
        if version is not None:
            report["current"]["version"] = version
            prev_version = previous.get("version")
            if prev_version and prev_version != version:
                report["drift"].append({"kind": "version_changed", "old": prev_version, "new": version})

    return report


def render_text(report: list[dict]) -> str:
    """Render report as human-readable text."""
    out: list[str] = ["# Ecosystem Doctor Report", ""]
    clean: list[dict] = []
    drifted: list[dict] = []
    errored: list[dict] = []
    for r in report:
        if r.get("errors"):
            errored.append(r)
        elif r.get("drift"):
            drifted.append(r)
        else:
            clean.append(r)

    out.append(f"Tools checked: {len(report)}")
    out.append(f"  Clean:    {len(clean)}")
    out.append(f"  Drift:    {len(drifted)}")
    out.append(f"  Errored:  {len(errored)}")
    out.append("")

    if drifted:
        out.append("## Drift detected")
        out.append("")
        for r in drifted:
            out.append(f"### {r['display_name']} ({r['id']})")
            if r.get("docs_url"):
                out.append(f"  Docs: {r['docs_url']}")
            for d in r["drift"]:
                kind = d["kind"]
                if kind == "headings_added":
                    out.append(f"  + Added headings ({len(d['items'])}):")
                    for item in d["items"]:
                        out.append(f"      - {item}")
                elif kind == "headings_removed":
                    out.append(f"  - Removed headings ({len(d['items'])}):")
                    for item in d["items"]:
                        out.append(f"      - {item}")
                elif kind == "marker_flips":
                    out.append(f"  * Marker changes: {', '.join(d['items'])}")
                elif kind == "version_changed":
                    out.append(f"  * Version: {d['old']} -> {d['new']}")
                elif kind == "content_changed_no_heading_delta":
                    out.append("  * Content changed (no heading delta) — minor edits or reordering")
            out.append("")

    if errored:
        out.append("## Errors")
        out.append("")
        for r in errored:
            out.append(f"- {r['display_name']} ({r['id']}): {'; '.join(r['errors'])}")
        out.append("")

    if clean and not drifted and not errored:
        out.append("All tools match the last snapshot. No action needed.")

    return "\n".join(out)


def update_snapshot(snapshot: dict, reports: list[dict]) -> dict:
    """Merge doctor reports back into the snapshot for the next run."""
    snapshot.setdefault("tools", {})
    for r in reports:
        if r.get("errors"):
            continue  # do not overwrite last-known-good state with error state
        tool_state = snapshot["tools"].get(r["id"], {})
        current = r.get("current", {})
        if "docs_hash" in current:
            tool_state["docs_hash"] = current["docs_hash"]
        if "markers" in current:
            tool_state["markers"] = current["markers"]
        if "version" in current:
            tool_state["version"] = current["version"]
        if "_headings_snapshot" in r:
            tool_state["headings"] = r["_headings_snapshot"]
        snapshot["tools"][r["id"]] = tool_state
    from datetime import datetime, timezone
    snapshot["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect upstream drift in tools ai-toolkit integrates with.")
    parser.add_argument("--tool", help="Check only this tool id (default: all)")
    parser.add_argument("--offline", action="store_true", help="Skip network probes (static checks only)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--update", action="store_true", help="Write current state to snapshot after check")
    parser.add_argument("--check", action="store_true", help="Exit 1 when drift is detected")
    args = parser.parse_args()

    registry = load_registry()
    snapshot = load_snapshot()

    tools = registry.get("tools", [])
    if args.tool:
        tools = [t for t in tools if t["id"] == args.tool]
        if not tools:
            print(f"Unknown tool id: {args.tool}", file=sys.stderr)
            sys.exit(1)

    snapshot_tools = snapshot.get("tools", {})
    reports = [check_tool(t, snapshot_tools.get(t["id"], {}), args.offline) for t in tools]

    if args.update:
        snapshot = update_snapshot(snapshot, reports)
        save_snapshot(snapshot)

    # Strip internal fields before serializing
    for r in reports:
        r.pop("_headings_snapshot", None)

    if args.format == "text":
        print(render_text(reports))
    else:
        print(json.dumps({"reports": reports}, indent=2, sort_keys=True))

    if args.check:
        # Content-hash-only drift (timestamps, ads, CSRF nonces) is expected noise
        # on dynamic docs pages. Gate only on structural drift + errors.
        def is_structural(drift_entry: dict) -> bool:
            return drift_entry.get("kind") != "content_changed_no_heading_delta"

        any_drift = any(
            any(is_structural(d) for d in r.get("drift", [])) or r.get("errors")
            for r in reports
        )
        sys.exit(1 if any_drift else 0)


if __name__ == "__main__":
    main()
