# Workflow

* Plan before implementing: tasks >1 hour need a plan, success criteria, and pre-mortem
* Research before acting: check existing code and documentation before proposing changes
* Use structured commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` (Conventional Commits)
* Prefer editing existing files over creating new ones to avoid file bloat
* Read-only exploration first, then targeted changes — never explore and write simultaneously
* Quality gates must pass before done: lint, type-check, tests green
* Cite sources when making decisions based on existing knowledge or documentation
* No destructive commands (`rm -rf`, `DROP TABLE`, `--force`) without explicit user confirmation
