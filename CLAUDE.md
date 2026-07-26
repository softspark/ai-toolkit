# ai-toolkit

## Overview
Shared AI development toolkit for Claude Code, Claude Chat/Cowork, Cursor, Devin, Copilot, Gemini, Cline, Roo/Zoo Code, Aider, Augment, Google Antigravity, and Codex CLI — skills, agents, lifecycle hooks, persona presets, plugin packaging, and safety constitution, distributed as a global npm package.

## Claude Code Runtime Rules
- Claude Code reads `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md`, skills, agents, settings, and hooks. It does **not** treat `AGENTS.md` as an instruction source.
- Claude Chat/Desktop/Cowork does **not** scan Claude Code's `~/.claude/` files. Use `ai-toolkit claude-app export`, upload the ZIP in Customize > Plugins, and apply the generated Cowork global instructions. Skills work in Chat/Cowork; hooks and sub-agents are Cowork-only.
- `AGENTS.md` is generated for Codex/OpenCode/Gemini compatibility. Do not move mandatory Claude behavior there.
- **KB-first is mandatory for technical work:** before answering or acting on a technical/project prompt, call `smart_query()` or `hybrid_search_kb()` and use the result to locate the relevant SOP/reference. Cite the KB path when the result materially informs the answer. If the KB tool is unavailable, state that explicitly and continue from local files.
- Any rule that must be enforced at a fixed lifecycle point belongs in `app/hooks.json` + `app/hooks/*.sh` with tests. `CLAUDE.md` guidance is context, not enforcement.

## CRITICAL: Documentation & Count Accuracy
**Every change to skills, agents, hooks, or editors MUST be reflected in ALL docs:**
README.md, CLAUDE.md, ARCHITECTURE.md, package.json, plugin.json, skills-catalog.md, architecture-overview.md, llms.txt, AGENTS.md.
Run `python3 scripts/validate.py --strict` + `python3 scripts/audit_skills.py --ci` before every commit.
When you touch any `app/hooks/*.sh`, ALSO run `shellcheck --severity=warning app/hooks/*.sh` — it runs in `ci.yml` but NOT in `validate.py`, `npm test`, or `publish.yml`, so a hook lint failure can publish on tag while turning `main` CI red (v4.5.1 postmortem).
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
# Shellcheck: shellcheck --severity=warning app/hooks/*.sh  (hook lint; required before tagging, not run by publish.yml)
# Benchmark: python3 scripts/benchmark_ecosystem.py --offline
# Harvest: python3 scripts/harvest_ecosystem.py --offline
# Generate: python3 scripts/generate_agents_md.py > AGENTS.md
# Generate: python3 scripts/generate_llms_txt.py > llms.txt
# Generate: python3 scripts/generate_language_rules_skills.py  (build app/skills/<lang>-rules/ from app/rules/<lang>/)
# Install:  ai-toolkit install            (global → ~/.claude/settings.json hooks + ~/.softspark/ai-toolkit/hooks/ scripts)
# Install:  ai-toolkit install --profile minimal|standard|strict
# Init:     ai-toolkit install --local    (project-local Claude Code configs only)
# Init:     ai-toolkit install --local --editors all  (+ all editors: cursor, windsurf, cline, roo, aider, augment, copilot, antigravity, codex)
# Init:     ai-toolkit install --local --editors cursor,aider  (+ specific editors)
# Doctor:   ai-toolkit doctor --fix       (auto-repair broken symlinks, hooks, artifacts)
# Claude app: ai-toolkit claude-app export --verify  (uploadable Chat/Cowork plugin + global instructions)
# Eject:    ai-toolkit eject              (standalone copy, no toolkit dependency)
# Compile:  ai-toolkit compile-slm       (compile toolkit for SLMs: --budget, --model-size, --persona, --dry-run)
# Config:   ai-toolkit config validate|diff|init|create-base|check  (config inheritance)
# Projects: ai-toolkit projects           (list/prune/remove registered local projects)
# Codex:   ai-toolkit codex-md            (generate AGENTS.md with marker injection for Codex CLI)
# Codex:   ai-toolkit codex-rules         (generate .agents/rules/*.md for Codex CLI)
# Codex:   ai-toolkit codex-hooks         (generate .codex/hooks.json for Codex CLI)
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
- `inject_hook_cli.py` injects hooks into `$TARGET_DIR/.claude/settings.json` — supports local files and HTTPS URLs
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
