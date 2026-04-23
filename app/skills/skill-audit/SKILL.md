---
name: skill-audit
description: "Scan skills and agents for security risks: dangerous patterns, secrets, excessive permissions"
effort: medium
disable-model-invocation: true
argument-hint: "[skill-name | --all | --fix]"
allowed-tools: Read, Grep, Glob, Bash
---

# /skill-audit - Skill Security Scanner

$ARGUMENTS

Scan skill and agent definitions for security risks before installation or after changes.

## Usage

```
/skill-audit                  # Audit all skills
/skill-audit debug            # Audit specific skill
/skill-audit --all --fix      # Audit all + auto-fix safe issues
```

## What This Command Does

1. **Scan SKILL.md frontmatter** for permission issues
2. **Scan scripts/** for dangerous code patterns
3. **Scan reference/** for hardcoded secrets
4. **Report** findings with severity levels
5. **Auto-fix** safe issues when `--fix` is passed

## Security Checks

### Frontmatter Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Overly permissive tools | WARN | `allowed-tools` includes Bash + Write + Edit without justification |
| Missing allowed-tools | WARN | No tool restriction = full access |
| Knowledge skill with Bash | HIGH | `user-invocable: false` skills should not need Bash |
| Missing effort field | INFO | Best practice to declare effort |

### Script Checks (Python)

| Pattern | Severity | Description |
|---------|----------|-------------|
| `eval(` / `exec(` | HIGH | Arbitrary code execution |
| `os.system(` | HIGH | Shell injection risk |
| `subprocess.*shell=True` | HIGH | Shell injection risk |
| `__import__` | WARN | Dynamic imports |
| `pickle.loads` | HIGH | Deserialization attack |
| `open(.*'w')` without path validation | WARN | Arbitrary file write |

### Script Checks (Bash)

| Pattern | Severity | Description |
|---------|----------|-------------|
| `curl.*\| bash` | HIGH | Remote code execution |
| `curl.*\| sh` | HIGH | Remote code execution |
| `wget.*\| bash` | HIGH | Remote code execution |
| `rm -rf /` or `rm -rf ~` | HIGH | Destructive command |
| Unquoted `$variables` in commands | WARN | Word splitting / injection |
| `chmod 777` | WARN | Overly permissive |

### Secret Detection

| Pattern | Severity | Description |
|---------|----------|-------------|
| `AKIA[0-9A-Z]{16}` | HIGH | AWS access key |
| `sk-[a-zA-Z0-9]{20,}` | HIGH | API key pattern |
| `password\s*=\s*['"][^'"]+` | WARN | Hardcoded password |
| `token\s*=\s*['"][^'"]+` | WARN | Hardcoded token |
| `-----BEGIN.*PRIVATE KEY` | HIGH | Private key |
| `ghp_[a-zA-Z0-9]{36}` | HIGH | GitHub PAT |

## Output Format

```markdown
## Skill Audit Report

### Summary
- Skills scanned: N
- HIGH: N | WARN: N | INFO: N

### Findings

#### [HIGH] skill-name/scripts/helper.py:12
Pattern: `eval(user_input)`
Risk: Arbitrary code execution
Fix: Replace with `ast.literal_eval()` or explicit parsing

#### [WARN] skill-name/SKILL.md (frontmatter)
Pattern: Missing `allowed-tools`
Risk: Skill has unrestricted tool access
Fix: Add `allowed-tools: Read, Grep, Glob` (principle of least privilege)
```

## Steps

1. Determine scope: single skill (`$ARGUMENTS`) or all skills
2. For each skill directory in `app/skills/`:
   a. Read `SKILL.md` — check frontmatter fields
   b. Glob `scripts/**/*.py` — scan for dangerous Python patterns
   c. Glob `scripts/**/*.sh` — scan for dangerous Bash patterns
   d. Grep all files for secret patterns
3. Also scan `app/agents/*.md` for overly broad tool lists
4. Collect findings, sort by severity (HIGH > WARN > INFO)
5. If `--fix` is passed:
   - Add missing `allowed-tools` to SKILL.md frontmatter (suggest minimal set)
   - Replace `eval(` with `ast.literal_eval(` where safe
   - Do NOT auto-fix HIGH severity — only report
6. Print audit report

## Deterministic Scanner

For CI pipelines or non-interactive use, run the Python scanner directly:

```bash
# Human-readable output
python3 scripts/audit_skills.py

# JSON output (for CI parsing)
python3 scripts/audit_skills.py --json

# CI mode: exit 1 on any HIGH finding
python3 scripts/audit_skills.py --ci
```

The `/skill-audit` slash command wraps this scanner with Claude's analysis for remediation suggestions.

## Rules

- **MUST** remain read-only by default — file modifications require the explicit `--fix` flag
- **MUST** exit with non-zero status on any HIGH finding so CI pipelines can gate merges
- **NEVER** auto-fix HIGH-severity findings — only the human owner decides on dangerous code
- **NEVER** silence findings by adding exceptions in the audit config; either fix the code or document why the pattern is safe in the skill body
- **CRITICAL**: scan both `app/skills/` and `app/agents/` — agents without tool restrictions are the same risk class as skills with broad `allowed-tools`
- **MANDATORY**: every finding names a specific fix (replace `eval()` with `ast.literal_eval()`, add missing `allowed-tools`). A finding without a fix is triage noise.

## Gotchas

- Regex-based secret detection catches canonical patterns (`sk-...`, `ghp_...`) but misses custom API key formats used by internal services. Augment the regex list with project-specific patterns before trusting "0 HIGH findings".
- `--fix` on `allowed-tools` infers minimal tool sets from imports, but skills that shell out via Bash may need tools not visible in the static scan. Review auto-added restrictions before merging.
- Knowledge skills (`user-invocable: false`) with Bash access are HIGH because they auto-load and can act without user triggering. Legitimate exceptions (e.g., `research-mastery` calling `smart_query()`) should be explicitly whitelisted in the audit config with a comment.
- The scanner flags `eval(` even inside docstrings and commented-out code. Context-aware scanning is hard; the alternative is reviewing each HIGH flag manually — the scan errs on the side of false positives.
- CI integration with `--ci` exits 1 on any HIGH, which **blocks the commit**. A sudden pattern match (e.g., a legitimate new use of `subprocess.run`) can block unrelated PRs. Keep a fast path for pre-approving new patterns.

## When NOT to Use

- For general code-quality metrics (complexity, coverage, duplication) — use `/analyze`
- For dependency CVE scans — use `/cve-scan`
- For HIPAA-specific audits — use `/hipaa-validate`
- For live pentesting of a deployed app — delegate to the `security-auditor` agent
- When the project has its own security scanner (semgrep, snyk) — prefer it; `/skill-audit` is toolkit-specific
