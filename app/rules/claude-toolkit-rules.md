# Claude Toolkit

Shared AI development toolkit — 87 skills, 47 agents, lifecycle hooks, safety constitution.

## Skill Tiers

- **Tier 1** — single-agent: `/debug`, `/review`, `/refactor`, `/analyze`, `/docs`, `/plan`, `/explain`, `/tdd`, `/triage-issue`
- **Tier 1.5** — planning: `/write-a-prd` → `/prd-to-plan` → `/prd-to-issues`; design: `/design-an-interface`, `/architecture-audit`, `/refactor-plan`
- **Tier 2** — multi-agent: `/workflow <type>` (feature-development, backend-feature, frontend-feature, api-design, database-evolution, test-coverage, security-audit, debugging, incident-response, spike, codebase-onboarding, performance-optimization, infrastructure-change, application-deploy, proactive-troubleshooting)
- **Tier 3** — custom: `/orchestrate <desc>` (3–6 agents) | `/swarm <mode> <desc>` (map-reduce | consensus | relay)

## Path Safety
- NEVER guess or hallucinate user home directory paths
- Use `~` or `$HOME` instead of hardcoded `/Users/<username>/` or `/home/<username>/`
- When an absolute path is needed, run `echo $HOME` first to get the correct value

## User Preferences

- **Style:** Direct & efficient. No pleasantries. Measurable results.
- **Methodology:** Provide >=3 alternatives. Use Socratic questioning.
- **Review:** Apply "Devil's Advocate" critique to decisions.
