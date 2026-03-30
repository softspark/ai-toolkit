---
name: fix
description: "Auto-fix lint errors, type issues, and simple bugs"
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
