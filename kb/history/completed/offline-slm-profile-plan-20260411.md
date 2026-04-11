---
title: "Plan: Offline-First SLM Profile — Lightweight Mode for Local Models"
category: planning
service: ai-toolkit
tags:
  - offline
  - slm
  - small-language-models
  - ollama
  - lm-studio
  - profile
  - context-optimization
  - privacy
doc_type: plan
status: completed
created: "2026-04-10"
last_updated: "2026-04-11"
completion: "100%"
completed: "2026-04-11"
description: "Lightweight profile for ai-toolkit optimized for Small Language Models (SLMs) running locally via Ollama, LM Studio, or similar. Compiles a minimal instruction set that fits within 4K-8K system prompt budgets while preserving critical safety guardrails. Targets air-gapped, privacy-first, and cost-sensitive development workflows."
---

# Plan: Offline-First SLM Profile — Lightweight Mode for Local Models

**Status:** Completed
**Completion:** 100%
**Completed:** 2026-04-11
**Created:** 2026-04-10
**Origin:** Enterprise IP security requirements (air-gapped environments), cost-sensitive solo developers, and the growing adoption of local models (Ollama, LM Studio, llamafile). Current toolkit emits 20K+ token system prompts that exceed SLM context windows and degrade small model performance.
**Estimated Effort:** 4-5 weeks (1 person)

---

## 1. Objective

Create a `--profile offline-slm` install profile and a `scripts/compile_slm.py` compiler that produces a minimal, high-signal instruction set optimized for Small Language Models (8B-32B parameters). The compiled output preserves critical safety guardrails while stripping agent orchestration, multi-agent coordination, and complex skill routing that SLMs cannot handle.

**Key design principles:**
- **Token budget** — compiled output fits within 4K tokens (system prompt), with optional 8K mode for larger SLMs
- **Safety-preserved** — Constitution Articles I-V always included (non-negotiable)
- **Single-agent focus** — no multi-agent orchestration, no /swarm, no /teams
- **Deterministic compilation** — same input → same output, no LLM involved in compilation
- **Model-aware** — detects model size from Ollama API or manual flag and adjusts verbosity
- **Platform-agnostic** — outputs plain markdown consumable by any local inference engine
- **Hooks stripped** — SLM providers don't support lifecycle hooks; rules compile into system prompt

---

## 1a. Functional Requirements

| ID | Requirement | Priority | Success Metric |
|----|-------------|----------|----------------|
| FR1 | Token counter (stdlib-only, ±10% accuracy target) | Must | Conservative estimate, no external deps |
| FR2 | Component parser + scorer with safety-priority ranking | Must | Constitution=1.0, all components scored |
| FR3 | Compression engine with 4 levels (ultra-light, light, standard, extended) | Must | Each level strips progressively less |
| FR4 | Budget packer (greedy knapsack by score/size ratio) | Must | Output ≤ budget × 0.95 in all cases |
| FR5 | Markdown emitter with safety-first structure | Must | Constitution always first in output |
| FR6 | `--profile offline-slm` install integration | Must | `install.py` + `manifest.json` updated |
| FR7 | `compile-slm` CLI command with flags | Must | `--budget`, `--model-size`, `--persona`, `--lang`, `--output`, `--format`, `--dry-run` |
| FR8 | Constitution always included (non-negotiable) | Must | Compilation fails if constitution exceeds budget alone |
| FR9 | Model size detection from Ollama API | Should | Auto-detect with graceful fallback to `14b` |
| FR10 | Persona-aware compilation (boost relevant skills) | Should | Persona skills ranked higher |
| FR11 | Language-aware compilation (include matching rules only) | Should | Non-matching language rules excluded |
| FR12 | Integration guides for 4 platforms (Ollama, LM Studio, Aider, Continue.dev) | Should | Step-by-step setup per platform |
| FR13 | Compile quality validator (post-compilation checks) | Should | FAIL on missing constitution, budget exceeded |
| FR14 | 4 output formats (raw markdown, Ollama Modelfile, JSON string, Aider-compatible) | Should | Each format usable by target tool |
| FR15 | `--dry-run` output showing included components + token counts | Should | Table: component, score, tokens, included? |

---

## 2. Architecture Overview

