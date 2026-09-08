#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Transactional, local journal for an agent-driven development process.

This program records observations. It never executes a project command, opens a
PR, grants permission, or establishes that an agent's report is truthful.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlparse

MAX_ATTEMPTS = 5
MAX_FAILURES = 3
RETRY_INTERVAL = 60
KINDS = ("validation", "review", "qa", "ci")
RESULTS = ("pass", "fail", "pending", "not-applicable")
STAGES = ("discover", "plan", "implement", "validate", "review", "qa", "publish", "ci", "blocked")


class StateError(Exception):
    """Expected input, ownership, Git, or completion error."""


class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise StateError(message)


def nonempty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must contain non-whitespace text")
    return value.strip()


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), "-c", "core.fsmonitor=false", *args],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise StateError(f"Git metadata query failed: {args[0]}; use an initialized working tree")
    return result.stdout


@dataclass(frozen=True)
class Fingerprint:
    repository: str
    worktree: str
    branch: str
    head: str
    digest: str
    clean: bool
    verification_problem: str | None = None


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as report:
        for block in iter(lambda: report.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_digest(repo: Path) -> tuple[str, str | None]:
    """Hash index and actual tracked/nonignored files, even assume-unchanged files."""
    index = git(repo, "ls-files", "--stage", "-z")
    digest = hashlib.sha256(index)
    gitlinks = {entry.split(b"\t", 1)[1] for entry in index.split(b"\0") if entry.startswith(b"160000 ")}
    visibility = git(repo, "ls-files", "-v", "-z")
    digest.update(visibility)
    problem = None
    if any(entry[:1].islower() or entry[:1] == b"S" for entry in visibility.split(b"\0") if entry):
        problem = "Tracked paths use assume-unchanged or skip-worktree; source cannot be fully verified"
    paths = git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for raw in sorted(set(paths.split(b"\0")) - {b""}):
        path = repo / os.fsdecode(raw)
        digest.update(raw + b"\0")
        if raw in gitlinks and not (path / ".git").exists():
            problem = "Uninitialized submodule cannot be fully verified"
        if path.is_symlink():
            value = b"link:" + os.fsencode(os.readlink(path))
        elif path.is_file():
            executable = path.stat().st_mode & stat.S_IXUSR
            value = f"file:{executable}:{file_digest(path)}".encode()
        elif path.is_dir():
            # Gitlinks need the nested contents, not just the superproject's
            # generic '-dirty' suffix. Uninitialized gitlinks have no .git.
            value = b"gitlink:uninitialized"
            if (path / ".git").exists():
                nested = fingerprint(path)
                value = json.dumps(asdict(nested), sort_keys=True).encode()
                if not nested.clean:
                    problem = "Submodule contains dirty or unverifiable source"
            else:
                problem = "Uninitialized submodule cannot be fully verified"
        else:
            value = b"missing"
        digest.update(value + b"\0")
    return digest.hexdigest(), problem


def fingerprint(repo: Path) -> Fingerprint:
    root = Path(os.fsdecode(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    common = os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).strip()
    digest, problem = source_digest(root)
    return Fingerprint(
        repository=str(Path(common).resolve()),
        worktree=str(root),
        branch=os.fsdecode(git(root, "rev-parse", "--abbrev-ref", "HEAD")).strip(),
        head=os.fsdecode(git(root, "rev-parse", "HEAD")).strip(),
        digest=digest,
        clean=not problem
        and not bool(git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none")),
        verification_problem=problem,
    )


def default_store(repo: Path) -> Path:
    # Git lists the primary worktree first, including when invoked from a linked
    # worktree; the common directory remains the identity stored inside SQLite.
    entry = git(repo, "worktree", "list", "--porcelain", "-z").split(b"\0", 1)[0]
    if not entry.startswith(b"worktree "):
        raise StateError("Cannot resolve the primary Git working tree")
    primary = str(Path(os.fsdecode(entry.removeprefix(b"worktree "))).resolve())
    return Path.home() / ".softspark/ai-toolkit/sessions" / primary.replace("/", "-") / "autonomous"


@dataclass
class Evidence:
    kind: str
    result: str
    report: str
    report_digest: str
    summary: str
    fingerprint: Fingerprint
    recorded_at: float


@dataclass
class Run:
    run_id: str
    subject: str
    objective: str
    source_kind: str
    source: str
    target_branch: str
    fingerprint: Fingerprint
    owner_digest: str
    created_at: float
    artifact_dir: str
    endpoint: str = "ready-pr"
    stage: str = "discover"
    status: str = "active"
    plan: str | None = None
    plan_digest: str | None = None
    artifacts: list[str] = field(default_factory=list)
    pr_url: str | None = None
    qa_required: bool = True
    ci_required: bool = True
    attempts: int = 0
    consecutive_failures: int = 0
    attempt_active: bool = False
    last_attempt_at: float | None = None
    last_attempt_result: str | None = None
    last_attempt_fingerprint: Fingerprint | None = None
    evidence: dict[str, Evidence] = field(default_factory=dict)

    @classmethod
    def decode(cls, payload: str) -> Run:
        raw = json.loads(payload)
        raw["fingerprint"] = Fingerprint(**raw["fingerprint"])
        if raw.get("last_attempt_fingerprint"):
            raw["last_attempt_fingerprint"] = Fingerprint(**raw["last_attempt_fingerprint"])
        raw["evidence"] = {
            kind: Evidence(**{**item, "fingerprint": Fingerprint(**item["fingerprint"])})
            for kind, item in raw["evidence"].items()
        }
        return cls(**raw)


def token_digest(token: str) -> str:
    if len(token) < 16 or not token.strip():
        raise StateError("Owner tokens must contain at least 16 characters; use a unique session token")
    return hashlib.sha256(token.encode()).hexdigest()


def assert_owner(run: Run, owner: str) -> None:
    if not run.owner_digest or not secrets.compare_digest(run.owner_digest, token_digest(owner)):
        raise StateError("Run is not owned by this session; claim it or explicitly take over")
    if run.status == "complete":
        raise StateError("Completed runs are immutable")


def report_problem(item: Evidence, current: Fingerprint) -> str | None:
    if item.fingerprint != current:
        return "stale Git fingerprint"
    path = Path(item.report)
    if not path.is_file() or path.stat().st_size == 0:
        return "report is missing or empty"
    if file_digest(path) != item.report_digest:
        return "report contents changed"
    return None


def gate_blockers(run: Run, current: Fingerprint, *, include_ci: bool = True) -> list[str]:
    blockers: list[str] = []
    for kind in KINDS if include_ci else KINDS[:-1]:
        item = run.evidence.get(kind)
        if item is None:
            blockers.append(f"{kind}: evidence missing")
            continue
        problem = report_problem(item, current)
        optional = (kind == "qa" and not run.qa_required) or (kind == "ci" and not run.ci_required)
        if problem:
            blockers.append(f"{kind}: {problem}")
        elif item.result != "pass" and not (optional and item.result == "not-applicable"):
            blockers.append(f"{kind}: {item.result}")
    return blockers


def blockers_for(run: Run, current: Fingerprint) -> list[str]:
    blockers = gate_blockers(run, current)
    if run.stage == "blocked":
        blockers.insert(0, "Run is blocked: resolve the cause and checkpoint the next stage")
    if current != run.fingerprint:
        blockers.insert(0, "Git state changed: checkpoint the intended branch and revision")
    if not current.clean:
        blockers.insert(
            0, current.verification_problem or "Working tree is dirty: commit the intended changes and rerun gates"
        )
    if current.branch == "HEAD" or current.branch == run.target_branch:
        blockers.append("Use an attached feature branch distinct from the PR target branch")
    if problem := plan_problem(run):
        blockers.append(problem)
    if not run.pr_url:
        blockers.append("PR URL missing: discover an existing PR before creating one")
    if run.attempt_active:
        blockers.append("Finish the active attempt with pass or fail")
    elif run.last_attempt_result != "pass" or run.last_attempt_fingerprint != current:
        blockers.append("A successfully closed latest attempt for the current source is required")
    if run.consecutive_failures >= MAX_FAILURES:
        blockers.insert(0, "Circuit breaker: three consecutive failed attempts")
    if not run.owner_digest and run.status != "complete":
        blockers.insert(0, "Run is released: claim it with a unique session owner token")
    return blockers


def plan_problem(run: Run) -> str | None:
    if not run.plan or not run.plan_digest:
        return "Plan file missing: attach an existing nonempty plan with checkpoint --stage plan --plan PATH"
    path = Path(run.plan)
    if not path.is_file() or path.stat().st_size == 0:
        return "Plan file is missing or empty"
    if file_digest(path) != run.plan_digest:
        return "Plan contents changed: checkpoint the revised plan and rerun its gates"
    return None


def attach_plan(run: Run, value: str) -> None:
    path = Path(value).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise StateError("Plan requires an existing nonempty local file")
    digest = file_digest(path)
    if run.plan != str(path) or run.plan_digest != digest:
        run.evidence.clear()
        run.last_attempt_result = None
        run.last_attempt_fingerprint = None
    run.plan, run.plan_digest = str(path), digest


def next_step(run: Run, current: Fingerprint) -> str:
    if run.status == "complete":
        return "done: ready-pr was recorded; later source changes require a separately scoped run"
    if not run.owner_digest:
        return "claim: acquire the released run with a unique session owner token"
    if run.consecutive_failures >= MAX_FAILURES:
        return "halt: three consecutive failed attempts; report the blocker"
    if current.worktree != run.fingerprint.worktree:
        return "claim --rebind-worktree: reconcile the saved working tree before explicit adoption"
    if current.verification_problem:
        return "blocked: " + current.verification_problem
    if problem := plan_problem(run):
        return "plan: " + problem
    if run.stage == "blocked":
        return "blocked: resolve the cause and checkpoint the next stage"
    needs_attempt = run.last_attempt_result != "pass" or run.last_attempt_fingerprint != current
    if run.attempts >= MAX_ATTEMPTS and not run.attempt_active and needs_attempt:
        return "halt: five attempts exhausted; report the blocker"
    if not run.attempt_active and needs_attempt:
        return "attempt start: begin the next implementation or verification cycle within the retry budget"
    if current != run.fingerprint or not current.clean:
        return "implement: reconcile source changes, commit and checkpoint the intended revision"
    if run.attempt_active and run.stage in ("discover", "plan", "implement") and "validation" not in run.evidence:
        return "implement: continue the active cycle, then checkpoint validate for the intended committed source"
    if local := gate_blockers(run, current, include_ci=False):
        return local[0]
    if not run.pr_url:
        return "publish: find or create the authorized PR and checkpoint its URL"
    if remote := gate_blockers(run, current):
        return remote[0]
    if run.attempt_active:
        return "attempt pass: close the successful current cycle"
    return "complete: verify the final ready-pr gate"


class Journal:
    def __init__(self, repo: Path, store: Path, *, clock: Callable[[], float] = time.time) -> None:
        self.repo = repo.resolve()
        self.store = store.resolve()
        self.clock = clock

    @contextmanager
    def connect(self, *, create: bool) -> Iterator[sqlite3.Connection]:
        path = self.store / "runs.sqlite3"
        if create:
            root = Path(fingerprint(self.repo).worktree)
            if self.store.is_relative_to(root):
                raise StateError("The journal must be outside the working tree; use --store elsewhere")
            self.store.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not create and not path.is_file():
            raise StateError("No run journal exists for this repository")
        uri = path.as_uri() + ("?mode=rwc" if create else "?mode=ro")
        connection = sqlite3.connect(uri, uri=True, timeout=15)
        try:
            if create:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, repository TEXT NOT NULL, subject TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(repository, subject))"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, time REAL NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL)"
                )
                connection.commit()
            with connection:
                yield connection
        finally:
            connection.close()

    def load(self, connection: sqlite3.Connection, run_id: str) -> Run:
        row = connection.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise StateError("Run does not exist")
        run = Run.decode(row[0])
        common = Path(
            os.fsdecode(git(self.repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).strip()
        ).resolve()
        if str(common) != run.fingerprint.repository:
            raise StateError("Run belongs to another Git repository")
        return run

    def save(self, connection: sqlite3.Connection, run: Run, action: str, detail: dict[str, Any]) -> None:
        connection.execute("UPDATE runs SET state = ? WHERE id = ?", (json.dumps(asdict(run)), run.run_id))
        connection.execute(
            "INSERT INTO events (run_id, time, action, detail) VALUES (?, ?, ?, ?)",
            (run.run_id, self.clock(), action, json.dumps(detail)),
        )

    def initialize(self, args: argparse.Namespace) -> dict[str, Any]:
        current = fingerprint(self.repo)
        owner = "session_" + secrets.token_urlsafe(32)
        run_id = str(uuid.uuid4())
        artifacts = self.store / run_id / "artifacts"
        run = Run(
            run_id=run_id,
            subject=args.subject,
            objective=args.objective,
            source_kind=args.source_kind,
            source=args.source,
            target_branch=args.target_branch,
            fingerprint=current,
            owner_digest=token_digest(owner),
            created_at=self.clock(),
            artifact_dir=str(artifacts),
            artifacts=args.artifact,
            qa_required=not args.qa_optional,
            ci_required=not args.ci_optional,
        )
        if args.plan:
            attach_plan(run, args.plan)
        with self.connect(create=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT id FROM runs WHERE repository = ? AND subject = ?", (current.repository, args.subject)
            ).fetchone()
            if existing:
                raise StateError(f"Subject already has run {existing[0]}; use status and claim")
            artifacts.mkdir(parents=True, exist_ok=False, mode=0o700)
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?)",
                (run_id, current.repository, args.subject, json.dumps(asdict(run))),
            )
            self.save(connection, run, "init", {"subject": run.subject})
        return {**self.status(run_id), "owner_token": owner}

    def list_runs(self, subject: str | None = None) -> dict[str, Any]:
        common = Path(
            os.fsdecode(git(self.repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).strip()
        ).resolve()
        if not (self.store / "runs.sqlite3").is_file():
            return {"ok": True, "runs": []}
        with self.connect(create=False) as connection:
            rows = connection.execute(
                "SELECT state FROM runs WHERE repository = ? AND (? IS NULL OR subject = ?) ORDER BY id",
                (str(common), subject, subject),
            ).fetchall()
        runs = [Run.decode(row[0]) for row in rows]
        return {"ok": True, "runs": [
            {"run_id": run.run_id, "subject": run.subject, "objective": run.objective,
             "status": run.status, "stage": run.stage, "pr_url": run.pr_url,
             "worktree": run.fingerprint.worktree, "branch": run.fingerprint.branch,
             "artifact_dir": run.artifact_dir}
            for run in runs
        ]}

    def status(self, run_id: str) -> dict[str, Any]:
        with self.connect(create=False) as connection:
            run = self.load(connection, run_id)
            history = [
                {"sequence": row[0], "time": row[1], "action": row[2], "detail": json.loads(row[3])}
                for row in connection.execute(
                    "SELECT id, time, action, detail FROM events WHERE run_id = ? ORDER BY id", (run_id,)
                )
            ]
        current = fingerprint(self.repo)
        blockers = blockers_for(run, current)
        payload = asdict(run)
        payload.pop("owner_digest")
        payload["owner_id"] = run.owner_digest[:16] if run.owner_digest else None
        return {
            "ok": True,
            "run": payload,
            "current_git": asdict(current),
            "history": history,
            "blockers": blockers,
            "next_step": next_step(run, current),
            "artifact_dir": run.artifact_dir,
        }

    def mutate(self, args: argparse.Namespace) -> dict[str, Any]:
        with self.connect(create=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self.load(connection, args.run)
            current = fingerprint(self.repo)
            if args.verb == "claim":
                detail = self.claim(run, args, current)
            else:
                assert_owner(run, args.owner)
                if current.worktree != run.fingerprint.worktree:
                    raise StateError("Wrong working tree; explicit claim --rebind-worktree is required")
                detail = self.apply(run, args, current)
            self.save(connection, run, args.verb, detail)
        return self.status(args.run)

    def claim(self, run: Run, args: argparse.Namespace, current: Fingerprint) -> dict[str, Any]:
        if run.status == "complete":
            raise StateError("Completed runs are immutable")
        owner = token_digest(args.owner)
        previous = run.owner_digest[:16]
        if (
            run.owner_digest
            and not secrets.compare_digest(run.owner_digest, owner)
            and (args.previous_owner != previous or not args.reason)
        ):
            raise StateError(f"Run is owned by session {previous}; takeover requires --previous-owner and --reason")
        if current.worktree != run.fingerprint.worktree:
            if not args.rebind_worktree:
                raise StateError("Wrong working tree; supply --rebind-worktree for explicit adoption")
            old = run.fingerprint
            if (
                not old.clean
                or not current.clean
                or (old.branch, old.head, old.digest) != (current.branch, current.head, current.digest)
            ):
                raise StateError("Rebinding requires the same branch, HEAD, clean contents and index")
            old_path = Path(old.worktree)
            if old_path.exists() and fingerprint(old_path) != old:
                raise StateError("Original working tree changed; reconcile it before rebinding")
            run.fingerprint = current
        run.owner_digest = owner
        return {
            "previous_owner": previous or None,
            "owner_id": owner[:16],
            "reason": args.reason,
            "rebound": args.rebind_worktree,
        }

    def apply(self, run: Run, args: argparse.Namespace, current: Fingerprint) -> dict[str, Any]:
        if args.verb == "checkpoint":
            return checkpoint(run, args, current)
        if args.verb == "record":
            return record(run, args, current, self.clock())
        if args.verb == "attempt":
            return attempt(run, args, current, self.clock())
        if args.verb == "release":
            run.owner_digest = ""
            return {"reason": args.reason}
        blockers = blockers_for(run, current)
        if blockers:
            raise StateError("Cannot complete: " + "; ".join(blockers))
        run.stage, run.status = "ready-pr", "complete"
        return {"head": current.head, "pr_url": run.pr_url}


def checkpoint(run: Run, args: argparse.Namespace, current: Fingerprint) -> dict[str, Any]:
    run.stage = args.stage
    run.fingerprint = current
    if args.plan:
        attach_plan(run, args.plan)
    run.artifacts = list(dict.fromkeys([*run.artifacts, *args.artifact]))
    if args.pr_url:
        parsed = urlparse(args.pr_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise StateError("PR identity must be an HTTPS URL without credentials, query or fragment")
        if run.pr_url and run.pr_url != args.pr_url:
            raise StateError("A different PR is already attached; reconcile the existing PR")
        run.pr_url = args.pr_url
    return {"stage": run.stage, "head": current.head, "branch": current.branch, "pr_url": run.pr_url}


def record(run: Run, args: argparse.Namespace, current: Fingerprint, now: float) -> dict[str, Any]:
    if problem := plan_problem(run):
        raise StateError(problem)
    path = Path(args.report).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise StateError("Evidence requires an existing nonempty report file")
    optional = (args.kind == "qa" and not run.qa_required) or (args.kind == "ci" and not run.ci_required)
    if args.result == "not-applicable" and not optional:
        raise StateError(
            "Only QA or CI made optional at init may be not-applicable; give the reason in --summary and report"
        )
    item = Evidence(args.kind, args.result, str(path), file_digest(path), args.summary, current, now)
    run.evidence[args.kind] = item
    return asdict(item)


def attempt(run: Run, args: argparse.Namespace, current: Fingerprint, now: float) -> dict[str, Any]:
    if args.action == "start":
        if run.attempt_active:
            raise StateError("An attempt is already active; resume it or finish with pass/fail")
        if run.attempts >= MAX_ATTEMPTS or run.consecutive_failures >= MAX_FAILURES:
            raise StateError("Autonomous attempt limit or failure circuit breaker reached")
        if run.last_attempt_at is not None and now - run.last_attempt_at < RETRY_INTERVAL:
            raise StateError("Wait at least 60 seconds between attempt starts")
        run.attempts += 1
        run.last_attempt_at, run.attempt_active = now, True
        run.last_attempt_result = None
        run.last_attempt_fingerprint = None
    else:
        if not run.attempt_active or not args.summary:
            raise StateError("Finishing requires an active attempt and --summary")
        if args.action == "pass" and (blockers := gate_blockers(run, current, include_ci="ci" in run.evidence)):
            raise StateError("Cannot pass attempt: " + "; ".join(blockers))
        if args.action == "pass" and (problem := plan_problem(run)):
            raise StateError(problem)
        run.attempt_active = False
        run.consecutive_failures = run.consecutive_failures + 1 if args.action == "fail" else 0
        run.last_attempt_result = args.action
        run.last_attempt_fingerprint = current
    return {
        "action": args.action,
        "attempt": run.attempts,
        "consecutive_failures": run.consecutive_failures,
        "summary": args.summary,
    }


def parser() -> argparse.ArgumentParser:
    result = JsonParser(description=__doc__)
    result.add_argument("--repo", type=Path, default=Path.cwd(), help="Target Git working tree")
    result.add_argument("--store", type=Path, help="External journal directory (fixtures or custom local storage)")
    verbs = result.add_subparsers(dest="verb", required=True)
    init = verbs.add_parser("init", help="Create a unique subject run and session owner token")
    for name in ("subject", "objective", "source"):
        init.add_argument(f"--{name}", required=True, type=nonempty)
    init.add_argument("--source-kind", choices=("brief", "spec", "issue", "pr"), required=True)
    init.add_argument("--target-branch", default="main", type=nonempty, help="PR base branch, not the work branch")
    init.add_argument("--endpoint", choices=("ready-pr",), default="ready-pr")
    init.add_argument("--plan", type=nonempty)
    init.add_argument("--artifact", action="append", default=[], type=nonempty)
    init.add_argument("--qa-optional", action="store_true")
    init.add_argument("--ci-optional", action="store_true")
    listing = verbs.add_parser("list", help="List this repository's runs without changing state")
    listing.add_argument("--subject", type=nonempty, help="Filter by exact stable task subject")
    for verb in ("status", "claim", "checkpoint", "record", "attempt", "release", "complete"):
        command = verbs.add_parser(verb)
        command.add_argument("--run", required=True)
        if verb != "status":
            command.add_argument("--owner", required=True, type=nonempty)
        add_verb_arguments(command, verb)
    return result


def add_verb_arguments(command: argparse.ArgumentParser, verb: str) -> None:
    if verb == "claim":
        command.add_argument("--previous-owner", help="Previous owner_id from status, for explicit takeover")
        command.add_argument("--reason", type=nonempty)
        command.add_argument("--rebind-worktree", action="store_true")
    if verb == "checkpoint":
        command.add_argument("--stage", choices=STAGES, required=True)
        command.add_argument("--plan", type=nonempty)
        command.add_argument("--artifact", action="append", default=[], type=nonempty)
        command.add_argument("--pr-url", type=nonempty)
    if verb == "record":
        command.add_argument("--kind", choices=KINDS, required=True)
        command.add_argument("--result", choices=RESULTS, required=True)
        command.add_argument("--report", required=True, type=nonempty)
        command.add_argument("--summary", required=True, type=nonempty)
    if verb == "attempt":
        command.add_argument("--action", choices=("start", "pass", "fail"), required=True)
        command.add_argument("--summary", type=nonempty)
    if verb == "release":
        command.add_argument("--reason", required=True, type=nonempty)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        journal = Journal(args.repo, args.store or default_store(args.repo))
        if args.verb == "init":
            payload = journal.initialize(args)
        elif args.verb == "list":
            payload = journal.list_runs(args.subject)
        elif args.verb == "status":
            payload = journal.status(args.run)
        else:
            payload = journal.mutate(args)
        print(json.dumps(payload, sort_keys=True))
        return 0
    except (StateError, OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
