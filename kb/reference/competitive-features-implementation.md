---
title: "Plan: Competitive Features Implementation — Learning System, Language Rules, Hook Matrix, MCP Templates"
category: reference
service: ai-toolkit
tags:
  - competitive-analysis
  - continuous-learning
  - language-rules
  - hook-matrix
  - mcp-templates
  - install-profiles
  - completed
doc_type: plan
status: completed
created: "2026-04-07"
last_updated: "2026-04-09"
completion: "100%"
description: "Implementation plan for features identified from competitive analysis of everything-claude-code and claude-mem. Focus on learning system, language rules, advanced hooks, MCP templates, and rag-mcp integration. COMPLETED: 8/9 features shipped (1 skipped). See kb/reference/ for permanent documentation."
---

# Plan: Competitive Features — ai-toolkit

**Status:** :white_check_mark: COMPLETED
**Completion:** 100% (8/9 features, 1 skipped)
**Started:** 2026-04-07
**Estimated Completion:** 2026-06-15
**Source:** Competitive analysis of `affaan-m/everything-claude-code` (ECC) + `thedotmack/claude-mem`

---

## 1. Objective

Strengthen ai-toolkit's competitive position by implementing 10 features from competitive analysis while maintaining our advantages (clean architecture, 11 editors, personas, safety constitution).

**Key design principle:** ai-toolkit is a **generic toolkit** — it does NOT know about rag-mcp or any specific consumer. Consumers (like rag-mcp) use ai-toolkit's public API (`inject-rule`, `inject-hook`, `merge-hooks`) to add their own rules and hooks.

**State before plan:** 88 skills, 47 agents, 14 hooks, 9 editor integrations
**State after plan:** See manifest.json and README.md for current counts. Target: skills, agents, hooks, language rules, MCP templates, extension API

---

## 2. Progress Tracking

| # | Feature | Priority | Status | Est. Time | Actual | Notes |
|---|---------|----------|--------|-----------|--------|-------|
| 1.1 | Language-Specific Rules (13 langs) | P0 | :white_check_mark: | 5-7d | 1d | 70 files (13 langs × 5 + 5 common) |
| 1.2 | Advanced Hook Matrix | P0 | :white_check_mark: | 5-7d | 1d | 6 new hooks + hooks.json |
| 1.3 | MCP Server Templates (25) | P0 | :white_check_mark: | 2-3d | 1d | 25 templates + mcp_manager.py + CLI |
| 2.1 | `inject-hook` CLI command | P1 | :white_check_mark: | 3-5d | 1d | inject_hook_cli.py + 17 tests + CLI |
| 2.2 | Manifest-Driven Install | P1 | :white_check_mark: | 7-10d | 1d | modules, state tracking, auto-detect |
| 3.1 | Council Skill | P2 | :white_check_mark: | 3-5d | 1d | /council (4-perspective orchestrator) |
| 3.2 | Brand Voice Skill | P2 | :white_check_mark: | 2-3d | 1d | knowledge skill + anti-trope list |
| 3.3 | Agent Introspection Skill | P2 | :white_check_mark: | 3-5d | 1d | /introspect (7 failure patterns) |
| 4.1 | Documentation Site (Starlight/Astro) | P3 | :no_entry: SKIPPED | — | — | Unnecessary — README/CLAUDE.md sufficient |

---

## 3. Dependency Graph

```
ALL FEATURES ARE INDEPENDENT — no external dependencies

MCP Templates (1.3) ← quick win, start here
Language Rules (1.1) ← independent
Hook Matrix (1.2) ← independent
inject-hook CLI (2.1) ← independent (extends existing inject-rule pattern)
Manifest Install (2.2) ← independent but complex
Council Skill (3.1) ← independent
Brand Voice (3.2) ← independent
Agent Introspection (3.3) ← independent
Documentation Site (4.1) ← independent
```

---

## 4. Detailed Implementation

### Faza 1: Quick Wins + Foundation (tydzień 1-2)

#### 1.1 Language-Specific Rules System

**Source:** ECC — 13 language dirs × 5 files each = 65 rule files
**What we create:** Skill-based language rules that inject into CLAUDE.md via `--local`

**Current state:** We have `app/skills/` with some language patterns (typescript-patterns, ruby-patterns, etc.)
**Gap:** No systematic coding-style + testing + security + hooks + patterns per language