```
ai-toolkit install --profile offline-slm [--model-size 8b|14b|32b|70b]
ai-toolkit compile-slm [--budget 4096] [--persona backend-lead] [--lang typescript]

  ┌──────────────────────────────────────────────────────────┐
  │              offline-slm Profile                          │
  │                                                          │
  │  Compiler: scripts/compile_slm.py                        │
  │  Input:  full toolkit (agents, skills, rules, constitution)│
  │  Output: single compiled .md file for system prompt       │
  │                                                          │
  │  Token Budget Tiers:                                     │
  │    ultra-light (2K) — safety + persona only              │
  │    light (4K) — safety + persona + top skills + rules    │
  │    standard (8K) — safety + persona + full skills + rules │
  │    extended (16K) — near-full toolkit (for 32B+ models)   │
  │                                                          │
  │  Output Files:                                           │
  │    ~/.ai-toolkit/compiled/slm-system-prompt.md           │
  │    ~/.ai-toolkit/compiled/slm-skills-reference.md        │
  │    CLAUDE.md (or equivalent) — auto-generated            │
  │                                                          │
  │  Integration Targets:                                    │
  │    Ollama (modelfile SYSTEM directive)                    │
  │    LM Studio (system prompt field)                       │
  │    llamafile (--system-prompt flag)                       │
  │    Open WebUI (system prompt setting)                    │
  │    Aider (--system-prompt-file flag)                     │
  │    Continue.dev (system prompt in config)                │
  └──────────────────────────────────────────────────────────┘
```

### Compilation Pipeline

```
Full Toolkit (20K+ tokens)
         │
         ▼
  ┌─────────────────┐
  │ 1. Parse Phase   │  Read all agents, skills, rules, constitution
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 2. Rank Phase    │  Score components by: safety criticality × usage frequency × persona relevance
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 3. Compress Phase│  Strip: examples, rationalization tables, related skills, verbose headers
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 4. Budget Phase  │  Pack highest-scoring components until token budget reached
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ 5. Emit Phase    │  Write compiled .md + integration instructions
  └─────────────────┘
```

---

## 3. Progress Tracking

| # | Feature | Priority | Status | Est. Time | Notes |
|---|---------|----------|--------|-----------|-------|
| 1.1 | Token counter (tiktoken-free, word-based estimator) | P0 | Proposed | 0.5d | ~0.75 tokens/word heuristic (stdlib only) |
| 1.2 | Component parser + scorer | P0 | Proposed | 2d | Parse frontmatter, score by criticality/frequency/persona |
| 1.3 | Compression engine | P0 | Proposed | 2d | Strip examples, rationalization tables, headers |
| 1.4 | Budget packer | P0 | Proposed | 1d | Greedy knapsack by score/size ratio |
| 1.5 | Emitter (markdown output) | P0 | Proposed | 1d | Clean compiled .md file |
| 2.1 | Profile integration (`--profile offline-slm`) | P0 | Proposed | 1.5d | Install.py + manifest.json + state.json |
| 2.2 | CLI command (`ai-toolkit compile-slm`) | P0 | Proposed | 1d | Standalone compilation with flags |
| 2.3 | Model size detection (Ollama API) | P1 | Proposed | 1d | Auto-detect model params from `ollama list` |
| 2.4 | Persona-aware compilation | P1 | Proposed | 1.5d | Boost persona-relevant skills in ranking |
| 2.5 | Language-aware compilation | P1 | Proposed | 1d | Include only matching language rules |
| 3.1 | Integration guides (Ollama, LM Studio, Aider, Continue) | P1 | Proposed | 1.5d | Step-by-step per platform |
| 3.2 | Compile quality validator | P1 | Proposed | 1d | Verify output covers constitution, fits budget |
| 3.3 | Tests | P1 | Proposed | 3d | Unit: compilation determinism, budget compliance, 4 compression levels × 4 output formats, constitution guard. Integration: `compile-slm --model-size 8b`, verify output fits 2048 tokens + constitution present end-to-end. Target: 40+ tests |
| 3.4 | Documentation | P1 | Proposed | 2.5d | All 9 docs per CLAUDE.md: README, CLAUDE.md, ARCHITECTURE.md, package.json, llms.txt, llms-full.txt, AGENTS.md, skills-catalog.md, architecture-overview.md + integration guide |

