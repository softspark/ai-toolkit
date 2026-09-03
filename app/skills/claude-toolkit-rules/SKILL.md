---
name: claude-toolkit-rules
description: "SoftSpark working agreement: never guess a home directory path, give at least three alternatives, and apply a devil's advocate critique to decisions. Triggers: toolkit, conventions, workflow, alternatives, review."
effort: low
user-invocable: false
allowed-tools: Read
---

# Claude Toolkit Rules

This rule comes from `app/rules/claude-toolkit-rules.md` in ai-toolkit. It applies to
every task in this workspace, not only when it is loaded.

# Claude Toolkit

Shared AI development toolkit — lifecycle hooks, safety constitution, multi-platform support.

## Skill Tiers

- **Tier 1** — single-agent: `/debug`, `/review`, `/refactor`, `/analyze`, `/docs`, `/plan`, `/explain`, `/tdd`, `/triage-issue`
- **Tier 1.5** — planning: `/write-a-prd` → `/prd-to-plan` → `/prd-to-issues`; design: `/design-an-interface`, `/architecture-audit`, `/refactor-plan`
- **Tier 2** — multi-agent: `/workflow <type>` (feature-development, backend-feature, frontend-feature, api-design, database-evolution, test-coverage, security-audit, debugging, incident-response, spike, codebase-onboarding, performance-optimization, infrastructure-change, application-deploy, proactive-troubleshooting)
- **Tier 3** — custom: `/orchestrate <desc>` (3–6 agents) | `/swarm <mode> <desc>` (map-reduce | consensus | relay)

## Path Safety
- NEVER guess or hallucinate user home directory paths
- Use `~` or `$HOME` instead of a hardcoded `/Users` or `/home` prefix followed
  by a user name. The literal prefix is deliberately not written out here: the
  plugin export scans shipped files for exactly that pattern, so an example of
  the mistake would be indistinguishable from the mistake.
- When an absolute path is needed, run `echo $HOME` first to get the correct value

## User Preferences

- **Style:** Direct & efficient. No pleasantries. Measurable results.
- **Methodology:** Provide >=3 alternatives. Use Socratic questioning.
- **Review:** Apply "Devil's Advocate" critique to decisions.
