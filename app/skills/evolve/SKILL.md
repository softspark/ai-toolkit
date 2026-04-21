---
name: evolve
description: "Analyzes failure patterns and inefficiencies in agent/skill definitions, then drafts and applies targeted improvements to system prompts, tool permissions, and behavioral rules. Use when the user asks to improve agent behavior, refine skill definitions, update system prompts, or optimize agent configurations based on observed failures."
effort: medium
disable-model-invocation: true
context: fork
agent: meta-architect
allowed-tools: Read, Edit, Grep, Glob
---

# Evolve Command

$ARGUMENTS

Triggers the Meta-Architect to improve agent and skill definitions based on observed patterns.

## Usage

```bash
/evolve [source]
# /evolve learnings        — analyze kb/learnings/ for recurring failure patterns
# /evolve last-failure     — analyze the most recent error log
# /evolve agents           — audit all agent definitions for gaps
```

## Protocol

### 1. Analyze

Read the input source and extract actionable patterns:

- **learnings**: grep `kb/learnings/` for entries tagged `failure`, `retry`, `timeout`, or `inefficiency`
- **last-failure**: read the most recent file in `kb/learnings/` and identify root cause
- **agents**: scan all `.md` files in `app/agents/` for missing tools, vague prompts, or mismatched model tiers

### 2. Design

Draft changes targeting the identified patterns:

| Target | File Location | Change Type |
|--------|--------------|-------------|
| Agent definitions | `app/agents/*.md` | Frontmatter (tools, model), system prompt text |
| Skill definitions | `app/skills/*/SKILL.md` | Description, workflow steps, allowed-tools |
| Rules | `app/rules/` | New or updated rule files |

Show the proposed diff to the user before applying.

### 3. Implement

Apply approved changes. After each edit:

- Run `python3 scripts/validate.py` to confirm structural integrity
- Verify YAML frontmatter parses without errors
- Confirm no forbidden patterns (eval, exec, shell=True)

### 4. Report

Create a summary documenting what evolved:

```markdown
## Evolution Report
- **Source**: [learnings | last-failure | agents]
- **Pattern found**: [description of failure/inefficiency]
- **Changes applied**:
  - `app/agents/[name].md` — [what changed and why]
- **Validation**: passed / failed
```