**Phasing:**
- **Phase 1 (week 1-2):** Compiler — parser, scorer, compressor, packer, emitter
- **Phase 2 (week 2-3):** Integration — profile, CLI, model detection, persona/language awareness
- **Phase 3 (week 3-4):** Polish — integration guides, validator, tests, documentation

> **Demand validation gate:** Ship Phase 1 + basic Phase 2 (compiler + profile + CLI with `--budget` and `--model-size` flags) as MVP. Test with 3 real models (8B, 14B, 32B). Only build persona/language-aware compilation and platform-specific integration guides if MVP validation confirms output quality.

---

## 4. Dependency Graph

```
                     Phase 1: Compiler (week 1-2)
                     ============================
Token counter (1.1) ────┐
                        ├──► Compression engine (1.3) ──► Budget packer (1.4) ──► Emitter (1.5)
Component parser (1.2) ──┘

                     Phase 2: Integration (week 2-3)
                     ================================
Profile integration (2.1) ──┐
                            ├──► CLI command (2.2)
Model detection (2.3) ──────┤
Persona-aware (2.4) ────────┤
Language-aware (2.5) ────────┘

                     Phase 3: Polish (week 3-4)
                     ===========================
                            ├──► Integration guides (3.1)
                            ├──► Compile validator (3.2)
                            └──► Tests + docs (3.3, 3.4)
```

---

## 5. Detailed Implementation

### Phase 1: Compiler Engine (week 1-2)

#### 1.1 Token Counter

**Stdlib-only token estimation** — no tiktoken, no external dependencies.

```python
def estimate_tokens(text: str) -> int:
    """Estimate token count from text without external dependencies.

    Uses two heuristics and returns the higher (conservative) estimate:
    1. Word-based: ~0.75 tokens/word for English prose
    2. Char-based: ~1 token per 4 chars (more accurate for code-heavy content)

    Accuracy target: ±10% vs tiktoken cl100k_base. To be validated on 50 toolkit files before shipping.
    """
    word_est = int(len(text.split()) * 0.75)
    char_est = len(text) // 4
    # Code blocks have higher token density — adjust
    code_blocks = text.count('```')
    code_penalty = code_blocks * 15
    return max(word_est, char_est) + code_penalty
```

**Why not tiktoken:** tiktoken requires a C extension and network download of the BPE file. This violates the stdlib-only constraint and fails in air-gapped environments (which is literally the target audience for this feature).

**Accuracy target:** ±10% vs tiktoken cl100k_base. Using `max(word, char)` gives a conservative estimate. We pack to budget × 0.95 (5% safety margin) to absorb estimation error.

---

#### 1.2 Component Parser + Scorer

**Parse all toolkit components into a unified scoring table:**

```python
@dataclass
class Component:
    name: str
    type: str          # 'constitution', 'agent', 'skill', 'rule', 'hook-equivalent'
    source_file: str
    full_text: str
    compressed_text: str  # after stripping (populated by compressor)
    tokens_full: int
    tokens_compressed: int
    score: float       # 0.0 - 1.0

    # Scoring factors
    safety_criticality: float   # 0.0-1.0 (constitution=1.0, guard hooks=0.9)
    usage_frequency: float      # 0.0-1.0 (from stats.json, normalized)
    persona_relevance: float    # 0.0-1.0 (match against active persona)
    language_relevance: float   # 0.0-1.0 (match against project language)
