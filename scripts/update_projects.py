#!/usr/bin/env python3
"""Update all registered projects in parallel.

Reads ~/.softspark/ai-toolkit/projects.json and runs install.py --local in each
project directory concurrently using a thread pool.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_steps.project_registry import get_active_projects, prune_stale, register_project


def _update_project(project: dict[str, Any], install_script: str, extra_args: list[str]) -> dict:
    """Run install --local in a single project. Returns result dict."""
    project_path = project["path"]
    start = time.monotonic()

    # Pass saved editors from registry so update re-installs the same editors
    cmd_args = ["python3", install_script, "--local"] + extra_args
    project_editors = project.get("editors", [])
    if project_editors:
        cmd_args.extend(["--editors", ",".join(project_editors)])

    try:
        proc = subprocess.run(
            cmd_args,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed = time.monotonic() - start
        return {
            "path": project_path,
            "profile": project.get("profile", ""),
            "extends": project.get("extends", ""),
            "success": proc.returncode == 0,
            "elapsed": round(elapsed, 1),
            "output": proc.stdout,
            "error": proc.stderr if proc.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "path": project_path,
            "success": False,
            "elapsed": 120.0,
            "output": "",
            "error": "Timed out after 120s",
        }
    except OSError as e:
        return {
            "path": project_path,
            "success": False,
            "elapsed": 0,
            "output": "",
            "error": str(e),
        }


def main() -> None:
    """Update all registered projects."""
    # Parse args
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    json_output = "--json" in sys.argv
    extra_args = [a for a in sys.argv[1:] if a not in ("--verbose", "-v", "--json")]

    # Prune stale projects first
    pruned = prune_stale()
    if pruned and not json_output:
        for p in pruned:
            print(f"  Pruned stale project: {p}")

    # Get active projects
    projects = get_active_projects()

    if not projects:
        if json_output:
            print(json.dumps({"projects": [], "summary": "No registered projects"}))
        else:
            print("  No registered projects.")
            print("  Run 'ai-toolkit install --local' in a project to register it.")
        sys.exit(0)

    install_script = str(Path(__file__).resolve().parent / "install.py")

    if not json_output:
        print(f"  Updating {len(projects)} registered project(s)...")
        print()

    # --skip-register: parallel installs must NOT write to projects.json
    # concurrently. We re-register sequentially after all installs complete.
    parallel_args = extra_args + ["--skip-register"]

    # Run in parallel (max 8 workers — don't overwhelm the system)
    max_workers = min(len(projects), 8)
    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_update_project, p, install_script, parallel_args): p
            for p in projects
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if not json_output:
                status = "✓" if result["success"] else "✗"
                path_short = result["path"].replace(str(Path.home()), "~")
                extends_info = f" (extends: {result.get('extends', '')})" if result.get("extends") else ""
                print(f"  {status} {path_short}{extends_info} ({result['elapsed']}s)")

                if verbose and result["output"]:
                    for line in result["output"].strip().split("\n"):
                        print(f"      {line}")

                if result.get("error"):
                    for line in result["error"].strip().split("\n"):
                        print(f"      ERROR: {line}")

    # Re-register projects sequentially (safe — no concurrent writes)
    for result in results:
        if result["success"]:
            register_project(
                result["path"],
                profile=result.get("profile", "standard"),
                extends=result.get("extends", ""),
            )

    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    if json_output:
        print(json.dumps({
            "projects": results,
            "total": len(results),
            "passed": passed,
            "failed": failed,
        }, indent=2))
    else:
        print()
        print(f"  Updated: {passed}/{len(results)} projects" +
              (f" ({failed} failed)" if failed else ""))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
