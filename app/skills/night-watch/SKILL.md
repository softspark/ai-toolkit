---
name: night-watch
description: "Run autonomous maintenance tasks (dependency updates, dead code removal, small refactors) in an isolated branch. Use only when the user triggers it explicitly — typically off-hours; never auto-invoked."
effort: medium
disable-model-invocation: true
context: fork
agent: night-watchman
allowed-tools: Bash, Read, Edit, Grep
---

# Night Watch Command

Triggers the autonomous maintenance agent.

## Usage

```bash
/night-watch [scope]
# Example: /night-watch deps
# Example: /night-watch cleanup
# Default: runs full suite
```

## Protocol
1. **Checkout**: Create `maintenance/` branch.
2. **Execute**: Run `night-watchman` agent skills.
3. **Verify**: Run full test suite.
4. **Report**: Generate Shift Report.

## Rules

- **MUST** work on a dedicated `maintenance/` branch — never commit to `main` or the user's active branch
- **NEVER** push without the full test suite passing
- **CRITICAL**: stop on the first failing test and surface it — do not try to "fix" tests opportunistically
- **MANDATORY**: every change lands in a discrete commit with a conventional message

## Gotchas

- `npm audit fix` bumps to the latest **major** version when `--force` is set — quietly introducing breaking changes. Always use plain `npm audit fix` first and only escalate to `--force` after the user approves each named package.
- `pip install --upgrade` without a constraints file resolves differently each run due to transitive dependencies. Pin via `pip-compile` and commit the lockfile, otherwise maintenance runs produce "mysterious" unrelated changes.
- `git add -A` on a maintenance run can pull in build artifacts and IDE caches if `.gitignore` is incomplete. Prefer explicit `git add <path>` per change category (deps, docs, lint-fixes) to keep commits attributable.
- Pre-commit hooks that format on commit may re-modify files AFTER your edit — the resulting commit may differ from the planned diff. Run the formatter as a separate step and verify `git diff --staged` before committing.

## When NOT to Use

- For planned refactors with a known scope — use `/refactor-plan`
- For immediate bug fixes — use `/fix` or `/debug`
- In a repo the user is actively working in — wait for idle time
- When there are uncommitted changes on the current branch — abort until clean