```

**Scoring formula:**
```python
score = (
    safety_criticality * 0.40 +    # Safety always dominates — non-negotiable content gets priority
    usage_frequency * 0.25 +       # Frequently used = valuable — from stats.json invocation counts
    persona_relevance * 0.20 +     # Persona-matched = valuable — e.g. backend-lead boosts API skills
    language_relevance * 0.15      # Language-matched = contextual — include only relevant rules
)
# Weight rationale: safety must dominate (0.40) to guarantee constitution + guard rules always fit.
# Usage + persona (0.45 combined) ensure the most practical content fills remaining budget.
# Language (0.15) is a tiebreaker — most projects use 1-2 languages.
# Weights are compile-time constants in v1. If empirical testing (5 standard tasks across
# 3 model sizes) shows suboptimal results, expose as --score-weights flag in v2.
```

**Fixed-score components (always included):**

| Component | Score | Reason |
|-----------|-------|--------|
| Constitution (Articles I-V) | 1.0 | Non-negotiable safety |
| Guard hooks (destructive, path) | 0.95 | Core safety rules (compiled as text, not hooks) |
| Active persona definition | 0.90 | User-selected identity |
| Active language rules | 0.85 | Project-specific quality gates |

**Dynamic-score components:**

| Component | Base Score | Adjusted By |
|-----------|-----------|-------------|
| Individual skills | 0.3-0.7 | Usage frequency + persona fit |
| Agent definitions | 0.2-0.6 | Persona relevance (only 1 agent in SLM mode) |
| Knowledge skills | 0.2-0.5 | Language match + persona match |
| Iron Law rules | 0.7 | Always high (quality enforcement) |

---

#### 1.3 Compression Engine

**Strip low-signal content while preserving semantics:**

| Strip Target | Savings (est.) | Example |
|-------------|---------------|---------|
| `## Common Rationalizations` tables | 200-400 tokens/skill | 15 skills have these tables |
| `## Related Skills` sections | 50-100 tokens/skill | Routing not useful for SLMs |
| `## Verification Checklist` (keep 1-liner summary) | 100-200 tokens/agent | Compress to "Verify: tests pass, no placeholders" |
| Markdown headers (collapse hierarchy) | 20-50 tokens/file | `### 2.1.3 Sub-feature` → plain paragraph |
| Example code blocks (keep first, strip rest) | 100-500 tokens/skill | Keep 1 example max |
| Frontmatter (YAML) | 50-100 tokens/file | Strip entirely from compiled output |
| Agent `## Allowed CLI Commands` lists | 200-400 tokens/agent | Not needed when agent won't execute them |
| Multi-agent coordination instructions | 300-500 tokens | SLM = single agent, no /orchestrate |
| Effort-based budgeting rules | 100 tokens | SLM doesn't manage budgets |

**Compression levels:**

```python
COMPRESSION_LEVELS = {
    'ultra-light': {
        'strip_examples': True,
        'strip_rationalizations': True,
        'strip_related_skills': True,
        'strip_verification': True,
        'strip_agent_commands': True,
        'strip_multi_agent': True,
        'max_skills': 5,         # Only top 5 skills by score
        'max_agents': 0,         # No agent definitions (persona only)
        'include_rules': False,
    },
    'light': {
        'strip_examples': True,
        'strip_rationalizations': True,
        'strip_related_skills': True,
        'strip_verification': 'summary',  # 1-liner
        'strip_agent_commands': True,
        'strip_multi_agent': True,
        'max_skills': 10,
        'max_agents': 1,         # Persona agent only
        'include_rules': True,
    },
    'standard': {
        'strip_examples': 'first-only',  # Keep 1 example
        'strip_rationalizations': True,
        'strip_related_skills': True,
        'strip_verification': 'summary',
        'strip_agent_commands': True,
        'strip_multi_agent': True,
        'max_skills': 20,
        'max_agents': 3,
        'include_rules': True,
    },
    'extended': {
        'strip_examples': 'first-only',
        'strip_rationalizations': 'first-only',
        'strip_related_skills': False,
        'strip_verification': False,
        'strip_agent_commands': False,
        'strip_multi_agent': True,  # Still stripped for SLMs
        'max_skills': 40,
        'max_agents': 5,
        'include_rules': True,
    },
}
```

---

#### 1.4 Budget Packer

**Greedy knapsack algorithm:** Sort components by `score / compressed_tokens` ratio (value density), pack until budget exhausted.

```python
def pack_components(components: list[Component], budget: int) -> list[Component]:
    """Pack highest-value components into token budget."""
    # Fixed components always included (constitution, persona, language rules)
    fixed = [c for c in components if c.score >= 0.85]
    remaining_budget = budget - sum(c.tokens_compressed for c in fixed)

    # Sort remaining by value density
    dynamic = sorted(
        [c for c in components if c.score < 0.85],
        key=lambda c: c.score / max(c.tokens_compressed, 1),
        reverse=True
    )

    packed = list(fixed)
    for comp in dynamic:
        if comp.tokens_compressed <= remaining_budget:
            packed.append(comp)
            remaining_budget -= comp.tokens_compressed

    return packed
```

