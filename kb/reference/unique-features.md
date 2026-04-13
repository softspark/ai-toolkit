---
title: "Unique Features & Differentiators"
category: reference
service: ai-toolkit
tags: [features, differentiators, constitution, hooks, security, tdd, memory]
created: "2026-04-13"
last_updated: "2026-04-13"
description: "Detailed description of ai-toolkit's unique features: constitution enforcement, hooks system, security scanning, effort budgeting, quality gates, and more."
---

# Unique Features & Differentiators

## 1. Machine-Enforced Constitution

Unlike other toolkits that put safety rules in documentation only, ai-toolkit enforces a 5-article constitution via `PreToolUse` hooks. The hook actually **blocks** execution of:
- Mass deletion (`rm -rf`, `DROP TABLE`)
- Blind overwrites of uncommitted work
- Any action that could cause irreversible data loss

## 2. Hooks as Executable Scripts

Hook logic lives in `app/hooks/*.sh` — not inline JSON one-liners. Scripts are copied to `~/.softspark/ai-toolkit/hooks/` on install and referenced from `~/.claude/settings.json`. Easy to read, debug, and extend.

**12 lifecycle events / 21 global hook entries:**

| Event | Script | Action |
|-------|--------|--------|
| SessionStart | `session-start.sh` | MANDATORY rules reminder + session context + instincts |
| SessionStart | `mcp-health.sh` | Check MCP server command availability (non-blocking warning) |
| SessionStart | `session-context.sh` | Capture environment snapshot to `~/.softspark/ai-toolkit/sessions/current-context.json` |
| Notification | `notify-waiting.sh` | Cross-platform desktop notification |
| PreToolUse | `guard-destructive.sh` | Block `rm -rf`, `DROP TABLE`, etc. |
| PreToolUse | `guard-path.sh` | Block wrong-user path hallucination |
| PreToolUse | `guard-config.sh` | Block edits to linter/formatter config files unless explicitly requested |
| PreToolUse | `commit-quality.sh` | Advisory validation of git commit messages |
| UserPromptSubmit | `user-prompt-submit.sh` | Prompt governance reminder |
| UserPromptSubmit | `track-usage.sh` | Record skill invocations to local stats |
| PostToolUse | `post-tool-use.sh` | Lightweight validation reminders after edits |
| PostToolUse | `governance-capture.sh` | Log security-sensitive operations to JSONL |
| Stop | `quality-check.sh` | Multi-language lint (ruff/tsc/phpstan/dart/go) |
| Stop | `save-session.sh` | Persist session context for cross-session continuity |
| TaskCompleted | `quality-gate.sh` | Block task completion on lint/type errors |
| SubagentStart | `subagent-start.sh` | Narrow-scope reminder for spawned subagents |
| SubagentStop | `subagent-stop.sh` | Completion checklist for subagent handoff |
| PreCompact | `pre-compact.sh` | Smart compaction: prioritized context |
| PreCompact | `pre-compact-save.sh` | Save timestamped context backup |
| SessionEnd | `session-end.sh` | Persist a session-end handoff note |
| TeammateIdle | *(inline)* | Completeness reminder |

**5 skill-scoped hooks:**

| Skill | Hook | Action |
|-------|------|--------|
| `/commit` | Pre | Run linter, block on failure |
| `/test` | Post | Coverage check, report threshold |
| `/deploy` | Post | Health check, rollback if degraded |
| `/migrate` | Pre | Backup verification |
| `/rollback` | Post | State verification |

## 3. Security Scanning

Two complementary security tools:

**`/skill-audit`** — scan skills and agents for code-level risks:

```bash
/skill-audit                              # Interactive (Claude remediation)
python3 scripts/audit_skills.py --ci      # CI mode: exit 1 on HIGH
```

Detects: `eval()`/`exec()`, hardcoded secrets, permission issues, bash risks.

**`/cve-scan`** — scan project dependencies for known CVEs:

```bash
/cve-scan                                 # Auto-detect ecosystems, scan all
python3 app/skills/cve-scan/scripts/cve_scan.py          # Direct invocation
python3 app/skills/cve-scan/scripts/cve_scan.py --json   # Machine-readable
```

Supports: npm, pip, composer, cargo, go, ruby, dart. Uses native audit tools — zero external deps.

**Severity levels:** HIGH (blocks CI), WARN (should fix), INFO (review)

## 4. Effort-Based Model Budgeting

Every skill declares an effort level used for model token budgeting:
- `low` — lint, build, fix (fast, cheap)
- `medium` — debug, analyze, ci
- `high` — review, plan, refactor, docs
- `max` — orchestrate, swarm, workflow

## 5. Multi-Language Quality Gates

The `Stop` hook runs after every response across 5 languages:

| Language | Lint | Type Check |
|----------|------|-----------|
| Python | ruff | mypy --strict |
| TypeScript | ESLint/tsc | tsc --noEmit |
| PHP | phpstan | phpstan |
| Dart | dart analyze | dart analyze |
| Go | go vet | go vet |

