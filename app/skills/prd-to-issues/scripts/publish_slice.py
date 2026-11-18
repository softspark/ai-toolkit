# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Publish one approved PRD slice and reconcile its GitHub issue dependencies."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status

    def unavailable(self) -> bool:
        if any(word in str(self).lower() for word in ("rate limit", "abuse", "throttl")):
            return False
        return self.status in {403, 404, 405, 410, 501}

    def rejected(self) -> bool:
        return self.status in {400, 401, 403, 404, 405, 410, 422, 429, 501}


class GitHub:
    def __init__(self, host: str):
        self.host = host

    def request(self, endpoint: str, *, payload=None, pages=False):
        command = ["gh", "api", "--hostname", self.host, endpoint]
        if pages:
            command += ["--paginate", "--slurp"]
        if payload is not None:
            command += ["--method", "POST", "--input", "-"]
        try:
            result = subprocess.run(
                command, input=json.dumps(payload) if payload is not None else None,
                capture_output=True, text=True, encoding="utf-8", timeout=90, check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ApiError("GitHub request timed out") from error
        try:
            data = json.loads(result.stdout)
        except ValueError as error:
            if not result.returncode:
                raise ApiError("Invalid JSON in GitHub response") from error
            data = {}
        if result.returncode:
            match = re.search(r"\bHTTP (\d{3})\b", result.stderr)
            message = data.get("message") if isinstance(data, dict) else None
            raise ApiError(message or result.stderr.strip() or "GitHub request failed", int(match[1]) if match else None)
        if pages:
            if not isinstance(data, list) or not all(isinstance(page, list) for page in data):
                raise ApiError("Expected paginated GitHub issue lists")
            rows = [item for page in data for item in page]
            if not all(isinstance(row, dict) for row in rows):
                raise ApiError("Invalid issue in GitHub list")
            return rows
        if not isinstance(data, dict):
            raise ApiError("Expected GitHub to return an object")
        return data


def checked_issue(issue, base: str, number: int):
    if (type(number) is not int or number < 1 or not isinstance(issue, dict)
            or "pull_request" in issue or type(issue.get("id")) is not int
            or issue["id"] <= 0 or issue.get("number") != number
            or str(issue.get("html_url", "")).lower() != f"{base}/{number}".lower()):
        raise ValueError(f"Could not verify GitHub issue {base}/{number}")
    return issue


def claim(db, key: str) -> bool:
    # Committed before POST: a killed process cannot blindly repeat the request.
    with db:
        return db.execute("INSERT OR IGNORE INTO attempts(key) VALUES (?)", (key,)).rowcount == 1


def clear_rejected(db, key: str) -> None:
    with db:
        db.execute("DELETE FROM attempts WHERE key = ? AND number IS NULL", (key,))


def record_confirmed(db, key: str, number: int) -> None:
    with db:
        db.execute("INSERT OR REPLACE INTO attempts(key, number) VALUES (?, ?)", (key, number))


def find_slice(api, endpoint: str, marker: str):
    issues = api.request(f"{endpoint}?state=all&per_page=100", pages=True)
    matches = [i for i in issues if "pull_request" not in i and marker in (i.get("body") or "").splitlines()]
    if len(matches) > 1:
        raise ValueError("Multiple issues contain the slice marker. Reconcile them before publishing.")
    return matches[0] if matches else None


def get_or_create(api, db, endpoint, key, marker, payload):
    row = db.execute("SELECT number FROM attempts WHERE key = ?", (key,)).fetchone()
    if row and row[0]:
        existing = api.request(f"{endpoint}/{row[0]}")
        if existing.get("number") != row[0]:
            raise ValueError("The saved issue number does not match GitHub's response.")
        return existing
    existing = find_slice(api, endpoint, marker)
    if existing:
        return existing
    if not claim(db, key):
        raise RuntimeError("An issue creation is pending. Rerun with the same receipts to reconcile it.")
    try:
        return api.request(endpoint, payload=payload)
    except ApiError as error:
        if error.rejected():
            clear_rejected(db, key)
        existing = find_slice(api, endpoint, marker)
        if existing:
            return existing
        raise


def verify_edge(api, endpoint: str, blocker) -> bool:
    rows = api.request(f"{endpoint}?per_page=100", pages=True)
    return any(row.get("id") == blocker["id"] and row.get("number") == blocker["number"]
               and row.get("html_url") == blocker["html_url"] for row in rows)


def link_blocker(api, db, endpoint, key, blocker) -> str:
    try:
        if verify_edge(api, endpoint, blocker):
            record_confirmed(db, key, blocker["number"])
            return "native"
    except ApiError as error:
        if error.unavailable():
            pending = db.execute("SELECT number FROM attempts WHERE key = ?", (key,)).fetchone()
            if pending and pending[0] is None:
                raise RuntimeError("Cannot reconcile the pending native dependency with current access.") from error
            return "text-only"
        raise
    if not claim(db, key):
        recorded = db.execute("SELECT number FROM attempts WHERE key = ?", (key,)).fetchone()
        if recorded and recorded[0]:
            raise RuntimeError(f"Previously confirmed blocker #{blocker['number']} was removed. Review that change.")
        raise RuntimeError(f"Unconfirmed dependency for #{blocker['number']}. Reconcile before retrying.")
    try:
        api.request(endpoint, payload={"issue_id": blocker["id"]})
    except ApiError as error:
        if error.rejected():
            clear_rejected(db, key)
        try:
            confirmed = verify_edge(api, endpoint, blocker)
        except ApiError as read_error:
            if not (error.unavailable() and read_error.unavailable()):
                raise
            confirmed = False
        if confirmed:
            record_confirmed(db, key, blocker["number"])
            return "native"
        if error.unavailable():
            return "text-only"
        raise
    if not verify_edge(api, endpoint, blocker):
        raise RuntimeError(f"GitHub accepted but did not confirm the dependency on #{blocker['number']}.")
    record_confirmed(db, key, blocker["number"])
    return "native"


@dataclass(frozen=True)
class Slice:
    endpoint: str
    base: str
    key: str
    marker: str
    title: str
    body: str
    actor: int
    parent: int
    blockers: dict

    def verify_child(self, issue, number: int) -> None:
        checked_issue(issue, self.base, number)
        if number == self.parent or number in self.blockers:
            raise ValueError("A slice cannot be its own blocker or the parent PRD.")
        saved = (issue.get("body") or "").replace("\r\n", "\n").rstrip()
        if (issue.get("user", {}).get("id") != self.actor or issue.get("title") != self.title
                or not (saved == self.body or saved.startswith(self.body + "\n\n"))):
            raise ValueError(f"Slice #{number} differs from the approved content or its author. Reconcile it first.")


def release_unapplied(api, db, plan: Slice, target: str):
    # Explicit operator recovery only. Never submit a remote write on this path.
    existing = find_slice(api, plan.endpoint, plan.marker)
    key = plan.key
    if target == "issue":
        if existing:
            raise ValueError("The issue exists. Rerun normal publication to reconcile it.")
    else:
        blocker = plan.blockers.get(int(target))
        if not blocker or not existing:
            raise ValueError("Choose a planned blocker and a verified existing slice.")
        child = existing["number"]
        plan.verify_child(existing, child)
        if verify_edge(api, f"{plan.endpoint}/{child}/dependencies/blocked_by", blocker):
            raise ValueError("The native edge exists. Rerun normal publication to reconcile it.")
        key = f"{key}/edge/{child}/{blocker['id']}"
    with db:
        changed = db.execute("DELETE FROM attempts WHERE key = ? AND number IS NULL", (key,)).rowcount
    if not changed:
        raise ValueError("No pending attempt for this operation. Confirmed receipts are retained.")
    return {"released_unapplied": target}


def approved_slice(args, api) -> Slice:
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", args.repo)
            or args.repo.split("/")[1] in {".", ".."} or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.key)):
        raise ValueError("Expected OWNER/REPO and a stable lowercase slice key.")
    numbers = sorted(set(args.blocked_by))
    if args.parent < 1 or args.parent in numbers or any(n < 1 for n in numbers):
        raise ValueError("Blockers must be positive issue numbers distinct from the parent PRD.")
    text = args.body_file.read_text(encoding="utf-8").strip()
    if not text or not args.title.strip() or "<!-- ai-toolkit:prd-slice:" in text:
        raise ValueError("Supply an approved title and body without reserved slice markers.")
    base = f"https://{api.host}/{args.repo}/issues"
    endpoint = f"repos/{args.repo}/issues"
    actor = api.request("user")["id"]
    if type(actor) is not int or actor < 1:
        raise ValueError("Could not verify the authenticated GitHub account.")
    parent = checked_issue(api.request(f"{endpoint}/{args.parent}"), base, args.parent)
    blockers = {n: checked_issue(api.request(f"{endpoint}/{n}"), base, n) for n in numbers}
    marker = f"<!-- ai-toolkit:prd-slice:{parent['id']}:{args.key} -->"
    key = f"{base.lower()}/{parent['id']}/{args.key}"
    refs = "\n".join(f"- Blocked by #{n}" for n in numbers) or "None."
    body = f"## Parent PRD\n\n#{args.parent}\n\n{text}\n\n## Blocked by\n\n{refs}\n\n{marker}"
    return Slice(endpoint, base, key, marker, args.title, body, actor, args.parent, blockers)