**Budget validation:** After packing, verify total tokens ≤ budget × 0.95 (5% safety margin for tokenizer estimation error).

**Constitution budget guard:** Before packing dynamic components, verify that fixed components (constitution + persona + language rules) fit within the budget. If `sum(fixed.tokens_compressed) > budget`, fail with: `"Constitution + safety rules alone exceed {budget} token budget. Minimum safe budget: {required}. Use --budget {required} or higher."` This prevents silent omission of safety-critical content.

---

#### 1.5 Emitter

**Output:** Single markdown file structured for maximum SLM comprehension.

```markdown
# AI Coding Assistant — System Instructions

## Safety Rules (MANDATORY)
[Compiled constitution — always first, highest attention position]

## Your Identity
[Compiled persona — who you are, what you focus on]

## Coding Standards
[Compiled language rules — active language only]

## Key Skills
[Top N skill summaries — compressed, actionable]

## Quality Checklist
[Compiled from Iron Laws + verification — bullet points only]
```

**Why this structure:**
- Safety first = maximum attention weight in transformer architecture
- Identity second = establishes persona before task instructions
- Standards = project-specific rules that shape code output
- Skills at end = reference material, lower attention needed

---

### Phase 2: Integration (week 2-3)

#### 2.1 Profile Integration

**manifest.json addition:**
```json
{
  "profiles": {
    "offline-slm": ["core"],
    "offline-slm-extended": ["core", "agents"]
  }
}
```

**Install behavior:**
```bash
ai-toolkit install --profile offline-slm

# What happens:
# 1. Standard install of core components
# 2. Runs compile_slm.py with auto-detected settings
# 3. Writes compiled output to ~/.ai-toolkit/compiled/
# 4. Generates integration instructions for detected local model tools
# 5. state.json records profile as "offline-slm"
```

**No hooks installed:** SLM providers (Ollama, LM Studio) don't support lifecycle hooks. The critical hook behavior (destructive command guard, path guard) is compiled into the system prompt text as rules.

---

#### 2.2 CLI Command

```bash
ai-toolkit compile-slm                              # auto-detect model, default budget
ai-toolkit compile-slm --budget 4096                 # explicit token budget
ai-toolkit compile-slm --budget 8192 --persona backend-lead  # persona + budget
ai-toolkit compile-slm --model-size 8b               # auto-select budget for 8B model
ai-toolkit compile-slm --model-size 32b              # auto-select budget for 32B model
ai-toolkit compile-slm --lang typescript,python       # include specific language rules
ai-toolkit compile-slm --output ./my-system-prompt.md # custom output path
ai-toolkit compile-slm --dry-run                     # show what would be included + token counts (table format below)

# --dry-run output format:
# Budget: 4096 tokens | Level: light | Persona: backend-lead
# ┌────────────────────────────┬──────────┬────────┬──────────┐
# │ Component                  │ Score    │ Tokens │ Included │
# ├────────────────────────────┼──────────┼────────┼──────────┤
# │ Constitution (Articles I-V)│ 1.00     │ 420    │ YES      │
# │ Persona: backend-lead      │ 0.90     │ 180    │ YES      │
# │ Rule: coding-style         │ 0.85     │ 310    │ YES      │
# │ Skill: /review             │ 0.68     │ 290    │ YES      │
# │ ...                        │ ...      │ ...    │ ...      │
# │ Skill: /deploy             │ 0.22     │ 350    │ NO (budget)│
# └────────────────────────────┴──────────┴────────┴──────────┘
# Total: 3,840 / 4,096 tokens (93.7% utilization)
ai-toolkit compile-slm --format ollama               # output as Ollama Modelfile SYSTEM block
ai-toolkit compile-slm --format json-string          # JSON-escaped string (for config files)
ai-toolkit compile-slm --format raw                  # plain markdown (default)
```

**Model size → budget mapping:**

Note: budget is about *effective instruction following capacity*, not context window. A 128K-context 8B model can *hold* 16K system prompt tokens, but cannot *follow* them reliably. Empirically, SLMs degrade when system prompt exceeds ~10-15% of their effective capacity.

