---
title: "Claude Ecosystem Benchmark Snapshot"
category: reference
service: ai-toolkit
tags: [benchmark, ecosystem, claude-code, competitive-analysis, roadmap]
version: "1.0.0"
created: "2026-03-28"
last_updated: "2026-04-01"
description: "Repeatable benchmark snapshot of official Claude Code and selected external repositories used to guide ai-toolkit expansion decisions."
---

# Claude Ecosystem Benchmark Snapshot

## Purpose

This document records the external repositories that `ai-toolkit` uses as benchmark inputs for ecosystem expansion work. It complements the planning documents by turning the benchmark set into a stable, repeatable reference.

## Source Set

- `anthropics/claude-code`
- `affaan-m/everything-claude-code`
- `ChrisWiles/claude-code-showcase`
- `disler/claude-code-hooks-mastery`
- `codeaholicguy/ai-devkit`
- `alirezarezvani/claude-code-skill-factory`

## Snapshot (2026-03-28)

| Repository | Category | Why it matters |
|------------|----------|----------------|
| `anthropics/claude-code` | official | Canonical plugin layout, command development, hook development, feature workflows |
| `affaan-m/everything-claude-code` | ecosystem-scale | Scale benchmark for commands, agents, and packaging patterns |
| `ChrisWiles/claude-code-showcase` | practical-showcase | Strong examples of edit-time automation and branch safety hooks |
| `disler/claude-code-hooks-mastery` | hooks-reference | Strong reference for lifecycle breadth and operational hook patterns |
| `codeaholicguy/ai-devkit` | cross-tool | Cross-tool toolkit positioning benchmark |
| `alirezarezvani/claude-code-skill-factory` | meta-tooling | Creator workflow and factory-style inspiration |

## Operational Use

Use the benchmark script for a repeatable snapshot:

```bash
python3 scripts/benchmark_ecosystem.py --offline
python3 scripts/benchmark_ecosystem.py --format json
python3 scripts/benchmark_ecosystem.py --dashboard-json
python3 scripts/harvest_ecosystem.py --offline
python3 scripts/benchmark_ecosystem.py --out /tmp/claude-ecosystem-benchmark.md
```

The script prefers live GitHub metadata when available and falls back to the embedded snapshot when offline.

Machine-readable artifacts:

- `benchmarks/ecosystem-dashboard.json` — curated dashboard summary with freshness and comparison matrix
- `benchmarks/ecosystem-harvest.json` — latest harvested benchmark JSON for roadmap / changelog reuse

## Adoption Matrix

| Pattern | Current ai-toolkit State | Benchmark Signal | Priority |
|---------|--------------------------|------------------|----------|
| Plugin manifest | Present | Strong in official Claude Code | High |
| Hook creator workflow | Present | Reinforced by official plugin-dev assets | High |
| Command creator workflow | Present | Reinforced by command-development patterns | High |
| Agent creator workflow | Present | Reinforced by agent-development patterns | High |
| Lifecycle breadth (`PreCompact`) | Present | Validated by hooks-focused repos | High |
| Lifecycle breadth (`PostToolUse`) | Present | Strong benchmark signal | High |
| Lifecycle breadth (`UserPromptSubmit`) | Present | Prompt-governance benchmark signal | High |
| Lifecycle breadth (`SubagentStart` / `SubagentStop`) | Present | Strong subagent instrumentation signal | Medium |
| Lifecycle breadth (`SessionEnd`) | Present | Needed for handoff / cleanup patterns | Medium |
| Ecosystem benchmark script | Present | Needed for repeatable comparison | High |
| Harvesting script + dashboard JSON | Present | Repeatable evidence for roadmap and release notes | High |
| Domain plugin packs | Present (experimental) | Validates modular packaging direction | Medium |
| Policy packs | Not yet implemented | Strong but still optional | Later |

## Notes

- This snapshot is intentionally small and curated.
- The goal is decision quality, not ecosystem collection for its own sake.
- Large benchmark repositories are references, not implementation blueprints.

