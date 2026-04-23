---
name: agent-creator
description: "Creates new specialized agents with frontmatter, tool selection, and delegation guidance"
effort: high
disable-model-invocation: true
argument-hint: "[agent name or role]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Agent Creator

$ARGUMENTS

Create a new specialized agent following ai-toolkit conventions.

## Workflow

1. **Capture role** -- what problem space should the agent own?
2. **Define triggers** -- which keywords or task types should route to this agent?
3. **Choose tools** -- minimal tool set, least privilege first
4. **Choose model** -- `opus` for deep reasoning, `sonnet` for lighter pattern work
5. **Map supporting skills** -- which knowledge skills should the agent reference?
6. **Write instructions** -- capabilities, constraints, escalation rules, deliverables
7. **Validate** -- frontmatter, naming, skills references, tool whitelist

## Required Frontmatter

```yaml
---
name: agent-name
description: "When to use this agent. Triggers: keyword1, keyword2."
tools: Read, Write, Edit
model: sonnet
skills: skill-one, skill-two
---
```

## Authoring Rules

- **MUST** match filename and `name:` using lowercase-hyphen format — drift breaks routing
- **MUST** include an explicit `Triggers:` list in the description so the router can dispatch deterministically
- **NEVER** reference skills that do not exist — either create the dependency first or drop the reference
- **NEVER** grant write access to `.claude/agents/` — that authority belongs to `meta-architect` alone
- **CRITICAL**: avoid tool bloat. Every extra tool widens blast radius; start from `Read` and justify additions one by one
- Give the agent a clear boundary: what it owns and what it must escalate
- Prefer specialized, narrow responsibility over generic "do everything" agents

## Agent Skeleton

```markdown
---
name: {agent-name}
description: "When to use this agent. Triggers: keyword1, keyword2."
tools: Read, Edit
model: sonnet
skills: relevant-skill
---

You are a specialized agent for {domain}.

## Responsibilities
- Responsibility one
- Responsibility two

## Constraints
- Do not edit files outside owned scope unless required
- Escalate security, data-loss, or architecture risks

## Deliverables
- Clear findings
- Specific edits or recommendations
- Validation notes
```

## Validation Checklist

- [ ] Filename matches `name:` in frontmatter
- [ ] Description includes trigger words and use cases
- [ ] Tools are from the approved Claude Code tool set
- [ ] Referenced skills exist
- [ ] Model choice matches expected complexity
- [ ] `scripts/validate.py` passes after adding the agent

## Gotchas

- The `description` is the **only** content the model sees at routing time (progressive disclosure, tier 1). Adding triggers to the body without putting them in `description` means the agent is invisible to the router.
- `tools:` parser acceptance varies between Claude Code, ai-toolkit adapters, and downstream consumers — some accept comma-separated, some space-separated, some YAML lists. Stick to one style consistent with neighbouring agents in the repo and let `scripts/validate.py` catch drift.
- Agent `name` is capped at 64 chars; some consumers silently truncate longer names, which then **fail to match** the filename at load time. Keep names short and unambiguous.
- `skills:` can reference skills inside plugin packs; if the user has not enabled that pack, the agent fails on first invocation with an opaque "skill not found" error. Either reference only in-tree skills, or document the plugin prerequisite in the agent body.

## When NOT to Use

- For a **skill** (slash command or knowledge doc) — use `/skill-creator` instead
- For a **slash command** that is *not* an agent delegate — use `/command-creator`
- For a **plugin pack** bundling multiple agents and skills — use `/plugin-creator`
- To *modify* an existing agent — delegate to the `meta-architect` agent; this skill is create-only
- When the task is really a workflow (orchestrator + N specialists) — reach for `/orchestrate` or `/workflow` before minting a new agent