```python
MODEL_BUDGETS = {
    '7b':  {'budget': 2048, 'level': 'ultra-light'},   # Llama 3.1 8B, Mistral 7B
    '8b':  {'budget': 2048, 'level': 'ultra-light'},
    '14b': {'budget': 4096, 'level': 'light'},          # Qwen 2.5 14B, Phi-3 14B
    '32b': {'budget': 8192, 'level': 'standard'},       # Qwen 2.5 32B, Mixtral 8x7B
    '70b': {'budget': 16384, 'level': 'extended'},      # Llama 3.1 70B
}
```

---

#### 2.3 Model Size Detection

**Auto-detect from Ollama:**
```python
def detect_model_size() -> str | None:
    """Detect running model size from Ollama API."""
    try:
        # curl http://localhost:11434/api/tags
        resp = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)
        data = json.loads(resp.read())
        models = data.get('models', [])
        if models:
            # Extract parameter count from model name: "llama3.1:8b" → "8b"
            latest = models[0]['name']
            match = re.search(r'(\d+)[bB]', latest)
            if match:
                return match.group(0).lower()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        pass
    return None
```

**Fallback:** If no model detected, use `14b` defaults (4K budget, light compression). User can override with `--model-size`.

---

### Phase 3: Polish (week 3-4)

#### 3.1 Integration Guides

Per-platform setup instructions generated by the compiler.

**Ollama:**
```bash
# 1. Compile system prompt
ai-toolkit compile-slm --format ollama --model-size 8b > Modelfile.ai-toolkit

# 2. Create custom model
ollama create my-coder -f Modelfile.ai-toolkit

# 3. Use
ollama run my-coder "implement the payment API"
```

**LM Studio:**
```
1. ai-toolkit compile-slm --model-size 14b
2. Open LM Studio → Chat → System Prompt
3. Paste contents of ~/.ai-toolkit/compiled/slm-system-prompt.md
```

**Aider:**
```bash
ai-toolkit compile-slm --output .aider.system-prompt.md --model-size 32b
aider --model ollama/qwen2.5-coder:32b --system-prompt-file .aider.system-prompt.md
```

**Continue.dev:**
```bash
# 1. Compile to a local file
ai-toolkit compile-slm --model-size 14b

# 2. In .continue/config.json, paste the compiled content into systemMessage
#    (Continue.dev does not support file references — content must be inline)
#    Use: ai-toolkit compile-slm --format json-string to get escaped output
```

---

#### 3.2 Compile Quality Validator

Post-compilation checks:

| Check | Severity | Description |
|-------|----------|-------------|
| Constitution present | FAIL | Articles I-V must be in output |
| Budget exceeded | FAIL | Token count > budget |
| Persona missing (when specified) | WARN | Persona definition not included |
| No language rules included | WARN | Project language not detected |
| Less than 3 skills included | WARN | Very minimal — may be too sparse |
| Output empty | FAIL | Compilation produced no content |

---

## 6. File Summary

| File | Action | LOC (est.) | Description |
|------|--------|------------|-------------|
| `scripts/compile_slm.py` | CREATE | ~500 | Main compiler — orchestrates pipeline: parse → score → compress → pack → emit. Contains `Component` dataclass, scorer, and budget packer |
| `scripts/slm_token_counter.py` | CREATE | ~50 | Token estimation (stdlib only) — `estimate_tokens()` function used by compiler and validator |
| `scripts/slm_compression.py` | CREATE | ~300 | Compression engine — strip/summarize functions per content type, compression level configs (`COMPRESSION_LEVELS` dict) |
| `scripts/slm_integration.py` | CREATE | ~150 | Platform-specific output formatters — Ollama Modelfile, JSON-escaped string, raw markdown, Aider-compatible |
| `bin/ai-toolkit.js` | EDIT | +10 | Register `compile-slm` command |
| `scripts/install.py` | EDIT | +30 | Handle `--profile offline-slm` |
| `manifest.json` | EDIT | +5 | Add offline-slm profile |
| `kb/reference/offline-slm-guide.md` | CREATE | ~200 | Integration guides for all platforms |
| `tests/test_compile_slm.bats` | CREATE | ~150 | Compilation tests |
| `tests/test_slm_budgets.bats` | CREATE | ~80 | Budget compliance tests |
| **Total** | | **~1575** | |

---

