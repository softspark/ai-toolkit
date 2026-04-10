---
title: "Plan: Enterprise Config Inheritance — Multi-Repo Governance with extends"
category: planning
service: ai-toolkit
tags:
  - enterprise
  - multi-repo
  - config-inheritance
  - extends
  - governance
  - team-management
  - monorepo
doc_type: plan
status: proposed
created: "2026-04-10"
last_updated: "2026-04-10"
completion: "0%"
description: "Configuration inheritance system for ai-toolkit. Enables organizations to define a shared base config (agents, rules, hooks, profiles, constitution overrides) published as an npm package or local path, which individual projects extend via an `extends` field. Changes to the base config propagate automatically on `ai-toolkit update`. Targets enterprises managing 10-100+ repositories with uniform AI governance."
---

# Plan: Enterprise Config Inheritance — Multi-Repo Governance with `extends`

**Status:** Proposed
**Completion:** 0%
**Created:** 2026-04-10
**Origin:** Organizations adopting ai-toolkit across 10-100+ repositories face a config synchronization problem — updating a rule or policy requires touching every repository individually. The `extends` pattern (popularized by ESLint, TypeScript, Prettier) solves this by establishing a single source of truth that projects inherit from.
**Estimated Effort:** 5-7 weeks (1 person) — MVP (core engine + install integration) shippable in ~3.5 weeks

---

## 1. Objective

Create a configuration inheritance system where projects can extend a shared base config published as an npm package, a Git URL, or a local path. The base config defines organizational defaults (which agents to enable, which rules to enforce, which hooks to require, persona presets, and constitution amendments). Individual projects can override or supplement the base, creating a layered governance model.

