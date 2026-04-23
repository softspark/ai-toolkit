---
name: fix
description: "Apply a targeted fix to a known bug or lint error and verify it with the same command that surfaced the problem. Use when the root cause is already identified — not for unknown symptoms or open-ended debugging."
effort: low
disable-model-invocation: true
argument-hint: "[test or lint target]"
allowed-tools: Bash, Read, Edit, Grep
---

# Fix Command

$ARGUMENTS

Attempts to fix code errors autonomously.

## Usage

```bash
/fix <file_or_scope>
# Example: /fix src/utils.ts
```

## Automated Error Classification

Before entering the fix loop, classify errors to prioritize auto-fixable ones:

```bash
# Pipe lint or test output
ruff check . 2>&1 | python3 "$(dirname "$0")/scripts/error-classifier.py"
mypy src/ 2>&1 | python3 scripts/error-classifier.py
npx eslint . 2>&1 | python3 scripts/error-classifier.py
```

The script outputs JSON with:
- **total_errors**: count of all parsed errors
- **auto_fixable_count**: errors that tools can fix automatically (e.g., F401 unused imports, formatting)
- **manual_count**: errors requiring human/agent intervention
- **tools_detected**: which linters produced the output (ruff, mypy, eslint, tsc, phpstan)
- **errors[]**: each error with file, line, code, message, and auto_fixable flag
- **suggested_order**: files to fix, auto-fixable first
- **fix_strategy**: recommended approach (auto-fix first, then manual)

Use this to run auto-fixers (e.g., `ruff check --fix .`) before spending time on manual fixes.

---

## Protocol (The "Fix Loop")

1. **Analyze**: Run validation to get the exact error message.
   ```bash
   # Get error
   npm test src/utils.ts 2>&1 | tee error.log
   ```

2. **Diagnose**: Analyze `error.log`.
   - Use `debugging-tactics` skill.
   - Trace the error to the source line.

3. **Patch**: Apply a fix.
   - Use `sed` or `write_file`.

4. **Verify**: Run validation again.
   - If PASS: Stop.
   - If FAIL: Repeat (Max 3 retries).

## Safety Limits
- **Max Retries**: 3
- **Scope**: Only modify the specified files.
- **Stop Condition**: If new errors appear that are totally different, STOP and ask user.

## Example Flow
```
User: /fix app.py
Agent: Running tests... FAIL (NameError)
Agent: Fixing app.py (Import missing module)
Agent: Running tests... PASS
Agent: Fixed NameError in app.py
```

## Rules

- **MUST** know the exact symptom (error message, failing test, lint code) before editing — guessing is not fixing
- **MUST** verify the fix by rerunning **the same command** that exposed the problem, not a different validator
- **NEVER** modify tests to make them pass — fixing the test is not fixing the bug
- **NEVER** touch files outside the declared scope — scope creep hides regressions
- **CRITICAL**: hard-stop after 3 iterations. If the fix loop has not converged, the problem is deeper than `/fix` handles — escalate to `/debug`.
- **MANDATORY**: if new, unrelated errors appear during a fix attempt, stop and ask the user — do not chase them

## Gotchas

- `ruff check --fix` reorders imports and rewrites them. On files with circular imports or conditional-imports-under-TYPE_CHECKING, the "fix" can break things silently. Run `--check` first, inspect the diff, then apply.
- `eslint --fix --cache` skips already-cached files even if their content changed (cache invalidation by mtime). On first-run misses, clear the cache with `--no-cache` to force a complete pass.
- `mypy --install-types` auto-installs stub packages, adding dependencies to the environment the user did not request. Reserve it for explicit opt-in; in CI, pass `--non-interactive` to prevent surprise installs.
- `npm test -- path/to/test` in a workspace repo runs the **root** workspace's test runner, not the leaf package's. Use `npm test --workspace=<name>` or the per-package `cd packages/foo && npm test` form.
- Fix loops occasionally produce **cycle diffs** — iteration 1 fixes A which triggers B, iteration 2 fixes B which re-breaks A. After every iteration compare the diff to the previous; identical or inverse diffs mean a cycle — stop.

## When NOT to Use

- When the root cause is unknown — use `/debug` first, then `/fix` with a clear target
- For systemic refactoring across modules — use `/refactor` or `/refactor-plan`
- For writing new features test-first — use `/tdd`
- For CI failures spanning many files — use `/workflow debugging` (coordinated)
- When the failing validation is itself broken — repair the validator separately, do not patch code to satisfy it