**Files to create:**

```
app/rules/
├── common/
│   ├── coding-style.md          # KISS, DRY, YAGNI, immutability
│   ├── testing.md               # Testing standards
│   ├── git-workflow.md          # Commit conventions
│   ├── performance.md           # Performance guidelines
│   └── security.md              # OWASP, input validation
├── typescript/
│   ├── coding-style.md          # TS-specific (strict mode, no any, etc.)
│   ├── testing.md               # Jest/Vitest patterns
│   ├── patterns.md              # TS patterns (discriminated unions, etc.)
│   ├── hooks.md                 # React hooks, lifecycle
│   └── security.md              # XSS, sanitization
├── python/
│   ├── coding-style.md          # PEP 8, type hints, dataclasses
│   ├── testing.md               # pytest, fixtures, parametrize
│   ├── patterns.md              # Python patterns
│   ├── hooks.md                 # Django/FastAPI lifecycle
│   └── security.md              # SQL injection, SSTI
├── golang/                      # Same 5-file structure
├── rust/
├── java/
├── kotlin/
├── swift/
├── dart/
├── csharp/
├── php/
├── cpp/
└── ruby/
```

**Total: 13 languages × 5 files + 5 common = 70 files**

**Integration with install:**
```bash
# During ai-toolkit install --local
# Detect project language from package.json, Cargo.toml, go.mod, etc.
# Inject relevant language rules into CLAUDE.md
```

**Files to modify:**

| File | Action | Description |
|------|--------|-------------|
| `app/rules/` (70 files) | CREATE | Language-specific rules |
| `scripts/install_steps/detect_language.py` | CREATE | Auto-detect project language |
| `scripts/install_steps/inject_rules.py` | EDIT | Inject language rules into CLAUDE.md |
| `scripts/validate.py` | EDIT | Validate rules format |
| `tests/test_rules.py` | CREATE | Tests |

**Success Criteria:**
- [x] 13 languages × 5 rule files created (70 files: 13 dirs × 5 + 5 common)
- [x] `ai-toolkit install --local` auto-detects language and injects rules (two-phase: marker files + extension scan)
- [x] Manual override: `ai-toolkit install --local --lang typescript` (with aliases: go→golang, c++→cpp, cs→csharp)
- [ ] validate.py checks rules format (not yet implemented)
- [ ] Tests: >=13 (no test_rules file yet)

---

#### 1.2 Advanced Hook Matrix

**Source:** ECC — 11+ specific hooks with PreToolUse/PostToolUse matrix
**Current state:** 14 hooks in `app/hooks/`
**Gap:** Missing specific hooks for config protection, MCP health, governance, continuous learning

**New hooks to add:**