## 6a. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Compilation < 2 seconds. No network calls during compilation (all data local). |
| **Accuracy** | Token estimation ±10% vs tiktoken cl100k_base. Budget compliance: output ≤ budget × 0.95. |
| **Determinism** | Same input (agents, skills, rules, persona, language, budget) → identical output. No randomness. |
| **Security** | Constitution Articles I-V always present in output — compilation fails if they exceed budget alone. |
| **Offline** | Zero network dependencies. Ollama auto-detection gracefully fails to manual fallback. |
| **Portability** | Output is plain markdown — consumable by any tool accepting a system prompt string/file. |
| **Quality gates** | `ruff check scripts/compile_slm.py scripts/slm_*.py` (0 errors), `mypy --strict scripts/compile_slm.py scripts/slm_*.py` (0 errors). Run before every commit. |
| **Type safety** | 100% public API type hints (all function signatures). `Component` dataclass fully typed. Scoring functions use typed parameters, not bare `dict`. |

---

## 6b. Cache Invalidation & Recompile Triggers

Compiled output (`~/.ai-toolkit/compiled/slm-system-prompt.md`) is a **derived artifact** — it must be recompiled when inputs change:

| Trigger | Action |
|---------|--------|
| `ai-toolkit update` | Auto-recompile if profile is `offline-slm` |
| `ai-toolkit install --profile offline-slm` | Always compile |
| Agent/skill/rule files changed (detected via mtime) | Warn: "Compiled SLM prompt may be stale. Run `ai-toolkit compile-slm`" |
| Manual `ai-toolkit compile-slm` | Always recompile |

Compiled output includes a header comment: `<!-- Compiled: 2026-04-10T10:30:00Z | Budget: 4096 | Level: light | Persona: backend-lead -->` for staleness detection.

---

## 6b-bis. Rollback & Removal

The offline-slm feature is purely additive — removing it is trivial:
1. Delete `scripts/compile_slm.py`, `scripts/slm_token_counter.py`, `scripts/slm_compression.py`, `scripts/slm_integration.py`
2. Remove `"offline-slm"` and `"offline-slm-extended"` from `manifest.json` profiles
3. Remove `compile-slm` from `SCRIPT_COMMANDS` in `bin/ai-toolkit.js`
4. Delete `~/.ai-toolkit/compiled/` directory (user-side)
5. No hooks, no state files, no config entries to clean up

---

## 6c. Quality Gate Degradation Notice

**Important:** The `offline-slm` profile strips lifecycle hooks because SLM providers don't support them. This means:

- No pre-commit quality check (ruff/tsc/mypy)
- No destructive command interception (guard hooks)
- No session context preservation

Guard hook behavior is **compiled into the system prompt as text rules** — the SLM is *instructed* not to run destructive commands, but unlike hook-based enforcement, this is advisory, not blocking.

Documentation must clearly state: **"SLM mode trades enforcement for guidance. Safety rules are present but not machine-enforced."**

For teams needing enforcement, recommend `--profile offline-slm` combined with a Git pre-commit hook (`.git/hooks/pre-commit`) that runs lint/type-check independently of the AI tool.

---

## 7. Success Criteria (Overall)

| Metric | Target |
|--------|--------|
| Budget tiers | 4 (ultra-light 2K, light 4K, standard 8K, extended 16K) |
| Token budget compliance | 100% (output ≤ budget in all cases) |
| Constitution inclusion | 100% (always present, all 5 articles) |
| Compilation time | < 2 seconds |
| Model size auto-detection | Ollama API (with graceful fallback) |
| Output formats | 4 (raw markdown, Ollama Modelfile, JSON-escaped string, Aider-compatible) |
| Integration guides | 4 platforms (Ollama, LM Studio, Aider, Continue.dev) |
| Persona support | 4 personas (backend-lead, frontend-lead, devops-eng, junior-dev) |
| Language rule support | 13 languages (all existing rules) |
| External dependencies | 0 (stdlib Python only) |
| Tests | 40+ |

---

## 8. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Token estimation too inaccurate | Medium | Medium | Validate against tiktoken on 50 files, target ±10% |
| Compiled prompt too compressed — loses meaning | Medium | High | Validate with 8B model on 5 standard tasks; if quality drops, increase minimum budget |
| Ollama API changes | Low | Low | Graceful fallback to manual `--model-size` |
| User expects full toolkit features with SLM | Medium | Medium | Clear documentation: "SLM mode = safety + coding standards, not multi-agent orchestration" |
| Air-gapped environment can't run `ai-toolkit compile-slm` | Low | Medium | Pre-compile during `install` when network is available; compiled output is self-contained |
| Constitution text changes break compiled cache | Low | Low | Recompile on every `ai-toolkit update` |

