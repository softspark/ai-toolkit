---
name: ai-toolkit-rules
description: "Mandatory engineering, security, testing, git, performance, quality, and response rules. Claude MUST load this skill for every technical, coding, debugging, review, architecture, DevOps, data, or file-editing task in Chat or Cowork."
user-invocable: true
---

# AI Toolkit Rules

Apply every relevant rule below before acting. Treat MUST/NEVER language as mandatory.

## Source: `app/rules/claude-toolkit-rules.md`

# Claude Toolkit

Shared AI development toolkit — lifecycle hooks, safety constitution, multi-platform support.

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

## Source: `app/rules/git-conventions.md`

# Git Conventions

- Do NOT add `Co-Authored-By: Claude` or any AI co-authorship to commits
- Do NOT add Claude signatures or attribution to commit messages
- Conventional commits format: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Source: `app/rules/output-mode.md`

# Output Mode

`output-mode: concise`

Default response mode for this project is **concise**. The `brand-voice` skill (when present in ai-toolkit) auto-loads its `concise` rules; assistants without that skill should still apply the directives below.

## Concise Mode Directives

- **No preamble.** Skip "I'll now...", "Sure, let me...", "Great question!" and similar warm-ups. Start with the answer.
- **Lead with the result.** Conclusion or output first; explanation only if asked or non-obvious.
- **Max 3 sentences per closed question.** Yes/no, single-fact, or "where is X" answers stay under three sentences.
- **Tables and lists over prose** when comparing options, listing steps, or showing values.
- **No trailing summaries.** If the diff or output already shows what changed, do not restate it.
- **Drop filler adjectives.** No "nice", "great", "powerful", "robust" unless the user asked for evaluation.
- **Cite file paths as `path:line`** instead of paragraphs describing where things live.
- **Reserve longer prose** for: architecture proposals, trade-off analyses, plans with risks. Everything else: terse.

## When to escalate to verbose

- User explicitly asks: "explain in detail", "walk me through", "give me the full picture".
- Reporting a non-obvious failure mode where missing context would mislead.
- Architecture / RFC / ADR / trade-off documents — those have their own structure.

## How to override

- Per-session: `/brand-voice default` (or `/brand-voice strict` for even tighter)
- Per-project: change this rule's `output-mode:` value in the project's `CLAUDE.md`
- Permanent removal: re-run `ai-toolkit install --skip rules` or strip the `<!-- TOOLKIT:output-mode -->` block manually

## Source: `app/rules/quality-gates.md`

# Quality Gates & Mandatory Practices

## MANDATORY PRACTICES
1.  **Plan First:** Tasks >1h require Plan, Success Criteria, and Pre-Mortem.
2.  **Quality Gates:**
    *   `ruff check .` (0 errors)
    *   `mypy --strict src/` (0 errors)
    *   `pytest --cov=src` (>70% coverage)
    *   **Type Safety:** 100% public APIs, >60% internal.
3.  **Security:** No secrets in code, sanitization, auth z/n.

## Source: `app/rules/common/coding-style.md`

# Universal Coding Style

## Principles
- KISS: simplest solution that works. Clever code is a liability. If 200 lines could be 50, rewrite.
- DRY: extract when you repeat 3+ times, not before.
- YAGNI: do not build features "just in case." No abstractions for single-use code.
- Prefer immutability: use `const`, `final`, `val`, `let` by default.
- Fail fast: validate inputs at boundaries, return early on errors.
- State assumptions before coding. If uncertain or multiple interpretations exist, ask — don't pick silently.

## Naming
- Use descriptive names that reveal intent (`remainingRetries`, not `r`).
- Boolean variables/functions: prefix with `is`, `has`, `can`, `should`.
- Functions: verb + noun (`fetchUser`, `calculateTotal`, `validateInput`).
- Avoid abbreviations unless universally understood (`id`, `url`, `http`).
- Collections use plural nouns (`users`, `orderItems`).