| Hook | Event | Script | Purpose |
|------|-------|--------|---------|
| `guard-config.sh` | PreToolUse (Edit/Write) | Bash | Block edits to .eslintrc, .prettierrc, tsconfig unless explicit |
| `mcp-health.sh` | SessionStart | Bash | Check MCP server health before session |
| `governance-capture.sh` | PostToolUse | Bash | Log governance events (security, policy) |
| `observe-session.sh` | PostToolUse | Bash | Send observations to rag-mcp (bridge) |
| `pre-compact-save.sh` | PreCompact | Bash | Save context state before compaction |
| `commit-quality.sh` | PreToolUse (Bash) | Bash | Check commit message quality |

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/hooks/guard-config.sh` | CREATE | Config file protection |
| `app/hooks/mcp-health.sh` | CREATE | MCP server health check |
| `app/hooks/governance-capture.sh` | CREATE | Governance event logging |
| `app/hooks/observe-session.sh` | CREATE | Send obs to rag-mcp |
| `app/hooks/pre-compact-save.sh` | CREATE | Context save before compact |
| `app/hooks/commit-quality.sh` | CREATE | Commit message quality |
| `scripts/install_steps/install_hooks.py` | EDIT | Register new hooks |
| `tests/test_hooks.py` | EDIT | Tests for new hooks |

**Success Criteria:**
- [x] 5/6 new hooks created and registerable (observe-session.sh not in app/hooks — lives in rag-mcp as consumer)
- [x] guard-config blocks config edits unless `--force`
- [x] mcp-health pings configured MCP servers on session start
- [x] All hooks optional (enable/disable in settings.json)
- [x] Tests: 89 hook tests in test_hooks.bats

---

#### 1.3 MCP Server Templates

**Source:** ECC — 25 preconfigured MCP servers
**What we create:** Template configs that users can copy

**File to create:**
```
app/mcp-templates/
├── README.md                    # How to use templates
├── github.json                  # GitHub MCP server
├── jira.json                    # Jira MCP server
├── context7.json                # Context7 docs
├── filesystem.json              # Filesystem MCP server
├── sequential-thinking.json     # Sequential thinking
├── exa-search.json              # Exa web search
├── supabase.json                # Supabase
├── postgres.json                # PostgreSQL
├── redis.json                   # Redis
├── cloudflare.json              # Cloudflare
├── vercel.json                  # Vercel
├── railway.json                 # Railway
├── docker.json                  # Docker
├── browser-use.json             # Browser automation
├── fal-ai.json                  # fal.ai (image/video)
├── firecrawl.json               # Web scraping
├── sentry.json                  # Sentry error tracking
├── linear.json                  # Linear issue tracker
├── slack.json                   # Slack
├── notion.json                  # Notion
├── confluence.json              # Confluence
├── grafana.json                 # Grafana
├── datadog.json                 # Datadog
└── custom-template.json         # Template for custom MCP
```

**CLI command:**
```bash
ai-toolkit mcp add github          # Copy github.json to .mcp.json
ai-toolkit mcp add github jira     # Add multiple
ai-toolkit mcp list                 # List available templates
ai-toolkit mcp show github         # Show config details
```

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/mcp-templates/` (25 files) | CREATE | MCP configs |
| `bin/ai-toolkit` | EDIT | Add `mcp` subcommand |
| `scripts/mcp_manager.py` | CREATE | MCP template manager |
| `tests/test_mcp_templates.py` | CREATE | Validate JSON schemas |

**Success Criteria:**
- [x] 25 MCP template configs created
- [x] `ai-toolkit mcp add <name>` merges into .mcp.json
- [x] `ai-toolkit mcp list` shows all available
- [x] Tests: 15 in test_mcp_manager.bats

---

### Faza 2: Extension API + Install (tydzień 3-5)

#### 2.1 `inject-hook` CLI Command (Generic Hook Injection)

**Purpose:** Allow ANY external tool to inject hooks into `~/.claude/settings.json` — the same way `inject-rule` works for `~/.claude/CLAUDE.md`. This is the missing piece that enables consumers (rag-mcp, custom tools, CI systems) to register hooks without knowing ai-toolkit internals.

**Current state:**
- `inject-rule ./my-rules.md` → injects rules into CLAUDE.md between `<!-- TOOLKIT:my-rules START/END -->` markers
- `merge-hooks.py inject <hooks.json> <settings.json>` → merges hooks but ONLY with `_source: "ai-toolkit"` tag
- **Gap:** No public CLI for external tools to inject hooks with their OWN `_source` tag

**Architecture (parallels inject-rule):**
```
inject-rule ./rag-mcp-rules.md          → CLAUDE.md      (markers: <!-- TOOLKIT:rag-mcp-rules -->)
inject-hook ./rag-mcp-hooks.json        → settings.json  (tag: "_source": "rag-mcp-hooks")
remove-rule rag-mcp-rules               → strips from CLAUDE.md
remove-hook rag-mcp-hooks               → strips from settings.json
```

**Example: rag-mcp consuming this API:**
```bash
# rag-mcp creates a hooks file:
cat > /tmp/rag-mcp-hooks.json << 'EOF'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "echo 'apply KB-first research'" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "$HOME/.rag-mcp/hooks/observe-session.sh" }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "$HOME/.rag-mcp/hooks/inject-instincts.sh" }]
      }
    ]
  }
}
EOF

# rag-mcp calls ai-toolkit to inject:
npx @softspark/ai-toolkit inject-hook /tmp/rag-mcp-hooks.json
# → all entries tagged with _source: "rag-mcp-hooks" in settings.json
# → re-running is idempotent (strips old rag-mcp-hooks entries, appends new)

# rag-mcp removes its hooks:
npx @softspark/ai-toolkit remove-hook rag-mcp-hooks
```

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `scripts/inject_hook_cli.py` | CREATE | CLI: inject-hook / remove-hook |
| `scripts/merge-hooks.py` | EDIT | Support custom `_source` tag (not just "ai-toolkit") |
| `bin/ai-toolkit.js` | EDIT | Register `inject-hook` + `remove-hook` subcommands |
| `tests/test_inject_hook.bats` | CREATE | Tests |
| `kb/howto/inject-hook-api.md` | CREATE | Documentation for consumers |

