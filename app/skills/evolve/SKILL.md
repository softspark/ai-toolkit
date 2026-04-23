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
# /evolve learnings        : analyze kb/learnings/ for recurring failure patterns
# /evolve last-failure     : analyze the most recent error log
# /evolve agents           : audit all agent definitions for gaps
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
  - `app/agents/[name].md`: [what changed and why]
- **Validation**: passed / failed
```

## Rules

- **MUST** delegate file edits to the `meta-architect` agent — this command is the trigger, the agent owns the changes
- **MUST** have a concrete failure signal (recurring error, named incident, repeated correction) before evolving — do not mutate based on vibes
- **NEVER** evolve an agent based on a **single** failure instance — evolution is pattern-matching, not reaction
- **NEVER** touch `.claude/agents/*` files directly from this skill; `meta-architect` is the only agent with that authority
- **CRITICAL**: every evolution names the trigger, the change, and the expected measurable shift (e.g., "reduces false routing of `/debug` to `/fix`")
- **MANDATORY**: run `scripts/validate.py --strict` after every applied change; roll back if the score drops

## Gotchas

- Small changes to an agent's description can silently re-route a dozen adjacent queries. After an evolution, run the skill router against a saved set of representative queries to confirm no drift.
- `kb/learnings/` entries without a `status: final` frontmatter field are often drafts — aggregating them treats speculative observations as validated patterns. Filter by status before mining.
- "Last-failure" often points at the **symptom**, not the root cause. A route-to-wrong-agent failure may actually be a description-field ambiguity; fix the description, not the router.
- Changes to agent frontmatter fields (`tools`, `model`) propagate to the installed global config only after `ai-toolkit update`. A locally-evolved agent still runs old behavior until the user reinstalls.
- Evolution in isolation invites regression. Keep a changelog (`kb/learnings/` entries or `CHANGELOG.md`) so future sessions can see what was tried and reverted.

## When NOT to Use

- For a specific, known agent edit — call `meta-architect` directly
- For fixing a failing test — use `/fix` or `/debug`
- For auditing **current** skill/agent quality — use `scripts/evaluate_skills.py` and `scripts/audit_skills.py --ci`
- For creating a **new** agent — use `/agent-creator`
- When no recurring pattern exists (single data point) — wait and observe; do not over-fit to noise