## Functions
- Max 20-30 lines per function. If longer, extract.
- Max 3 parameters. Beyond that, use an options/config object.
- Single responsibility: one function does one thing.
- Pure functions preferred: same input, same output, no side effects.
- Avoid boolean parameters: use separate functions or enums.

## File Organization
- One primary concept per file (class, module, component).
- Group imports: stdlib, external, internal, relative.
- Constants at top, public API before private helpers.
- Keep files under 300 lines. Split when they grow.

## Comments
- Code should be self-documenting. Comment *why*, not *what*.
- Delete commented-out code. That is what version control is for.
- Use TODO/FIXME with ticket references: `// TODO(PROJ-123): migrate to v2`.
- Document public APIs with doc comments (JSDoc, docstrings, etc.).

## Formatting
- Use project formatter (Prettier, Black, gofmt, rustfmt). No manual formatting debates.
- Consistent indentation: follow project convention (spaces vs tabs, width).
- Max line length: 80-120 characters depending on language convention.
- Trailing commas in multi-line structures (where language supports).

## Surgical Changes
- Touch only what the task requires. Every changed line should trace to the request.
- Match existing style, even if you would do it differently.
- Do not "improve" adjacent code, comments, or formatting unprompted.
- Orphan cleanup: remove imports/variables/functions that YOUR changes made unused.

## No Dead Code (Constitution Art. VI.1)
- When a refactor leaves a file, class, function, import, l10n key, or variable unused, DELETE it in the same change. Verify via grep that zero references remain in the repo.
- This applies to pre-existing code too, if your work makes its unusedness verifiable. "Legacy", "separate refactor", "out of scope", or "świadome pominięcie" are NOT valid excuses.
- Before claiming the task done: grep for every symbol you removed or renamed; fix orphaned references.

## Fix Every Found Bug (Constitution Art. VI.2)
- A bug, missing test for changed behavior, or stale doc discovered while working on a task MUST be fixed in the same change — not deferred to "second step", "separate PR", or "świadome pominięcie".
- When behavior changes, update integration AND unit tests AND the affected docs alongside. A unit test on a new helper is not sufficient when the behavior is exposed over an API — add the integration test too.
- Legitimate deferral exists ONLY when: (a) the fix requires a user decision — in that case, surface it explicitly and ask, don't bury in a summary; or (b) the issue is genuinely unrelated to the current change surface.
- Before marking done: re-read the diff and confirm no orphaned references, no missing test coverage for changed paths, no stale docs. If any are present, keep working.

## Goal-Driven Execution
- Transform vague tasks into verifiable goals before starting.
- For multi-step work, state a brief plan with verification per step:
  `1. [Step] → verify: [check]`
- Strong success criteria enable independent looping. Weak criteria ("make it work") require clarification — ask first.

