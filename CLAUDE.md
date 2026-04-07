# ai-toolkit

## Overview
Shared AI development toolkit for Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, and Augment — 90 skills, 44 agents, expanded lifecycle hooks, persona presets, experimental opt-in plugin packs, and safety constitution, distributed as a global npm package.

## CRITICAL: Documentation & Count Accuracy
**Every change to skills, agents, hooks, or editors MUST be reflected in ALL docs:**
README.md, CLAUDE.md, ARCHITECTURE.md, package.json, plugin.json, skills-catalog.md, architecture-overview.md, llms.txt, AGENTS.md.
Run `python3 scripts/validate.py --strict` + `python3 scripts/audit_skills.py --ci` before every commit.
Stale counts = broken user trust. This is non-negotiable.

## Tech Stack
- **Language**: Python (scripts, stdlib-only), Bash (hooks only), Node.js (CLI wrapper + visual-server.cjs)
- **Framework**: Claude Code Agent Skills standard
- **Database**: —

## Commands
```bash
# Test:   npm test  (bats tests/)
# Validate: python3 scripts/validate.py
# Evaluate: python3 scripts/evaluate_skills.py
# Audit:    python3 scripts/audit_skills.py --ci  (security scan, exit 1 on HIGH)
# Benchmark: python3 scripts/benchmark_ecosystem.py --offline
# Harvest: python3 scripts/harvest_ecosystem.py --offline
# Generate: python3 scripts/generate_agents_md.py > AGENTS.md
# Generate: python3 scripts/generate_llms_txt.py > llms.txt
# Install:  ai-toolkit install            (global → ~/.claude/settings.json hooks + ~/.ai-toolkit/hooks/ scripts)
# Install:  ai-toolkit install --profile minimal|standard|strict
# Init:     ai-toolkit install --local    (project-local CLAUDE.md + settings + constitution + copilot + cline + roo + aider + git hooks)
# Doctor:   ai-toolkit doctor --fix       (auto-repair broken symlinks, hooks, artifacts)
# Eject:    ai-toolkit eject              (standalone copy, no toolkit dependency)
# Deps:    python3 scripts/check_deps.py  (check system dependencies, OS-specific install hints)
```

## Skill Tiers (When to Use What)

- **Tier 1 — Quick single-agent** (`/debug`, `/review`, `/refactor`, `/analyze`, `/docs`, `/plan`, `/tdd`, `/grill-me`, `/triage-issue`): one concern, one file area, fast
- **Tier 1.5 — Product planning pipeline** (`/write-a-prd` → `/prd-to-plan` → `/prd-to-issues`): interview-driven PRD → vertical-slice plan → GitHub issues
- **Tier 1.5 — Design & architecture** (`/design-an-interface`, `/architecture-audit`, `/refactor-plan`, `/ubiquitous-language`, `/qa-session`): parallel sub-agent exploration
- **Tier 2 — Multi-agent workflow** (`/workflow <type>`): cross-cutting task with a known pattern — spawns specialized agents per phase
- **Tier 3 — Custom parallelism** (`/orchestrate`, `/swarm`): no predefined workflow matches, you define the domains

`/workflow` types: `feature-development`, `backend-feature`, `frontend-feature`, `api-design`, `database-evolution`, `test-coverage`, `security-audit`, `codebase-onboarding`, `spike`, `debugging`, `incident-response`, `performance-optimization`, `infrastructure-change`, `application-deploy`, `proactive-troubleshooting`

## Key Conventions
- All scripts live in `scripts/` (Python) and `app/hooks/` (Bash) — never at repo root
- `install` / `update` = global (`~/.claude/`); add `--local` for project-local setup
- `inject_rule_cli.py` always writes to `$TARGET_DIR/.claude/CLAUDE.md`
- Skill names: lowercase-hyphen, max 64 chars, unique across `app/skills/`
- Task skills: `disable-model-invocation: true` | Knowledge skills: `user-invocable: false` | Explicit hybrid skills: `user-invocable: true` (used by `instinct-review` and `teams` — explicit user-invocable slash commands with LLM response)
- All scripts (skills + CLI) are Python stdlib only, JSON to stdout, zero external deps
- Hooks remain in Bash for startup speed
- After any agent/skill change: run `python3 scripts/validate.py` before commit
- After adding agents: regenerate `AGENTS.md` and `llms.txt`
- Version bump required before every `git tag` + publish
- `agent:` — names the specialized agent to delegate to
- `context: fork` — runs skill in isolated forked context

## MCP Servers
<!-- Configure per-machine in ~/.claude/settings.local.json, not here -->