**merge-hooks.py changes:**
```python
# Current: always uses SOURCE_TAG = "ai-toolkit"
# New: accept --source parameter
SOURCE_TAG = "ai-toolkit"  # default

def cmd_inject(toolkit_path: str, target_path: str, source: str = "") -> None:
    source_tag = source or derive_source_from_filename(toolkit_path)
    # ... tag all entries with _source: source_tag
    # ... strip old entries with same source_tag
    # ... append new entries
```

**inject_hook_cli.py:**
```python
#!/usr/bin/env python3
"""Inject external hooks into ~/.claude/settings.json.

Usage:
  inject_hook_cli.py <hooks-file.json> [target-dir]
  inject_hook_cli.py --remove <hook-source-name> [target-dir]

The source name is derived from the filename stem (e.g., rag-mcp-hooks.json → "rag-mcp-hooks").
All entries are tagged with "_source": "<source-name>" for idempotent updates.
"""
```

**Consistency table — all ai-toolkit extension commands:**

| Command | Target File | Mechanism | Idempotent |
|---------|------------|-----------|------------|
| `inject-rule <file.md>` | `~/.claude/CLAUDE.md` | HTML markers (`<!-- TOOLKIT:name -->`) | Yes |
| `remove-rule <name>` | `~/.claude/CLAUDE.md` | Strip markers | Yes |
| `inject-hook <file.json>` | `~/.claude/settings.json` | JSON `_source` tag | Yes |
| `remove-hook <name>` | `~/.claude/settings.json` | Strip by `_source` | Yes |
| `add-rule <file.md>` | `~/.softspark/ai-toolkit/rules/` | File copy + re-inject all | Yes |

**Success Criteria:**
- [x] `inject-hook ./my-hooks.json` merges hooks with auto-derived `_source` tag
- [x] `remove-hook my-hooks` strips all entries with that `_source`
- [x] Re-running is idempotent (update, not duplicate)
- [x] Existing ai-toolkit hooks (`_source: "ai-toolkit"`) are never touched
- [x] Tests: 17 in test_inject_hook.bats

---

#### 2.2 Manifest-Driven Install System

**Source:** ECC — JSON manifests, state tracking, 5 profiles
**Current state:** Simple profile-based install (minimal/standard/strict)
**Gap:** No granular module selection, no state tracking, no incremental updates

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `manifest.json` | EDIT | Full module manifest with dependencies |
| `scripts/install_steps/install_plan.py` | CREATE | Plan what to install |
| `scripts/install_steps/install_apply.py` | CREATE | Execute install plan |
| `scripts/install_steps/install_state.py` | CREATE | Track installed modules |
| `tests/test_manifest_install.py` | CREATE | Tests |

**manifest.json structure:**
```json
{
  "modules": {
    "core": {
      "description": "Core skills and hooks",
      "files": ["app/skills/commit/*", "app/skills/review/*", "app/hooks/*.sh"],
      "required": true
    },
    "agents": {
      "description": "Specialized agents",
      "files": ["app/agents/*.md"],
      "required": false,
      "default": true
    },
    "rules-common": {
      "description": "Common coding rules",
      "files": ["app/rules/common/*.md"],
      "required": false,
      "default": true
    },
    "rules-typescript": {
      "description": "TypeScript-specific rules",
      "files": ["app/rules/typescript/*.md"],
      "auto_detect": "package.json"
    },
    "rules-python": {
      "description": "Python-specific rules",
      "files": ["app/rules/python/*.md"],
      "auto_detect": "requirements.txt|pyproject.toml|setup.py"
    },
    "mcp-templates": {
      "description": "MCP server templates",
      "files": ["app/mcp-templates/*.json"],
      "required": false
    },
    "rag-mcp-bridge": {
      "description": "rag-mcp integration hooks",
      "files": ["app/hooks/observe-session.sh", "scripts/config/rag-mcp-bridge.yaml"],
      "required": false,
      "requires": ["core"]
    }
  },
  "profiles": {
    "minimal": ["core"],
    "standard": ["core", "agents", "rules-common"],
    "strict": ["core", "agents", "rules-common", "mcp-templates"],
    "full": ["*"]
  }
}
```

