# Contributing

We welcome bug fixes, new skills, agents, hooks, and improvements. This guide explains
how to contribute: workflow, branching, commits, and the checks your PR must pass.

## Workflow

1. **Fork** the repository and clone your fork
2. **Create a branch** from `main`: `git checkout -b feat/my-change`
3. **Make your changes** — follow the conventions below
4. **Run all checks** locally (see CI Requirements)
5. **Push** to your fork and open a **Pull Request** against `main`
6. The maintainer will review, request any needed corrections, and merge after the required checks pass

Update affected documentation in the same pull request as the behavior change. Keep README tables and badges, CHANGELOG, manifests, KB references, and generated integration instructions consistent. Run the applicable generators and `python3 scripts/validate.py --strict` before requesting review.

## Branch Naming

| Prefix | Use |
|--------|-----|
| `feat/` | New skill, agent, hook, or feature |
| `fix/` | Bug fix |
| `refactor/` | Code improvement without behavior change |
| `docs/` | Documentation-only change |
| `test/` | Test-only change |

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add search-specialist agent
fix: guard-destructive false positive on git rm
refactor: simplify install.py symlink logic
test: add bats tests for doctor command
```

- One logical change per commit
- Keep the subject line under 72 characters
- No `WIP` commits in the final PR

## CI Requirements

Your PR must pass **all** CI jobs before review. Run them locally:

```bash
# All of these must pass with zero errors:
npm test                                # Test suite (bats tests/)
python3 scripts/validate.py --strict    # Toolkit integrity + count drift
python3 scripts/audit_skills.py --ci    # Security audit (0 HIGH findings)
python3 scripts/evaluate_skills.py      # Skill evaluation
```

Python logic in `scripts/` is unit-tested with pytest and gated by ruff and
mypy. These are repository dev tools only (`requirements-dev.txt`); the
published package and user machines stay stdlib-only, so install them in a
local venv, never into the system interpreter:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
npm run test:py        # pytest tests/python
npm run lint:py        # ruff E,F (rule set is the package.json script)
npm run typecheck:py   # mypy --strict over the allowlist in mypy.ini
```

New tests for Python modules go to `tests/python/`; bats remains for hooks,
CLI surfaces, and anything observed from a shell.

If you touched any hook script, also run ShellCheck yourself. CI and the publish
workflow run it, but `validate.py` and `npm test` do not:

```bash
shellcheck --severity=warning app/hooks/*.sh
```

Additionally, CI runs:
- **ShellCheck** on all hook scripts (`app/hooks/*.sh`)
- **Python syntax check** on all scripts
- **Required files check** (LICENSE, CHANGELOG, SECURITY, etc.)

## What to Contribute

**Good first contributions:**
- Bug fixes with a reproducing test
- New skills (use `ai-toolkit create skill <name>`)
- New agents (follow existing patterns in `app/agents/`)
- Hook improvements
- Language rules (`app/rules/<language>/`)

**Please open an issue first for:**
- New plugin packs
- Changes to the constitution
- Breaking changes to the install/update flow
- Changes to CI/CD workflows

## Coding Standards

- **Python runtime scripts:** standard library only; network access and subprocess execution must be explicit, bounded, and tested. Keep development dependencies in the local virtual environment.
- **Bash hooks:** ShellCheck clean, fast execution (hooks run on every tool call)
- **Skills:** follow the SKILL.md frontmatter schema in existing skills
- **Agents:** follow the agent `.md` schema in `app/agents/`
- **Tests:** add bats tests for new CLI commands and hooks

## Security

- No secrets, API keys, or tokens in code
- No `eval()`, `exec()`, or `subprocess(shell=True)` without justification
- No `curl | bash` patterns in hooks
- Review the [Security Policy](../SECURITY.md) for scope

## Bug Reports and Feature Requests

- **Bugs:** use the [Bug Report](../../issues/new?template=bug_report.md) template
- **Features:** open an issue with the `enhancement` label
- **Security vulnerabilities:** email `biuro@softspark.eu` (do not open a public issue)