def publish(args, api, db):
    plan = approved_slice(args, api)
    db.execute("CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, number INTEGER)")
    if args.release_unapplied is not None:
        return release_unapplied(api, db, plan, args.release_unapplied)
    payload = {"title": plan.title, "body": plan.body}
    issue = get_or_create(api, db, plan.endpoint, plan.key, plan.marker, payload)
    number = issue["number"]
    plan.verify_child(issue, number)
    endpoint = f"{plan.endpoint}/{number}"
    plan.verify_child(api.request(endpoint), number)
    record_confirmed(db, plan.key, number)
    edges = {}
    for n, blocker in plan.blockers.items():
        key = f"{plan.key}/edge/{number}/{blocker['id']}"
        edges[n] = link_blocker(api, db, f"{endpoint}/dependencies/blocked_by", key, blocker)
        if edges[n] == "text-only":
            checked_issue(api.request(f"{plan.endpoint}/{n}"), plan.base, n)
    if "text-only" in edges.values():
        plan.verify_child(api.request(endpoint), number)
    return {"issue": issue["html_url"], "number": number, "dependencies": edges}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--host", default=os.environ.get("GH_HOST") or "github.com")
    parser.add_argument("--parent", required=True, type=int)
    parser.add_argument("--key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--blocked-by", type=int, action="append", default=[])
    parser.add_argument("--receipts", required=True, type=Path, help="Persistent local SQLite file for this publisher")
    parser.add_argument("--release-unapplied", metavar="issue|BLOCKER_NUMBER",
                        help="Clear a pending local receipt only after independent proof the POST cannot land")
    args = parser.parse_args()
    try:
        with sqlite3.connect(args.receipts.resolve()) as db:
            print(json.dumps(publish(args, GitHub(args.host), db)))
    except (OSError, ValueError, KeyError, RuntimeError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