**State tracking (~/.softspark/ai-toolkit/state.json):**
```json
{
  "installed_version": "1.2.1",
  "installed_modules": ["core", "agents", "rules-common", "rules-typescript"],
  "installed_at": "2026-04-07T10:00:00Z",
  "last_updated": "2026-04-07T10:00:00Z",
  "file_hashes": {
    "app/hooks/session-start.sh": "abc123..."
  }
}
```

**CLI:**
```bash
ai-toolkit install --profile standard          # Profile-based (existing)
ai-toolkit install --modules core,agents       # Module-based (new)
ai-toolkit install --auto-detect               # Detect language, install matching rules
ai-toolkit update                              # Incremental update (only changed files)
ai-toolkit status                              # Show installed modules
```

**Success Criteria:**
- [x] manifest.json defines all modules with dependencies
- [x] install --modules allows granular selection
- [x] install --auto-detect detects language from project files (two-phase: markers + extensions)
- [x] state.json tracks what's installed
- [x] update only changes modified files (content hash)
- [x] Backward compatible with existing install
- [x] Tests: 35 across test_install.bats, test_install_flags.bats, test_install_state.bats

---

### Faza 3: New Skills (tydzień 6-7)

#### 3.1 Council Skill (/council)

**Source:** ECC — 4-voice decision workflow
**Type:** Hybrid skill (user-invocable: true)

**File:** `app/skills/council/SKILL.md`

**Skill definition:**
```yaml
---
name: council
description: "4-perspective decision evaluation for architecture choices"
user-invocable: true
agent: orchestrator
context: fork
---
```

