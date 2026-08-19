#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate native Cline rules plus extension-compatible rule files.

Cline CLI/SDK reads ``.cline/rules/*.md``. The IDE extension also reads the
``.clinerules/*.md`` compatibility surface. A user-owned legacy single-file
``.clinerules`` is preserved byte-identically while native rules are emitted.

This generator also produces:
  * ``.clinerules/workflows/*.md`` — project-local workflow files that
    users invoke with ``/name.md`` in Cline chat. Emitted by default and
    mirrors the same workflow catalogue used by Antigravity and Codex.
  * Conditional rules (YAML ``paths:`` frontmatter) for file-type-scoped
    rules such as testing and language-specific guidance, so Cline only
    loads them when the user is editing matching files. See Cline docs:
    customization/cline-rules#conditional-rules.

Usage:
  python3 scripts/generate_cline_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    LANG_GLOBS,
    LANG_PREFIX,
    PREFIX,
    STANDARD_RULES,
    STANDARD_SCOPE,
    STANDARD_WORKFLOWS,
    build_language_rules,
    build_registered_rules,
    rule_scope,
    rule_testing,
)
from secure_fs import (
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)


# ---------------------------------------------------------------------------
# Conditional-rule helper
# ---------------------------------------------------------------------------

def _conditional(content: str, paths: list[str]) -> str:
    """Prepend a Cline ``paths:`` YAML frontmatter block.

    Cline activates the rule only when the current working files match
    one of the globs. See docs.cline.bot → customization/cline-rules.
    """
    lines = ["---", "paths:"]
    for p in paths:
        lines.append(f'  - "{p}"')
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _conditional_testing_rule() -> str:
    """Scope the testing rule to test files only (reduces context use)."""
    return _conditional(
        rule_testing(),
        ["**/*.test.*", "**/*.spec.*", "**/test_*", "**/tests/**"],
    )


def _wrap_language_rule(raw: str, lang: str) -> str:
    """Scope a language rule to its file extensions via conditional ``paths``."""
    globs = LANG_GLOBS.get(lang)
    if not globs:
        return raw
    return _conditional(raw, globs)


def _trusted_target(target_dir: Path) -> tuple[Path, Path]:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Cline target directory: {target}")
    return target, nearest_existing_root(target)


def _output_root(target: Path, root: Path) -> Path:
    output = lexical_absolute(root)
    try:
        output.relative_to(target)
    except ValueError as error:
        raise RuntimeError(f"Cline rules root escapes target: {output}") from error
    return output


def _preflight_roots(target: Path, roots: list[Path], trusted_root: Path) -> None:
    probes = [
        SecureDestination(
            root / ".ai-toolkit-secure-probe",
            trusted_root,
            f"Cline {root.relative_to(target)} ancestry",
        )
        for root in roots
    ]
    transaction = SecureTransaction(probes)
    transaction.close()


def _managed_paths(root: Path, scopes: set[str]) -> list[Path]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"Unsafe Cline rules directory: {root}")
    return sorted(
        path for path in root.iterdir() if rule_scope(path.name) in scopes
    )


def _render_rules(rules: dict[str, callable]) -> dict[str, bytes]:
    return {
        filename: content_fn().encode("utf-8")
        for filename, content_fn in rules.items()
    }


def _write_transaction(
    target: Path,
    trusted_root: Path,
    outputs: dict[Path, dict[str, bytes]],
    *,
    cleanup: bool,
    managed_scopes: tuple[str, ...],
) -> None:
    active = [
        SecureDestination(root / name, trusted_root, f"Cline {name}")
        for root, files in outputs.items()
        for name in files
    ]
    stale: list[SecureDestination] = []
    if cleanup:
        scopes = set(managed_scopes)
        for root, files in outputs.items():
            for path in _managed_paths(root, scopes):
                if path.name not in files:
                    stale.append(
                        SecureDestination(path, trusted_root, f"Cline stale {path.name}")
                    )

    def apply(transaction: SecureTransaction) -> None:
        for destination in active:
            root_files = outputs[destination.path.parent]
            transaction.atomic_write(
                destination,
                root_files[destination.path.name],
                0o644,
            )
        for destination in stale:
            transaction.unlink(destination)

    run_secure_transaction(active + stale, apply)
    for root, files in outputs.items():
        for name in files:
            print(f"  Generated: {(root / name).relative_to(target)}")


def generate(
    target_dir: Path,
    *,
    language_modules: list[str] | None = None,
    rules_dir: Path | None = None,
    cleanup: bool = True,
    emit_workflows: bool = True,
    managed_scopes: tuple[str, ...] = (STANDARD_SCOPE,),
    output_root: Path | None = None,
) -> None:
    """Write Cline rule files.

    By default writes project-local ``target_dir/.cline/rules/*.md`` and the
    extension-compatible ``target_dir/.clinerules/*.md``. When ``output_root``
    is provided, writes only into that directory so installers can target one
    documented global rules root at a time.
    """
    target, trusted_root = _trusted_target(target_dir)
    legacy_clinerules = target / ".clinerules"
    if legacy_clinerules.is_symlink():
        raise RuntimeError(f"Unsafe symlinked Cline rules root: {legacy_clinerules}")
    preserve_legacy_file = output_root is None and legacy_clinerules.is_file()

    rules: dict[str, callable] = dict(STANDARD_RULES)
    # Replace the testing rule with a conditional variant so it only
    # loads when the user is editing tests.
    rules[f"{PREFIX}testing.md"] = _conditional_testing_rule

    # Language rules — wrap each in conditional frontmatter scoped to
    # the language's file globs so the language-specific guidance only
    # loads for matching files.
    for filename, content_fn in build_language_rules(language_modules).items():
        lang = filename.removeprefix(LANG_PREFIX).removesuffix(".md")
        if lang == "common":
            # "common" spans all languages — apply unconditionally.
            rules[filename] = content_fn
            continue
        rules[filename] = (
            lambda fn, language: lambda: _wrap_language_rule(fn(), language)
        )(content_fn, lang)

    rules.update(build_registered_rules(rules_dir))

    rendered_rules = _render_rules(rules)
    if output_root is None:
        rule_roots = [target / ".cline" / "rules"]
        if not preserve_legacy_file:
            rule_roots.append(target / ".clinerules")
    else:
        rule_roots = [_output_root(target, output_root)]
    outputs = {root: rendered_rules for root in rule_roots}
    if emit_workflows and output_root is None and not preserve_legacy_file:
        outputs[target / ".clinerules" / "workflows"] = _render_rules(
            dict(STANDARD_WORKFLOWS)
        )
    _preflight_roots(target, list(outputs), trusted_root)
    _write_transaction(
        target,
        trusted_root,
        outputs,
        cleanup=cleanup,
        managed_scopes=managed_scopes,
    )


def _managed_roots(
    target: Path,
    output_roots: tuple[Path, ...] | None,
    include_workflows: bool,
) -> list[Path]:
    if output_roots is not None:
        return [_output_root(target, root) for root in output_roots]
    roots = [target / ".cline" / "rules"]
    legacy = target / ".clinerules"
    if legacy.is_symlink():
        raise RuntimeError(f"Unsafe symlinked Cline rules root: {legacy}")
    if not legacy.is_file():
        roots.append(legacy)
        if include_workflows:
            roots.append(legacy / "workflows")
    return roots


def managed_files(
    target_dir: Path,
    *,
    output_roots: tuple[Path, ...] | None = None,
    include_workflows: bool = True,
) -> list[Path]:
    """List Cline rule artifacts owned by ai-toolkit."""
    target, trusted_root = _trusted_target(target_dir)
    roots = _managed_roots(target, output_roots, include_workflows)
    _preflight_roots(target, roots, trusted_root)
    paths = [
        path
        for root in roots
        for path in _managed_paths(root, {STANDARD_SCOPE, "lang", "custom"})
    ]
    destinations = [
        SecureDestination(path, trusted_root, f"Cline managed {path.name}")
        for path in paths
    ]
    if not destinations:
        return []
    transaction = SecureTransaction(destinations)
    try:
        return [
            destination.path
            for destination in destinations
            if transaction.initial_content(destination) is not None
        ]
    finally:
        transaction.close()


def cleanup(
    target_dir: Path,
    *,
    output_roots: tuple[Path, ...] | None = None,
    include_workflows: bool = True,
) -> int:
    """Remove only ai-toolkit-managed Cline rule and workflow files."""
    files = managed_files(
        target_dir,
        output_roots=output_roots,
        include_workflows=include_workflows,
    )
    if not files:
        return 0
    _, trusted_root = _trusted_target(target_dir)
    destinations = [
        SecureDestination(path, trusted_root, f"Cline managed {path.name}")
        for path in files
    ]

    def apply(transaction: SecureTransaction) -> None:
        for destination in destinations:
            transaction.unlink(destination)

    run_secure_transaction(destinations, apply)
    return len(files)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
