---
title: "AI Toolkit - Config Benchmark"
category: reference
service: ai-toolkit
tags: [benchmark, config, comparison, coverage]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-03-29"
description: "Compare your installed ai-toolkit config vs toolkit defaults vs ecosystem competition."
---

# Config Benchmark

## Usage

```bash
ai-toolkit benchmark --my-config
```

## What It Shows

1. **Your Configuration** — counts of installed agents, skills, hooks in `~/.claude/`
2. **Toolkit Totals** — counts of available assets in the toolkit package
3. **Coverage** — percentage of toolkit assets you have installed
4. **Missing Components** — up to 10 agents and skills not yet installed
5. **Ecosystem Comparison** — your config vs public Claude Code ecosystem repos

## Output Example

```
AI Toolkit Config Benchmark
========================

## Your Configuration (~/.claude/)
  Agents:  44
  Skills:  80
  Hooks:   12

## Toolkit Totals
  Agents:  44
  Skills:  80
  Hooks:   12

## Coverage
  Agents:  100%  (44 / 44)
  Skills:  100%  (80 / 80)
  Hooks:   100%  (12 / 12)

## Ecosystem Comparison
Repo                                     Agents  Skills  Hooks
--------------------------------------------------------------
Your config                                  47      80     12
--------------------------------------------------------------
anthropics/claude-code                       15      10      5
affaan-m/everything-claude-code             152     397      2
```

## Data Sources

- User config: `~/.claude/agents/`, `~/.claude/skills/`, `~/.ai-toolkit/hooks/`
- Toolkit: `app/agents/`, `app/skills/`, `app/hooks/`
- Ecosystem: `benchmarks/ecosystem-dashboard.json`