**Behavior:**
1. User invokes `/council "Should we migrate from Redis to Valkey?"`
2. Spawn 4 sub-agents in parallel:
   - **Advocate:** Strongest case FOR
   - **Critic:** Strongest case AGAINST (devil's advocate)
   - **Pragmatist:** Trade-offs, costs, timeline, team capacity
   - **User-Proxy:** End-user/customer impact
3. Synthesize into structured output:
   - Pros (from Advocate)
   - Cons (from Critic)
   - Trade-offs (from Pragmatist)
   - User Impact (from User-Proxy)
   - **Recommendation** with confidence level

**Success Criteria:**
- [x] `/council` invocable
- [x] 4 perspectives generated
- [x] Structured output with recommendation
- [ ] Tests: dedicated council tests not yet written

---

#### 3.2 Brand Voice Skill (/brand-voice)

**Source:** ECC — canonical voice system
**Type:** Knowledge skill (user-invocable: false, auto-loaded for writing tasks)

**File:** `app/skills/brand-voice/SKILL.md`

**Content:**
- Anti-trope list (banned LLM phrases: "dive into", "game-changer", "cutting-edge", etc.)
- Voice capture template (how to define a project's voice)
- Consistency checks (before outputting content, verify voice match)

**Success Criteria:**
- [x] Skill auto-loads when writing docs/content
- [x] Anti-trope list prevents generic LLM rhetoric
- [ ] Tests: dedicated brand-voice tests not yet written

---

#### 3.3 Agent Introspection Skill (/introspect)

**Source:** ECC — agent-introspection-debugging
**Type:** Task skill (user-invocable: true)

**File:** `app/skills/introspect/SKILL.md`

**Behavior:**
1. Capture current failure/stuck state
2. Classify pattern (loop, wrong approach, missing context, etc.)
3. Suggest smallest recovery action
4. Emit structured introspection report
5. Optionally hand off to verification

**Success Criteria:**
- [x] `/introspect` invocable when agent is stuck
- [x] Classifies failure pattern
- [x] Suggests recovery action
- [ ] Tests: dedicated introspect tests not yet written

---

### Faza 4: Documentation & Marketing (tydzień 8)

#### 4.1 Documentation Site

**Source:** claude-mem (Mintlify, 27 languages)
**Options:**
1. **Starlight (Astro)** — free, static, fast (recommended)
2. **Mintlify** — paid, beautiful, hosted
3. **Docusaurus** — free, React-based

**Structure:**
```
docs/
├── astro.config.mjs
├── src/content/docs/
│   ├── getting-started/
│   │   ├── installation.md
│   │   ├── quick-start.md
│   │   └── first-skill.md
│   ├── skills/
│   │   ├── tier-1.md
│   │   ├── tier-2.md
│   │   └── tier-3.md
│   ├── agents/
│   │   └── catalog.md
│   ├── hooks/
│   │   └── lifecycle.md
│   ├── guides/
│   │   ├── create-skill.md
│   │   ├── create-agent.md
│   │   └── rag-mcp-integration.md
│   └── reference/
│       ├── cli.md
│       └── manifest.md
```

**Success Criteria:**
- :no_entry: SKIPPED — README/CLAUDE.md sufficient, no documentation site needed

---

## 5. Extension API Design (Generic — No Consumer Knowledge)

ai-toolkit provides a **generic extension API**. It does NOT know about any specific consumer. Consumers use the public CLI to register their rules and hooks.

```
┌──────────────────────────────────────────────────────┐
│                   ai-toolkit (generic)                │
│                                                      │
│  Public Extension API:                               │
│    inject-rule  <file.md>     → CLAUDE.md            │
│    remove-rule  <name>        → CLAUDE.md            │
│    inject-hook  <file.json>   → settings.json  [NEW] │
│    remove-hook  <name>        → settings.json  [NEW] │
│    add-rule     <file.md>     → rules/ registry      │
│    mcp add      <template>    → .mcp.json      [NEW] │
│                                                      │
│  Idempotent: markers (rules) / _source tags (hooks)  │
│  ai-toolkit NEVER calls external services            │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ uses API
        ┌───────────────┼───────────────┐
        │               │               │
   rag-mcp          custom-tool     ci-system
   (consumer)       (consumer)      (consumer)
```

**Example: how rag-mcp would consume (handled in rag-mcp repo, NOT here):**
```bash
# rag-mcp install script calls:
npx @softspark/ai-toolkit inject-rule  ./rag-mcp-rules.md      # existing
npx @softspark/ai-toolkit inject-hook  ./rag-mcp-hooks.json    # NEW
# → rag-mcp's hooks + rules are registered, ai-toolkit doesn't care what they do
```

---

## 6. Success Criteria (Overall)

| Metric | Before | Target |
|--------|--------|--------|
| Skills | 88 | ~91 (+3 new skills) |
| Hooks | 14 | 21 (+7, observe-session in rag-mcp) |
| Language rules | ~8 (pattern skills) | 70 (13 langs × 5 + 5 common) |
| MCP templates | 0 | 25 |
| Install granularity | 3 profiles | 3 profiles + module-level |
| Extension API | inject-rule only | inject-rule + inject-hook + mcp add |
| Documentation | README only | Published site |

---

## 7. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Rule files = maintenance burden | Medium | Medium | Auto-generate from ECC (port script), validate.py checks |
| inject-hook misuse by consumers | Low | Medium | Validate JSON schema, reject malformed hooks |
| Manifest install breaks existing | Low | High | Backward compatible, existing CLI preserved |
| Documentation site drift | Medium | Medium | Generate from source (CLAUDE.md → site), CI check |
| Too many hooks slow session start | Low | Medium | Hooks run async, timeout 5s each |

---

## 8. Pre-Mortem

1. **Language rules become stale** — Mitigation: version in frontmatter, validate.py checks freshness
2. **inject-hook consumers conflict** — Mitigation: each consumer has unique `_source` tag, never collide
3. **Manifest install confuses users** — Mitigation: `--profile` still works, manifest is opt-in power feature
4. **Council skill too slow** — Mitigation: parallel sub-agents, timeout 60s per perspective
5. **Documentation out of sync** — Mitigation: CI job: generate docs → diff → fail if stale

---

## 9. Remaining Gaps

All major features shipped. Outstanding items:

1. [ ] `validate.py` does not check rules format (1.1)
2. [ ] No dedicated `test_rules` test file (1.1)
3. [ ] No dedicated tests for council, brand-voice, introspect skills (3.1-3.3)
4. [x] `observe-session.sh` lives in rag-mcp (consumer), not ai-toolkit — by design

---

## 10. Blockers

None — all features are independent of external systems.

---

**Last Updated:** 2026-04-09