**Key design principles:**
- **Familiar pattern** — mirrors ESLint's `extends`, TypeScript's `extends`, and Prettier's shared configs
- **npm-first distribution** — base configs are regular npm packages (e.g., `@mycompany/ai-toolkit-config`). Resolver shells out to `npm pack` CLI (respects `.npmrc` auth) — no hand-rolled npm client, preserves stdlib-only constraint
- **Single extends in v1** — `"extends": "string"` only. Multi-base merge (`"extends": [...]`) deferred to v2 to avoid merge-ordering complexity (ESLint's multi-extends is a known source of confusion)
- **Layered merge** — base → project, with explicit override semantics (`override: true` required for safety-critical overrides)
- **Constitution immutable** — base constitution articles cannot be modified by projects, period. Projects can only ADD new articles (article 6+). No weakening detection heuristics — absolute immutability is simpler and safer
- **Offline-capable** — resolved at `install`/`update` time, not at runtime
- **Backward-compatible** — projects without `extends` work exactly as today (no breaking changes)
- **Audit trail** — `state.json` records which base config was resolved and what was overridden

---

## 1a. Functional Requirements

| ID | Requirement | Priority | Success Metric |
|----|-------------|----------|----------------|
| FR1 | Resolve `extends` from npm package, git URL, local path | Must | 4 source types work |
| FR2 | Deep merge base → project config with layered semantics | Must | Merge engine handles dict, list, scalar types |
| FR3 | Constitution immutability — Articles I-V cannot be modified | Must | 100% block rate on modification attempts |
| FR4 | Override validation with `override: true` + `justification` | Must | Missing justification → error |
| FR5 | `enforce` block constraints (minHookProfile, requiredPlugins, forbidOverride, requiredAgents) | Must | All 4 constraint types enforced |
| FR6 | Install/update integration — resolve extends during install | Must | `install --local` detects `.ai-toolkit.json` |
| FR7 | `config diff` command — show project vs base differences | Must | All merge layers visible |
| FR8 | `config validate` command — schema + enforcement validation | Must | Exit 0/1 for pass/fail |
| FR9 | `config init` — interactive project config setup | Should | Guided flow produces valid `.ai-toolkit.json` |
| FR10 | `config create-base` — scaffold npm base config package | Should | Ready-to-publish package with `package.json` |
| FR11 | Lock file for reproducible installs | Should | Identical resolved config across team members |
| FR12 | Audit trail in `state.json` | Should | Resolved version + overrides recorded |
| FR13 | CI enforcement command (`config check`) | Could | Exit 0/1 for governance compliance |
| FR14 | Multi-base extends (`"extends": [...]`) | Won't (v2) | Deferred — merge ordering complexity |

---

## 2. Architecture Overview

```
Organization Level (published once, consumed by all repos):
═══════════════════════════════════════════════════════════

  @mycompany/ai-toolkit-config (npm package)
  ├── ai-toolkit.config.json       ← base configuration
  ├── rules/
  │   ├── code-review-policy.md    ← company-specific rules
  │   └── deployment-checklist.md
  ├── agents/
  │   └── compliance-auditor.md    ← company-specific agent
  └── package.json

Project Level (per-repository):
══════════════════════════════

  my-service/
  ├── .ai-toolkit.json             ← project config with "extends"
  ├── .claude/
  │   ├── CLAUDE.md                ← generated (base + project merged)
  │   └── settings.json            ← generated (base hooks + project hooks merged)
  └── ...

Merge Pipeline:
══════════════

  @mycompany/ai-toolkit-config     ← Layer 0: organizational defaults
          │
          ▼
  ai-toolkit defaults (manifest.json) ← Layer 1: toolkit defaults
          │
          ▼
  .ai-toolkit.json                  ← Layer 2: project overrides
          │
          ▼
  Resolved Configuration             ← Final: CLAUDE.md, settings.json, etc.
```

### Config Resolution Order

```
1. Load base config from "extends" (npm package, git URL, or local path)
2. Merge with ai-toolkit defaults (manifest.json profiles)
3. Apply project-level overrides from .ai-toolkit.json
4. Validate merged config (constitution immutability, schema validation)
5. Generate output files (CLAUDE.md, settings.json, agent symlinks, etc.)
```

---

## 3. Progress Tracking

| # | Feature | Priority | Status | Est. Time | Notes |
|---|---------|----------|--------|-----------|-------|
| 1.1 | `.ai-toolkit.json` schema definition | P0 | Proposed | 1d | JSON Schema with `extends` field |
| 1.2 | Config resolver (npm, git, local path) | P0 | Proposed | 3d | Fetch + cache + validate base configs |
| 1.3 | Merge engine (layered merge with override semantics) | P0 | Proposed | 3d | Deep merge with `override: true` gates |
| 1.4 | Constitution immutability guard | P0 | Proposed | 1d | Block weakening of safety articles |
| 2.1 | Install/update integration | P0 | Proposed | 2d | Resolve extends during install/update |
| 2.2 | `ai-toolkit config diff` command | P0 | Proposed | 1.5d | Show project vs base differences — primary debugging tool |
| 2.3 | `ai-toolkit config validate` command | P0 | Proposed | 1d | Validate .ai-toolkit.json schema + extends resolution |
| 2.4 | `ai-toolkit config init` command | P1 | Proposed | 1.5d | Interactive project config setup |
| 2.5 | `ai-toolkit config create-base` command | P1 | Proposed | 2d | Scaffold base config package |
| 3.1 | Audit trail in state.json | P1 | Proposed | 1d | Record resolved config provenance |
| 3.2 | Lock file (`.ai-toolkit.lock.json`) | P1 | Proposed | 1.5d | Pin resolved versions for reproducibility |
| 3.3 | Base config scaffolder (npm package template) | P1 | Proposed | 1.5d | Ready-to-publish template |
| 3.4 | CI enforcement (`ai-toolkit config check`) | P2 | Proposed | 1d | Verify project adheres to base + no unapproved overrides |
| 4.1 | Tests | P1 | Proposed | 3d | Unit: resolution, merge, immutability, override, CLI commands. Integration: `install --local` with `.ai-toolkit.json` containing `extends`, verify resolved `CLAUDE.md` has base + project rules merged end-to-end |
| 4.2 | Documentation | P1 | Proposed | 3d | Enterprise setup guide + all 9 docs per CLAUDE.md: README, CLAUDE.md, ARCHITECTURE.md, package.json, llms.txt, llms-full.txt, AGENTS.md, skills-catalog.md, architecture-overview.md |

**Phasing (MVP-first):**
- **MVP Phase 1 (week 1-2):** Core engine — schema (1.1), resolver (1.2), merge engine (1.3), constitution guard (1.4)
- **MVP Phase 2 (week 2-3):** Integration + diff — install integration (2.1), `config diff` (2.2), `config validate` (2.3), tests for above (~3.5 weeks = shippable MVP)
- **Phase 3 (week 4-5):** CLI polish — `config init` (2.4), `config create-base` (2.5), scaffolder (3.3)
- **Phase 4 (week 5-6):** Enterprise — audit trail (3.1), lock file (3.2), CI enforcement (3.4) (**gate behind real enterprise feedback**)
- **Phase 5 (week 6-7):** Tests + documentation (4.1, 4.2) (3d docs — all 9 docs per CLAUDE.md rules)

> **Demand validation gate:** Ship MVP (Phases 1-2), announce, measure adoption. Only build Phase 4 (lock file, CI enforcement, audit trail) in response to confirmed enterprise demand.

---

## 4. Dependency Graph

```
                     MVP Phase 1: Core Engine (week 1-2)
                     ====================================
Schema definition (1.1) ──────┐
                              ├──► Merge engine (1.3)
Config resolver (1.2) ────────┤
                              └──► Constitution guard (1.4)

                     MVP Phase 2: Integration + Diff (week 2-3)
                     ============================================
Install integration (2.1) ──┐
                            ├──► config diff (2.2)
                            └──► config validate (2.3)
                            └──► MVP tests → SHIP

                     ═══ DEMAND VALIDATION GATE ═══

                     Phase 3: CLI Polish (week 4-5)
                     ===============================
                            ├──► config init (2.4)
                            └──► create-base (2.5) + scaffolder (3.3)

                     Phase 4: Enterprise (week 5-6)
                     ================================
Audit trail (3.1) ──┐
                    ├──► Lock file (3.2)
                    └──► CI enforcement (3.4)

                     Phase 5: Polish (week 6-7)
                     ===========================
                            └──► Full tests + docs (4.1, 4.2)
```

---

## 5. Detailed Implementation

### Phase 1: Core Engine (week 1-2)

#### 1.1 Configuration Schema (`.ai-toolkit.json`)

> **v1 scope:** The full schema below shows the target state. v1 implements only: `extends`, `profile`, `agents`, `rules`, `constitution`, and `enforce`. See section 6a for the v1/v2 field breakdown.

**Project-level config file:**

```json
{
  "$schema": "https://softspark.github.io/ai-toolkit/schemas/ai-toolkit-config.json",

  "extends": "@mycompany/ai-toolkit-config",

  "profile": "standard",
  "persona": "backend-lead",
  "hookProfile": "strict",

  "agents": {
    "enabled": ["backend-specialist", "test-engineer", "debugger"],
    "disabled": ["game-developer", "mobile-developer"],
    "custom": ["./agents/compliance-auditor.md"]
  },

  "skills": {
    "disabled": ["/deploy", "/rollback"],
    "custom": ["./skills/internal-deploy/"]
  },

  "rules": {
    "inject": ["./rules/code-review-policy.md"],
    "remove": []
  },

  "plugins": {
    "required": ["security-pack", "memory-pack"],
    "forbidden": []
  },

  "languages": ["typescript", "python"],

  "editors": ["cursor", "windsurf", "copilot"],

  "constitution": {
    "amendments": [
      {
        "article": 6,
        "title": "Data Sovereignty",
        "text": "All code generation must comply with GDPR. No personal data in prompts. No PII in generated code comments."
      }
    ]
  },

  "overrides": {
    "hooks": {
      "quality-check": {
        "override": true,
        "justification": "Company uses custom lint pipeline via Jenkins",
        "replacement": "skip"
      }
    }
  }
}
```

**Base config (`ai-toolkit.config.json` in npm package):**

```json
{
  "$schema": "https://softspark.github.io/ai-toolkit/schemas/ai-toolkit-base-config.json",
  "name": "@mycompany/ai-toolkit-config",
  "version": "2.1.0",
  "description": "MyCompany standard AI coding config",

  "extends": null,

  "profile": "strict",
  "persona": "backend-lead",
  "hookProfile": "strict",

  "agents": {
    "enabled": ["backend-specialist", "test-engineer", "code-reviewer", "security-auditor", "debugger", "documenter"],
    "disabled": ["game-developer"],
    "custom": ["./agents/compliance-auditor.md"]
  },

  "rules": {
    "inject": [
      "./rules/code-review-policy.md",
      "./rules/deployment-checklist.md",
      "./rules/data-handling-policy.md"
    ]
  },

  "plugins": {
    "required": ["security-pack"]
  },

  "languages": ["typescript"],

  "constitution": {
    "amendments": [
      {
        "article": 6,
        "title": "Data Sovereignty",
        "text": "All code generation must comply with GDPR. No personal data in prompts."
      },
      {
        "article": 7,
        "title": "Audit Compliance",
        "text": "All AI-generated code changes must be logged to the company audit system. The governance-capture hook must remain enabled."
      }
    ]
  },

  "enforce": {
    "minHookProfile": "standard",
    "requiredPlugins": ["security-pack"],
    "forbidOverride": ["constitution", "guard-destructive", "guard-path"],
    "requiredAgents": ["security-auditor"]
  }
}
```

**`enforce` section:** Base configs can define non-overridable constraints:
- `minHookProfile` — projects cannot go below this profile
- `requiredPlugins` — must be installed in all projects
- `forbidOverride` — these components cannot be overridden
- `requiredAgents` — must be enabled in all projects

---

#### 1.2 Config Resolver

**Resolution sources:**

| Source | Syntax | Resolution |
|--------|--------|------------|
| npm package | `"extends": "@mycompany/ai-toolkit-config"` | `npm pack --pack-destination /tmp` + extract |
| npm with version | `"extends": "@mycompany/ai-toolkit-config@^2.0.0"` | Version resolution via npm |
| Git URL | `"extends": "git+https://github.com/myco/ai-config.git"` | `git clone --depth 1` to cache |
| Local path | `"extends": "../shared-config"` | Resolve relative to project root |
| ~~Multiple bases~~ | ~~`"extends": ["@mycompany/base", "@mycompany/typescript-extra"]`~~ | Deferred to v2 — multi-base merge ordering is a complexity trap |

**Cache directory:** `~/.ai-toolkit/config-cache/`
```
~/.ai-toolkit/config-cache/
  @mycompany/
    ai-toolkit-config/
      2.1.0/
        ai-toolkit.config.json
        rules/
        agents/
```

**Resolution algorithm:**
```python
def resolve_extends(extends_value: str, project_root: str) -> list[BaseConfig]:
    """Resolve extends chain into ordered list of base configs.

    v1: single string only. Multi-base (list) deferred to v2.
    """
    configs = []
    for source in [extends_value]:  # v2: support list[str]
        if source.startswith('@') or source.startswith('npm:'):
            config = resolve_npm(source)
        elif source.startswith('git+'):
            config = resolve_git(source)
        elif source.startswith('.') or source.startswith('/'):
            config = resolve_local(source, project_root)
        else:
            raise ConfigError(f"Unknown extends source: {source}")

        # Recursive: base config may also have "extends"
        if config.extends:
            parent_configs = resolve_extends(config.extends, config.root)
            configs.extend(parent_configs)

        configs.append(config)

    return configs


def resolve_extends(extends_value: str, project_root: str,
                    _visited: set[str] | None = None) -> list[BaseConfig]:
    """Full signature with cycle detection via visited set."""
    if _visited is None:
        _visited = set()
    if extends_value in _visited:
        raise ConfigError(
            f"Circular extends detected: {extends_value} already in chain "
            f"{' → '.join(_visited)}. Check your base config's 'extends' field."
        )
    if len(_visited) >= 5:
        raise ConfigError(
            f"Extends chain too deep (max 5 levels). Chain: {' → '.join(_visited)}"
        )
    _visited.add(extends_value)
    # ... resolution logic as above, passing _visited to recursive calls
```

**Max recursion depth:** 5 levels (prevent circular extends). Circular detection via visited set.

**Offline handling:** If the npm/git source is unavailable:
1. Check cache (`~/.ai-toolkit/config-cache/`)
2. If cached version found → use with warning: "Using cached config v2.1.0 (offline)"
3. If not cached → error with instructions: "Run `ai-toolkit config update` when online"

---

#### 1.3 Merge Engine

**Layered deep merge with explicit override semantics:**

```python
def merge_configs(base: dict, project: dict) -> dict:
    """Merge project config over base config with rules."""
    merged = {}

    for key in set(base.keys()) | set(project.keys()):
        base_val = base.get(key)
        proj_val = project.get(key)

        if proj_val is None:
            merged[key] = base_val
        elif base_val is None:
            merged[key] = proj_val
        elif key == 'constitution':
            merged[key] = merge_constitution(base_val, proj_val)
        elif key == 'agents':
            merged[key] = merge_agents(base_val, proj_val)
        elif key == 'rules':
            merged[key] = merge_rules(base_val, proj_val)
        elif key == 'overrides':
            merged[key] = validate_overrides(base, proj_val)
        elif isinstance(base_val, dict) and isinstance(proj_val, dict):
            merged[key] = merge_configs(base_val, proj_val)
        elif isinstance(base_val, list) and isinstance(proj_val, list):
            merged[key] = list(set(base_val + proj_val))  # union
        else:
            merged[key] = proj_val  # project wins for scalars

    return merged
```

**Agent merge rules:**
```python
def merge_agents(base: dict, project: dict) -> dict:
    """Merge agent configs — project can enable/disable but not remove base-required."""
    merged_enabled = set(base.get('enabled', []))

    # Project can add agents
    merged_enabled.update(project.get('enabled', []))

    # Project can disable agents (unless base enforces them)
    for agent in project.get('disabled', []):
        if agent in base.get('enforce', {}).get('requiredAgents', []):
            raise ConfigError(
                f"Cannot disable '{agent}' — required by base config '{base['name']}'. "
                f"Contact your team lead to request an exemption."
            )
        merged_enabled.discard(agent)

    return {
        'enabled': sorted(merged_enabled),
        'custom': base.get('custom', []) + project.get('custom', [])
    }
```

**Override validation:**
```python
def validate_overrides(base: dict, overrides: dict) -> dict:
    """Validate project overrides against base enforcement rules."""
    forbidden = set(base.get('enforce', {}).get('forbidOverride', []))

    for key, override in overrides.items():
        if key in forbidden:
            raise ConfigError(
                f"Cannot override '{key}' — forbidden by base config '{base['name']}'.\n"
                f"Forbidden overrides: {', '.join(sorted(forbidden))}\n"
                f"Contact your team lead to request an exemption."
            )
        if not override.get('override'):
            raise ConfigError(
                f"Override for '{key}' requires explicit 'override: true' + 'justification' field.\n"
                f"This ensures intentional deviation from organizational defaults."
            )
        if not override.get('justification'):
            raise ConfigError(
                f"Override for '{key}' requires a 'justification' field explaining why.\n"
                f"Example: \"Company uses custom lint pipeline via Jenkins\""
            )

    return overrides
```

---

#### 1.4 Constitution Immutability Guard

**Core rule:** Base constitution articles are absolutely immutable. Projects can only ADD new articles.

No weakening-detection heuristic (character count, semantic analysis) — these produce false positives and are gameable. Instead, the rule is simple and absolute: if an article number exists in the base, it cannot be modified by the project.

```python
def merge_constitution(base: dict, project: dict) -> dict:
    """Merge constitution — additions only, no modifications."""
    base_amendments = {a['article']: a for a in base.get('amendments', [])}
    proj_amendments = {a['article']: a for a in project.get('amendments', [])}

    # Toolkit articles I-V are always immutable
    IMMUTABLE_ARTICLES = {1, 2, 3, 4, 5}

    merged = dict(base_amendments)

    for article_num, amendment in proj_amendments.items():
        if article_num in IMMUTABLE_ARTICLES:
            raise ConfigError(
                f"Cannot modify Constitution Article {article_num} — immutable.\n"
                f"Articles I-V are defined by ai-toolkit and cannot be overridden.\n"
                f"You can ADD new articles (article 6+)."
            )
        if article_num in base_amendments:
            # Base articles are immutable — projects cannot modify them
            raise ConfigError(
                f"Cannot modify Constitution Article {article_num} — "
                f"defined by base config '{base.get('name', 'unknown')}'.\n"
                f"Base articles are immutable. You can ADD new articles "
                f"with a higher article number."
            )
        merged[article_num] = amendment

    return {'amendments': list(merged.values())}
```

---

### MVP Phase 2: Integration + Diff (week 2-3)

#### 2.1 Install/Update Integration

**Modified `install.py` flow:**

```python
# During install --local:
# 1. Check for .ai-toolkit.json in project root
# 2. If found and has "extends":
#    a. Resolve base config(s)
#    b. Merge base → project
#    c. Validate merged config
#    d. Generate files from merged config
# 3. If not found: proceed with current behavior (backwards compatible)
```

**CLI flags:**
```bash
ai-toolkit install --local                           # auto-detect .ai-toolkit.json
ai-toolkit install --local --config ./custom.json    # explicit config file
ai-toolkit update --local                            # re-resolve extends + update
ai-toolkit update --local --refresh-base             # force re-fetch base config
```

---

#### 2.2 `ai-toolkit config diff`

**Show differences between project config and base:**

```bash
ai-toolkit config diff

# Output:
# Base: @mycompany/ai-toolkit-config@2.1.0
#
# Profile:     strict (base) → standard (project) ⚠ OVERRIDE
# Persona:     backend-lead (base) → frontend-lead (project)
# Hook Profile: strict (base) → strict (inherited)
#
# Agents:
#   + frontend-specialist     (project adds)
#   - game-developer          (base disables)
#   = security-auditor        (base requires, cannot disable)
#
# Rules:
#   + ./rules/api-standards.md  (project adds)
#   = code-review-policy.md     (inherited from base)
#
# Constitution:
#   = Articles I-V              (immutable)
#   = Article 6: Data Sovereignty (inherited from base)
#   + Article 8: API Standards    (project adds)
#
# Overrides:
#   quality-check: SKIP (justification: "Custom Jenkins pipeline")
```

---

#### 2.3 `ai-toolkit config validate`

```bash
ai-toolkit config validate

# Checks:
# ✓ .ai-toolkit.json schema valid
# ✓ extends: @mycompany/ai-toolkit-config@2.1.0 resolved
# ✓ No forbidden overrides
# ✓ Required plugins installed: security-pack
# ✓ Required agents enabled: security-auditor
# ✓ Constitution articles I-V intact
# ✓ Hook profile meets minimum: standard ≥ standard
# ✓ All custom rule files exist
# ✓ All custom agent files exist
```

---

### Phase 3: CLI Polish (week 4-5)

#### 2.4 `ai-toolkit config init`

**Interactive project config setup:**

```bash
ai-toolkit config init

# Flow:
# 1. "Does your organization have a shared ai-toolkit config? [y/n]"
#    → y: "npm package name or git URL:" → resolves + validates
#    → n: creates minimal .ai-toolkit.json without extends
# 2. "Which profile? [minimal/standard/strict]" → default from base or standard
# 3. "Which persona? [none/backend-lead/frontend-lead/devops-eng/junior-dev]"
# 4. Auto-detect languages from project
# 5. Auto-detect editors from project files
# 6. Write .ai-toolkit.json
# 7. Run ai-toolkit install --local
```

---

#### 2.5 `ai-toolkit config create-base`

**Scaffold a base config package:**

```bash
ai-toolkit config create-base @mycompany/ai-toolkit-config

# Creates:
# @mycompany-ai-toolkit-config/
# ├── package.json          (name, version, files, peerDependencies)
# ├── ai-toolkit.config.json (base config with sane defaults)
# ├── rules/                (empty, ready for company rules)
# ├── agents/               (empty, ready for company agents)
# └── README.md             (setup instructions)
```

**Generated `package.json`:**
```json
{
  "name": "@mycompany/ai-toolkit-config",
  "version": "1.0.0",
  "description": "Shared ai-toolkit configuration for MyCompany",
  "main": "ai-toolkit.config.json",
  "files": ["ai-toolkit.config.json", "rules/", "agents/"],
  "peerDependencies": {
    "@softspark/ai-toolkit": ">=1.5.0"
  },
  "keywords": ["ai-toolkit", "config", "shared"]
}
```

---

### Phase 4: Enterprise Features (week 5-6)

#### 3.1 Audit Trail

**`state.json` additions:**
```json
{
  "extends": {
    "source": "@mycompany/ai-toolkit-config",
    "version": "2.1.0",
    "resolved_at": "2026-04-10T10:30:00Z",
    "hash": "sha256:abc123...",
    "overrides_applied": [
      {
        "key": "hooks.quality-check",
        "action": "skip",
        "justification": "Custom Jenkins pipeline"
      }
    ]
  }
}
```

---

#### 3.2 Lock File (`.ai-toolkit.lock.json`)

**Purpose:** Pin the exact resolved version of base configs for reproducible installs across team members and CI.

```json
{
  "lockfileVersion": 1,
  "resolved": {
    "@mycompany/ai-toolkit-config": {
      "version": "2.1.0",
      "resolved": "https://registry.npmjs.org/@mycompany/ai-toolkit-config/-/ai-toolkit-config-2.1.0.tgz",
      "integrity": "sha512-abc123...",
      "cached": "~/.ai-toolkit/config-cache/@mycompany/ai-toolkit-config/2.1.0/"
    }
  },
  "generated_at": "2026-04-10T10:30:00Z",
  "ai_toolkit_version": "1.5.1"
}
```

**Behavior:**
- `ai-toolkit install --local` → uses lock file if present (like `npm ci`)
- `ai-toolkit update --local` → re-resolves and updates lock file (like `npm install`)
- `ai-toolkit update --local --refresh-base` → force re-fetch ignoring cache
- `.ai-toolkit.lock.json` should be committed to git (team synchronization)

---

#### 3.4 CI Enforcement

**`ai-toolkit config check` — for CI pipelines:**

```bash
ai-toolkit config check

# Exit codes:
# 0 — project complies with base config
# 1 — violations found (missing required plugins, forbidden overrides, etc.)
# 2 — .ai-toolkit.json not found
```

**GitHub Actions example:**
```yaml
- name: AI Toolkit Governance Check
  run: |
    npx @softspark/ai-toolkit config check
    npx @softspark/ai-toolkit config validate --strict
```

**What it checks:**
1. Required plugins are installed
2. Required agents are enabled
3. No forbidden overrides applied without exemption
4. Hook profile meets minimum
5. Constitution articles intact
6. Lock file up-to-date (warn if stale)

---

## 6. File Summary

| File | Action | LOC (est.) | Description |
|------|--------|------------|-------------|
| `scripts/config_resolver.py` | CREATE | ~400 | Resolve extends (npm, git, local path) |
| `scripts/config_merger.py` | CREATE | ~350 | Layered merge engine |
| `scripts/config_validator.py` | CREATE | ~200 | Schema + enforcement validation |
| `scripts/config_scaffold.py` | CREATE | ~250 | create-base scaffolder |
| `scripts/config_diff.py` | CREATE | ~200 | Diff viewer |
| `scripts/config_check.py` | CREATE | ~150 | CI enforcement checker |
| `scripts/install.py` | EDIT | +80 | Integrate extends resolution |
| `bin/ai-toolkit.js` | EDIT | +40 | Register config subcommands |
| `manifest.json` | EDIT | +10 | Schema references |
| `kb/reference/enterprise-config-guide.md` | CREATE | ~300 | Enterprise setup guide |
| `kb/reference/base-config-template/` | CREATE | ~200 | Scaffolded base config files |
| `tests/test_config_resolver.bats` | CREATE | ~150 | Resolution tests |
| `tests/test_config_merger.bats` | CREATE | ~200 | Merge + override tests |
| `tests/test_config_immutability.bats` | CREATE | ~100 | Constitution guard tests |
| `tests/test_config_cli.bats` | CREATE | ~150 | CLI command tests |
| **Total** | | **~2780** | |

---

## 6a. Schema Scope (v1 vs v2)

v1 ships with a minimal schema. Each additional field adds merge logic, validation, diff output, and test surface. Expand based on real usage, not speculation.

| Field | v1 | v2 | Rationale |
|-------|----|----|-----------|
| `extends` | single string | array (multi-base) | Multi-base merge ordering is complex |
| `profile` | yes | — | Core governance knob |
| `agents` | yes | — | Most common customization |
| `rules` | yes | — | Rule injection is existing feature |
| `constitution` | yes | — | Key differentiator |
| `enforce` | yes | — | Non-overridable constraints |
| `skills` | — | yes | Less commonly customized at org level |
| `plugins` | — | yes | Depends on plugin maturity |
| `languages` | — | yes | Auto-detected, rarely org-level |
| `editors` | — | yes | Auto-detected, rarely org-level |
| `overrides` | — | yes | Complex, needs real-world feedback |
| `hookProfile` / `persona` | — | yes | Low demand signal |

---

## 6b. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | `install --local` with extends resolution < 5s (cached), < 15s (first fetch). Config merge < 100ms. |
| **Offline** | Cached configs used when registry unavailable, with clear warning. |
| **Security** | No secret exposure in config files or audit trail. npm auth via `.npmrc` (user-managed). `execFile` for npm CLI (no shell injection). |
| **Error messages** | Every validation error includes: what failed, which config layer caused it, and what to do (e.g., "Contact your team lead to request an exemption"). |
| **Backward compatibility** | 100% — projects without `.ai-toolkit.json` work exactly as today. Zero behavioral changes for existing users. |
| **Maintainability** | Each new schema field requires: merge logic, validation, diff output, test. Budget 0.5d per new field. |
| **Quality gates** | `ruff check scripts/config_*.py` (0 errors), `mypy --strict scripts/config_*.py` (0 errors). Run before every commit. |
| **Type safety** | 100% public API type hints (all function signatures). >60% internal. Use `TypedDict` for config schemas, `dataclass` for resolved configs. |

---

## 7. Success Criteria (Overall)

| Metric | Target |
|--------|--------|
| Extends sources (v1) | 4 (npm, npm+version, git URL, local path) — single string only |
| Merge depth | 5 levels max (recursive extends) |
| Config schema | JSON Schema validated |
| Constitution protection | 100% (Articles I-V immutable) |
| Override justification | Required for all overrides |
| Enforce constraints | 4 types (minHookProfile, requiredPlugins, forbidOverride, requiredAgents) |
| Backward compatibility | 100% (projects without .ai-toolkit.json work as today) |
| CI enforcement | Exit code 0/1 for governance compliance |
| Lock file | Reproducible installs across team members |
| Scaffold command | Ready-to-publish npm package template |
| Tests | 30+ |
| Offline resolution | Cached configs with warning |

---

## 8. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| npm registry unavailable during install | Low | Medium | Cache + offline fallback with warning |
| Circular extends chain | Low | High | Max depth 5 + visited set for cycle detection |
| Base config breaks project | Medium | High | Lock file pins exact version; `ai-toolkit config diff` shows changes before update |
| Override abuse (teams bypass governance) | Medium | Medium | `enforce.forbidOverride` + CI check + justification requirement |
| Config schema too restrictive | Medium | Medium | Start with minimal enforcement, expand based on enterprise feedback |
| Multiple base configs conflict | — | — | Deferred to v2 (single extends only in v1) |
| Private npm registry authentication | Medium | Low | Use existing npm auth (`.npmrc`), document setup |
| Git URL resolution slow | Low | Low | `--depth 1` clone, cache aggressively |

---

## 9. Pre-Mortem

1. **"Config file fatigue"** — developers already have `.eslintrc`, `tsconfig.json`, `.prettierrc`. Another `.ai-toolkit.json` may feel like bloat. Mitigation: file is optional, all features work without it. The DX gain (organizational governance without per-repo updates) justifies the file.
2. **"Base config never gets updated"** — team lead creates base config, nobody maintains it. Mitigation: `ai-toolkit config check` in CI catches drift; lock file staleness warnings.
3. **"Override justification is annoying"** — developers will write "needed" as justification. Mitigation: CI check can enforce minimum justification length (>20 chars); code review culture catches low-effort justifications.
4. **"Merge semantics are confusing"** — "does project override or extend the base agent list?" Mitigation: explicit semantics documented in schema; `ai-toolkit config diff` shows exactly what happened.
5. **"Enterprise teams want RBAC on overrides"** — who can approve overrides? Mitigation: v1 uses justification text + code review; v2 could integrate with GitHub CODEOWNERS for override approval.

---

## 10. Market Positioning

**Target users:**
1. **Engineering managers** — enforce AI coding standards across 20+ repos without touching each one
2. **Security teams** — ensure constitution + security-auditor agent is always enabled
3. **Platform teams** — distribute company-specific agents, rules, and plugins via npm
4. **Compliance officers** — audit trail of what AI governance rules are active in each project

**Competitive advantage:** No existing AI coding toolkit supports configuration inheritance. This is a unique enterprise feature that transforms ai-toolkit from a developer tool into an organizational governance platform.

**Revenue potential:** Enterprise teams are the primary audience for paid support/consulting around ai-toolkit. Config inheritance is the feature that makes enterprise adoption manageable.

---

## 11. Next Actions

**MVP (ship first, ~3.5 weeks):**
1. [ ] Approve plan
2. [ ] Define `.ai-toolkit.json` JSON Schema — v1 scope only (1.1)
3. [ ] Implement config resolver (npm, git, local) with caching (1.2)
4. [ ] Implement merge engine with override validation (1.3)
5. [ ] Implement constitution immutability guard (1.4)
6. [ ] Integrate into install.py flow (2.1)
7. [ ] Create `config diff` viewer (2.2) — primary debugging tool
8. [ ] Create `config validate` checker (2.3)
9. [ ] Tests for above (4.1 partial)
10. [ ] **Ship MVP → announce → measure adoption**

**Post-MVP (if demand validated):**
11. [ ] Create `config init` interactive command (2.4)
12. [ ] Create `config create-base` scaffolder (2.5)
13. [ ] Add audit trail to state.json (3.1)
14. [ ] Implement lock file generation + resolution (3.2)
15. [ ] Create base config npm package template (3.3)
16. [ ] Create CI enforcement command `config check` (3.4)
17. [ ] Full tests + documentation — all 9 docs per CLAUDE.md (4.1, 4.2)

---

## 12. Future (v2)

| Feature | Rationale |
|---------|-----------|
| Multi-base extends (`"extends": [...]`) | Needs real-world feedback on merge ordering UX |
| v1 deferred schema fields (skills, plugins, languages, editors, overrides, hookProfile, persona) | Expand based on actual enterprise requests |
| RBAC on overrides (GitHub CODEOWNERS integration) | v1 uses justification + code review |
| Semantic constitution analysis | Character-count heuristics removed in v1; revisit only if absolute immutability proves too restrictive |
| `ai-toolkit config audit` (full governance report) | Depends on audit trail maturity |

---

## 13. Cross-Plan Dependencies

This plan shares modification targets with two other proposed plans:

| Shared File | This Plan | Local Dashboard Plan | Offline SLM Plan |
|-------------|-----------|---------------------|-----------------|
| `scripts/install.py` | +80 LOC (extends resolution) | — | +30 LOC (offline-slm profile) |
| `manifest.json` | +10 LOC (schema refs) | — | +5 LOC (offline-slm profile) |
| `bin/ai-toolkit.js` | +40 LOC (config subcommands) | +15 LOC (ui command) | +10 LOC (compile-slm command) |

**If implementing in parallel:** coordinate merge order for shared files. Recommended sequence: Offline SLM (smallest changes) → Enterprise Config → Dashboard (no install.py changes).

**Dashboard integration note:** If this plan ships before the Dashboard plan, the Dashboard's Config page (2.6) should display `.ai-toolkit.json` / `extends` status and the `config diff` output.

---

**Last Updated:** 2026-04-10
