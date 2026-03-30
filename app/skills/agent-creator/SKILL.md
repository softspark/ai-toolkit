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

- Match filename and `name` exactly using lowercase-hyphen format
- Keep the description trigger-rich and operational
- Give the agent a clear boundary: what it owns and what it should escalate
- Prefer specialized, narrow responsibility over generic “do everything” agents
- Reference only existing skills unless the task also includes creating the missing skill
- Avoid tool bloat; every extra tool increases risk and ambiguity

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