## 6. Iron Law Enforcement

Three skills enforce non-negotiable quality gates with anti-rationalization tables:

| Skill | Iron Law | What it prevents |
|-------|----------|-----------------|
| `/tdd` | `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST` | Code written before test? Delete it. Start over. |
| `debugging-tactics` | `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST` | 4-phase debugging: root cause → pattern → hypothesis → fix. |
| `verification-before-completion` | `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE` | Gate: IDENTIFY → RUN → READ → VERIFY → CLAIM. |

Additionally, **15 core skills** include `## Common Rationalizations` tables — domain-specific excuses with rebuttals that prevent agent drift.

## 7. Confidence Scoring & Self-Evaluation (`/review`)

The `/review` skill outputs findings with per-issue confidence scores (1-10) and severity classification (critical/major/minor/nit). After completing a review, an LLM-as-Judge self-evaluation pass checks for blind spots: anchoring bias, assumption vs verification, missing unhappy paths, and calibrates confidence scores.

## 8. Agent Verification Checklists

10 key agents include `## Verification Checklist` — exit criteria that MUST be met before presenting results:

| Agent | Key exit criteria |
|-------|------------------|
| `code-reviewer` | Every finding has file:line + evidence, not just opinion |
| `security-auditor` | Each finding includes proof-of-concept or exploit path |
| `test-engineer` | No empty/placeholder tests, mocks only at boundaries |
| `debugger` | Root cause identified, regression test added |
| `backend-specialist` | Input validation, error format, query optimization |
| `frontend-specialist` | Empty/loading/error states, accessibility, responsive |
| `database-architect` | Migration tested on prod-like volume, rollback tested |
| `performance-optimizer` | Baseline measured, profiler evidence attached |
| `devops-implementer` | Dry run passed, rollback documented, no hardcoded secrets |
| `documenter` | Code examples runnable, no placeholders, valid links |

## 9. Skill Reference Routing

7 core skills include `## Related Skills` sections that suggest logical follow-up skills:

```
/review → found issues? → /debug, /tdd, /cve-scan, /analyze
/debug  → bug fixed?   → /review, /tdd, /workflow incident-response
/plan   → approved?    → /orchestrate, /write-a-prd, /grill-me
```

## 10. Two-Stage Review (`/subagent-development`)

Per-task review pipeline inspired by [obra/superpowers](https://github.com/obra/superpowers):

```
Implementer → Spec Compliance Review → Code Quality Review → Next Task
```

- Implementer reports: `DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`
- Spec reviewer: all requirements met, nothing extra, nothing missing
- Quality reviewer: SOLID, naming, error handling, tests, security

## 11. Ralph Wiggum Loop (`/repeat`)

Autonomous agent loop with safety controls:

```bash
/repeat 5m /test          # run tests every 5 min until all pass
/repeat --iterations 3 /review   # max 3 review passes
```

| Safety Control | Default |
|----------------|---------|
| Max iterations | 5 |
| Circuit breaker | 3 consecutive failures → halt |
| Min interval | 1 minute |
| Exit detection | DONE / COMPLETE / ALL PASS |

## 12. Persistent Memory (`memory-pack` plugin)

SQLite-based session memory (opt-in plugin pack):

| Component | Purpose |
|-----------|---------|
| `observation-capture.sh` | PostToolUse hook — captures tool actions to SQLite |
| `session-summary.sh` | Stop hook — AI-compress session observations |
| `mem-search` skill | FTS5 full-text search across past sessions |
| `<private>` tags | Content between tags stripped before storage |
| Progressive disclosure | Summary (~500 tok) → relevant (~2k tok) → full |

## 13. Persona Presets

4 engineering personas that adjust Claude's communication style per role:

| Persona | Focus | Key Skills |
|---------|-------|------------|
| `backend-lead` | System design, scalability, data integrity | `/workflow backend-feature`, `/tdd` |
| `frontend-lead` | Component architecture, a11y, Core Web Vitals | `/design-an-interface`, `/review` |
| `devops-eng` | IaC, CI/CD, blast radius, rollback safety | `/workflow infrastructure-change`, `/deploy` |
| `junior-dev` | Step-by-step explanations, learning focus | `/explain`, `/explore`, `/debug` |

Persistent via `--persona` at install time, or session-scoped via `/persona` runtime command.

## 14. Visual Brainstorming Companion

Optional browser-based companion for `/write-a-prd` and `/design-an-interface`:
- Ephemeral Node.js HTTP server (auto-kills after 30min idle)
- Dark theme, responsive, zero external dependencies
- Per-question routing: mockups/diagrams → browser, text/conceptual → terminal

## 15. KB Integration Protocol

Agents follow a research-before-action protocol enforced via rules:
1. `smart_query()` or `hybrid_search_kb()` before any technical answer
2. Source citation mandatory (`[PATH: kb/...]`)
3. Strict order: KB → Files → External Docs → General Knowledge