---

## 9. Pre-Mortem

1. **"Compiled prompt is too generic"** — without the full agent definitions, the SLM may produce generic code that doesn't match project conventions. Mitigation: Language rules and persona have highest priority after constitution — they provide project-specific context.
2. **"Users expect /review to work with 8B model"** — Skill invocations won't be available via SLM providers that lack hook support. Mitigation: Compiled output includes skill *knowledge* as rules, not invocable commands. Clear docs: "Skills are compiled as coding standards, not slash commands."
3. **"Model detects wrong size"** — Ollama model naming is inconsistent (`llama3.1:8b` vs `codellama:7b-instruct`). Mitigation: regex extracts any `\d+[bB]` pattern; fallback to `14b` if ambiguous.
4. **"Other local inference tools emerge"** — Jan.ai, GPT4All, Tabby, etc. Mitigation: Raw markdown output works with any tool that accepts a system prompt file.
5. **"Nobody uses the feature"** — SLM adoption among professional developers may be niche. Mitigation: Low effort (3-4 weeks), high signaling value ("we support air-gapped environments"), enterprise sales enabler.

---

## 10. Market Positioning

**Target users:**
1. **Enterprise (air-gapped)** — financial services, defense, healthcare firms that cannot send code to cloud LLM APIs
2. **Privacy-conscious solo devs** — developers who don't want code leaving their machine
3. **Cost-sensitive teams** — startups that can't afford Anthropic/OpenAI API costs at scale
4. **Offline-first** — developers working on trains, planes, or in regions with poor connectivity

**Competitive advantage:** No existing AI coding toolkit provides a compilation pipeline that adapts its instruction set to model capacity. This is a first-mover feature.

---

## 11. Next Actions

1. [ ] Approve plan
2. [ ] Implement token counter (1.1)
3. [ ] Implement component parser + scorer (1.2)
4. [ ] Implement compression engine (1.3)
5. [ ] Implement budget packer + emitter (1.4, 1.5)
6. [ ] Integrate profile into install.py + manifest.json (2.1)
7. [ ] Create CLI command `compile-slm` (2.2)
8. [ ] Add Ollama model detection (2.3)
9. [ ] Add persona + language aware compilation (2.4, 2.5)
10. [ ] Write integration guides for 4 platforms (3.1)
11. [ ] Compile quality validator (3.2)
12. [ ] Tests + documentation (3.3, 3.4)

---

## 12. Future

| Feature | Rationale |
|---------|-----------|
| Automatic recompile on file changes (file watcher) | v1 uses manual recompile + staleness warning |
| Quality benchmarks (run 5 standard tasks, measure output quality per budget tier) | Validate compilation quality empirically before shipping |
| Plugin-aware compilation (include memory-pack prompts if installed) | Depends on plugin system maturity |
| Model-specific prompt templates (different SLM families prefer different instruction styles) | Needs empirical testing across model families |
| `--profile offline-slm --enforce-git-hooks` (install git pre-commit hook for quality gates) | Compensates for stripped lifecycle hooks |

---

## 13. Cross-Plan Dependencies

This plan shares modification targets with two other proposed plans:

| Shared File | This Plan | Enterprise Config Plan | Local Dashboard Plan |
|-------------|-----------|----------------------|---------------------|
| `scripts/install.py` | +30 LOC (offline-slm profile) | +80 LOC (extends resolution) | — |
| `manifest.json` | +5 LOC (offline-slm profile) | +10 LOC (schema refs) | — |
| `bin/ai-toolkit.js` | +10 LOC (compile-slm command) | +40 LOC (config subcommands) | +15 LOC (ui command) |

**If implementing in parallel:** this plan has the smallest changes to shared files — merge first to minimize conflicts.

**Enterprise Config interaction:** If Enterprise Config ships, `compile-slm` should respect the `extends` chain — compile the merged config, not just local. Add a `--ignore-extends` flag for air-gapped environments without access to the base config.

---

**Last Updated:** 2026-04-10