## JSON Wire Format Conventions
- Field names (keys): `camelCase`. Aligns with JSON:API spec, Google JSON Style Guide, and framework defaults (Symfony Serializer, Spring Jackson, `json_serializable` for Dart). No public major API uses `snake_case` keys in modern designs except ecosystem-bound cases (Rails/Django APIs defaulting to ecosystem convention).
- Enum / status / permission / domain values: `UPPER_SNAKE_CASE`. Community consensus: [Protocol Buffers style guide](https://protobuf.dev/programming-guides/style/) (mandatory), [Google AIP-126 / api-linter](https://linter.aip.dev/126/upper-snake-values) (enforced), [Zalando Rule #240](https://opensource.zalando.com/restful-api-guidelines/), Java/Kotlin/C++/Python enum convention. `lowercase snake_case` (Stripe-style) is a legitimate outlier but not consensus.
- Avoid `camelCase` for enum values — no major public API uses it, loses visual distinction between keys and values.
- Pick one convention per project and enforce it with a CI grep gate. Mixing conventions inside a single API surface is the worst outcome.
- External contracts (Stripe, GitHub, webhooks you receive) follow their own convention — map to your project convention at the adapter boundary, do not leak their keys past it.

## Anti-Patterns to Avoid
- God classes/modules with 500+ lines and multiple responsibilities.
- Deep nesting (>3 levels): use early returns and extract functions.
- Magic numbers/strings: use named constants.
- Mutable global state: use dependency injection instead.

## Source: `app/rules/common/git-workflow.md`

# Git Workflow Rules

## Commit Messages
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- First line: imperative mood, max 72 chars (`feat: add user registration endpoint`).
- Body (optional): explain *why*, not *what*. The diff shows what.
- Reference tickets: `fix: prevent duplicate orders (PROJ-456)`.

## Commit Practices
- Commit small, atomic changes. One commit = one logical change.
- Never commit: secrets, `.env` files, build artifacts, large binaries.
- Never commit broken code to `main`. Use feature branches.
- Squash fixup commits before merging to keep history clean.

## Branching
- `main` is always deployable. Protect it with required reviews and CI.
- Feature branches: `feat/user-registration`, `fix/order-total-calc`.
- Delete branches after merge. Stale branches are clutter.
- Rebase feature branches on main before PR to keep linear history.

## Pull Requests
- Keep PRs small: <400 lines changed. Split large features into stacked PRs.
- PR title follows conventional commit format.
- Include: summary, test plan, and screenshots/recordings for UI changes.
- Require at least one approval before merge.

## Code Review
- Review for: correctness, security, performance, readability.
- Approve with comments if nits only. Block for: bugs, security, missing tests.
- Respond to reviews within 24 hours. Do not let PRs rot.

## Tags and Releases
- Use semantic versioning: MAJOR.MINOR.PATCH.
- Tag releases: `git tag v1.2.3`. Automate changelog from commits.

## Recovery
- Use `git stash` for WIP, not unfinished commits.
- Prefer `git revert` over `git reset --hard` on shared branches.
- Never force-push to `main` or shared branches.

## Source: `app/rules/common/performance.md`

# Universal Performance Rules

## Mindset
- Profile before optimizing. Measure, do not guess.
- Premature optimization is the root of all evil. Ship correct first, fast second.
- Set performance budgets and test against them in CI.

## Database
- Fix N+1 queries: use JOINs, eager loading, or batch fetching.
- Add indexes for columns used in WHERE, ORDER BY, and JOIN clauses.
- Use EXPLAIN/ANALYZE to verify query plans. Avoid full table scans.
- Paginate all list endpoints. Never return unbounded result sets.
- Use connection pooling. Never open a new connection per request.

## Caching
- Cache at the right layer: CDN > reverse proxy > application > database.
- Set explicit TTLs. Stale cache is worse than no cache.
- Cache immutable or slowly-changing data. Avoid caching user-specific mutable data.
- Use cache-aside pattern: check cache, fetch on miss, populate cache.
- Include cache invalidation strategy before adding any cache.

## I/O and Network
- Async/non-blocking for I/O-bound work. Thread pools for CPU-bound work.
- Batch operations where possible: bulk inserts, batch API calls.
- Set timeouts on all external calls: HTTP, database, message queues.
- Use streaming for large payloads instead of loading everything into memory.

## Memory
- Preallocate collections when size is known.
- Use streaming/iterators for large datasets instead of loading all into memory.
- Watch for memory leaks: unclosed connections, growing caches, event listener accumulation.
- Avoid unnecessary copies/clones of large data structures.

## API Performance
- Compress responses (gzip/brotli). Return only requested fields.
- Use HTTP/2 or HTTP/3 where supported.
- Implement request deduplication for identical concurrent requests.
- Return 202 Accepted for long-running operations, process async.

## Monitoring
- Track p50, p95, p99 latencies, not just averages.
- Alert on latency regressions, not just errors.
- Log slow queries (>100ms) and slow endpoints (>500ms).

## Source: `app/rules/common/security.md`

# Universal Security Rules

## Input Validation
- Validate ALL input at API boundaries. Trust nothing from clients.
- Use allowlists over denylists: define what IS valid, reject everything else.
- Validate type, length, format, and range for every input field.
- Sanitize output for the target context (HTML, SQL, shell, URL).

## Authentication
- Hash passwords with bcrypt, scrypt, or argon2. Never MD5/SHA for passwords.
- Use constant-time comparison for tokens and secrets.
- Implement rate limiting on auth endpoints (login, register, password reset).
- Enforce MFA for admin and sensitive operations.

## Authorization
- Check permissions on every request, not just at the UI level.
- Use principle of least privilege: default deny, explicitly grant.
- Validate resource ownership: user can only access their own data.
- Never rely on client-side authorization checks.

## Secrets Management
- Never hardcode secrets in source code. Use environment variables or vaults.
- Rotate secrets regularly. Automate rotation where possible.
- Use different secrets per environment (dev/staging/prod).
- Add `.env` to `.gitignore`. Use `.env.example` as a template.

## SQL Injection Prevention
- Always use parameterized queries or ORM query builders.
- Never concatenate user input into SQL strings.
- Validate and cast types before using in queries.

## XSS Prevention
- Escape all dynamic content rendered in HTML.
- Use Content Security Policy (CSP) headers.
- Set `HttpOnly` and `Secure` flags on authentication cookies.
- Avoid `innerHTML`, `eval()`, and `dangerouslySetInnerHTML`.

## API Security
- Use HTTPS everywhere. No exceptions.
- Implement rate limiting and request throttling.
- Set CORS headers explicitly. Never use `*` in production.
- Return generic error messages to clients. Log details server-side.
- Use security headers: HSTS, X-Content-Type-Options, X-Frame-Options.

## Dependencies
- Audit dependencies regularly (`npm audit`, `pip-audit`, `cargo audit`).
- Pin dependency versions. Use lockfiles.
- Remove unused dependencies. Each dependency is an attack surface.

## Logging
- Never log passwords, tokens, credit cards, or PII.
- Log security events: failed logins, permission denials, input validation failures.
- Use structured logging with correlation IDs for traceability.

## Source: `app/rules/common/testing.md`

# Universal Testing Rules

## Test Structure
- Use Arrange-Act-Assert (AAA) pattern in every test.
- One logical assertion per test. Multiple `assert` calls are fine if testing one behavior.
- Test names describe behavior: `test_returns_404_when_user_not_found`.
- Keep tests independent: no shared mutable state between tests.

## Test Organization
- Mirror source structure: `src/auth/login.ts` -> `tests/auth/login.test.ts`.
- Separate unit, integration, and e2e tests into distinct directories or markers.
- Shared fixtures go in `conftest.py`, `test-utils.ts`, or equivalent.

## What to Test
- Test behavior, not implementation. Tests should survive refactors.
- Cover: happy path, error cases, edge cases, boundary values.
- New code: 100% coverage. Overall project: >70%.
- Critical paths (auth, payments, data mutations): always tested.

## What NOT to Test
- Framework internals (ORM save, HTTP library send).
- Trivial getters/setters with no logic.
- Third-party library correctness.
- Private methods directly: test through public API.

## Mocking
- Mock at boundaries: HTTP clients, databases, file systems, clocks.
- Prefer fakes over mocks when logic is complex.
- Never mock the thing you are testing.
- Reset mocks between tests to prevent leakage.

## Test Quality
- Tests must be deterministic: no flaky tests allowed.
- Tests must be fast: unit tests <100ms each, test suite <60s.
- Avoid `sleep` in tests: use polling, events, or test clocks.
- Do not test implementation details (private methods, internal state).

## Coverage
- Measure coverage but do not chase 100%: focus on critical paths.
- Coverage gaps in error handling and edge cases are worse than gaps in happy paths.
- New PRs must not decrease overall coverage.

## Test Data
- Use factories/builders to create test data, not raw constructors.
- Keep test data minimal: only set fields relevant to the test.
- Do not share mutable test data across tests.
- Use realistic but not real data (no production data in tests).
