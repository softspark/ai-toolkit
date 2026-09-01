# Changelog

All notable changes to `ai-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## v4.30.0 - Managed DSH and plugin-owned MCP (2026-09-01)

### Added

- **Explicit DSH project target.** Added `install --local --editors dsh` for the
  managed `.agents/skills` surface without implicit selection or `$DSH_HOME`
  mutation.
- **Managed DSH profile lifecycle.** Added `ai-toolkit dsh
  install|update|doctor|uninstall --profile web` with exact DSH `0.1.1-rc.2`,
  dsh-codex `1.0.0`, dsh-orchestrator `1.0.1`, preset ownership, dry-run, and
  read-only diagnostics.
- **Plugin-owned MCP and native rules.** Plugin packs can deliver MCP templates
  and owned rule surfaces to Claude, Codex, Cursor, and Gemini.
- **RAG MCP templates.** Added `rag-mcp` and `rag-mcp-legal` with concrete
  localhost defaults and unauthenticated-endpoint warnings. The built-in MCP
  catalogue now contains 28 templates.

### Changed

- **DSH remains explicit-only.** It stays outside editor defaults,
  auto-detection, and `--editors all`; vendor CLIs retain authentication
  ownership and no provider API key is accepted.
- **Plugin lifecycle is transactional.** Install, update, and removal coordinate
  MCP settings, rules, hook/script assets, and ownership state with pinned-path
  CAS and last-consumer cleanup.
- **Test count.** Increased from 1675 to 1920.

### Fixed

- **Cold DSH installs fail safely.** Added pnpm preflight, bounded probe and
  mutation timeouts, full process-tree termination, exact executable identity,
  directory-level lifecycle locking, and durable recovery gates.
- **Concurrent plugin edits are preserved.** Atomic quarantine and rollback no
  longer overwrite concurrent bytes, modes, inodes, marker sections, or
  user-added assets.

---

## v4.29.2 — The Codex dry-run stops hiding a surface (2026-08-21)

### Fixed

- **`install --dry-run` never mentioned the Codex hook surfaces.** Selecting
  `codex` runs `gen_codex_hooks()` unconditionally, at every profile, writing
  `.codex/hooks.json` and the hook scripts under `.codex/hooks/` (23 files). The
  dry-run branch in `scripts/install_steps/ai_tools.py` printed only
  `.codex/agents/` and `.agents/skills/`. A preview that omits a whole surface is
  worse than no preview, and this is the surface a user is asked to review and
  trust with `/hooks` before Codex will run any of it.
- **The global preview named the manifest but not its scripts.** It listed
  `$CODEX_HOME/hooks.json` and stopped there, leaving out
  `$CODEX_HOME/ai-toolkit-hooks/`. Same defect, other branch.

### Added

- Four tests in `tests/test_install_profiles.bats`: the preview names both hook
  paths, it names them at `minimal`/`standard`/`full` alike, the preview matches
  what a live install then writes to disk, and `--dry-run` still writes nothing.
  All four fail against v4.29.1.

### Changed

- Test count: 1671 → 1675.

**Found by:** running the Release Verification SOP against the published
v4.29.1. Phase 9.1 checks dry-run output for each native surface, and the Codex
hook lines were missing — so that SOP check would have produced a false negative
on a build where the surface really was gone.

---

## v4.29.1 — The guard stops blocking the safe branch delete (2026-08-21)

### Fixed

- **`guard-destructive.sh` no longer folds `-d` onto `-D`.** Every pattern was
  matched by a single `grep -qEi`, so the `git\s+branch\s+-D\b` pattern also
  caught `git branch -d`. Those are different operations: `-D` discards an
  unmerged branch, `-d` refuses to. The safe one is what
  `.claude/rules/ai-toolkit-git-workflow.md` tells users to run after every
  merge, and the guard blocked it — a false positive on the toolkit's own
  advice, in the toolkit's own safety hook.
- **Patterns are matched in two passes, split by whether case carries meaning.**
  Command names and flags go through a case-sensitive `grep -qE`; POSIX flags
  that differ only in case are different flags, and folding them together can
  only lose information. SQL keywords and the Windows `format` command go
  through a case-insensitive `grep -qEi`, because their casing genuinely varies
  in the wild — `drop table`, `Truncate`, and `delete from` all still block.
  The `-i` was presumably there for the SQL patterns all along; it was the
  flag patterns that paid for it.

- **A cross-file race in the test suite.** `doctor --fix regenerates missing
  llms-full.txt` deleted the artifact from the shared checkout and asserted on
  doctor's `FIXED` line. `npm test` runs `bats --jobs 4
  --no-parallelize-within-files`, so files run concurrently, and
  `test_doctor_plugin_double_load.bats` also runs `doctor --fix` — which
  regenerates that artifact. When it won, the assertion saw a present file, no
  `FIXED` line, and a red suite; the test also left a `llms-full.txt.test-bak`
  in the repo, because the restoring `mv` never ran. v4.29.0 added a second
  `doctor --fix` call to the plugin test file, which is what made a latent race
  start firing. The test now runs doctor against a private copy of the toolkit,
  so it mutates no shared state at all.

### Changed

- `kb/reference/hooks-catalog.md` documents the two-pass matching and lists the
  safe branch delete among the guard's exemptions.
- Test count: 1666 → 1671. The new cases pin both directions: the safe delete
  and an uppercase non-flag pass, lowercase and mixed-case SQL block.

### Known gap (not addressed here)

- The guard matches `git branch -D` but not its long form, `git branch --delete
  --force`. That gap predates this fix and closing it is a coverage change
  rather than a case-sensitivity one, so it is left for a separate decision.

---

## v4.29.0 — Stale plugin uploads stop hiding (2026-08-21)

### Added

- **`doctor` reports Claude app plugin version drift.** Check 11 now compares the
  `version` recorded for every `ai-toolkit@…` entry in
  `~/.claude/plugins/installed_plugins.json` against the installed toolkit's
  `package.json` and warns when they differ. The upload is a point-in-time ZIP:
  once the toolkit moves on, Chat and Cowork keep running the skills, agents,
  hooks, and rules from whenever the export was made, with no signal anywhere
  that they are behind. `--fix` deliberately cannot clear this warning — the
  export can be regenerated but the upload itself happens by hand in the app's
  Customize > Plugins panel, so the check names the two steps instead of
  pretending to do them.

### Changed

- **Version drift is checked before the enabled/disabled branch.** A plugin
  disabled for Claude Code still feeds Chat and Cowork, which have no other
  channel for toolkit content. The old flow returned `OK: registered but
  disabled` and never looked at versions, so the state a user reaches by running
  `doctor --fix` was also the state where a stale upload passed silently. That
  was the wrong place to stop looking.
- **`ai-toolkit install` re-asserts the plugin as disabled for Claude Code.**
  Uploading the ZIP re-enables the plugin every time, which put the double-load
  fix back on whoever remembered to run `doctor --fix` afterwards. Global
  installs and updates now flip enabled toolkit plugins to `false` in
  `~/.claude/settings.json` and print each key they touched. `--local` and
  `--dry-run` are untouched, and non-toolkit plugins are never modified. The
  disable logic moved into `disable_toolkit_plugins_for_claude_code()` in
  `scripts/doctor.py`, shared by both call sites.
- Test count: 1659 → 1666.
- Skill body budget threshold unchanged. The largest body (`medplum-rules`, 16760
  bytes) sits 1240 bytes under the 18000-byte warn line, short of the 2000-byte
  margin the ratchet requires, so the threshold stays where it is this release.

---

## v4.28.0 — MCP servers reach Chat and Cowork (2026-08-21)

### Added

- **`claude-app` MCP adapter.** `ai-toolkit mcp install --editor claude-app
  --scope global <template>` writes `claude_desktop_config.json` — macOS
  `~/Library/Application Support/Claude/`, Windows `%APPDATA%/Claude/`, Linux
  `~/.config/Claude/`, with `CLAUDE_USER_DATA_DIR` overriding the root the same
  way the app itself honors it. Until now the Claude app was reachable only
  through an uploaded plugin ZIP, so a user with seven MCP servers configured for
  Claude Code still had an empty `mcpServers` block in Chat and Cowork. The app
  parses this file on startup and reports invalid entries in its own warning
  dialog, so it was always a supported surface — ai-toolkit just never wrote to
  it. Note that `--editor claude` targets Claude Code (`.mcp.json`,
  `~/.claude.json`); the two are different runtimes and different files.
- **HTTP and SSE templates are bridged through `mcp-remote`.** The app validates
  each entry as `{command, args, env}`; remote endpoints live in a separate
  `remoteMcpServers` surface managed from its Connectors UI and are not
  file-configurable. Writing a portable `{"type":"http","url":…}` entry verbatim
  would produce a config the app silently skips, so the adapter wraps remote
  servers as `npx -y mcp-remote <url>`, forwarding `headers` as `--header`
  arguments. `mcp-remote` negotiates the transport itself, so one bridge shape
  covers both the `http` and `sse` spellings. This also applies to
  `ai-toolkit inject-mcp`, which propagates to every editor exposing a global
  path and therefore now reaches the Claude app too.

### Changed

- `_resolve_global_config_root` gained a `_validate_configured_config_root`
  helper, shared with the new adapter. `COPILOT_HOME` and `CODEX_HOME` keep
  their existing semantics; the Claude app root is validated only when set
  explicitly, because its platform default need not exist yet.

### Fixed

- **Two docs described the `claude` adapter's config path wrongly.**
  `kb/reference/mcp-editor-compatibility.md` and `kb/reference/mcp-templates.md`
  both claimed it writes `.claude/settings.local.json` and
  `~/.claude/settings.json`. It writes `.mcp.json` and `~/.claude.json`, and has
  for as long as the adapter has existed. Both scopes were wrong in both files.

### Ecosystem

- `claude-app` gains three `config_paths`, the `scripts/mcp_editors.py`
  generator, and an `MCP` capability marker. Re-baseline with
  `python3 scripts/ecosystem_doctor.py --update --tool claude-app`.

### Tests

- 1645 → 1659. Thirteen cover the adapter (path resolution, parent-tree
  creation, preservation of `preferences`/`coworkUserFilesPath`/user-owned
  servers, byte-identical re-install, the bridge shape, rejection of entries
  with neither or both transports, four `CLAUDE_USER_DATA_DIR` validation cases,
  removal, and transactional rollback). One covers `inject-mcp` propagation,
  where per-editor failures are downgraded to warnings and a regression would
  otherwise be silent.

---

## v4.27.0 — Doctor sees the Claude app plugin (2026-08-21)

### Added

- **Doctor check 11: plugin double-load.** `ai-toolkit doctor` now reads the
  Claude Code plugin registry (`~/.claude/plugins/installed_plugins.json`) and
  `enabledPlugins` in `~/.claude/settings.json`. When an uploaded Claude app
  plugin is active next to the global install, both feed the same session:
  Claude Code merges plugin hooks with user hooks without deduplication, so every
  toolkit hook fires twice per event and skills and agents load twice. The check
  warns with the hook count, and `--fix` disables the plugin for Claude Code
  while leaving the global install authoritative. Previously this passed as a
  healthy install with no signal at all.
- `kb/troubleshooting/plugin-double-load.md` documents the symptom, the debug-log
  evidence, and the fix.

---

## v4.26.0 — Python floor is declared and enforced (2026-08-21)

### Added

- **Python preflight in the CLI.** `bin/ai-toolkit.js` now verifies `python3`
  exists and reports at least 3.11 before spawning any script, and prints a
  platform-specific fix (`brew install python@3.13` on macOS) instead of a
  traceback from deep inside `scripts/`. The check is lazy and memoized, so
  `help` and `--version` still run without a Python interpreter.
- **Matching floor check in `scripts/_common.py`.** Every entry point imports
  `_common` first, so `python3 scripts/install.py` run directly fails with the
  same message rather than a `TypeError` from whichever module happens to use
  3.11+ syntax.
- **CI import sweep.** The `python-syntax` job now runs on a `['3.11', '3.13']`
  matrix and imports every module under `scripts/` on each. `py_compile` only
  catches syntax, which is exactly why a 3.10-only construct shipped: version-
  gated runtime features surface on import, not on compile.

### Fixed

- **`ai-toolkit update --local` crashed on macOS system Python.** `/usr/bin/python3`
  is 3.9 on every Mac, and `scripts/mcp_editors.py` uses
  `@dataclass(frozen=True, slots=True)` (3.10+), so the install path died with
  `TypeError: dataclass() got an unexpected keyword argument 'slots'` while
  importing `install_steps/ai_tools.py`. The interpreter is now rejected up
  front with instructions.

### Changed

- **`scripts/check_deps.py` declares Python >= 3.11**, up from a `min_version`
  of `3.8` that never matched what the scripts actually needed, and its reason
  string calls out the macOS 3.9 trap.
- **Requirements are documented.** README gained a Requirements note above the
  install snippet; `CLAUDE.md` records the three places the floor is declared
  (`bin/ai-toolkit.js`, `scripts/_common.py`, `scripts/check_deps.py`) and the
  CI matrix that guards it.

### Ecosystem

- Snapshot refreshed: 11 tools drifted, all class A (content reworded, no
  heading delta). Claude Code 2.1.235 → 2.1.238 and Codex CLI 0.147.0 → 0.148.0
  are upstream patch bumps with no new surface, so no generator changed.

### Tests

- Three CLI regression tests: a stale `python3` shim exits 1 with the version
  message, a missing `python3` exits 1 instead of crashing, and `help` still
  works with no interpreter on PATH. Test count: 1637 → 1640.

---

## v4.25.1 — npm advisories count again (2026-08-19)

### Fixed

- **`cve-scan` reported zero findings for a vulnerable npm project.** npm audit
  can return the legacy `advisories` object as well as the current
  `vulnerabilities` object. The scanner parsed only the latter, so five real
  lodash advisories remained trapped in `raw_output` while `total_findings` was
  zero and the process exited successfully. Both formats are now normalized,
  and HIGH advisories restore the documented non-zero exit code.

### Changed

- **The published-package scanner smoke uses real per-scanner fixtures and
  flags.** It now includes healthcare patterns and a deliberately vulnerable
  locked npm dependency, invokes `cve-scan` with `--json`, and treats raw npm
  advisories with no normalized findings as a parser failure.

### Tests

- Added a public-CLI regression test with a stubbed legacy npm audit response;
  it asserts normalized severity, installed version, CVE, fixed range, finding
  count, and exit status.

## v4.25.0 — editor-native integrations catch up (2026-08-19)

### Added

- **Codex now has an exact native hook and plugin contract.** The hook generator
  covers all 11 supported events, including bounded `SessionEnd`, while the new
  deterministic plugin exporter bundles required runtime resources and verifies
  the complete archive offline before installation.
- **Google Antigravity gains native hooks, agents, plugin packaging, MCP mapping,
  and install profiles.** Generated hooks use the documented five-event schema;
  project and user installs use the current IDE and CLI paths without conflating
  legacy compatibility surfaces.
- **Gemini, OpenCode, and Cline gain native assets.** Gemini receives local agent
  files, OpenCode receives complete native skill directories, and Cline receives
  native rules plus all eight current extension and CLI hook events.

### Changed

- **Claude Code validation follows the current hook and plugin schemas.** Prompt
  and agent handlers share the documented 13-event allowlist, HTTP handlers are
  restricted to their supported lifecycle, and current plugin surfaces include
  workflows, output styles, and themes.
- **Editor installation and removal are transactional.** Profile downgrades and
  uninstall remove only toolkit-managed assets, preserve user files, and cover
  the new native Gemini, OpenCode, Antigravity, and Cline paths.

### Security

- **Filesystem writers reject symlink ancestry and ancestor-swap attacks.** New
  generators and cleanup paths use pinned transactions with rollback, while
  plugin verification rejects missing, extra, modified, or wrongly-modeled
  archive members.

### Ecosystem

- Refreshed the 13-tool compatibility registry and upstream snapshot after
  revalidating Claude Code, Codex CLI, Antigravity, Gemini, OpenCode, and Cline
  against their current native contracts.

## v4.24.1 — a dead link reported itself as installed (2026-08-19)

### Fixed

- **`plugin install` treated a dangling symlink as an installed asset.** The guard
  was `if path.exists() or path.is_symlink()`, and a link whose target is gone
  satisfies the second half — so the installer printed `OK agent` / `OK skill`,
  changed nothing, and left the user with a dead link and a green log. This is the
  exact state a toolkit upgrade produces: `npm install -g @softspark/ai-toolkit`
  replaces `app/` wholesale, so every `~/.claude` link into the old package points
  at nothing, and re-running install could not repair it.

  A dangling link is now dropped before the guard runs and relinked to the
  resolved source, printing `Dangling agent link removed: <name>`. **Live links and
  real files are untouched** — those are user content, and the merge-friendly
  install model keeps them.

  Surfaced while migrating a pack from `app/plugins/` to the v4.24.0 user root:
  the upgrade broke both links and `plugin install` insisted everything was fine.

### Added

- **Two tests.** One builds the post-upgrade state (links pointing into a path
  that no longer exists) and asserts install removes and relinks both; the other
  pins the negative — a real file on the agent name and a live skill link survive
  a reinstall untouched.

## v4.24.0 — external packs stop dying on upgrade (2026-08-18)

### Added

- **`~/.softspark/ai-toolkit/plugins/` is a second pack root.** Until now
  `plugin.py` scanned exactly one directory — `app/plugins/`, inside the npm
  package — so the only way to add a pack from its own repository was to drop it
  in there, where the next `npm install -g @softspark/ai-toolkit` deleted it along
  with the rest of `app/`. External packs now live in the user-owned data dir and
  survive every upgrade. `plugin list`, `install`, `update`, `remove` and `status`
  all see both roots; `AI_TOOLKIT_HOME` moves the user root with the data dir.

  A **core pack wins a name collision**, so an external directory cannot shadow
  shipped behaviour. Each pack dict carries `_root` (`core` or `user`) — `_source`
  was already taken as the hook-ownership marker.

  The entry may be a directory or a **symlink**, which is what gives an external
  pack a versioned update path: point it at an npm-installed package and
  `npm install -g <pack>@latest` rewrites the target in place, with nothing to
  re-link. Documented in `kb/reference/plugin-pack-conventions.md`
  (*Where Packs Live*), including the per-scope registry caveat when one package
  in a scope is public and another private.

- **Three tests.** A pack in the user root is listed, installs with both its agent
  and skill linked back into that root, and loses a name collision to a core pack.

## v4.23.1 — a pack could ship an agent nobody installed (2026-08-18)

### Fixed

- **`plugin install` never linked an agent the pack shipped itself.**
  `_install_claude_agents` resolved `includes.agents` only against the toolkit's
  own `app/agents/<name>.md`, so a self-contained pack got `WARN agent not found`
  and the agent silently stayed uninstalled. The asymmetry was visible inside the
  same file: skills already resolved through `_resolve_skill_source`, which falls
  back to the pack directory, and `_remove_claude_pack_links` already unlinked
  agent symlinks pointing into a pack — a removal path for links the installer
  could never create.

  Agents now go through `_resolve_agent_source`, mirroring skills: a core agent in
  `app/agents` still wins, otherwise `<pack>/agents/<name>.md` is linked. Packs
  that merely reference a core agent behave exactly as before.

- **`validate.py` reported self-contained packs as broken.** `validate_references`
  checked `app/agents` and `app/skills` only, so a pack shipping its own assets
  drew `References missing agent: X` and `References missing skill: Y` even though
  the installer handled the skill correctly. It now also accepts
  `<pack>/agents/<name>.md` and `<pack>/skills/<name>/SKILL.md`; a genuinely
  missing reference still errors. `pack_dir` is an optional argument, so existing
  callers are unaffected.

  Found by the post-release smoke test of a downstream pack (`legal-pl-pack`),
  not by a user report.

### Added

- **Three tests covering the class.** `tests/test_plugin.bats` builds a throwaway
  toolkit whose only pack ships its own agent and skill, then asserts the agent is
  linked into the pack (not `app/agents`), that removal drops the link, and that
  reference validation accepts pack-shipped assets while still failing on a
  genuinely missing one.

## v4.23.0 — a compliance scanner that says nothing must say why (2026-08-06)

### Fixed

- **`hipaa-validate` scanned a manifest-less project silently clean.** Category
  1, 3, 4 and 7 patterns are language-tagged and fire only for a detected
  language, and detection read manifest files only. A directory of Python with
  PHI in its loggers therefore reported `HIGH: 0` while every Python rule sat
  unused — the worst possible output for a compliance tool, because zero reads
  as compliant. Found by the post-release SOP on v4.22.1.

  Detection now falls back to the extensions of the files being scanned when no
  manifest is present. **Manifests still win**, so a project that already
  declared itself keeps exactly the behaviour it had.

### Changed

- **The scan summary reports how the language was decided.** A new
  `language_detection` field says `manifest`, `file extensions (no manifest
  found)`, or `none`. When it is `none` the text report writes to stderr that
  language-tagged patterns did not run and that a zero-finding result means
  unscanned rather than compliant.

  **Upgrade note:** a project scanned without a manifest may now report HIGH
  findings where v4.22.x reported none. Those findings were always there. A CI
  job gating on the exit code can start failing on real PHI exposure.

---

## v4.22.1 — nine skills, not four, could not find their own scripts (2026-08-06)

v4.22.0 claimed to fix four skills whose documented script path never resolved.
The first real run of the post-release SOP found five more, plus a wrong
interpreter and a script that crashed on `--help`. The v4.22.0 fix had grepped
for one spelling of the bug and missed the others.

### Fixed

- **Five more skills ran their own script through a path that cannot resolve
  after install**: `brand-voice` (repo-relative `app/skills/.../measure.py`),
  `ci`, `deploy`, `migrate` and `rollback` (cwd-relative `scripts/*.py`). Four
  further example lines in `debug`, `fix`, `pr` and `review` had the same defect
  in a secondary snippet while the primary invocation was already correct.
- **`rollback` ran a Python file through `bash`.** `bash scripts/rollback_info.py`
  was wrong twice over.
- **`explore` used `python` rather than `python3`**, which is missing or Python 2
  on many systems.
- **`explore`'s `visualize.py` crashed with a traceback on `--help`**, treating
  the flag as a directory to scan. It now prints usage, and reports a JSON error
  with exit 1 for a path that does not exist.

### Added

- **`validate.py` fails the build on the whole class.**
  `_validate_skill_script_invocations` checks every documented command that runs
  a skill-owned script: the path must go through `${CLAUDE_SKILL_DIR}`, and the
  interpreter must match the file. `python` instead of `python3` is a warning.
  Repo-level scripts such as `scripts/validate.py` are correctly ignored, and the
  frontmatter `scripts:` list stays relative because it declares rather than runs.
- **Post-release SOP phases 4b and 4c** (`post-release-testing-sop.md` v1.1.0):
  run every skill's documented invocation from the installed copy, and prove
  scanner-wrapping skills actually scan a fixture with known defects. Phase 4b
  found every defect in this release on its first run.

---

## v4.22.0 — the public surface is a test, not a promise (2026-08-06)

### Added

- **`scripts/surface_manifest.py` + `app/surface.json`** — 275 entries of public
  surface (skills, agents, frontmatter fields, CLI commands, hook scripts and
  events, KB categories, plugin packs) snapshotted and checked in `npm test`.
  Removing any of them fails the build; adding is free, because a surface nobody
  has installed has no users to break. The manifest is deliberately not
  auto-regenerated — if it were, deleting a skill would delete its entry in the
  same breath and the check would prove nothing.
- **`BACKWARD_COMPATIBILITY.md`** — which surfaces are load-bearing, what may
  change freely, and the deprecation path when a break is unavoidable.
- **`DECISIONS.md`** — why things are the way they are, including what was
  rejected and what may yet turn out to be ceremony.
- **`scripts/check_split.py`** — five gates proving a `SKILL.md` → `reference/`
  refactor lost nothing: fenced code lines survive, removed prose is traceable,
  always-loaded sections stay in the body, `description` is byte-identical, and
  every relative link still resolves. It caught a heading corrupted inside a
  fenced example on its first real use.
- **`scripts/sync_badges.py`** — README count badges derived from the tree and
  rewritten inside `generate:all`, before `validate.py --strict` reads them.
  Hand-maintained badges broke the build three times in one session.
- **`/brainstorm`** — the first planning skill allowed to end in "do not build
  this". Prices the zero option as a real candidate and sends the conclusion to a
  separate challenger agent before routing anywhere.
- **Skill body budget in `validate.py`** — error above 20,000 bytes, warn above
  18,000, with the current headroom printed on every run and a ratchet step in
  the release SOP.
- **Hook events `MessageDisplay` and `DirectoryAdded`** added to
  `VALID_HOOK_EVENTS`. Both are documented Claude Code events; without them
  `validate.py` rejected a user's hook on either as an invalid name.

### Changed

- **`a11y-validate` and `seo-validate` now run the scanners they ship.**
  `a11y-scanner.py` (643 lines) and `seo-scanner.py` (553 lines) were on disk and
  invoked by nothing — the model was told to grep the pattern tables by hand.
  Both skills now run their script for a deterministic baseline, then take an
  explicit manual pass, with a measured coverage table in the body saying which
  part is which. `a11y-scanner.py` covers 13 of ~50 documented WCAG success
  criteria; `seo-scanner.py` covers 8 of 10 categories and none of category 7
  (Rendering & Crawlability) or 10 (Topical Authority).
- **Review severity is one four-tier scale.** `/review` asked for
  `Critical/Major/Minor/Nit` while the `code-reviewer` agent it delegates to
  reported `CRITICAL/HIGH/MEDIUM/LOW/INFO`. The agent won at runtime, so the
  skill never received the format it specified. Both now use
  `blocker/major/minor/nit` with a mechanical verdict rule, and severity (impact)
  is explicitly separated from confidence (certainty).
- **`/review`, `/ci` and `/debug` collect every failing signal before judging**
  instead of stopping at the first red one.
- **Three validator skills split into `reference/`**: `hipaa-validate`
  23,905 → 10,433 B, `a11y-validate` 25,306 → 13,269 B, `seo-validate`
  35,066 → 13,430 B. 47 KB off the hot path.
- **`a11y-validate` and `seo-validate` gained `## Gotchas` and
  `## When NOT to Use`**, written from the traps the scanner wiring introduced.

### Fixed

- **Four skills invoked their scripts through a path that never resolved.**
  `debug`, `fix`, `pr` and `hipaa-validate` used `$(dirname "$0")`, which expands
  to the shell's directory, not the skill's. All four now use
  `${CLAUDE_SKILL_DIR}`, matching the other 14.

---

## v4.21.0 — one KB taxonomy, in one place (2026-07-28)

### Fixed

- **The `documentation-standards` skill contradicted itself.** Its frontmatter
  said "5-category taxonomy", its table listed those five, and three paragraphs
  below a "Valid categories" line named six — adding `planning`. An author
  reading the table and a validator reading the code disagreed about what was
  legal, and only the validator got a vote.
- **`decisions` and `runbooks` were not valid categories**, while the
  `kb-migration` SOP had been instructing people to create exactly those
  directories for months. A correctly-filed ADR failed `scripts/validate.py`.
  Both are now in the taxonomy, which is eight: `reference`, `howto`,
  `procedures`, `troubleshooting`, `best-practices`, `decisions`, `runbooks`,
  `planning`.
- **`procedures` and `runbooks` no longer describe each other.** The table gave
  "SOPs, runbooks, operational processes" for `procedures`, which left no way to
  choose between them. `procedures` is a process a person follows; `runbooks`
  are run against a live system, usually under pressure.

### Added

- **`section:` is documented as what it is: a legacy alias for `category:`.**
  Older documents and the `kb-migration` SOP write `section:`; both names are
  read in the wild. A document may carry both, and `validate.py` now rejects it
  when they disagree — a document filed as `category: reference` and
  `section: howto` is indexed twice and found once.
- **`validate.py` checks that a document's category names its directory.** The
  rule is scoped to directories that *are* category names, deliberately:
  `kb/history/completed/` is a lifecycle location rather than a type, and a
  finished plan filed there is still a `planning` document. Fifteen of this
  project's own documents are in exactly that position.

### Changed

- `VALID_KB_CATEGORIES` in `scripts/validate.py` and the taxonomy table in
  `app/skills/documentation-standards/SKILL.md` are one list in two places, and
  each now says so. They were previously two lists that had drifted.

---

## v4.20.0 — Apache-2.0, nine plugin packs removed (2026-07-27)

### Changed — licence: MIT to Apache-2.0

The project is now licensed under the Apache License 2.0. It stays permissive:
fork it, modify it, ship it commercially. What changes is what a redistributor
owes back.

- **`NOTICE` is the point.** MIT already required keeping the copyright notice,
  so attribution is not new. What Apache-2.0 adds is §4(d): a redistributor must
  carry the contents of the `NOTICE` file — project name, copyright, source URL —
  into their distribution. That is the strongest attribution mechanism available
  in a permissive licence, and it is why this change was made. `NOTICE` is now in
  `package.json` `files`, so it ships with the npm package.
- **Modified files must say so** (§4b). MIT had no equivalent.
- **Express patent grant with retaliation** (§3) and **no trademark rights**
  (§6). Neither existed under MIT.
- **Nothing is revoked.** Releases up to and including v4.20.0 were published
  under MIT and remain available under MIT. This applies going forward.
- **Prior contributions are handled correctly.** Contributions received while the
  project was MIT-licensed remain their authors' copyright. MIT permits
  sublicensing, so they are redistributed under Apache-2.0 with the original MIT
  notice preserved verbatim in `NOTICE`, which is what MIT requires.

`LICENSE` now holds the verbatim Apache-2.0 text, cross-verified against two
independent published copies before being written.

- **SPDX headers on 253 source files.** Short three-line form, placed after the
  shebang. Markdown is deliberately excluded: skill and agent files carry parsed
  frontmatter, and their descriptions cost 5,051 and 2,750 tokens of every
  session's context, so a header there would be billed on every conversation for
  a notice Apache only recommends.
- **`tests/test_licensing.bats`, 7 assertions, enforced in CI**: headers present
  and naming Apache-2.0, no header in markdown, `LICENSE` complete, `NOTICE`
  carrying attribution and section 4(d), both files in `package.json` `files`,
  and every manifest agreeing. The release SOP gains Phase 5c running the same
  gate before the tag. Convention and reasoning: `kb/reference/licensing.md`.

### Removed

- **Nine plugin packs that installed nothing**: `csharp-pack`, `java-pack`,
  `kotlin-pack`, `ruby-pack`, `rust-pack`, `swift-pack`, `frontend-pack`,
  `research-pack`, `security-pack`. Every one declared only skills and agents
  that already ship in the core install, so `plugin install` reported
  `(0 file items)` and put no file on disk. Measured on both runtimes and all
  three profiles. Eight of the nine owned nothing but a `README.md`.

  **Nothing is lost.** `rust-patterns`, `java-patterns`, `security-patterns`,
  `research-mastery` and every other asset those packs named are core skills and
  agents; they are still installed and still trigger exactly as before. A pack
  never held them.

  `frontend-pack` was the sole partial exception: on codex it copied core's
  `post-tool-use.sh` in under a pack-prefixed name. That is a generic hook with a
  domain label, not frontend functionality. If `post-tool-use` should run on
  codex it belongs in the core codex hook set, as its own change.

  Full measurement: `kb/history/completed/no-op-plugin-packs-removed-20260727.md`.
- `kb/reference/language-packs.md`, the reference for six of the removed packs,
  moved to `kb/history/completed/language-packs-removed-20260727.md`.

### Changed

- **`plugin-creator` now requires a pack to do something.** The authoring rule
  said "reference existing toolkit assets before duplicating", which against a
  core install that ships everything produces a no-op every time — nine packs
  followed it exactly. It now requires that a pack install files the core does
  not, and the validation checklist carries a non-zero-file-count check on every
  runtime the pack claims.
- `kb/reference/plugin-pack-conventions.md` documents the two surviving packs by
  what they **own**, not by what they list.

### Kept

`memory-pack` (2 hooks, 2 scripts, its own `mem-search` skill) and
`enterprise-pack` (`status-line.sh`, `output-style.sh`) — the two packs that
ship files of their own.

---

## v4.19.1 — re-release from corrected history (2026-07-27)

No functional change. The package contents are identical to v4.19.0.

v4.19.0 was committed with two commit messages attached to the wrong changes:
the commit titled `chore: release v4.19.0` held only the post-release testing
SOP, and the release itself shipped under a recycled message about a CodeQL
action bump. `main` has been rewritten so the history states what each commit
actually did, and this version is published from that corrected history.

The `v4.19.0` tag is deliberately left pointing at the pre-rewrite commit
`8c90024`. That commit is what the published SLSA attestation for v4.19.0 pins,
so the tag keeps it fetchable even though it is no longer an ancestor of `main`.
Do not delete that tag.

---

## v4.19.0 — rtk-pack retired (2026-07-27)

### Removed

- **`rtk-pack`**, one day after it shipped. The first real install proved every
  rewritten command failed with exit 127: rtk names itself bare in the rewrite
  and the pack keeps its binary off `PATH` on purpose, so the shell could not
  find it. `git`, `ls`, `cat`, `find`, `grep`, `diff` and the rest all died
  before running. A second defect fetched the Intel build onto Apple Silicon,
  because `platform.machine()` reports `x86_64` from a Rosetta-translated
  Python. The pack's own `plugin status` reported both as green.

  All three were fixed and tested before the decision. The measured saving was
  0.0615% of input tokens against a kill number of 0.05%, a margin the
  integration plan itself called "a pass, not a vindication", which does not
  justify a supply-chain surface, a five-target cross-build workflow, an
  upstream-sync SOP, and a hook that rewrites every command before it runs.

  Full postmortem: `kb/history/completed/rtk-pack-retirement-20260727.md`.
- `.github/workflows/rtk-build.yml`, `scripts/verify_rtk_binary.py`,
  `tests/test_rtk_pack.bats`, `tests/test_verify_rtk_binary.bats`,
  `kb/procedures/rtk-upstream-sync-sop.md`, and the GitHub Release
  `softspark-rtk-v0.44.0-1` holding the five cross-built binaries.

If you installed the pack under v4.18.0, run
`ai-toolkit plugin remove rtk-pack`.

### Kept

Everything the pack work built underneath it, none of which is rtk-specific:
pack hook wiring for Cursor and Gemini, `supported_editors` in the manifest,
generic `plugin status` dispatch to a pack's own `scripts/status.py`,
version-aware `plugin update`, and `audit_skills.py --ci` plus the ShellCheck
gate covering `app/plugins/`.

---

## v4.18.0 — rtk-pack, an opt-in command rewriter (2026-07-26)

### Added

- **`rtk-pack`**, an opt-in plugin pack that rewrites Bash commands at
  `PreToolUse` via [rtk](https://github.com/rtk-ai/rtk) (Apache-2.0). Nothing
  installs it for you. `ai-toolkit plugin install rtk-pack` fetches a
  platform-specific binary from an ai-toolkit GitHub Release and verifies its
  SHA-256 before installing anything; a mismatch aborts and leaves nothing
  behind. Read `app/plugins/rtk-pack/README.md` before enabling it: the rewrite
  means what runs is not literally what the model asked for, and rtk applies
  your permission verdict for the original command to the rewritten one.
- **`.github/workflows/rtk-build.yml`**, a manual-dispatch pipeline that
  cross-builds rtk from upstream source for five targets with the compile-time
  telemetry endpoint left undefined, proves each artifact starts, writes no
  telemetry state and (on Linux) behaves identically with no network route,
  then publishes checksummed artifacts with LICENSE and NOTICE.
- **`scripts/verify_rtk_binary.py`**, the silence verifier that pipeline uses.
  A target it cannot start reports `inconclusive`, never `pass`.
- **`kb/procedures/rtk-upstream-sync-sop.md`**, the procedure for moving to a
  newer upstream tag, including a re-measure gate and a published kill number.
- Plugin packs can now ship `scripts/status.py` and have `plugin status` pick it
  up. This replaces a hardcoded `if name == "memory-pack"` branch, so any pack
  can report its own health.

### Changed

- **`ai-toolkit update` now updates installed plugin packs.** It reads
  `plugins.json` and runs the equivalent of `plugin update --all` for every
  installed pack. `--local` leaves packs alone, since they are global.
- **`plugin update` is version-aware.** `plugins.json` records the pack version
  installed per editor, and an update whose manifest version matches is a silent
  no-op. Previously every update removed and reinstalled unconditionally, which
  for a pack that downloads a binary meant refetching it every time. `--force`
  overrides; `--dry-run` reports without acting. State written before versions
  were tracked updates each pack exactly once.
- Plugin packs are now covered by `audit_skills.py --ci` and by the ShellCheck
  gate in CI. Both previously scanned only `app/skills`, `app/agents` and
  `app/hooks`, exempting the highest-risk code in the repo.
- A pack's install-time script may be named `init.py`; `init_db.py` still works.
  Previously only the latter ran, so a pack using any other name installed
  successfully while doing nothing.

### Fixed

- `plugin install` no longer aborts with `IsADirectoryError` when a pack ships a
  subdirectory under `scripts/`.
- A failing pack init script now always reports, instead of printing nothing
  when it exited non-zero with empty stderr.

---

## v4.17.0 — Native tool-output filter removed (2026-07-26)

### Removed

- **BREAKING for anyone who opted in.** The native tool-output filter shipped
  in v4.16.0 is gone: the `PostToolUse` hook `filter-tool-output.sh`, the
  `scripts/tool_output_filter/` runtime, the `ai-toolkit output-filter` CLI,
  the benchmark corpus, and the `toolOutputFilter` key in
  `.softspark-toolkit.json`. The key is accepted and ignored rather than
  rejected, so an existing config still validates; `ai-toolkit config validate`
  reports it as a retired key you can delete.
- Why: measured whole-session token saving was **0.0000%** on real traffic.
  Across 134 session transcripts spanning 22 projects, 7600 successful Bash
  results contained 145 that parsed as simple command shapes, 18 that matched a
  registered shape, and 0 that any filter accepted. The filter was correct;
  its premise was not. Agent-issued commands are overwhelmingly compound
  (`&&` and `;` chains, pipelines, heredocs), and the design accepted only
  simple registered shapes. See
  `kb/history/completed/output-filter-retirement-20260726.md`.

### Changed

- `ai-toolkit install` and `ai-toolkit update` now remove the artifacts left by
  v4.16.x: the installed hook script, the global
  `hooks/output-filter-policy.json`, the managed project policy and owner
  marker under `.claude/`, and stored recovery trees under
  `sessions/<repo-key>/output-filter/`. Cleanup is idempotent, verifies
  ai-toolkit ownership before deleting, and leaves foreign files untouched.
- The stale `PostToolUse` entry is removed from `~/.claude/settings.json` by
  the existing hook strip-and-remerge cycle, so no manual edit is needed.
- Hook counts drop from 29 entries to 28 across the same 14 events.

## v4.16.1 — Copilot skill remnant recovery (2026-07-24)

### Fixed

- **Legacy Copilot skill remnants no longer abort local updates** — `.github/skills/ai-toolkit-*` directories left behind by pre-manifest cleanups (assets without `SKILL.md`) are rebuilt in place instead of raising `Refusing user-owned Copilot skill collision`, which aborted the entire `install --local` / `update` run on affected projects. User files inside a remnant that do not collide with generated output are preserved; any directory that still contains a `SKILL.md` stays protected and is never reclaimed.
- **Readable installer errors** — `scripts/install.py` reports fail-closed `RuntimeError` conditions as a single `ERROR:` line instead of a raw traceback.

Test count: 1477 → 1479.

## v4.16.0 — Native tool-output filtering (2026-07-24)

Minor release. Adds a dependency-free, opt-in native tool-output filter for Claude Code and hardens the enterprise configuration, session-isolation, and editor-adapter surfaces around it. The filter ships disabled; `observe` and `safe` are per-project opt-ins. No source catalog count change (44 agents, 108 skills).

### BREAKING

- **Unknown config keys rejected** — `.softspark-toolkit.json` and `ai-toolkit.config.json` are now validated against a closed set of top-level keys. Files carrying typos or unsupported keys that previously validated will fail `config validate` and `config check` until the key is removed.
- **Constitution Article VII reserved** — reserved articles expand from I-VI to I-VII, so custom amendments must start at article 8 instead of 7. A base config that defines article 7 was valid before and now aborts validation.
- **Plugin manifests require `requires`** — `plugin.json` must declare a non-empty `requires` map of non-empty string constraints. Existing manifests without the field fail schema validation.
- **Lock files go stale on every toolkit version bump** — `.softspark-toolkit.lock.json` records the toolkit version and is reported stale when it differs from the running version. This is intentional integrity design: re-run `install --local` or `update --local` after upgrading to refresh the lock.

### Added

- **Native tool-output filter** — added a dependency-free, opt-in Claude Code `PostToolUse` filter with `off`, `observe`, and `safe` modes. The initial version handles only allowlisted successful Bash test and validation output through deterministic `repeat-lines` and `tap-success` profiles.
- **Exact ephemeral recovery** — every safe replacement is preceded by a private, bounded, session-scoped copy of the exact native response object. Opaque handles support manual recovery and cleanup without storing commands, paths, session IDs, or raw output in telemetry.
- **Output-filter operations** — added inspect, status, recover, and clean entry points under `ai-toolkit output-filter`, plus a deterministic benchmark script for the built-in profiles.
- **Project policy inheritance** — `toolOutputFilter` participates in schema validation, inheritance, merge, lock, local install, and managed project-policy cleanup.
- **GitHub Copilot compatibility reference** — added `kb/reference/copilot-compatibility.md` documenting the Copilot integration surface, with cross-links from the Codex CLI, opencode, and global-install references.

### Fixed

- **Hook safety** — `guard-path.sh` now blocks when `jq` is unavailable instead of silently skipping path validation. Codex Bash hooks apply the same path guard during `PreToolUse` and `PermissionRequest`.
- **Filter eligibility** — allowlisted task names now use exact token boundaries, and recovery-backed filtering rejects unsafe or unbounded native session identifiers instead of creating mismatched cleanup paths.
- **Session isolation** — edit tracking uses per-session state files, hook adapters preserve native OpenCode and Augment session identifiers, unsafe identifiers receive collision-resistant normalized names, and pre-compact snapshots prefer the payload session identifier.
- **Editor adapter integrity** — OpenCode propagates guard exit code 2 as a blocked tool execution, Gemini preserves malformed settings, rejects symlinked destinations, and writes valid updates atomically, while Claude app exports omit the Claude Code-only output replacement hook.
- **Statusline token trend** — the documented baseline file now drives a visible input/output token trend, including payloads without optional cost or effort fields.
- **Brand-voice fact checks** — missing extracted facts now fail the quality gate, while inline-code extraction is restricted to identifier-shaped values to avoid false positives.
- **Enterprise configuration** — config and lock readers reject non-object JSON and invalid UTF-8 without traceback, invalid output-filter updates preserve the last valid managed policy, and lock staleness checks cover lock format, toolkit version, source, resolved version, and content integrity. Constitution Articles I through VII remain reserved, `requiredPlugins` materializes enforceable enable intent, and plugin manifests validate non-empty dependency constraints.
- **Recovery cleanup** — session end and global uninstall remove only validated ai-toolkit recovery artifacts, remain idempotent for foreign-only trees, and abort before other mutations when the recovery namespace is unsafe.
- **Flaky pack-audit tests** — npm's update-notifier stderr no longer corrupts JSON parsing in the package-content tests (`npm_config_update_notifier=false` in the test environment).
- **Linux-only test failures** — the jq-unavailable guard test hides `jq` via a stub `PATH` (plain `PATH=/bin` keeps `jq` visible on usrmerge systems where `/bin` is `/usr/bin`), and the foreign-recovery uninstall test now asserts the message `uninstall.py` actually prints. Both passed on macOS only because bash 3.2 does not enforce bare `[[ ]]` bats assertions.

Hook entries: 28 → 29. Test count: 1377 → 1477.

## v4.15.1 — Copilot profile cleanup (2026-07-15)

### Fixed
- **Copilot profile downgrade cleanup** — switching a project from `standard`, `strict`, or `full` to `minimal` now removes managed instructions, prompts, and hooks, including byte-exact pre-marker output from v3.0.0 through v4.14.1, while preserving user-owned files.
- **Atomic downgrade preflight** — hook-only cleanup is validated before any Copilot file changes, so unsupported native Windows mutations fail without leaving a partial profile transition.
- **Release gate enforcement** — tag publishing now regenerates package assets and runs ecosystem, validation, audit, ShellCheck, and test gates before the provenance-signed npm publish; SARIF is uploaded to GitHub code scanning.

Test count: 1367 → 1377.

## v4.15.0 — Native Codex and Copilot parity (2026-07-14)

Minor release. Rebuilds the Codex CLI and GitHub Copilot integrations around their current native instruction, agent, skill, hook, and MCP surfaces. It also hardens managed-file migration and multi-file configuration updates so toolkit refreshes preserve user-owned content and fail without leaving partial state. No source catalog count change (44 agents, 108 skills).

### Added
- **Codex native custom agents** — `scripts/generate_codex_agents.py` materializes all 44 source agents as validated `.codex/agents/ai-toolkit-*.toml` files with native `name`, `description`, and `developer_instructions` fields. Logical-name collisions, unmanaged files, stale symlinks, and staging failures preserve user content.
- **Complete Codex skill delivery** — project installs expose all 108 skills under `.agents/skills/`: 51 portable skills link to their canonical source and 57 Claude-specific skills receive self-contained, signature-free Codex adaptations with required assets retained.
- **Self-contained Codex hooks** — project and user installs emit schema-validated `.codex/hooks.json` plus native runtime assets under `.codex/hooks/` or `$CODEX_HOME/ai-toolkit-hooks/`. Managed handlers merge idempotently with user hooks and keep Codex trust review explicit.
- **Copilot native customization bundle** — project installs now generate all 44 native `.agent.md` agents, all 108 materialized portable skills, 62 slash-command `.prompt.md` files, and scoped instruction files under `.github/`. User installs provide instructions, agents, and skills under `$COPILOT_HOME`; prompt files remain repository-scoped.
- **Copilot native lifecycle hooks** — `scripts/generate_copilot_hooks.py` writes GitHub version-1 hook configuration and a self-contained runtime with native camelCase events, event-specific decisions, destructive-command/path guards, quality gates, and a bounded stop-loop circuit breaker.
- **Codex project and user MCP** — MCP templates now render validated STDIO or Streamable HTTP `[mcp_servers.*]` tables into project `.codex/config.toml` and user `$CODEX_HOME/config.toml`, while preserving unrelated TOML text and comments.

### Changed
- **One shared instruction and constitution core** — Codex and Copilot `AGENTS.md` output now comes from `scripts/instruction_core.py` and the canonical `app/constitution.md`. Agent and skill catalogs are discovered from native directories instead of being duplicated into always-on instructions.
- **Portable skill translation** — Codex, Copilot, and opencode adapters replace Claude-only tools, prompt placeholders, and skill-directory variables with runtime-neutral workflow intent instead of guessed client function signatures. opencode commands retain native `$ARGUMENTS` and positional argument behavior.
- **Profile-aware Copilot install model** — project `minimal` installs agents and skills; `standard`, `strict`, and `full` additionally install instructions, prompts, and native hooks. User installs always provide instructions, agents, and skills, with hooks enabled from `standard` upward. `COPILOT_HOME` replaces the default user root consistently.
- **Release workflow runtime** — pinned `softprops/action-gh-release` to the reviewed v3.0.2 commit for the Node 24 action runtime.

### Fixed
- **Rules and constitution enforcement gaps** — current Codex and Copilot instruction files now receive the same always-on policy derived from the canonical constitution, eliminating stale or unread duplicated rule catalogs.
- **Managed marker migration** — instruction injection handles nested, crossed, orphaned, empty legacy, and Unicode section markers without consuming adjacent user-authored content.
- **Transactional MCP updates** — canonical `.mcp.json` and all requested native editor configs are preflighted and applied as one atomic transaction. Invalid JSON/TOML, symlinked destinations, concurrent changes, or a late replace failure leave prior files byte-identical or trigger an explicit rollback failure.
- **Managed output safety** — native generators stage and validate replacements, reject symlinked roots, preserve reserved user collisions and unmanaged files, and remove only files carrying ai-toolkit ownership markers.

### Ecosystem
- **Class B/F — Codex CLI**: adopted native custom-agent TOML, current skill discovery, the documented hook schema and trust model, project/user configuration layers, `$CODEX_HOME`, and project-scoped MCP from the current OpenAI documentation.
- **Class B/F — GitHub Copilot**: adopted repository and user custom agents, prompt files, instruction files, portable skills, version-1 hooks, `$COPILOT_HOME`, and `.github/mcp.json` from the current GitHub documentation.

## v4.14.1 — Keep fact-checker on Sonnet (2026-07-14)

Patch release. Reverts one of the two agent model reassignments from v4.14.0: `fact-checker` goes back to `model: sonnet`. Claim verification is accuracy-sensitive and Haiku's recall on subtle claims did not justify the cost saving. `explorer-agent` (pure read/search) stays on `model: haiku`. No count change (44 agents, 108 skills, 1216 tests).

### Changed
- **`fact-checker` reverted to Sonnet** — `model: haiku → model: sonnet`. Quality over cost for claim verification / RAG-accuracy checks.

## v4.14.0 — Model refresh + effort-aware routing (2026-07-14)

Minor release. Refreshes Claude model IDs to the current generation across the toolkit, teaches the routing skill to route on `effort` (not just model tier), and moves two pure-retrieval agents to Haiku. No skill/agent/hook count change (44 agents, 108 skills, 1216 tests).

### Changed
- **Canonical model IDs bumped** — `scripts/_common.py` `DEFAULT_CLAUDE_MODELS` now resolves `opus → claude-opus-4-8` and `sonnet → claude-sonnet-5` (`haiku → claude-haiku-4-5` unchanged). This is the single source of truth generators emit.
- **`model-routing-patterns` skill refreshed** — tier table updated to Haiku 4.5 / Sonnet 5 / Opus 4.8 with per-1M pricing, added a **Fable 5** row plus a "not the default best model" caveat (target for "strongest model" stays `claude-opus-4-8`), and a new **Effort routing** section (effort is the cheaper lever before swapping models — it does not invalidate the prompt cache). Fallback-chain example IDs updated.
- **Stale example model IDs refreshed** — `json-mode-patterns`, `prompt-caching-patterns`, and `skill-creator` code samples now reference `claude-opus-4-8`.
- **Pure-retrieval agents routed to Haiku** — `explorer-agent` (Read/Grep/Glob only) and `fact-checker` (Read only) changed from `model: sonnet` to `model: haiku`, closing the gap where the routing skill recommended Haiku workers but no agent used the tier.

## v4.13.0 — Claude app delivery + Devin sunset cleanup (2026-07-10)

Minor release. Adds a validated distribution path for Claude Chat/Desktop/Cowork, fixes the core plugin contract, and removes the retired Cascade hook surface. Test count: 1208 → 1216 (seven deprecated Cascade assertions removed; six Claude app contract tests, three editor migration/propagation tests, two state-isolation/cleanup tests, two untagged-hook diagnostics, and two dry-run regressions added).

### Added
- **Claude app plugin export** — `ai-toolkit claude-app export [--output FILE] [--no-custom-rules] [--verify]` creates a deterministic plugin ZIP for `Customize > Plugins` and a sibling Cowork global-instructions file. The archive bundles skills, agents, app-relative hooks, required helper scripts, core rules, and registered user rules (opt-out for shareable bundles).
- **App-native rules delivery** — common and standalone rule sources are rendered into the `ai-toolkit-rules` skill because Claude Chat/Cowork does not read Claude Code's `CLAUDE.md` or `~/.claude/rules/` surfaces.
- **Claude app ecosystem target** — registry/tooling now tracks 13 targets: Claude Code, Claude Chat/Cowork, and 11 editor integrations.

### Fixed
- **Official plugin manifest** — changed `repository` from an invalid object to the required URL string, removed four ignored non-schema fields, and declared the generated app skill/hook component paths. `claude plugin validate` now passes on a clean staged plugin.
- **Cowork hook portability** — generated plugin hooks use `${CLAUDE_PLUGIN_ROOT}` and bundle their Python helpers instead of assuming a separate `~/.softspark/ai-toolkit/hooks` install.
- **Untagged hook diagnostics** — `doctor` and `config-desync-guard.sh` now recognize canonical hook behavior when Claude rewrites settings without preserving ai-toolkit's private `_source` marker, eliminating false "hooks missing" warnings.
- **Update dry-run safety** — `ai-toolkit update --dry-run` and `--list` no longer invoke registered-project updates or create `projects.lock` after the read-only preview.
- **Cline dry-run accuracy** — global preview now reports reuse of Cline-compatible `~/.claude/skills` instead of claiming it will create a redundant `~/.cline/skills` pointer.
- **Global/local state isolation** — project-local installs and registered-project propagation no longer overwrite global `state.json` modules/profile with the last project's detected languages; project metadata remains in `projects.json`.
- **Detected-language state cleanup** — explicit module installs now clear stale `auto_detected_languages` metadata instead of reporting an obsolete last-detected language in `status`.
- **Registered-project editor/profile propagation** — explicit `ai-toolkit update --editors/--profile ...` overrides now reach registered projects; without an override, each project's saved editor set and profile are preserved.
- **Devin skill discovery** — emit a single canonical pointer under `.windsurf/skills` instead of also writing `.devin/skills`. Both are in Devin's documented eight-path discovery list (all scanned in every repo), so one pointer keeps skills discoverable while avoiding duplicate registration.

### Removed
- **Cascade hook generator** — removed `generate_windsurf_hooks.py`, `.windsurf/hooks.json` install wiring, tests, and docs after Cascade's 2026-07-01 sunset. `generate_devin_hooks.py` / `.devin/hooks.v1.json` is the sole Windsurf-family hook surface.
- **Retired path migration** — local Windsurf/Devin updates strip only ai-toolkit-owned entries from legacy `.windsurf/hooks.json` and remove the managed `.devin/skills/ai-toolkit-skill-catalogue` pointer while preserving user content.

### Ecosystem
- **Class B/F — Claude app plugins**: adopted the official plugin surface shared by Chat/Desktop/Cowork; skills work across Chat and Cowork while hooks/sub-agents are Cowork-only.
- **Class D — Devin/Cascade**: completed the scheduled removal and refreshed current skill paths. Devin Desktop v3.4.27 and its v3.4.22 skill-permission change were reviewed; no permission field is needed for ai-toolkit's non-executing pointer skill.
- **Class A — editor docs**: reviewed content-only drift for Cursor, Copilot, Gemini, Cline, Augment, and opencode; no generator contract changes were found.
- **Class A — versions/docs**: refreshed Claude Code 2.1.206 and Codex CLI 0.144.1 after reviewing their official releases/current config surfaces.

## v4.12.0 — Global-first editor installs + Codex path fix (2026-07-02)

Minor release. Expands global (HOME-scoped) installs to every editor with a documented, merge-safe file surface, and fixes a Codex global-install bug where instructions landed in a file Codex never reads. Test count: 1203 → 1208.

### Fixed
- **Codex global instructions path** — `ai-toolkit install --editors codex` and `ai-toolkit plugin install --editor codex` wrote to `~/AGENTS.md`, which Codex never loads as global instructions, so global installs delivered zero instructions. Now write `~/.codex/AGENTS.md` (the documented `$CODEX_HOME/AGENTS.md`), strip the stale `~/AGENTS.md` toolkit section on upgrade, and warn when `~/.codex/AGENTS.override.md` would mask it.
- **Codex plugin-pack rules** — pack rules were copied to `~/.agents/rules/`, a directory Codex never reads; now marker-injected into `~/.codex/AGENTS.md`, with legacy dead files cleaned on install/remove (`scripts/plugin.py`).
- **`inject-hook` Codex event parity** — `CODEX_EVENTS` propagated only 5 of the 9 events `scripts/generate_codex_hooks.py` wires; added `PermissionRequest`, `SubagentStart`, `SubagentStop`, `PreCompact`.

### Added
- **Global native surfaces for 7 editors** — `install_ai_tools` now threads `--profile` and installs each editor's documented HOME surfaces (gated like the local install): **Gemini** (hooks `~/.gemini/settings.json`, `~/.gemini/commands/`, skills pointer), **Augment** (`~/.augment/agents/`, `~/.augment/commands/`, hooks), **Roo/Zoo** (skills via `~/.agents/skills`), **Windsurf** (`~/.config/devin/AGENTS.md` for Devin CLI), **Cursor** (`~/.cursor/hooks.json`), **GitHub Copilot** (`~/.copilot/` instructions), **Google Antigravity** (skill pointer to `~/.gemini/config/skills` and `~/.gemini/antigravity-cli/skills`).

### Changed
- **`GLOBAL_CAPABLE_EDITORS`** — added `cursor`, `copilot`, and `antigravity` (scoped: cursor = hooks, copilot = instructions, antigravity = skills; RULES stay project-local where no mergeable global file surface exists).
- **`generate_copilot.py`** and **`generate_antigravity.py`** gained global layouts (`config_root=~/.copilot`; `generate_global()`).

### Ecosystem
- **Roo → Zoo Code** (class D) — `RooCodeInc/Roo-Code` archived (frozen v3.54.0, dead release feed); retargeted the feed to the successor `Zoo-Code-Org/Zoo-Code` and added skills/commands config paths. (class F) Global skill install via `~/.agents/skills`.
- **Cursor** (class F) global `~/.cursor/hooks.json`; (class D) `.cursorrules` demoted to legacy (dropped from official rules docs).
- **GitHub Copilot** (class F) documented `~/.copilot/` user-level surface adopted.
- **Google Antigravity** (class F) global skill dirs adopted; `~/.gemini/config/mcp_config.json` global MCP path resolved and recorded (adapter is backlog).
- **Gemini / Augment** (class F) hooks/commands/agents made global.
- Version refresh: Gemini v0.49.0, Codex 0.142.5, Auggie 0.31.0, Antigravity CLI 1.0.14, Claude Code 2.1.198; Devin `read_config_from` 7-key matrix. Snapshot re-baselined via `scripts/ecosystem_doctor.py --update`.

## v4.11.0 — Claude rules-space fix + editor registry parity (2026-06-30)

Minor release. Reduces Claude Code startup context pressure by moving ai-toolkit rules out of global/project `CLAUDE.md` inline blocks and into Claude Code rule files. Also finishes the editor registry sync by recording all Gemini generators in the canonical ecosystem registry. Test count: 1198 → 1203.

### Changed
- **Claude Code global rules now use `~/.claude/rules/ai-toolkit-*.md`.** `ai-toolkit install/update` writes toolkit rules from `app/rules/*.md` and registered rules from `~/.softspark/ai-toolkit/rules/*.md` into Claude Code user-level rule files, keeps `~/.claude/CLAUDE.md` as a compact index, and removes legacy inline rule markers during migration. The `ai-toolkit-*` prefix is installer-managed.
- **Claude Code common rules now use `.claude/rules/ai-toolkit-*.md`.** `install --local` writes `ai-toolkit-coding-style.md`, `ai-toolkit-git-workflow.md`, `ai-toolkit-performance.md`, `ai-toolkit-security.md`, and `ai-toolkit-testing.md` under `.claude/rules/` with `paths: ["**/*"]` frontmatter, while `.claude/CLAUDE.md` stays a compact index. This follows Claude Code's current guidance to keep `CLAUDE.md` concise and move larger instruction sets into scoped rules.
- **Language rules reference updated.** `kb/reference/language-rules.md` now documents the Claude-specific split: common rules as project-local Claude rules, per-language rules as knowledge skills, and other editors still receiving native rule files from their generators.
- **Ecosystem registry reflects Gemini native surfaces.** `scripts/ecosystem_tools.json` now includes `generate_gemini_hooks.py`, `generate_gemini_commands.py`, and `generate_gemini_skills.py` alongside `generate_gemini.py`, matching the installer and supported-tools registry.
- **Ecosystem doctor baseline refreshed.** Snapshot updated after class A/C upstream documentation drift review; no additional generator contract changes were required.

### Fixed
- **Claude rules-space regression.** Global Claude installs no longer inline toolkit/registered rules into `~/.claude/CLAUDE.md`, and project-local Claude installs no longer inflate `.claude/CLAUDE.md` with the full common-rule corpus. Regression tests now assert compact CLAUDE.md indexes, generated rule files, legacy marker cleanup, and managed `.claude/rules/ai-toolkit-*.md` refresh behavior.

## v4.10.1 — Copilot AGENTS.md install + Claude KB-first rule (2026-06-23)

Patch release. Fixes two governance regressions found in the editor-update audit: Copilot installs now emit the root `AGENTS.md` surface documented in the registry, and Claude Code receives the KB-first rule in `CLAUDE.md`, which it actually reads. Test count: 1195 → 1198.

### Fixed
- **GitHub Copilot local install now emits root `AGENTS.md`.** `ai-toolkit install --local --editors copilot` writes the generated agent catalog into a `TOOLKIT:copilot-agents` section without clobbering existing Codex/opencode `TOOLKIT:ai-toolkit` sections or user-authored content. Dry-run output and tests now cover the `.github/copilot-instructions.md + AGENTS.md` contract.
- **Claude Code KB-first rule restored in the right instruction file.** `CLAUDE.md` now explicitly requires `smart_query()` or `hybrid_search_kb()` before technical/project answers; the prior generated `AGENTS.md` placement was not sufficient for Claude Code runtime enforcement.
- **Codex PostToolUse no longer emits unsupported `suppressOutput`.** `loop-guard.sh` no longer forces `AI_TOOLKIT_HOOK_FORMAT=json`; under Codex it stays quiet/plain unless the generator explicitly opts into a supported JSON schema.
- **Npm package excludes local Claude session artifacts.** `package.json` now excludes `app/**/.claude/**` so ignored maintainer-local session files cannot leak into `npm pack`.

### Changed
- **Editor registry/docs aligned with implementation.** README, architecture overview, and the supported-tools registry now describe Copilot's root `AGENTS.md` emission consistently.
- **Ecosystem doctor baseline refreshed.** Snapshot updated for upstream Claude Code and Gemini CLI documentation content hash drift; no generator changes were required.

## v4.10.0 — Per-repo session storage outside the repo + drop dead session-context hook (2026-06-17)

Minor release. Session lifecycle hooks stop writing auto-generated files into each project's `.claude/` directory and store them per-repo under `~/.softspark/ai-toolkit/`. The dead `session-context.sh` hook (write-only, no consumer) is removed across all editor generators. Test count: 1197 → 1195.

### Changed
- **Session lifecycle hooks store artifacts outside the repo.** `save-session.sh`, `session-end.sh`, `session-start.sh`, and `pre-compact.sh` now read/write the auto-generated session files (`session-context.md`, `session-end.md`, `session-context.md.checkpoints`, `decisions.md`) under `~/.softspark/ai-toolkit/sessions/<repo-key>/` instead of the project's `.claude/` directory. `<repo-key>` is the git work-tree root path (fallback: cwd) with `/` replaced by `-`, keyed per repo so projects stay isolated. Stops these files from piling up in every repository. New shared helper `app/hooks/_session-paths.sh` is the single source of path resolution. No migration of pre-existing in-repo files: the new store starts fresh, old `.claude/session-*.md` left for the user to delete.
- **Constitution Art. I §5** updated to point proactive checkpointing at the per-repo session store.

### Removed
- **Dropped the dead `session-context.sh` hook.** It fired on `SessionStart` and wrote an environment snapshot (`~/.softspark/ai-toolkit/sessions/<id>.json`: pwd, git branch/status, node/python versions) that no hook, script, or tool ever read — pure write-only dead code (Constitution Art. VI.1). Removed the script, its `app/hooks.json` wiring, its entries across all 7 editor hook generators (cursor, windsurf, codex, devin, augment, gemini, opencode), its tests, and its catalog/overview docs. Editors that had it as the sole entry for an event (windsurf `post_setup_worktree`, codex `PostCompact`, gemini `BeforeModel`, devin `SessionStart`) drop that event. Not related to the session-storage change above — it never wrote to the repo.

---

## v4.9.0 - Epistemic integrity rules + deep-research skill + custom-rule leak fix (2026-06-15)

Minor release. Adds a constitution article on injection resistance and grounding, a new web-research methodology skill, and an anti-sycophancy/formatting pass across the voice layer. Also fixes a leak where a maintainer's personal registered rules were baked into the toolkit's own committed editor files. Skill count: 107 → 108. Constitution: 6 → 7 articles. Test count: 1196 → 1197.

### Added
- **`deep-research` skill** — new knowledge skill (`user-invocable: false`) for multi-source web research: retrieve-vs-answer gate, complexity-scaled search budget, query craft, primary-source preference, source-conflict skepticism, adversarial verification, and attribution-without-reproduction. The web/multi-source counterpart to `research-mastery` (KB-first). Skill count: 107 → 108.
- **Constitution Article VII — Epistemic & Injection Integrity** — instruction provenance (text in tool output, fetched pages, files, or pasted data is data, not commands; embedded instructions never escalate privileges or trigger destructive/exfiltrating actions) and no-fabrication (never invent files, APIs, versions, or citations; declare ungrounded when sources are empty). Constitution: 6 → 7 articles.
- **`AI_TOOLKIT_NO_CUSTOM_RULES` flag** — when set to `1`, `generator_base.py` and `generate_codex.py` skip injecting registered custom rules from `~/.softspark/ai-toolkit/rules/`. Set on the `generate:agents`, `generate:gemini`, and `generate:copilot` npm scripts so the toolkit's own canonical files never embed a maintainer's personal rules.
- **Anti-sycophancy rule** — `golden-rules` output style gains an "Honesty Over Agreeableness" section: re-check evidence before reversing a verified answer, own mistakes without excessive apology, never validate a wrong premise to be agreeable.
- **Formatting discipline** — `brand-voice` gains a "Formatting Discipline" section (default to prose, content-complexity list gating, minimum-substance bullets, no bullets when declining) and an "Accountable over apologetic" voice principle. `concise`/`strict` modes gain carve-outs: code/artifact quality is never reduced, the mode is suspended when the user asks for detail, and the mode is named only on user pushback.

### Changed
- **Research, verification, design, and MCP skills enriched** — `research-mastery` (retrieve-vs-answer gate, complexity-scaled budget, internal-first ladder, query craft, source skepticism, confabulation guard); `verification-before-completion` (don't-assume-it-exists, declare-ungrounded, pre-completion self-audit table); `design-engineering` (anti-slop checklist, minimum-scale floors, context-first discipline, question-budget gate, explore-many-variations, two-stage verification handoff); `mcp-patterns` / `mcp-builder` / `api-patterns` (tool-description rubric and parameter-documentation conventions); `security-patterns` (Prompt Injection & LLM-Output Trust section, cross-referencing Article VII).

### Fixed
- **Custom-rule leak in canonical editor files** — `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md` had a maintainer's personal registered rules (`~/.softspark/ai-toolkit/rules/*.md`) baked in by `generator_base.py` and `generate_codex.py`. Both injection sites are now gated behind `AI_TOOLKIT_NO_CUSTOM_RULES`, the three files regenerated clean (~131 lines of leaked config removed from each), and a regression test in `tests/test_metadata_contracts.bats` now fails if any non-toolkit `TOOLKIT:` marker reappears. Test count: 1196 → 1197.

---

## v4.8.0 - Devin CLI hooks (Cascade migration) (2026-06-10)

Minor release. Migrates the deprecated Windsurf Cascade hooks onto the Devin CLI surface ahead of the 2026-07-01 Cascade sunset. Class D/F ecosystem change per `kb/procedures/ecosystem-sync-sop.md`. No skill/agent count change; no new broad-access skills.

### Added
- **Devin CLI hooks** — new `scripts/generate_devin_hooks.py` emits `.devin/hooks.v1.json` in the Claude-compatible hook format Devin CLI uses (docs.devin.ai/cli/extensibility/hooks). Wired into `ai-toolkit install --local --editors windsurf --profile full` alongside the existing (now deprecated) Cascade generator. Events are Claude-style (`PreToolUse`/`PostToolUse`/`UserPromptSubmit`/`Stop`/`SessionStart`) with matchers on Devin tool names (`read`/`edit`/`exec`/`mcp__*`); blocking uses the flat `{"decision":"block","reason":...}` shape + exit 2 (no `AI_TOOLKIT_HOOK_FORMAT=json`). Reuses the existing `~/.softspark/ai-toolkit/hooks/*.sh` scripts; `_hook-io.sh` already parses Devin's flat `hook_event_name`/`tool_name`/`tool_input` payload, so no normalizer change was needed. Test count: 1186 → 1196.

### Changed
- **Cascade hooks deprecation** — `scripts/generate_windsurf_hooks.py` (`.windsurf/hooks.json`) is marked deprecated: the Cascade agent and its hook surface stop working 2026-07-01, and Devin Local / Devin CLI do not read `.windsurf/hooks.json` as a fallback. Both generators run during the transition; `generate_windsurf_hooks.py` will be dropped in the first release after the sunset.
- **Global hooks reach Devin for free** — documented that Devin CLI reads `~/.claude/settings.json` + `.claude/settings.json` hooks directly (`read_config_from.claude` default on), so a global `ai-toolkit install` already covers Devin even without the project-local file.
- Registry: `.devin/hooks.v1.json` + `generate_devin_hooks.py` added to the windsurf entry in `scripts/ecosystem_tools.json` and `kb/reference/supported-tools-registry.md`; new "Per-Editor Native Hooks" section in `kb/reference/hooks-catalog.md`. `validate.py` maps the `devin` hook-generator stem back to the windsurf README platform key.

---

## v4.7.0 - Devin Desktop .devin tree + Antigravity CLI surfaces (2026-06-10)

Minor release. Ecosystem sync per `kb/procedures/ecosystem-sync-sop.md` (window 2026-06-05 → 2026-06-10, doctor run + per-tool docs review with adversarial verification). No skill/agent count change; no new broad-access skills.

### Ecosystem (class B/D/F drift)
- **Windsurf/Devin Desktop: `.devin/` dual-emit** — `generate_windsurf_rules.py` and `generate_windsurf_skills.py` now write rules, workflows, and the skill pointer to `.devin/{rules,workflows,skills}/` (primary tree since the 2026-06-02 rebrand) alongside legacy `.windsurf/` (still read as fallback). `.devin/rules` added to editor auto-detection. Test count: 1179 → 1186.
- **Antigravity: CLI skill pointer** — `generate_antigravity.py` dual-emits the skill pointer to `.agent/skills/` (IDE) and `.agents/skills/` (CLI, plural). Editor auto-detection no longer misreads a pointer-only `.agents/skills/` as a Codex install.
- **Registry coverage** — added verified config surfaces to `scripts/ecosystem_tools.json`: Claude Code project `.claude/settings.json` + `.claude/rules/*.md` + `http` hook handler; Cursor subagent fallback dirs; Devin Local config files; Gemini CLI hook events (`BeforeToolSelection`, `AfterModel`, `Notification`, `PreCompress`) + `~/.agents/skills` alias; Cline CLI/SDK unified `.cline/` layout, `AGENTS.md` rules sources, and plugins; Augment workspace settings + `Notification` event; Codex project-layer `.codex/config.toml`; opencode skill discovery aliases; Antigravity CLI `.agents/{skills,hooks.json,mcp_config.json}`.

### Changed
- **Cascade deprecation note** — `.windsurf/hooks.json` (Cascade-scoped) marked deprecated: Cascade is available only through 2026-07-01; migration target is the Devin CLI lifecycle-hooks surface (tracked in registry status_note).
- **Cursor registry fix** — removed phantom `.cursor/rules/*.md` path (plain `.md` files are ignored by Cursor's rules system); fixed the stale claim in `generate_cursor_mdc.py` docstring.
- **Augment registry fix** — `.augment/guidelines.md` replaced with documented `.augment-guidelines` + `~/.augment/user-guidelines.md`; `our_generators` synced to all 6 augment generators.
- **Maintenance SOP** — added `claude --safe-mode` (v2.1.169) isolation step to the rule-enforcement troubleshooting flow.
- Doctor snapshot refreshed (Claude Code 2.1.170, Codex CLI 0.138.0); class-C items recorded as not adopted (`fallbackModel`, Copilot `excludeAgent`); opencode v1.16.0 experimental v2 skill registry tracked as a watch item.

---

## v4.6.0 - Editor ecosystem sync + Codex rules in AGENTS.md (2026-06-05)

Minor release. Syncs the editor registry with current upstream reality (Windsurf→Devin rebrand, Roo Code archive, Gemini CLI sunset, moved docs hosts) and fixes several generators that wrote to paths their editors never read. Headline: Codex now actually receives the universal coding rules.

### Added
- **Codex CLI: all 10 native hook events** — wired the 5 previously-missing events (`PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`) to the shared toolkit hook scripts, mirroring `app/hooks.json`. Was 5 of 10.

### Changed
- **Codex CLI: coding rules now in `AGENTS.md`** — the universal code-style/testing/security/output-mode rule bodies are inlined into `AGENTS.md`, the only instruction path Codex reads. They were previously emitted to `.agents/rules/`, which Codex never reads (confirmed against `developers.openai.com/codex`). Language rules continue via `.agents/skills/`.
- **Google Antigravity: plural `.agents/`** — generators now emit `.agents/rules/` and `.agents/workflows/` (the Antigravity 2.0 default); singular `.agent/` is still read by Antigravity as a fallback.
- **Conditional skill pointers** — Cursor/Cline/Augment skip the `ai-toolkit-skill-catalogue` pointer when real skills are discoverable at `.claude/skills/` (project or `~/.claude/skills/`), emitting it only as the editor-only fallback. Windsurf keeps its pointer unconditionally (its `.claude/skills` scan is gated behind a Devin "Claude Code config reading" setting).
- **Cursor subagents** — emit `model: inherit`; dropped the undocumented `tools`/`color` fields to match the current Cursor schema.
- **Augment subagents** — omit the `model` field (Augment uses the CLI default model; `inherit` is not a documented value).
- **Ecosystem registry sync** — Windsurf → Devin Desktop (docs/changelog redirects); Roo Code repo archived + docs moved to `roocodeinc.github.io`; Claude Code docs host `code.claude.com`; Codex docs `developers.openai.com/codex`; Gemini CLI free/paid tier sunset 2026-06-18 (enterprise continues); Cline config-path corrections; stale Gemini `Stop` marker dropped.

### Fixed
- **opencode commands were empty** — the prompt now lives in the markdown body. Commands previously put it in a `template:` frontmatter block (JSON-config-only) with an empty body, so every generated opencode command was effectively blank.
- **Cline global rules** — now written to `~/Documents/Cline/Rules/` (the documented Cline global path) instead of the never-read `~/.cline/rules/`.
- **Augment commands** — dropped the undocumented `agent:` frontmatter field; fixed a false `generate_augment_hooks.py` docstring claim about per-workspace settings.

### Removed
- **`scripts/generate_codex_rules.py`** and the `ai-toolkit codex-rules` / `npm run generate:codex-rules` subcommands — Codex never read the `.agents/rules/` output. Coding rules now ship via `AGENTS.md` (universal) and `.agents/skills/` (language). Installs need no migration; if you scripted `ai-toolkit codex-rules`, the rules are now produced by `ai-toolkit codex-md`. Test count: 1181 → 1179 (dead-path tests removed).

### Ecosystem
- Class B (integrate): Codex 10 hook events. Class E (now-default): Antigravity plural `.agents/`, conditional skill pointers. Class D (deprecation): Windsurf→Devin, Roo Code archive, Gemini CLI tier sunset. Plus registry URL/version/config-path corrections across 9 tools.

---

## v4.5.1 - ShellCheck fix for loop-guard hook (2026-06-02)

Patch release. Clears two ShellCheck `SC2034` warnings in `loop-guard.sh` that turned the `main` CI ShellCheck job red after v4.5.0. The publish workflow does not run ShellCheck, so v4.5.0 published despite the red CI; this patch makes `main` green again. No runtime behavior change.

### Fixed
- **`loop-guard.sh` ShellCheck** — `INPUT` now carries the `# shellcheck disable=SC2034` directive (it is consumed via the sourced `_hook-io.sh`, matching `guard-destructive.sh`), and `AI_TOOLKIT_HOOK_FORMAT` is `export`ed. `shellcheck --severity=warning app/hooks/*.sh` is clean.

---

## v4.5.0 - Unicode-safety scanner, loop guard, honest instincts (2026-06-02)

Minor release. Hardens the security audit against invisible prompt injection, adds a repeated-action loop guard, fixes destructive-guard false positives, and turns the instinct system from a dormant promise into a working manual feature.

### Added
- **Unicode-safety scanner** — `scripts/audit_skills.py` now flags invisible/smuggled Unicode across shipped prompt text (skills, agents, rules, personas, mcp-templates): tag-block ASCII smuggling (`U+E0000–E007F`) and Trojan Source bidi controls as HIGH, zero-width/invisible format chars as WARN. Emoji ZWJ (`U+200D`) is allowlisted. Runs inside the existing `--ci` gate.
- **`loop-guard.sh`** — advisory `PostToolUse` hook (`Bash|Edit|MultiEdit|Write`) that warns when the same action repeats within a short window, catching successful-but-identical loops the `/repeat` circuit breaker (failures-only) misses. Edits track content, so iterative editing of one file does not trip it. Tunable via `AI_TOOLKIT_LOOP_WINDOW`/`AI_TOOLKIT_LOOP_THRESHOLD`. Hook entries: 28 → 29.
- **Per-hook opt-out** — `AI_TOOLKIT_DISABLED_HOOKS` (comma list) disables named profile-gated hooks via `_profile-check.sh`. Safety guards are intentionally excluded — remove them with `ai-toolkit remove-hook`.
- **Editor hooks honesty** — the README platform matrix gained a **Hooks** column marking which editors get lifecycle hook enforcement; `validate.py` cross-checks the claim against the actual `generate_*_hooks.py` generators and fails on drift.
- **`doctor` language-rules drift check** — warns when a local-install project gained a language (e.g. a new `Cargo.toml`) whose `<lang>-rules` were never injected.
- **Live-app rubric verification** — `verification-before-completion` documents an optional weighted-rubric scoring pass for behavioral/visual work.

### Changed
- **Instincts load by default** — `session-start.sh` loads `.claude/instincts/*.md` whenever present (previously gated behind `AI_TOOLKIT_HOOK_VERBOSE=1`, so they never surfaced by default). `AI_TOOLKIT_HOOK_QUIET=1` suppresses; no instincts on disk means no output.
- **memory-pack `strip_private.py`** — now redacts high-confidence secrets (API keys, tokens, private keys) to `[REDACTED:<label>]` in addition to stripping `<private>` blocks before SQLite storage.

### Fixed
- **`guard-destructive.sh` false positives** — `git push --force-with-lease`/`--force-if-includes` are no longer blocked, and a single non-chained `echo`/`printf`/`git commit`/`git tag` carrying a destructive token as data (e.g. a commit message mentioning `DROP TABLE`) passes. Chained commands (`&&`, `||`, `;`, `|`) and real executions (e.g. `psql -c "DROP TABLE"`) are still inspected and blocked.
- **`instinct-review` documentation** — removed the false claim of an automatic session-end instinct extractor that never existed; the skill now documents the real manual authoring + curation flow.

Test count: 1151 → 1179. No skill/agent count change.

---

## v4.4.2 - Ecosystem sync: Claude Code 2.1.158 + Codex 0.134 hook events (2026-05-30)

Patch release. Syncs the tool registry and `hook-creator` skill with newly detected upstream hook events and refreshes the ecosystem drift snapshot. No generated output or runtime behavior changes.

### Changed

- **Claude Code hook events** - Recorded `MessageDisplay` (new in Claude Code 2.1.152) in `scripts/ecosystem_tools.json` and the `hook-creator` skill's Supported Hook Events table. Also added three real-but-untracked events to the registry: `PostToolUseFailure`, `PostToolBatch`, `UserPromptExpansion`.
- **Codex hook events** - Recorded the four Codex events we did not track (`PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`); Codex exposes 10 lifecycle events. Updated the `scripts/generate_codex_hooks.py` docstring (6 to 10) and `kb/reference/supported-tools-registry.md`.
- **Ecosystem snapshot** - Refreshed `benchmarks/ecosystem-doctor-snapshot.json` to baseline Claude Code 2.1.158 and Codex 0.134, and bumped the registry `last_updated`.

### Ecosystem

- Class-B drift (new Claude Code and Codex hook events) tracked in the registry and skill docs; wiring the Codex subagent/compaction events into generated `.codex/hooks.json` is deferred to a future release. GitHub Copilot docs reorg classified class C (not adopted). Seven editors showed cosmetic-only doc drift (class A).

### Verification

- `python3 scripts/validate.py --strict`
- `python3 scripts/ecosystem_doctor.py --offline --check`
- `npm test` (1151 passing)

## v4.4.1 - Codex hook output compatibility fix (2026-05-25)

Patch release. Fixes Codex `UserPromptSubmit` hook JSON validation failures and visible hook-context noise while preserving hook side effects.

### Fixed

- **Codex `UserPromptSubmit` default output** - generated Codex hooks now keep `user-prompt-submit.sh` in quiet plain-text mode, preserving search-first flag side effects without emitting visible `additionalContext` in the Codex TUI.
- **Event-specific JSON context** - `hook_emit_context` can include `hookSpecificOutput.hookEventName`, and `user-prompt-submit.sh` emits `"UserPromptSubmit"` with `additionalContext` when JSON context mode is explicitly enabled.
- **Prompt hook output corruption** - `user-prompt-submit.sh` now suppresses filesystem redirection errors when search-first state writes are blocked by sandboxing or local permissions, keeping JSON output parseable.
- **Usage tracking tracebacks** - `track-usage.sh` now treats stats writes as best-effort and suppresses Python tracebacks when `~/.softspark/ai-toolkit/stats.json` cannot be written.

### Verification

- `bats tests/test_hooks.bats --filter 'track-usage|user-prompt-submit|post-tool-use'`
- `python3 scripts/validate.py --strict`

## v4.4.0 - native editor skill pointers and hook governance hardening (2026-05-25)

Minor release. Adds native skill pointer generation for more editor surfaces and hardens search-first governance so quiet hooks still inject model context without noisy transcript output.

### Added

- **Native editor skill pointers** - Added Cursor, Windsurf, and Cline skill pointer generators so supported editors can discover the ai-toolkit skill catalog through their native skill directories.
- **Shared skill pointer builder** - Added `scripts/skill_pointer.py` to keep generated skill pointer metadata consistent across editor-specific generators.
- **Release coverage** - Added generator and hook tests covering the new skill pointer outputs, quiet JSON `UserPromptSubmit` context, and noisy Codex search-first log fallback.

### Changed

- **Editor registry and install flow** - Updated supported-tool metadata and install behavior for Cursor, Windsurf, and Cline native skill pointer targets.
- **Codex hook generation** - `scripts/generate_codex_hooks.py` now emits quiet JSON context for `user-prompt-submit.sh`, matching Claude Code's installed hook behavior.
- **Hook runtime documentation** - Updated the hooks catalog, Codex compatibility notes, global install model, supported tools registry, and maintenance SOP with the new runtime behavior.

### Fixed

- **Quiet hook context injection** - `_hook-io.sh` now lets `AI_TOOLKIT_HOOK_FORMAT=json` emit `hookSpecificOutput.additionalContext` even when `AI_TOOLKIT_HOOK_QUIET=1` is set.
- **Search-first false positives in Codex** - `stop-search-check.sh` now scans a larger recent Codex log window and recognizes both `ToolCall: mcp__...__smart_query` and `tool.name="smart_query"` log shapes.
- **Installed runtime drift** - Claude and Codex hook manifests now install `UserPromptSubmit` with `AI_TOOLKIT_HOOK_QUIET=1 AI_TOOLKIT_HOOK_FORMAT=json`.

### Ecosystem

- **Snapshot refresh** - Refreshed the ecosystem doctor snapshot after upstream documentation/content drift review and generator updates.

### Verification

- `bats tests/test_generators.bats`
- `bats tests/test_cli.bats`
- `bats tests/test_skills_native.bats tests/test_native_surfaces.bats`
- `bats tests/test_hooks.bats tests/test_search_first_flow.bats`
- `bats tests/test_install.bats tests/test_codex.bats`
- `python3 scripts/validate.py --strict`
- `git diff --check`

---

## v4.3.3 - silent hook context roll-forward (2026-05-21)

Patch release. Rolls forward the quiet-hook release with a stricter default: non-blocking plain-text hook context is now silent even when a runtime uses a stale or manually copied command without `AI_TOOLKIT_HOOK_QUIET=1`.

### Fixed

- **Silent plain-text context by default** - non-blocking hook context output now requires `AI_TOOLKIT_HOOK_VERBOSE=1` in plain-text mode, so prompt-submit and startup reminders do not leak into the visible chat window.
- **SessionStart default output** - `session-start.sh` keeps session-state reset, stale search-flag cleanup, and update-notification side effects, but no longer prints startup reminders or loaded context unless verbose mode is enabled.

### Changed

- **Hook output helper** - `_hook-io.sh` supports `AI_TOOLKIT_HOOK_VERBOSE=1` for local debugging while keeping plain-text context silent by default.
- **Runtime hook docs** - `kb/reference/hooks-catalog.md` and `kb/reference/codex-cli-compatibility.md` document the new silent-by-default behavior and verbose opt-in.

### Tests

- **Silent default coverage** - `tests/test_hooks.bats` now verifies default silence for `SessionStart` and `UserPromptSubmit`, plus verbose opt-in for the same context messages.

### Verification

- `npm test` - 1144 passing.
- `python3 scripts/validate.py --strict` - passed.

---

## v4.3.2 - quiet hooks and no-RAG search-first hardening (2026-05-21)

Patch release. Fixes noisy lifecycle hook output in Codex and Claude prompt-submit flows while preserving search-first enforcement and blocking decisions.

### Fixed

- **Quiet Codex startup hooks** - `scripts/generate_codex_hooks.py` now prefixes generated Codex hook commands with `AI_TOOLKIT_HOOK_QUIET=1`, preventing informational `SessionStart` and prompt reminders from appearing as visible hook context.
- **Quiet Claude prompt-submit hook** - `app/hooks.json` now installs `user-prompt-submit.sh` with `AI_TOOLKIT_HOOK_QUIET=1`, suppressing non-blocking prompt governance output while still arming the per-session search-first flag.
- **No-RAG false positives** - `_search-capability.sh` now detects search providers from actual MCP server definitions only, so hook matchers and permission allowlists no longer make no-RAG installs block incorrectly.
- **Codex search tracking gap** - `stop-search-check.sh` now checks the Codex TUI log for search tool calls after the search-first flag timestamp before blocking, covering Codex MCP calls that do not fire the shared `PostToolUse` tracker.

### Changed

- **Hook output helper** - `_hook-io.sh` supports `AI_TOOLKIT_HOOK_QUIET=1` for non-blocking context output.
- **Runtime hook docs** - `kb/reference/hooks-catalog.md` and `kb/reference/codex-cli-compatibility.md` document quiet mode and the Codex search-first fallback.
- **Manifest hook count** - `manifest.json` now describes the current 28 hook entries across 14 lifecycle events.

### Tests

- **Hook quiet-mode coverage** - `tests/test_hooks.bats`, `tests/test_codex.bats`, and `tests/test_install.bats` cover quiet mode for `SessionStart`, `UserPromptSubmit`, `PostToolUse`, Codex hook generation, and installed Claude hook configuration.
- **Search-first flow coverage** - `tests/test_search_first_flow.bats` covers real-provider detection, no-RAG behavior, custom `customer-rag` style providers, and Codex log fallback.

### Ecosystem

- **Snapshot refresh** - `benchmarks/ecosystem-doctor-snapshot.json` refreshed after class A/C upstream documentation and version drift review. No generator contract changes were required.

### Verification

- `npm test` - 1142 passing.
- `python3 scripts/validate.py --strict` - passed.
- `python3 scripts/audit_skills.py --ci` - passed with 0 HIGH / 0 WARN.

---

## v4.3.1 - per-session search-first flag (2026-05-19)

Patch release. Fixes a cross-session race condition in the search-first enforcement trio (`user-prompt-submit.sh` + `search-tracker.sh` + `stop-search-check.sh`): the single global flag file `~/.softspark/ai-toolkit/state/search-required.flag` was shared by every parallel Claude Code window, so a Stop in session B could consume session A's flag (or vice versa), blocking unrelated turns with someone else's prompt. Also unblocks `bats 1.13` regression in the test-cohesion runner default.

### Fixed

- **Search-first flag is now per-session** - `user-prompt-submit.sh`, `search-tracker.sh`, and `stop-search-check.sh` key the flag by `session_id` from the hook stdin payload (`search-required-<session_id>.flag`), falling back to `transcript_path` basename, then `default`. Parallel sessions no longer interfere with each other. Each Stop check reads only its own session's flag.
- **`bats 1.13` regression in test-cohesion runner** - `scripts/test_cohesion.py` no longer passes `--no-parallelize-within-files` (now requires `--jobs 2` in bats 1.13). Default sequential mode is used, which is what the hook expected anyway.

### Added

- **`hook_session_id()` helper in `_hook-io.sh`** - Resolves and sanitizes the per-session key for any hook that needs to scope state to a single Claude Code window.
- **`session-start.sh` GC** - Stale per-session search-required flags older than 60 minutes are deleted on every `SessionStart`, so crashed sessions do not leave residue.
- **Two new bats tests** in `tests/test_search_first_flow.bats` verifying per-session isolation and that `search-tracker` only clears its own session's flag.

### Changed

- **`kb/reference/hooks-catalog.md`** - Documents the new per-session flag layout, GC behavior, and isolation guarantee.
- **`README.md`** - Test count badge 1131 → 1133.

---

## v4.3.0 - inject-mcp extension API (2026-05-12)

Minor release. Closes the asymmetry between `inject-rule` / `inject-hook` and MCP servers by adding `inject-mcp` and `remove-mcp` as first-class members of the extension API. External tools (rag-mcp, jira-mcp, custom integrations) can now register their MCP templates the same way they register rules and hooks -- from a local file or HTTPS URL, with full editor propagation and auto-refresh on `ai-toolkit update`.

### Added

- **`ai-toolkit inject-mcp <file|url> [--name <name>] [--force]`** - Inject an external MCP server template into `~/.mcp.json` (toolkit source-of-truth) and propagate it to every editor with a `global_path` (Claude, Cursor, Codex, Gemini, Windsurf, Cline, Augment, Copilot). Servers in `~/.mcp.json` are tagged with `_source` for idempotent re-injection; native editor configs receive the same servers without `_source`.
- **`ai-toolkit remove-mcp <name>`** - Strip all servers tagged with the given source from `~/.mcp.json` and every editor config, unregister URL sources, and remove cached template files.
- **`--name <name>` flag** - Override the auto-derived source name for both local files and URLs. Required when filename stem is generic (e.g., `mcp-template.json` → `--name rag-mcp`).
- **`--force` flag** - Overwrite servers tagged with a different `_source`. Without `--force`, collisions exit with code 3. Entries tagged `"_source": "ai-toolkit"` are protected even with `--force`.
- **URL fetch + cache + auto-refresh** - HTTPS templates are cached in `~/.softspark/ai-toolkit/mcp-templates/external/<name>.json` and registered in `sources.json` with sha256 pin. On every `ai-toolkit update`, URL-sourced templates are re-fetched and re-injected; cached version is used on fetch failure.
- **`scripts/mcp_sources.py`** - Source registry for external MCP templates, mirroring `hook_sources.py`.
- **`scripts/inject_mcp_cli.py`** - CLI entry point implementing both inject and remove modes.
- **`refresh_url_mcp()` in `install_steps/markers.py`** - Update flow integration, called from `install.py` alongside `refresh_url_hooks()`.

### Changed

- **`paths.py`** - Added `MCP_TEMPLATES_DIR` and `EXTERNAL_MCP_DIR` constants.
- **`bin/ai-toolkit.js`** - Registered `inject-mcp` / `remove-mcp` handlers and help text.
- **`kb/reference/extension-api.md`** - Documented inject-mcp / remove-mcp + flags. Version bumped to 1.5.0.
- **`kb/reference/mcp-templates.md`** - Added External Templates section pointing to inject-mcp. Version bumped to 1.2.0.

### Tests

- **`tests/test_inject_mcp.bats`** - 15 bats cases covering local-file inject, URL fetch via fixture, `--name` override, `--force` collision override, ai-toolkit source protection, idempotent re-inject, editor propagation to Cursor (JSON) and Codex (TOML), `_source` strip from native configs, sources.json registry, `--remove` cleanup, HTTPS-only enforcement.

### Verification

- 15/15 bats cases passing in `test_inject_mcp.bats`.
- E2E smoke test: injecting an external `mcp-template.json` writes 9 files (`~/.mcp.json` + 8 editor configs) with `_source` only in source-of-truth and stripped from native configs.
- No regressions in `test_inject_hook.bats` or `test_mcp_manager.bats`.

---

## v4.2.5 - Hook safety and no-RAG compatibility (2026-05-12)

Patch release. Hardens Claude Code hook enforcement while keeping the toolkit safe for users who do not have RAG/MCP search providers installed.

### Added

- **Capability-aware search hooks** - Added shared search capability detection so search-first enforcement uses RAG/MCP when available and degrades to guidance when no provider is installed.
- **Revert guard** - Added destructive Git restore/checkout protection that blocks unsafe rollback commands when they would discard unrelated user work.
- **Test cohesion hook** - Added source-to-test mapping for focused Bats verification after relevant edits, with project-level override support.
- **Hook payload adapter** - Added shared hook input/output helpers for consistent Claude, Gemini, Augment, Codex, Cursor, and Windsurf hook payload handling.

### Changed

- **Hook installation** - Installs hook JSON maps and runtime helper scripts needed by the new hooks into the global toolkit runtime directory.
- **Generated editor configs** - Regenerated multi-editor hook guidance and project agent surfaces after the hook expansion.

### Fixed

- **No-RAG installs** - Search-first hooks no longer block users who installed the toolkit without `rag-mcp` or another supported search provider.
- **Doctor coverage** - `ai-toolkit doctor` now verifies the new hook helper scripts and runtime hook files.

### Ecosystem

- Refreshed `benchmarks/ecosystem-doctor-snapshot.json` after class-A documentation drift only: upstream docs changed content hashes without heading or marker deltas.

### Verification

- `npm view @softspark/ai-toolkit version`: latest published version is `4.2.4`; `4.2.5` is available.
- Local Claude test confirmed RAG-backed prompts still call `rag-mcp` when present.
- Local Claude destructive-revert scenario was refused before data loss.

---

## v4.2.4 - GitHub Actions Node 24 readiness (2026-05-12)

Patch release. Removes GitHub Actions Node 20 action-runtime deprecation warnings from CI, publish, and reusable action surfaces.

### Changed

- **GitHub Actions runtime** - Updated `actions/setup-node` from `v4` to `v6` in CI, publish, and reusable composite action workflows.
- **Generated CI guidance** - Refreshed CI templates, CI/CD skill examples, Docker DevOps examples, and LLM index output to use current GitHub Actions action versions.

### Verification

- Source checked against the official [`actions/setup-node` documentation](https://github.com/actions/setup-node), which documents `v6` usage and Node 24 action runtime support.

---

## v4.2.3 - SEO FAQ rich results deprecation (2026-05-12)

Patch release. Updates `seo-specialist` guidance after Google deprecated FAQ rich results.

### Changed

- **SEO structured data guidance** - `seo-specialist` now treats `FAQPage` as deprecated for Google rich results and recommends keeping it only when explicitly targeting non-Google engines.
- **Citability schema checklist** - Prioritizes `Article`, `HowTo`, `QAPage`, and `Person` schema guidance for Google-facing SEO/GEO work.

### Verification

- Source checked against [Google Search Central `FAQPage` structured data documentation](https://developers.google.com/search/docs/appearance/structured-data/faqpage).

---

## v4.2.2 - Legacy hook duplicate cleanup (2026-05-12)

Patch release. Cleans up legacy untagged hook duplicates found during post-release verification of v4.2.1.

### Fixed

- **Legacy notification hook cleanup** - `scripts/merge-hooks.py` now removes old direct `osascript` notification hooks from pre-script installs while preserving user-owned notification hooks.
- **External hook duplicate cleanup** - `scripts/inject_hook_cli.py` now removes legacy untagged entries matching the same event, matcher, and handler payload as the external hook being re-injected.

### Verification

- `bats tests/test_merge_hooks_statusline.bats tests/test_inject_hook.bats`: 42/42 passing.
- Local `~/.claude/settings.json`: 0 behavior duplicates, 0 exact duplicates, 0 untagged hook groups after cleanup.

---

## v4.2.1 - Claude Code hook enforcement and README cleanup (2026-05-12)

Patch release. Tightens Claude Code runtime enforcement, fixes duplicated hook cleanup during install/update, and removes the README hero image for release.

### Changed

- **Stop quality gate** - Registered `quality-gate.sh` for `Stop` in addition to `TaskCompleted`, so final Claude Code responses are blocked when supported lint/type checks fail.
- **README release surface** - Removed the README hero image block while keeping badges and release notes intact.
- **Runtime guidance** - Clarified in `CLAUDE.md` that Claude Code consumes `CLAUDE.md`, settings, hooks, skills, and agents, while `AGENTS.md` is generated for Codex/OpenCode/Gemini compatibility.

### Fixed

- **Quality gate exit codes** - Reworked shell pipelines so `ruff`, `tsc`, `dart analyze`, `phpstan`, and `go test` failures are not masked by output truncation.
- **Hook merge cleanup** - `scripts/merge-hooks.py` now removes legacy untagged ai-toolkit hook entries matching current toolkit hook signatures while preserving custom hooks.

### Ecosystem

- Refreshed `benchmarks/ecosystem-doctor-snapshot.json` for current editor/runtime docs. Claude Code now exposes `Stop` in docs; the toolkit already supported `Stop` hooks, and this release registers the strict quality gate there.

### Verification

- `python3 scripts/ecosystem_doctor.py --offline --check`: no drift.
- `python3 scripts/validate.py --strict`: 0 errors, 0 warnings.
- `python3 scripts/audit_skills.py --ci`: HIGH 0, WARN 0.
- `npm test`: 1049/1049 passing.
- `npm --cache /tmp/ai-toolkit-npm-cache pack --dry-run`: `softspark-ai-toolkit-4.2.1.tgz`.

---

## v4.2.0 - SEO GEO pipeline and release gate hardening (2026-05-07)

Minor release. Adds AI pipeline, content citability, and topical authority guidance to `seo-validate` from PR #9 by @fakenso, and keeps the release gate fixes prepared for v4.1.1 in the same unreleased train.

### Added

- **SEO AI pipeline reference** - Added `app/skills/seo-validate/reference/ai-pipeline.md` covering the Prepare/Retrieve/Signal/Serve pipeline, ranking signals, Query Fan Out, and format routing.
- **Content citability reference** - Added `app/skills/seo-validate/reference/content-citability.md` covering chunk architecture, semantic triples, hedging patterns, decision frameworks, contrast patterns, negative definitions, freshness, and E-E-A-T.
- **Topical authority scope** - Added `--scope topical` to `seo-validate`, with checks for pillar/cluster structure, internal link density, generic anchors, orphan pages, ID-based slugs, and keyword cannibalization.
- **Expanded GEO guidance** - Expanded Category 6 from INFO-only guidance to INFO/WARN heuristics for chunk boundaries, author quality, and freshness. Updated `seo-specialist` with AI pipeline, multi-platform SEO, and topical authority responsibilities.

### Fixed

- **URL rule registration test** - Replaced the live `raw.githubusercontent.com` dependency with a local fixture path guarded by `AI_TOOLKIT_TEST_MODE=1`, keeping production URL fetching HTTPS-only while making the full Bats suite hermetic.
- **Release validation gate** - Updated CI and `prepublishOnly` to run `python3 scripts/validate.py --strict`, matching the release preparation SOP.

### Verification

- `npm test`: 1047/1047 passing.
- `python3 scripts/validate.py --strict`: 0 errors, 0 warnings.
- `python3 scripts/audit_skills.py --ci`: HIGH 0, WARN 0.
- `python3 scripts/evaluate_skills.py`: 107/107 passing.

---

## v4.1.0 — Default `output-mode: concise` propagated to all editors (2026-05-06)

Minor release. Adds a global `output-mode: concise` directive that propagates to every editor config produced by ai-toolkit. Reduces token usage and removes preamble/filler from assistant responses across Claude Code, Cursor, Windsurf, Cline, Roo Code, Augment, Codex, Antigravity, GitHub Copilot, Gemini CLI, and Aider.

### Added

- **`app/rules/output-mode.md`** — auto-injected into `~/.claude/CLAUDE.md` (global) and project-local `CLAUDE.md` via the existing `inject_rules()` mechanism on every `ai-toolkit install` / `ai-toolkit update`.
- **`rule_output_mode()` in `scripts/dir_rules_shared.py`** — registered in `STANDARD_RULES`, so directory-based generators (Cursor `.mdc`, Windsurf, Cline, Roo, Augment, Codex, Antigravity) emit a dedicated `ai-toolkit-output-mode.md` file alongside the other six standard rules.
- **Output Mode block in `scripts/generator_base.render_generator()`** — single-file editor outputs (`GEMINI.md`, `.github/copilot-instructions.md`, `.cursorrules`, Aider `CONVENTIONS.md`) now include the directive between TOOLKIT markers.

### Directives

The `concise` mode applies these rules to assistant responses:

- No preamble — skip "I'll now…", "Sure, let me…", "Great question!"
- Lead with the result; explanation only if asked or non-obvious.
- Max 3 sentences per closed question.
- Tables and lists over prose for comparisons, steps, values.
- No trailing summaries when the diff or output already shows what changed.
- Drop filler adjectives ("nice", "great", "powerful", "robust").
- Cite as `path:line`, not paragraphs of location prose.
- Escalate to verbose only for architecture / RFC / ADR / trade-off documents or explicit user request.

### Changed

- **Standard rule count for directory-based generators: 6 → 7**. Tests updated: `tests/test_generators.bats` (count assertions in two cases bumped from 6/8 to 7/9).

### How to opt out

- Per-session: `/brand-voice default` (or `/brand-voice strict` for tighter)
- Per-project: edit `output-mode:` value in project's `CLAUDE.md` or strip the `<!-- TOOLKIT:output-mode -->` block manually
- Re-install without rules: `ai-toolkit install --skip rules`

### Why

User feedback after v4.0.x consolidation: asked for a hook-like mechanism to enforce concise responses. The `brand-voice` skill already had `concise`/`strict` modes (shipped v3.2.0) but activation required per-project opt-in. This release flips the default to opt-out — every editor that consumes ai-toolkit configs now sees the directive immediately after install/update.

---

## v4.0.1 — CI hotfix: README "What You Get" table counts (2026-05-06)

Patch release. Fixes CI failure on v4.0.0 main branch — three `tests/test_metadata_contracts.bats` cases failed because the `What You Get` table in `README.md` and the skill type table in `kb/reference/architecture-overview.md` still referenced pre-consolidation counts (32 task / 32 hybrid / 48 knowledge).

### Fixed

- **README.md `What You Get` table**: hybrid 32 → 30, knowledge 48 → 45 (task unchanged at 32; total 107).
- **`kb/reference/architecture-overview.md`**: same correction in the skill type table.
- **`manifest.json`**: skill subtype description updated from `(30 task + 31 hybrid + 46 knowledge)` to the correct `(32 task + 30 hybrid + 45 knowledge)`.

### Why

v4.0.0 release path missed these three count locations. They are gated by the metadata contract test suite, which I misread locally (the trailing `ok 1047` line is the *last test number*, not a pass count). Confirmed by re-running `bats tests/test_metadata_contracts.bats` directly, which shows three `not ok` failures.

### Process note

Lesson for future releases: always inspect `bats … 2>&1 | grep "^not ok"` rather than trusting tail of npm test. Updating the release-verification SOP separately.

---

## v4.0.0 — Skill consolidation: 112 → 107, removes 5 overlapping skills (2026-05-06)

**Breaking release.** Five redundant skills removed; their substantive knowledge migrated into the surviving targets. Resolves the `/skills` listing truncation that v3.5.x partially addressed and removes user-facing overlap that made dispatch ambiguous.

### Removed (BREAKING)

- **`/search`** (task skill) — `/research-mastery` is the superset, now includes local Grep/Glob fallback for the no-MCP case.
- **`/teams`** (task skill) — `/workflow` covers all preset scenarios (debug, feature, security, migration, etc.) without requiring `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- **`plan-writing`** (knowledge skill) — estimation patterns and pre-mortem rules merged into `/plan`.
- **`debugging-tactics`** (knowledge skill) — Iron Law, 4-phase methodology, and "5 Whys" merged into `/debug`.
- **`hive-mind`** (knowledge skill) — consensus voting and aggregation rules merged into `/swarm`.

### Changed

- **`/plan`** — added Estimation & Templates section (T-shirt sizing, cone of uncertainty, SMART vs phase-aligned outcomes, mandatory pre-mortem ≥5 failure modes).
- **`/debug`** — added Methodology section (Iron Law, 4 phases, "5 Whys" depth gate, architecture escalation after 3 failed fixes).
- **`/swarm`** — Aggregation section now covers consensus weighted voting and file-ownership escalation rules previously in `hive-mind`.
- **`/research-mastery`** — added Local Fallback section for Grep/Glob when `rag-mcp` is unavailable.
- **Agent `skills:` field** — `orchestrator`, `product-manager`, `chief-of-staff` switched from `plan-writing` to `plan`. `meta-architect`, `night-watchman`, `predictive-analyst` switched from `debugging-tactics` to `debug`.
- **`research-pack` plugin** — dropped `search`, `plan-writing` from skill list; added `plan`.
- **Cross-references** — `/refactor-plan`, `/persona`, `/explore`, `/mem-search`, `/explain`, `/index` updated to reference surviving skills.
- **`scripts/codex_skill_adapter.py`** — removed dead `teams`-specific branch; `_adapt_body` no longer takes `skill_name`.
- **Documentation counts** — `README.md`, `package.json`, `manifest.json`, `app/ARCHITECTURE.md`, `kb/reference/skills-catalog.md` updated from 112 → 107.

### Migration

| Before | After |
|--------|-------|
| `/search <query>` | `/research-mastery <query>` |
| `/teams <preset>` | `/workflow <type>` |
| Agent `skills: plan-writing` | Agent `skills: plan` |
| Agent `skills: debugging-tactics` | Agent `skills: debug` |
| Agent `skills: hive-mind` | Agent `skills: swarm` |

### Why

`/skills` listing reported 2.1%/2% truncation in Claude Code 2.1.131 — 5 descriptions silently dropped. v3.5.x trimmed individual descriptions; v4.0.0 removes the underlying overlap (5 skills with knowledge already covered elsewhere). Net effect: smaller listing, no lost knowledge, clearer dispatch.

---

## v3.5.1 — Description trim follow-up + GEMINI/Copilot drift fix (2026-05-06)

Patch release. Continues v3.5.0 condensation on 20 skills and re-syncs platform artifacts that v3.5.0 forgot to regenerate.

### Changed

- **20 skills with further trimmed descriptions** — `a11y-validate`, `api-patterns`, `app-builder`, `architecture-audit`, `biz-scan`, `ci-cd-patterns`, `design-an-interface`, `docker-devops`, `evolve`, `flutter-patterns`, `git-mastery`, `hive-mind`, `mcp-patterns`, `migrate`, `migration-patterns`, `observability-patterns`, `performance-profiling`, `plan-writing`, `research-mastery`, `typescript-patterns`. Drops redundant trigger keywords already implied by the summary.
- **`AGENTS.md`, `llms-full.txt`** regenerated to match the new descriptions.

### Fixed

- **`GEMINI.md` and `.github/copilot-instructions.md`** were not regenerated by the v3.5.0 release commit — they still carried pre-v3.5.0 verbose descriptions. Both now refreshed via `npm run generate:all`.
- **`/audit.sarif`** added to `.gitignore` so output from `audit_skills.py --ci` does not pollute `git status`.

### Why

Drift in two generated platform files was visible only after running `npm run generate:all` on a clean v3.5.0 checkout. The fix is mechanical and contains no behavior change beyond the description tweaks.

---

## v3.5.0 — Skill description condensation: 33% smaller, consistent pattern (2026-05-06)

Minor release. All 112 skill descriptions rewritten into a single consistent pattern: short summary, then `Triggers: <comma-separated keywords>.` Drops the verbose "Load when..." tail entirely. Consequence: Claude Code's skill listing fits in ~2% context budget without truncation, and the trigger lists stay intact for accurate auto-loading.

### Changed

- **All 112 `app/skills/*/SKILL.md` `description:` fields** rewritten to a single pattern: `<short summary>. Triggers: <comma-separated keywords>.` Verbose explanations and "Load when..." tails removed.
- **Total description length: 26 465 → 17 837 chars (~6 616 → ~4 459 tokens, 33% reduction)** measured at description-frontmatter level.
- **Top offenders cut hardest** — `a11y-validate` (393 → 192), `testing-patterns` (391 → 174), `typescript-patterns` (386 → 186), `security-patterns` (376 → 179), `research-mastery` (376 → 198), `rag-patterns` (374 → 174), `documentation-standards` (371 → 179), `mcp-patterns` (370 → 185), `docker-devops` (369 → 188), `performance-profiling` (368 → 197).
- **`scripts/generate_language_rules_skills.py`** generator template updated to emit the same condensed pattern, so `<lang>-rules` skills stay consistent on regeneration. All 9 language-rules skills regenerated.

### Why

`/doctor` reported "Skill listing will be truncated: 60 descriptions dropped (1% budget)" then "30 dropped (2% budget)". Trigger keywords were getting silently stripped from less-used skills, breaking auto-loading. The fix is description-side, not budget-side: tighter descriptions mean Claude Code can keep all 112 in a normal 2% budget with headroom.

### Migration

- No breaking changes. All trigger keywords preserved.
- Skills auto-load on the same triggers as before.
- If you customized `app/skills/<name>/SKILL.md` description, your edit is preserved (only ai-toolkit-shipped skills were touched).

---

## v3.4.1 — URL-tracked sources protected from path-write demotion (2026-05-06)

Patch release. Fixes a regression introduced in v3.4.0 where `ai-toolkit update` could rewrite a URL-tracked hook entry into a local-path entry.

### Fixed

- **`register_path_source` no longer overwrites URL entries** in `scripts/hook_sources.py` and `scripts/rule_sources.py`. The function now returns early when an existing entry has a `url` field. Previously, `scripts/install_steps/markers.py:refresh_url_hooks` re-injected URL hooks from their cached file, and `inject_hook_cli.py` would call `register_path_source` with that cached path — silently demoting the URL record to a local one on every update.
- **Regression test** in `tests/test_inject_hook.bats` that pre-seeds a URL entry, runs the local-path inject path, and asserts the URL entry survives untouched.

### Recovery

- If your `~/.softspark/ai-toolkit/hooks/external/sources.json` has a `path` instead of a `url` for a hook that was originally URL-installed, run `ai-toolkit remove-hook <name>` followed by `ai-toolkit inject-hook <original-url>` to re-register from the URL.

---

## v3.4.0 — Local-path source tracking & orphan detection (2026-05-06)

Minor release. Closes the visibility gap for rules and hooks installed from local files: `add-rule` and `inject-hook` now record the origin path in `sources.json`, and `status` flags any rule files on disk that have no source recorded.

### Added

- **`register_path_source()` in `scripts/rule_sources.py` and `scripts/hook_sources.py`** — records `{"path": <abs_path>, "fetched_at": ..., "sha256": ...}` for local-file injections. Schema-compatible with existing URL entries (mutually exclusive `url` vs `path` field, `schema_version` unchanged at 1).
- **`add-rule` registers local paths** — `scripts/add_rule.py` now calls `register_path_source` after copying a local file, and prints the origin path with a hint to re-run `add-rule` to refresh.
- **`inject-hook` registers local paths** — `scripts/inject_hook_cli.py` writes a `path`-tracked entry into `~/.softspark/ai-toolkit/hooks/external/sources.json` for file-sourced hooks. URL behavior unchanged. Registration failures are non-fatal — injection always proceeds.
- **`ai-toolkit status` distinguishes URL vs local sources** — local-path entries display the absolute path with a `[local]` tag; URL entries display the URL. Format: `rule  <name>  <- <origin>[ [local]] (<fetched_at>)`.
- **Orphan rule detection in `status`** — files in `~/.softspark/ai-toolkit/rules/` that have no entry in `sources.json` are listed as `(orphan, no source recorded — re-run add-rule)`. Surfaces rules registered before the registry existed (pre-v3.3.0).

### Migration

- Existing URL-tracked sources continue to work unchanged.
- To upgrade an orphan local rule into the registry, re-run `ai-toolkit add-rule <path>` from the rule's source directory. The new run records the path.

---

## v3.3.0 — External-source visibility & skill-listing budget default (2026-05-06)

Minor release. Two coordinated install-time additions: `ai-toolkit status` now surfaces every registered external rule and hook, and fresh installs / updates set a sane `skillListingBudgetFraction` so all 112 skill descriptions stay loadable in Claude Code.

### Added

- **`ai-toolkit status` shows external sources** — `scripts/install_steps/install_state.py` reads `~/.softspark/ai-toolkit/rules/sources.json` and `~/.softspark/ai-toolkit/hooks/external/sources.json` and prints an `External sources:` section listing each registered rule/hook with its source URL and last-fetched timestamp. The section is omitted entirely when no external sources are registered. Closes the long-standing gap where `add-rule`/`inject-hook` had no read-side counterpart.
- **`skillListingBudgetFraction` default in `~/.claude/settings.json`** — new `_install_skill_listing_budget()` step in `scripts/install_steps/hooks.py` writes `"skillListingBudgetFraction": 0.02` on install/update, but only when the key is absent. Existing user values are never overwritten. Prevents Claude Code's default 1% budget from truncating ~60 of the toolkit's 112 skill descriptions.

### Changed

- **`ai-toolkit status` help text** — updated in `bin/ai-toolkit.js` to mention external rules/hooks alongside modules, version, and profile.



Patch release. Lint-only fix in the default status line hook — no behavior change.

### Fixed

- **`app/hooks/ai-toolkit-statusline.sh` shellcheck warnings** — removed the unused `C_GRAY` color variable (SC2034) and replaced the deprecated `[ p -o q ]` form with `{ [ p ] || [ q ]; }` (SC2166). CI shellcheck gate at `--severity=warning` now passes clean across `app/hooks/*.sh`.

---

## v3.2.1 — Statusline shellcheck cleanup (2026-05-04)

Patch release. Lint-only fix in the default status line hook — no behavior change.

### Fixed

- **`app/hooks/ai-toolkit-statusline.sh` shellcheck warnings** — removed the unused `C_GRAY` color variable (SC2034) and replaced the deprecated `[ p -o q ]` form with `{ [ p ] || [ q ]; }` (SC2166). CI shellcheck gate at `--severity=warning` now passes clean across `app/hooks/*.sh`.

---

## v3.2.0 — Output discipline & token-aware status line (2026-05-04)

Minor release. Two coordinated additions: per-response output discipline and a real-token status line installed by default.

### Added

- **`brand-voice` output modes** — `concise` (≤60% tokens) and `strict` (≤40% tokens) extend the existing brand-voice skill with response-length governance. Activate via `output-mode: concise` in project `CLAUDE.md` or `/brand-voice concise`. Mode rules in `app/skills/brand-voice/modes/`.
- **`measure.py` token evaluator** — fixture-driven before/after comparison at `app/skills/brand-voice/scripts/measure.py`. Asserts budget compliance and load-bearing fact preservation via optional `must_contain.txt` per fixture. JSON and human report formats.
- **`session_token_stats.py`** — stdlib-only Claude Code session JSONL parser at `scripts/session_token_stats.py`. Reports real input/output/cache token counts per session, supports `--since`, `--baseline`, `--statusline`, and `--json` modes.
- **Comprehensive default status line** — new `app/hooks/ai-toolkit-statusline.sh` renders a single line with cwd, git branch + dirty marker, context-window as a 10-cell progress bar (green <70% / orange 70–89% / red ≥90%), upload arrow `↑` (input tokens, green) + download arrow `↓` (output tokens, red), effort level, and model name. All token + cost data is read directly from Claude Code's statusLine stdin (`context_window.total_input_tokens`, `total_output_tokens`, `cost.total_cost_usd`, `effort.level`) — no JSONL parsing in the hot path, ~50ms cold start. Installed automatically into `~/.claude/settings.json` by `ai-toolkit install` (and `update`). User-customized statusLine entries (without the ai-toolkit `_source` tag) are preserved untouched. Cost-estimate segment is opt-in via `AI_TOOLKIT_STATUSLINE_SHOW_COST=1`.
- **`merge-hooks.py` statusLine support** — `inject` writes the toolkit statusLine only when the target has none or has a stale toolkit-installed one. `strip` removes only toolkit-installed entries.
- **`briefing` skill `--tokens` mode** — `/briefing --tokens [--since 7d]` for explicit reporting and baseline capture. Includes wire-up docs for the status-line hook and `AI_TOOLKIT_STATUSLINE_*` opt-out env vars.
- **Hook runtime scripts deployed alongside hooks** — `scripts/install_steps/hooks.py` now copies a curated allowlist of Python helpers (`session_token_stats.py`, `version_check.py`) to `~/.softspark/ai-toolkit/scripts/`, so hooks work on a fresh install before the npm-global package catches up. Hook resolution order: `AI_TOOLKIT_DIR` → `~/.softspark/ai-toolkit/` → npm global → walk up from script (dev fallback).

### Opt-out

- `AI_TOOLKIT_STATUSLINE_DISABLE=1` silences output entirely
- `AI_TOOLKIT_STATUSLINE_NO_TOKENS=1` hides token arrows segment
- `AI_TOOLKIT_STATUSLINE_NO_GIT=1` hides git segment
- `AI_TOOLKIT_STATUSLINE_NO_EFFORT=1` hides effort level segment
- `AI_TOOLKIT_STATUSLINE_NO_COLOR=1` disables ANSI colors
- `AI_TOOLKIT_STATUSLINE_SHOW_COST=1` appends Claude Code's reported `cost.total_cost_usd` (off by default — long Opus sessions show alarming numbers)
- `AI_TOOLKIT_STATUSLINE_DUMP=1` writes received stdin to `/tmp/cc-statusline-input.json` (debug only)

### Tests

- 38 new bats tests across `tests/test_brand_voice.bats`, `tests/test_session_token_stats.bats`, `tests/test_statusline_hook.bats`, `tests/test_merge_hooks_statusline.bats`, plus install-step assertion in `tests/test_install.bats`.

---

## v3.1.1 — Windows install fix (2026-04-29)

Patch release. `ai-toolkit install --local` crashed on Windows before doing any work because `scripts/install_steps/project_registry.py` imported `fcntl` (POSIX-only) at module load, raising `ModuleNotFoundError: No module named 'fcntl'`.

### Fixed

- **Windows install crash** — `project_registry` now imports `fcntl` and `msvcrt` defensively (try/except → `None`) and `_registry_lock()` selects between `fcntl.flock` (POSIX) and `msvcrt.locking` (Windows) at runtime. POSIX semantics unchanged; Windows acquires the lock with `LK_NBLCK` + 30 s deadline + 10 ms retry backoff.

### Added

- **Windows compat regression test** — `tests/test_windows_support.bats` now blocks `import fcntl` via a custom `meta_path` finder, stubs `msvcrt`, and forces the Windows branch of `_registry_lock` so future regressions are caught on the POSIX CI runners without needing a Windows machine.

## v3.1.0 — Global Editor Install Alignment (2026-04-28)

Minor release aligning global and project-local editor configuration with the current documented surfaces for all supported editors.

### Added

- **Global Cline rules** — `ai-toolkit install --editors cline` now writes documented global rules under `~/Documents/Cline/Rules/ai-toolkit-*.md`.
- **Global Roo Code rules** — `ai-toolkit install --editors roo` now writes documented global rules under `~/.roo/rules/ai-toolkit-*.md`.
- **Safe global Aider bootstrap** — `ai-toolkit install --editors aider` now creates `~/.aider.conf.yml` only when absent and refreshes `~/.aider-ai-toolkit-CONVENTIONS.md`; existing user YAML is preserved.
- **Project Roo MCP sync** — `ai-toolkit mcp install --editor roo --scope project ...` and `install --local --editors roo` now mirror canonical `.mcp.json` servers into `.roo/mcp.json`.

### Changed

- **Global editor target policy** — global install now uses only documented, file-based targets: `aider`, `augment`, `cline`, `codex`, `gemini`, `opencode`, `roo`, and `windsurf`.
- **Cursor rules scope** — Cursor rule generation is now explicitly project-local. Cursor still supports project/global MCP via `.cursor/mcp.json` and `~/.cursor/mcp.json`, but global rule writes are not emitted because Cursor's global user rules are settings-managed rather than a stable merge-safe file.
- **Release and registry docs** — updated the supported-tools registry, MCP compatibility tables, global install model, release SOP, README platform matrix, and ecosystem doctor snapshot for the April 28, 2026 upstream baseline.
- **Release SOP meta-generator gate** — registry/generator drift checks now exclude `generate_language_rules_skills.py` alongside docs/index meta-generators, keeping the editor registry focused on editor config generators.

### Fixed

- **SOP compliance gap** — Cline, Roo Code, and Aider global surfaces are now used where documented, while Cursor/Copilot/Antigravity rules remain local-only where no safe global rule file exists.
- **Release metadata drift** — test count is now synced to 973 across README and validation metadata.

## v3.0.2 — Validation, Windows, Telemetry, and generate:all parity (2026-04-24)

Patch release that closes known validation gaps, expands the hook-surface contracts, adds Windows dependency hints, exposes local product telemetry, and restores `npm run generate:all` parity with the CLI so registered custom rules reach every editor.

### Added

- **Hook surface validation** — `scripts/validate.py` now accepts the current Claude Code hook event surface, including `PostToolUseFailure`, `PostToolBatch`, and `UserPromptExpansion`.
- **Hook handler contracts** — validation now checks supported handler types (`command`, `http`, `prompt`, `agent`, `mcp_tool`), required handler fields, and prompt/agent event compatibility.
- **Language rule validation** — `scripts/validate.py` now checks `app/rules/<language>/*.md` frontmatter, category names, filename/category alignment, directory/language alignment, and required category coverage.
- **Windows dependency hints** — `_common.detect_os()` recognizes Windows package managers (`winget`, Chocolatey, Scoop), and `check_deps.py` emits package install commands for Python, Git, Node, SQLite, and supported optional tooling.
- **Product telemetry summary** — `ai-toolkit stats --summary` reports local usage telemetry; `--summary --json` emits machine-readable totals, coverage, unused catalog count, recent activity, and top skills.
- **Dedicated gap tests** — added contracts for structured rules, Windows dependency support, council/brand-voice/introspect skill coverage, and `npm run generate:all` directory-rule generator coverage. Total test count: 945 -> 960.
- **Windows Support KB** — new `kb/reference/windows-support.md` documents WSL, Git Bash, package managers, and hook runtime constraints.

### Changed

- **`package.json` `generate:all`** — now invokes all directory-based rule generators (`generate_cursor_mdc.py`, `generate_windsurf_rules.py`, `generate_roo_rules.py`, `generate_augment_rules.py`) so registered custom rules in `~/.softspark/ai-toolkit/rules/` propagate to every editor that supports per-rule module files. Restores parity with `ai-toolkit generate-all` (CLI).
- **`app/skills/hook-creator/SKILL.md`** — documents the expanded hook event and handler type surface.
- **`README.md` and `kb/reference/cli-reference.md`** — document `stats --summary` and Windows support.
- **`kb/reference/hooks-catalog.md`** — documents the validated hook surface and non-command handler support.

---

## v3.0.1 — Release SOP Deep-Coverage Checks (2026-04-24)

Doc-only patch. No code, generators, or runtime behavior changed.

### Changed

- **`kb/procedures/release-verification-sop.md` 1.3.0 -> 1.4.0** — added Phase 9 (six new checks for v3.0.0 native surfaces: `--profile full` emission, `--codex-skills` orthogonality, breaking-change surfaces at `standard`, install idempotence, live JSON parse, registry/generator drift). Refreshed stale thresholds (`Tests >= 350` -> `Tests >= 900`, `e.g., 669` -> `e.g., 945`). Editor list updated from 8 to 11 (+codex, +gemini, +opencode). Added HOME-scoped write safety warning.
- **`kb/procedures/release-preparation-sop.md` 1.9.0 -> 1.10.0** — added the registry-vs-generators drift check to Phase 5 so a bad registry can never escape into a release.
- **`kb/reference/supported-tools-registry.md` 1.1.0 -> 1.2.0** — enumerated the 11 new v3.0.0 generators (cursor_hooks/agents, windsurf_hooks, gemini_hooks/commands/skills, augment_hooks/agents/commands/skills, codex_skills) with profile and opt-in annotations.

---

## v3.0.0 — Deep Coverage: Full Native Surface Utilization (2026-04-23)

Skips `2.13.0`. Upgrade path is `2.12.x` -> `3.0.0`.

### BREAKING

- **`--profile standard` now installs Gemini hooks** by default. Users who relied on `standard` leaving Gemini hooks alone must switch to `--profile minimal` or pass `--skip gemini-hooks`.
- **Copilot moved to directory mode** (`.github/copilot/`) for new installs. Existing single-file `.github/copilot-instructions.md` installs are preserved; re-running `install` will emit the directory form alongside.

### Added

- **`--profile full`** flag that activates every native surface across every supported editor in a single invocation.
- **`--codex-skills`** opt-in flag that materializes the full skill catalog under Codex's `.agents/skills/` directory (other editors continue using pointer-skill or compat-read).
- **11 new generators** covering hooks, sub-agents, commands, and skill pointers per editor:
  - `scripts/generate_cursor_agents.py`, `scripts/generate_cursor_hooks.py`
  - `scripts/generate_windsurf_hooks.py`
  - `scripts/generate_gemini_commands.py`, `scripts/generate_gemini_hooks.py`, `scripts/generate_gemini_skills.py`
  - `scripts/generate_augment_agents.py`, `scripts/generate_augment_commands.py`, `scripts/generate_augment_hooks.py`, `scripts/generate_augment_skills.py`
  - `scripts/generate_codex_skills.py`
- **105 new bats tests**: `tests/test_native_surfaces.bats` (33), `tests/test_skills_native.bats` (25), `tests/test_hooks_per_editor.bats` (30), `tests/test_install_profiles.bats` (17), plus per-editor suites for aider, antigravity, augment, claude-code, cline, codex, copilot, cursor, gemini, opencode, roo, windsurf. Total test count: 840 -> 945.
- **Folded-in skill quality pass** (originally targeted at 2.13): 62 skills upgraded to 4-5 / 5 on the meta-architect audit with `## Rules`, `## Gotchas`, and `## When NOT to Use` sections. `add_gotcha` added as a fifth mutation strategy.

### Changed

- `scripts/install_steps/ai_tools.py` now routes profile and `--codex-skills` through a `_try_generator` wrapper that degrades gracefully when a generator is missing. All new generators are wired behind explicit profile checks; no generator runs at `minimal`.
- `scripts/install.py` accepts `--profile full` and `--codex-skills`.
- `config_validator.VALID_PROFILES` extended with `full`.
- Per-tool generator matrix documented in `kb/reference/supported-tools-registry.md` (profile column).
- Profile semantics documented in `kb/reference/global-install-model.md` and `kb/procedures/maintenance-sop.md`.

### Migration notes

- If you pin `--profile standard` in CI and need to keep Gemini hooks out, switch to `--profile minimal` or pass `--skip gemini-hooks`.
- Copilot users on single-file mode: no action required. To adopt the directory layout, delete `.github/copilot-instructions.md` before re-running `install`.
- Users running `install` against a project that already has hand-edited Cursor / Windsurf / Gemini hooks are safe. All new generators preserve prefix/suffix markers and only rewrite the managed block.

---

## v2.12.0 — Skill Quality Pass (Rules + Gotchas + When NOT to Use) (2026-04-23)

### Added
- **Meta-architect audit criteria across 62 skills** — every previously low-scoring skill (2-3/5 on the 5-criterion meta-architect audit) gained three new sections:
  - `## Rules` — prescriptive MUST / NEVER / CRITICAL / MANDATORY markers for non-negotiable process constraints
  - `## Gotchas` — Anthropic-recommended section for environment-specific traps and domain surprises (only where genuine traps exist; not padded)
  - `## When NOT to Use` — explicit boundary with 2-5 adjacent skills to prevent over-triggering
- **`meta-architect.md` mutation strategy taxonomy extended** — added `add_gotcha` as a fifth strategy alongside `add_example`, `add_constraint`, `add_edge_case`, `restructure`. Clarifies that Rules (prescriptive) and Gotchas (environment-specific) are distinct semantic buckets.
- **`skill-creator/SKILL.md` and `command-creator/SKILL.md` templates updated** — new skills now default to the three-section pattern (Rules + optional Gotchas + When NOT to Use). Quality checklist extended to match.
- **`scripts/evaluate_skills.py` — `_meta_architect_audit()` function** — non-failing advisory scoring per skill against the 5 binary criteria (description ≥50 chars, example, constraint, edge_case, length). Surfaces bottom-10 watchlist in every evaluation run.
- **rag-mcp KB integration**: new document `kb/troubleshooting/rag-failure-patterns.md` (12-pattern taxonomy P01-P12) adapted from `awesome-llm-apps/rag_tutorials/rag_failure_diagnostics_clinic/`. New planning doc `kb/planning/toon-output-format-spike.md` proposes a timeboxed benchmark of TOON vs JSON output format for search tool responses.

### Changed
- **14 task skills (wave-1)** upgraded from 2/5 to 5/5 audit score: `analyze`, `chaos`, `ci`, `debug`, `evaluate`, `health`, `index`, `mem-search`, `night-watch`, `onboard`, `panic`, `performance-profiling`, `pr`, `test`. Short frontmatter descriptions extended with trigger hints; hard-rule markers added; explicit sibling-skill boundaries documented.
- **48 task and knowledge skills (wave-2)** upgraded from 3/5 to 5/5: `agent-creator`, `api-patterns`, `app-builder`, `architecture-audit`, `architecture-decision`, `biz-scan`, `brand-voice`, `briefing`, `build`, `ci-cd-patterns`, `content-moderation-patterns`, `database-patterns`, `design-engineering`, `docker-devops`, `ecommerce-patterns`, `evolve`, `explain`, `explore`, `fix`, `git-mastery`, `grill-me`, `hipaa-validate`, `hook-creator`, `instinct-review`, `introspect`, `lint`, `mcp-builder`, `migrate`, `migration-patterns`, `observability-patterns`, `persona`, `plan`, `plan-writing`, `plugin-creator`, `prd-to-issues`, `prd-to-plan`, `predict`, `qa-session`, `rag-patterns`, `refactor`, `refactor-plan`, `rollback`, `security-patterns`, `skill-audit`, `swift-patterns`, `testing-patterns`, `triage-issue`, `ubiquitous-language`.
- **`swift-patterns/SKILL.md` restructured** — 108-line `Common Frameworks` section moved to `reference/frameworks.md` (progressive disclosure per Anthropic spec), room reclaimed for Rules/Gotchas/When NOT to Load. SKILL.md now 420 lines (under 500 limit).

### Notes
- Score distribution: `{2: 14, 3: 48, 4: 32, 5: 5}` → `{4: 33, 5: 66}`. Zero skills remain below 4/5.
- Approach validated against official Anthropic guidance (`agentskills.io/skill-creation/best-practices.md`): Gotchas section is Anthropic-recommended; prescriptive negative instructions (MUST/NEVER) and default-plus-escape-hatch (When NOT to Use) map to documented patterns.
- Changes are **additive** — no existing skill content removed; sections appended or, in the case of `swift-patterns`, relocated to a reference subdirectory. Test count unchanged (669). No new skills or agents added, so counts unchanged (44 agents, 99 skills).

---

## v2.11.0 — JSON Wire Format Rules (2026-04-21)

### Added
- **`app/rules/common/coding-style.md` v1.2.0 — JSON Wire Format Conventions section** — `camelCase` for field names (JSON:API, Google JSON Style, Symfony Serializer + `json_serializable` defaults), `UPPER_SNAKE_CASE` for enum/status/permission values (Protocol Buffers style guide, Google AIP-126 / api-linter, Zalando Rule #240, Java/Kotlin/C++/Python consensus). Explicit call-out that `camelCase` for enum VALUES is an anti-pattern with no major public API precedent.
- **`app/rules/php/frameworks.md` v1.1.0 — Symfony Serializer section** — documents the `property-names-used-as-is` default, the global-override side effect of `api_platform.name_converter` ([api-platform/core #6101](https://github.com/api-platform/core/issues/6101)), pragmatic `#[SerializedName]` usage (only when justified), and the Symfony 7.3.5+ `ObjectNormalizer` `isXxx` behavior change ([symfony/symfony #62353](https://github.com/symfony/symfony/issues/62353)) that makes pre-7.3.5 `SerializedName` aliases redundant. API Platform section extended with `operation_name` metadata note.
- **`app/rules/dart/frameworks.md` v1.1.0 — JSON Serialization section** — `json_serializable` `FieldRename.none` default + Effective Dart `lowerCamelCase` = `camelCase` JSON keys without configuration; community recommendation to prefer class-level `fieldRename` over per-field `@JsonKey(name:)`; enum value strategy (`UPPER_SNAKE_CASE` on wire, Dart case names stay `lowerCamelCase`).
- **`tests/test_rules_content.bats` (3 bats cases)** — smoke tests guarding the three new rule sections (`JSON Wire Format Conventions`, `Symfony Serializer`, `JSON Serialization`). Heading-only checks, intentionally non-brittle. Test count: 666 → 669.

### Notes
- Changes are additive — no existing rule text removed or reworded. Projects that ran `ai-toolkit install --local` before v2.11.0 will pick up the new sections on next re-run (install is idempotent — existing TOOLKIT markers get replaced, not duplicated).
- Rules codify documented facts + widely-cited community consensus, not project-specific enforcement. Project-level SOPs (grep gates, migration workflows, whitelists) remain in each project's `kb/procedures/`.

---

## v2.10.1 — Art. VI Enforcement Drift Repair (2026-04-21)

### Fixed
- **`IMMUTABLE_ARTICLES` extended to include Article 6** (`scripts/config_merger.py`, `scripts/config_validator.py`) — v2.10.0 declared Art. VI immutable in `app/constitution.md` but left the enforcement constant at `{1..5}`, so a downstream `extends:` config with `amendments: [{article: 6, ...}]` would silently override Repair Discipline. Constant now `{1..6}`; error message points at article 7+ as the first allowed project-added article.
- **`scripts/emission.py::generate_quality_standards()` emits Article VI** — generator hard-coded I–V only, so `AGENTS.md`, `GEMINI.md`, editor rule files, and `llms-full.txt` did not carry Art. VI text after the v2.10.0 release. Added four-clause VI block (no dead code, fix every found bug, tests and docs follow behavior, verify before done). All downstream catalogs regenerated.
- **"5 articles" / "Articles I-V" literals updated to 6 / I-VI** across `README.md`, `app/ARCHITECTURE.md`, `kb/reference/architecture-overview.md`, `kb/reference/enterprise-config-guide.md`, `scripts/config_cli.py` diff label, and `scripts/schemas/ai-toolkit-config.schema.json` description. Added Article VI row to the Constitution table in `architecture-overview.md`.
- **Article I.3 "Max 3" aligned to Section 4 "Max 5"** in `app/constitution.md` to resolve a pre-existing internal contradiction. Same iteration cap now quoted in `scripts/emission.py` general/quality guidelines.
- **SKILL.md improvements from PR #8 by @rohan-tessl** — `biz-scan`, `evolve`, `plan`, `predict`, and `teams` gained richer descriptions with explicit "Use when..." clauses and executable protocol steps; team preset details moved to `teams/reference/presets.md` (progressive disclosure). Repo style applied (no em dashes); `plan/SKILL.md` KB Integration section preserved.

### Added
- **`scripts/validate.py` article-count drift lint** (`validate_constitution_drift`) — parses `app/constitution.md` for `## Article <roman>:` headings, derives the expected count and max roman numeral, and fails strict validation when `README.md`, `app/ARCHITECTURE.md`, or `kb/reference/*` references a stale `N articles` or `Articles I-<roman>` literal. This is how v2.10.0 drift slipped past CI; it will not next time.

### Notes
- No skill/agent/hook counts changed. Totals remain: 44 agents, 99 skills, 666 tests.
- Art. VI text itself (in `app/constitution.md`) unchanged from v2.10.0 — only surfaces and enforcement are reconciled with it.

---

## v2.10.0 — Constitution Article VI: Repair Discipline (2026-04-21)

### Added
- **Constitution Article VI — Repair Discipline** (`app/constitution.md`) — four new immutable rules: no dead code (VI.1), fix every found bug (VI.2), tests and docs follow behavior (VI.3), verify before claiming done (VI.4). Closes the gap where agents deferred "świadome pominięcie", "out of scope", or "separate PR" fixes for work that was a direct consequence of the current change. Articles I–V remain unchanged.
- **`system-governor` Art. VI audit protocol** (`app/agents/system-governor.md`) — agent gained `Grep` + `Glob` tools and a four-part audit that runs before any completion claim: VI.1 dead-symbol grep, VI.2 deferred-work scan (scoped to commit message + PR body + non-`.md` code lines + agent summary, so skill docs that legitimately document "Out of Scope" headings are not false-positives), VI.3 behavior/test/doc coverage detection, VI.4 diff re-read. Outputs a structured verdict with per-Article PASS/VETO citations.
- **`clean-code` skill Art. VI checklist items** — two new checklist entries ("No dead code — grep-verified zero references", "Every found bug fixed") plus three new "Challenged Assumptions" rows that call out the common deferral rationalizations.
- **`refactor-plan` skill Art. VI anchor** — mandatory dead-code cleanup per step, not deferred. Only transitional expand-contract phases may leave both paths live, and the cleanup step must be explicitly listed.
- **`verification-before-completion` skill Art. VI rows** — three new rows in the evidence-vs-non-evidence table covering VI.1/VI.2/VI.4, plus a "Constitutional Anchors" section that pins the skill to Art. VI.4.
- **`coding-style` rule Art. VI sections** (`app/rules/common/coding-style.md`, v1.0.0 → v1.1.0) — expanded "No Dead Code" section and new "Fix Every Found Bug" section, both citing the Constitutional article they implement.

### Changed
- **`system-governor` description** widened to reflect Art. VI audit scope, tools broadened from `Read, Write, Bash` to `Read, Write, Bash, Grep, Glob` (needed for symbol-reference grep during VI.1).

### Notes
- No skill/agent/hook counts changed. Totals remain: 44 agents, 99 skills, 666 tests.
- Art. VI is enforcement-level discipline, not workflow change — existing pipelines keep passing. Governor veto gates a completion claim, not a commit.

---

## v2.9.0 — Skill Routability & Description Lint (2026-04-19)

### Changed
- **30 knowledge-skill descriptions rewritten** — every skill with `user-invocable: false` used the `"Loaded when user asks about X"` shape, which carries no action verb and no concrete trigger keywords. Per [Anthropic skill docs](https://code.claude.com/docs/en/skills.md), Claude Code auto-routes skills using only the `description:` field (+ optional `when_to_use:`), so weak descriptions silently lowered hit rate. Rewritten with the pattern `[capability]. Triggers: [keywords]. Load when [...]`. Affected skills: `api-patterns`, `app-builder`, `architecture-decision`, `ci-cd-patterns`, `clean-code`, `csharp-patterns`, `database-patterns`, `debugging-tactics`, `design-engineering`, `docker-devops`, `documentation-standards`, `ecommerce-patterns`, `flutter-patterns`, `git-mastery`, `hive-mind`, `java-patterns`, `kotlin-patterns`, `mcp-patterns`, `migration-patterns`, `observability-patterns`, `performance-profiling`, `plan-writing`, `rag-patterns`, `research-mastery`, `ruby-patterns`, `rust-patterns`, `security-patterns`, `swift-patterns`, `testing-patterns`, `typescript-patterns`.

### Added
- **`scripts/audit_skills.py` description-quality lint (`check_description`)** — new WARN rules that prevent the `"Loaded when user asks about/to ..."` anti-pattern from returning. Enforces three limits on auto-loadable skills: `description + when_to_use ≤ 1536 chars` (Anthropic truncation limit), knowledge-skill description ≥ 80 chars, and a regex block on the historical weak-opening patterns. Task skills (`disable-model-invocation: true`) are skipped — their description is a menu label, not a routing signal.
- **Regenerated `AGENTS.md`, `llms.txt`, `llms-full.txt`, `GEMINI.md`, `.github/copilot-instructions.md`** — machine-readable catalogs now carry the new descriptions. External clients (Cursor, Windsurf, Copilot, Gemini CLI, Codex) get the same routing signal as Claude Code.



### Added
- **`scripts/audit_skills.py --sarif`** — emits SARIF 2.1.0 JSON compatible with GitHub Advanced Security Code Scanning. Severity maps HIGH→error / WARN→warning / INFO→note. Enables the GitHub Security tab to ingest audit findings directly.
- **`scripts/audit_skills.py --permissions`** — per-skill tool-permission report (human + `--json` forms). Aggregates skills by tool usage (e.g. "50 skills use Bash"), flags broad Bash+Write+Edit access, prints full skill/invocable/tools table. Security review can now answer "show me every skill that can Bash" in one command.
- **Checksum pinning for URL-sourced rules and hooks** — `rule_sources.py` and `hook_sources.py` now persist `sha256` of the fetched payload in `sources.json`. Subsequent refreshes log `CHECKSUM CHANGED` when the upstream payload changes. Setting `AI_TOOLKIT_STRICT_PIN=1` turns the mismatch into a hard failure (exit 2) so CI can reject silent upstream tampering.
- **`SECRET_PLACEHOLDER_PREFIXES`** allowlist in `audit_skills.py` — WARN-level hardcoded-secret patterns now skip values starting with `REPLACE_`, `CHANGEME_`, `CHANGE_ME`, `YOUR_`, `EXAMPLE_`, `PLACEHOLDER_`, `${`, `{{`, `$ENV_`, `$(`, `<`, `xxx`, `XXX`. Fewer false positives on docs and `.env.example` fixtures.

### Changed
- **npm publish workflow (`.github/workflows/publish.yml`)** now runs with `--provenance` and `id-token: write`. Published tarballs carry a cryptographic provenance attestation visible on npmjs.com and verifiable via `npm audit signatures`.
- **`scripts/config_resolver.py:_extract_tarball`** passes `filter="data"` to `tarfile.extract` on Python 3.12+. Defense in depth on top of existing path-traversal, symlink, and absolute-path rejection. Future-proofs against the 3.14 default-filter change.
- **`app/hooks/session-start.sh`** sanitises `VERSION_MSG` with `LC_ALL=C tr -d '"'"'"'\\`$'` before interpolating into `osascript` / `powershell.exe` notification commands. Closes a latent command-injection footgun.
- **`scripts/install_steps/ai_tools.py`** and **`hooks.py`** — generator and merge-hooks `subprocess.run` calls now have `timeout=120`. A stuck generator produces a clear error instead of hanging `ai-toolkit install` indefinitely.
- **`app/hooks/commit-quality.sh`** — extracted commit message via a small Python regex instead of fragile shell `grep -oE` chain. Handles commit messages containing mixed `"` and `'` correctly.
- **`app/hooks/quality-check.sh`** — normalised `|| true` handling across all languages (Python ruff was previously the only one propagating exit status). All language checks are now consistently advisory on the Stop hook.
- **`bin/ai-toolkit.js:handleAddRule`** — simplified HTTPS/HTTP detection (single `startsWith('https://')` after the `http://` reject).
- **`package.json` description** shortened from 400+ to 241 characters — stops mid-sentence truncation in npm search. Surfaces the new SARIF + provenance differentiators.
- **`package.json` `engines`** — removed non-standard `bats` entry (npm ignores unknown engines and warned on install). Bats requirement is documented in `CLAUDE.md` Commands section.

---

## v2.7.3 — Regenerate llms after Medplum Merge (2026-04-17)

### Fixed
- **`llms.txt` + `llms-full.txt` stale after PR #7 (Medplum/FHIR rules)** — contributor did not re-run `npm run generate:all` before merge, so the machine-readable catalogs did not list `kb/reference/medplum-docs-map.md`, and `kb/reference/language-rules.md` still advertised `13 languages / 68 rule files` instead of `14 languages / 73 rule files`. Validator passes regardless (it does not diff generated text), so the drift slipped past CI. Regenerated from source; added Medplum row to the languages table.

---

## v2.7.2 — Doc & Model-ID Consistency (2026-04-17)

### Changed
- **Centralized Claude model IDs** — introduced `DEFAULT_CLAUDE_MODELS` dict in `scripts/_common.py` (single source of truth: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`). `scripts/generate_aider_conf.py` now imports the constant instead of hardcoding `claude-sonnet-4-6`. Next Anthropic model bump touches one file. Agent frontmatter aliases (`opus`/`sonnet`/`haiku`) stay version-free and are resolved at runtime.
- **`app/agents/ai-engineer.md`** now points to the `model-routing-patterns` skill as the single source of truth for current Claude IDs, cost tiers, and fallback chains instead of duplicating a tier table that would drift with every Anthropic release.

### Fixed
- **`GEMINI.md` missed 5 skills from v2.7.0** — `generate:all` was not re-run before the v2.7.0 release tag, so `GEMINI.md` did not list `prompt-caching-patterns`, `json-mode-patterns`, `content-moderation-patterns`, `model-routing-patterns`, or `/mcp-builder`. Regenerated.
- **`manifest.json` stale skill counts** — `components.skills.description` and `modules.skills.description` still reported `94 skills (31 task + 31 hybrid + 32 knowledge)` instead of the current `99 skills (32 task + 31 hybrid + 36 knowledge)`. Fixed in 2 places.

---

## v2.7.1 — Eject Output-Styles Fix (2026-04-17)

### Fixed
- **`ai-toolkit eject` now exports `app/output-styles/*.md`** — pre-existing gap dating back to when output-styles were introduced. `scripts/eject.py` copied agents, skills, rules, constitution, and ARCHITECTURE, but silently skipped the `output-styles/` directory. Standalone `.claude/` produced by eject had no system-prompt styles (no `golden-rules`, and after v2.7.0 no `learning`/`explanatory`). Now eject writes `.claude/output-styles/` with all source `.md` files and includes the count in the summary line: `Ejected: N agents, N skills, N rules, N output style(s)`.

### Added
- **2 `tests/test_eject.bats` cases** — `eject copies output-styles directory with all source styles` (also asserts `golden-rules.md` baseline) and `eject reports output-style count in summary line`. Test count: 664 → 666.

---

## v2.7.0 — Anthropic Ecosystem Alignment (2026-04-17)

### Added
- **`/mcp-builder` task skill** — opinionated 4-phase MCP server build workflow (Phase 1 research & planning, Phase 2 implementation with Zod/Pydantic schemas, Phase 3 review & testing via MCP Inspector, Phase 4 eval set of 10 realistic questions). Complements the existing `mcp-patterns` knowledge skill.
- **4 knowledge skills for Claude API work**, auto-loaded by relevant agents:
  - `prompt-caching-patterns` — TTL, cache breakpoints, 4-layer stacking, hit-rate measurement, anti-patterns.
  - `json-mode-patterns` — tool-use forcing as idiomatic JSON mode, schema design, partial-output recovery.
  - `content-moderation-patterns` — 2-stage pre-filter + Haiku classifier, category design, threshold router, HIL queue.
  - `model-routing-patterns` — Haiku/Sonnet/Opus routing, confidence-based escalation, Opus-planner-with-Haiku-workers sub-agent delegation, task-specific routing table.
- **2 output styles** in `app/output-styles/`:
  - `learning.md` — interactive "⟶ Your turn" prompts on meaningful decisions, ★ Insight educational blocks.
  - `explanatory.md` — one-way ★ Insight blocks exposing implementation trade-offs, no user prompts.
- **`app/ARCHITECTURE.md` → Frontmatter Schema section** — documents ai-toolkit's spec-defined fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) and top-level extensions (`user-invocable`, `disable-model-invocation`, `effort`, `agent`, `context`, `argument-hint`, `color`). Explains the comma-separated `allowed-tools` convention enforced by `scripts/codex_skill_adapter.py:70` and `scripts/audit_skills.py:157`.
- **`kb/reference/agent-skills-spec.md` (rag-mcp KB)** — canonical mirror of `agentskills.io/specification` with ai-toolkit extension mapping, validation commands, and progressive-disclosure tiers.
- **4 fixture tests in `tests/test_review_diff_analyzer.bats`** — category ordering (docs vs security), false-positive guard for unquoted identifier assignments (e.g. `request_token = generate_token_v2_legacy()` no longer flagged), quoted + unquoted env-style detection with accurate file/line tracking, rename record parsing in `git diff --numstat -z`. Test count: 660 → 664.

### Changed
- **`/review` diff analyzer (`app/skills/review/scripts/diff-analyzer.py`) hardened end-to-end:**
  - Secret scan now tracks the actual file line number per hunk (parses `@@ -a,b +c,d @@`) and reports `{"file": path, "line": file_line, "preview": snippet}`. Previously reported `line` was the offset in the unified diff text.
  - Base ref existence verified via `git rev-parse --verify` before diffing. Silent fallback to `--cached` now emits a stderr notice and a `warnings[]` entry in the JSON output, so callers see the reduced scope explicitly.
  - `git diff --numstat -z` parser replaces naive tab-split; rename entries (three NUL-separated tokens) are handled correctly.
  - Secret pattern list expanded: JWT (three-segment), PEM private key header (`-----BEGIN … PRIVATE KEY-----`), Google API key (`AIza…`), Slack tokens (`xox[baprs]-…`), GitHub fine-grained PAT (`github_pat_…`), unquoted env-style assignments.
  - Unquoted env-style pattern tightened so `request_token = generate_token_v2_legacy()` (snake_case identifier on RHS) is not flagged while `API_KEY=abcdef1234567890` and `API_KEY=SECRET_VALUE_XYZ` are. Uses scoped `(?-i:…)` for the ALL_CAPS constant alternative.
  - Category regex reordered (`docs` and `test` checked before `security`) and anchored with word boundaries and path segments (`(^|/)…` / `\b…\b`). Files like `docs/role-permissions.md`, `roles_and_responsibilities.md`, `accessor.py` are now categorised correctly; `authentication_config_loader.py` resolves to `security`; `notification_settings.py` resolves to `logic` (not `config`).
  - New output fields: `scope` (`"{base}...HEAD"` or `"staged"`), `warnings[]`.
- **Doc-count sync** — README, package.json, manifest.json, `app/.claude-plugin/plugin.json`, `app/ARCHITECTURE.md`, `kb/reference/skills-catalog.md`, `AGENTS.md`, `llms-full.txt` all advance to 99 skills (32 task / 31 hybrid / 36 knowledge) and 664 tests.

---

## v2.6.2 — Eject Count Fix (2026-04-17)

### Fixed
- **`ai-toolkit eject` skill count** — reported `95 skills` while `validate.py` reported `94`. Root cause: eject iterated every directory under `app/skills/`, including the shared `_lib/` helper (no `SKILL.md`). Now matches `validate.py` semantics — skips underscore-prefixed dirs and requires `SKILL.md` for the count. `_lib/` is still copied so dependent skills (`ci`, `test`, `build`, `lint`) keep working after eject.

### Added
- **Two eject tests** in `tests/test_eject.bats` — `eject reports skill count matching validate.py (excludes _lib helpers)` and `eject still copies _lib helper directory for dependent skills`. Test count: 658 → 660.

---

## v2.6.1 — HIPAA Scanner Precision (2026-04-17)

### Changed
- **`hipaa-validate` Cat 3 regexes tightened to cut false positives** — `CERT_NONE` → `ssl\.CERT_NONE` (module-anchored, no longer matches constants like `USE_CERT_NONE_MODE`); `ssl\s*=\s*False` → `[,(]\s*ssl\s*=\s*False\b` (argument-position anchored, no longer matches feature flags like `is_ssl_enabled = False`).
- **`SECURE_SSL_REDIRECT = False` severity HIGH → WARN** — commonly `False` in dev/local Django settings; compliance reviewer must confirm production config.
- **Cat 1 Python logger patterns merged** — three overlapping regexes (`logging.*`, `logger.*`, `pprint.*`) collapsed into one `(logging|logger|pprint)\.\w+\(...` pattern; eliminates duplicate findings on the same line.
- **SQLAlchemy session data-op regexes word-anchored** in Cat 2 and Cat 5 (`\bsession.(query|add|execute|delete|merge)\b`) — prevents false matches on unrelated identifiers.

### Added
- **`LANG_EXTENSIONS` file-extension filter** in `scripts/hipaa_scan.py` — language-tagged patterns now fire only when the file's extension matches the tag. Eliminates cross-language double-flagging (e.g. Python `logger.\w+` regex no longer triggers on `.java` files in mixed projects).
- **`tests/test_hipaa_scan.bats`** — 11 fixture-driven tests covering Python positive/negative cases for the new patterns and the cross-language isolation guarantee. Test count: 647 → 658.

---

## v2.6.0 — opencode Integration (2026-04-15)

### Added
- **opencode editor support** — `ai-toolkit install --editors opencode` generates a full native integration: `AGENTS.md` (shared with Codex via distinct marker sections), `.opencode/agents/ai-toolkit-*.md` (44 subagents), `.opencode/commands/ai-toolkit-*.md` (62 slash commands), `.opencode/plugins/ai-toolkit-hooks.js` (JS plugin bridging Bash hooks to opencode lifecycle events), and `opencode.json` with MCP servers merged from `.mcp.json`.
- **Global opencode configs** — `ai-toolkit install --editors opencode` (without `--local`) installs the **complete surface** to `~/.config/opencode/{AGENTS.md, agents/, commands/, plugins/ai-toolkit-hooks.js, opencode.json}`. Tracked in `state.json`, auto-refreshed on `update`. (Earlier pre-release iteration shipped only AGENTS.md/agents/commands globally; plugin and opencode.json are now also installed globally so hooks and MCP work without `--local`.)
- **Expanded hook coverage** — plugin now bridges `session.compacted` → `pre-compact.sh` + `pre-compact-save.sh`, `permission.asked` → `guard-destructive.sh`, and `command.executed` → `post-tool-use.sh` on top of the original session/tool/message events. Maximises opencode lifecycle coverage without introducing new Bash hooks.
- **Auto-detection** — projects with `opencode.json` or `.opencode/` are detected by `ai-toolkit install --local` (no explicit `--editors` needed).
- **MCP translation** — `generate_opencode_json.py` translates Claude-style `.mcp.json` into opencode's `mcp` shape (local `command` + args flattened, remote `url` + headers preserved, `enabled: true` default). User-authored keys in `opencode.json` are preserved; re-runs are idempotent.
- **New CLI commands** — `ai-toolkit opencode-md`, `opencode-agents`, `opencode-commands`, `opencode-plugin`, `opencode-json`. Included in `generate-all`.
- **Skill reuse** — opencode reuses the Codex skill adapter (`codex_skill_adapter.py`) for Claude-only orchestration primitives since both lack `Agent`/`TeamCreate`/`TaskCreate` — no duplication.

### Changed
- README `What's New`, package.json description, manifest.json, and `app/.claude-plugin/plugin.json` all list opencode as a supported editor.
- **Plugin exports** — `.opencode/plugins/ai-toolkit-hooks.js` now uses a single named export (`AiToolkitHooks`) per opencode spec. The prior redundant `export default` was removed.
- **Agent frontmatter** — `model` field and source-model-hint comment are no longer emitted because opencode requires `provider/model-id` format, which ai-toolkit does not store. opencode falls back to the user's configured default model.
- **Global install layout fix** — global generators now write directly under `~/.config/opencode/{agents,commands,plugins}/` instead of the incorrect `~/.config/opencode/.opencode/…` nesting. Generators accept a `config_root` parameter to distinguish project vs global layout.
- **Test suite** — grew from 641 to 647 tests covering new event bridges, named-export invariant, missing-source-model-hint regression, and global-layout contract.

---

## v2.5.0 — Community Skills, Automated Scanners & Design Craft (2026-04-15)

### Added
- **`/seo-validate` skill** (community PR #2) — 9-category SEO scanner: W3C semantics, meta/OG tags, Schema.org, hreflang, Core Web Vitals, GEO, SPA/SSG crawlability. Framework-aware (React/Next/Nuxt/Astro/Gatsby/SvelteKit/Remix/Angular/Vue).
- **`/a11y-validate` skill** (community PR #3) — 10-category accessibility scanner: WCAG 2.1 AA, WCAG 2.2 AA, EN 301 549, European Accessibility Act (EAA). Mobile-aware (React Native/Flutter).
- **`seo-scanner.py`** — automated stdlib-only SEO scanner script (9 checks, JSON output, CI exit codes).
- **`a11y-scanner.py`** — automated stdlib-only accessibility scanner script (10 checks, WCAG criterion mapping, contrast calculation, CI exit codes).
- **`wcag-2-2-aa.md`** reference — all 9 new WCAG 2.2 success criteria with failure patterns, grep patterns, and framework notes.
- **`geo-aeo-patterns.md`** reference — Answer Engine Optimization: AI answer engines, llms.txt, robots.txt AI bot directives, E-E-A-T signals.
- **Design Craft vocabulary** (community PR #4) — 7-domain impeccable design guidance in `frontend-specialist` agent and `frontend-lead` persona: typography, OKLCH color, spatial scale, motion, interaction, responsive, UX writing. AI-Native UI patterns section.

### Changed
- **`code-reviewer` agent** — added Grep/Glob tools, rewrote Mandatory Protocol to use actual tools. Expanded review checklist: full OWASP Top 10, API/contract, concurrency/async, migration/schema.
- **`clean-code` python reference** — fixed invalid `any` type hint, modernized to PEP 604 syntax.
- **`design-engineering` skill** — fixed CSS hold-to-delete example (duplicate selector → proper `:active` override).
- **`review` skill** — fixed script path to use `CLAUDE_SKILL_DIR`.
- **`.gitattributes`** — added `merge=ours` for generated files to prevent contributor PR conflicts.
- **Misleading CLI outputs** fixed — plugin.py Codex status glob, --only help examples, install/update --local descriptions, doctor stale rules dr.warn(), config_cli phantom check.
- **`gemini` added to ALL_EDITORS** — `--editors gemini` no longer rejected by CLI validation.
- Skill count: 92 → 94 (31 task + 31 hybrid + 32 knowledge).

---

## v2.4.1 — Codex Global Install, Security Hardening & Editor Tracking (2026-04-15)

### Added
- **Codex hook propagation** — `inject-hook` auto-propagates Codex-compatible events (`SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`) to `~/.codex/hooks.json`. `remove-hook` cleans both targets.
- **Global editor tracking** — `ai-toolkit install --editors codex` installs editors globally (opt-in). Tracked in `state.json`, auto-refreshed on `update`. Default: Claude only.
- **Per-project editor tracking** — `install --local --editors` records editors in `projects.json`. `update` re-installs saved editors per project.
- **Auto-propagation** — `add-rule`, `remove-rule`, `mcp add` auto-propagate to globally installed editors via `propagate_global.py`.
- **Doctor Check 9** — URL hook sources health check with `--fix` re-fetch support.

### Fixed
- **Tarball path traversal** — `_extract_tarball` rejects symlinks, absolute paths, and paths escaping dest directory.
- **Git clone URL validation** — `_resolve_git` enforces HTTPS-only, rejects `file://`, `ssh://`.
- **`dr.error()` crash** — `DiagResult` has no `error()` method; fixed to `dr.fail()`.
- **`refresh_url_hooks` missing timestamp update** — now calls `register_url_source` after re-fetch.
- **Defense-in-depth name validation** — `register_url_source()` rejects path traversal chars in both `hook_sources` and `rule_sources`.
- **Unused `execSync` import** — removed from CLI entry point.
- **URL truncation detection** — `url_fetch.py` raises `ValueError` when response exceeds 10MB.
- **MCP templates path** — corrected `app/plugins/mcp-templates/` → `app/mcp-templates/` in ARCHITECTURE docs.
- **MCP templates header count** — corrected 25 → 26 in `app/ARCHITECTURE.md`.

---

## v2.4.0 — URL Hook Injection & Karpathy Coding Rules (2026-04-15)

### Added
- **URL hook injection** — `ai-toolkit inject-hook https://...` fetches, caches, and injects hooks from HTTPS URLs. Cached in `~/.softspark/ai-toolkit/hooks/external/`, auto-refreshed on every `update`. `remove-hook` also unregisters URL source and cleans cache.
- **Shared URL fetch module** — extracted `url_fetch.py` from `rule_sources.py` for reuse by both rule and hook URL sources.
- **Hook URL source registry** — `hook_sources.py` tracks URL-sourced hooks in `sources.json` (analogous to `rule_sources.py`).
- **Surgical Changes rule** — orphan cleanup protocol, match existing style, don't touch adjacent code (inspired by Karpathy's LLM coding guidelines).
- **Goal-Driven Execution rule** — `step → verify: check` pattern for multi-step tasks, strong success criteria before looping.

---

## v2.3.1 — Release Quality Gate (2026-04-14)

### Fixed
- **README "What's New" section** — was stuck at v2.1.3, now auto-validated by `validate.py --strict`
- **Release SOP** — added mandatory "Update README What's New" step to Phase 3 checklist

---

## v2.3.0 — Jira MCP Template & Cross-Editor Sync (2026-04-14)

### Added
- **Jira MCP template** — `ai-toolkit mcp add jira` installs `@softspark/jira-mcp` via global binary. Templates now support `postInstall` field for first-time setup hints shown after `mcp add`, `mcp install`, and `mcp show`. MCP template count: 25 → 26.
- **MCP template tracking** — globally installed templates are recorded in `state.json`. `ai-toolkit update` automatically syncs tracked templates to Claude global config. `ai-toolkit status` shows tracked MCP templates. "Install once, sync everywhere."

### Fixed
- **Claude MCP config paths** — corrected to `~/.claude.json` (global) and `.mcp.json` (project) per official Claude Code docs. Previously wrote to `~/.claude/settings.json` and `.claude/settings.local.json`.
- **Jira MCP template uses global binary** — `jira-mcp` instead of `npx -y` for faster startup and offline support

---

## v2.2.0 — URL Rules & Registry Safety (2026-04-14)

### Added
- **URL rule registration** — `ai-toolkit add-rule https://...` registers rules from HTTPS URLs. URL-sourced rules are tracked in `rules/sources.json` and auto-refreshed on every `ai-toolkit update`. Falls back to cached local copy on network failure.
- **Version consistency validation** — `validate.py --strict` now cross-checks `package.json`, `manifest.json`, and `plugin.json` versions match

### Fixed
- **Project registry race condition** — parallel `install --local` during `ai-toolkit update` could silently drop registry entries. Fixed with `fcntl.flock` exclusive lock, atomic writes (tempfile + rename), and deferred sequential registration after parallel phase.
- **Version drift** — `manifest.json` and `plugin.json` were stuck at 1.9.0 since v2.0.0, now synced
- **Language rules count** — ARCHITECTURE.md claimed 70 files, actual is 68
- **Skills catalog tiers** — added missing Tier 1.5 (planning pipeline + design/architecture)

---

## v2.1.3 — Idempotent Update Fix (2026-04-13)

### Fixed
- **`ai-toolkit update` no longer dirties git** — `inject_with_rules()` now strips all existing TOOLKIT sections before re-injecting, and `generate_agents_md.py` includes the Codex block for format consistency. Running `update` on a clean repo leaves zero uncommitted changes.
- **Custom rules always present** — all generators (standalone and via `inject_with_rules`) emit registered custom rules in every output format

---

## v2.1.1 — Custom Rules in Generators & README Restructure (2026-04-13)

### Fixed
- **Custom rules in generators** — `generate:all` now includes registered custom rules (from `ai-toolkit add-rule`) in all single-file generators (Cursor, Windsurf, Copilot, Gemini, AGENTS.md) and directory-based generators (Cline, Roo, Codex, Augment, Antigravity, Cursor MDC). Previously custom rules were lost on regeneration.
- **AGENTS.md double generation** — `generate-all` CLI no longer generates AGENTS.md twice; uses `codex-md` (superset) only
- **CLI help completeness** — added missing `--persona` option and `codex` to `--editors` list in `ai-toolkit help`

### Changed
- **README restructured** — reduced from 951 to 292 lines with Table of Contents, "What's New" section, and links to KB docs. Detailed content moved to dedicated KB documents.
- **npm `generate:agents`** — now uses `generate_codex.py` (consistent with CLI `generate-all`)
- **Test assertions** — generator file count tests use `>= 6` to accommodate registered custom rules

### New Files
- `kb/reference/cli-reference.md` — complete CLI command reference (moved from README)
- `kb/reference/unique-features.md` — detailed differentiators documentation (moved from README)
- `kb/reference/comparison.md` — ecosystem comparison table (moved from README)

---

## v2.1.0 — Codex CLI Support & Native Editor MCP Install (2026-04-13)

### Added
- **Codex CLI as 10th editor** — full support via `--editors codex`: `AGENTS.md`, `.agents/rules/*.md`, `.agents/skills/*`, `.codex/hooks.json`
- **Codex skill translation layer** — Claude-only orchestration skills (orchestrate, workflow, swarm, teams, subagent-development) are automatically translated to Codex-native `spawn_agent`/`update_plan` wrappers; native skills are symlinked directly
- **Native editor MCP install** — `ai-toolkit mcp install --editor <name> --scope project|global` renders canonical `.mcp.json` templates into 8 editor-native config formats (Claude, Cursor, Copilot, Gemini, Windsurf, Cline, Augment, Codex)
- **MCP auto-sync on local install** — `install --local` mirrors `.mcp.json` into `.claude/settings.local.json` plus selected project editors (Cursor, Copilot)
- **`mcp editors` subcommand** — lists all supported native MCP adapters with scope/path info
- **Cross-editor verification SOP** — mandatory check against official docs before adding any component
- **Runtime-aware plugin installs** — `ai-toolkit plugin install|update|remove|status --editor claude|codex|all` now targets Claude and a global Codex plugin layer consistently
- **Global Codex plugin layer** — plugin packs can bootstrap `~/AGENTS.md`, `~/.agents/`, and `~/.codex/hooks.json` without changing the default project-local Codex core install model
- **Plugin lifecycle tests** — coverage for install/update/remove behavior across Claude and Codex runtimes, including shared asset retention
- **Safe Codex and Cline rule regeneration** — `generate_codex_rules.py` and `generate_cline_rules.py` now support `--skip-cleanup` to refresh standard generated rules without deleting custom overlays

### New Files
- `scripts/mcp_editors.py` — 8 native MCP config adapters
- `scripts/codex_skill_adapter.py` — skill translation layer for Codex
- `scripts/generate_codex.py` — AGENTS.md generator with Codex orchestration guidance
- `scripts/generate_codex_hooks.py` — `.codex/hooks.json` generator
- `scripts/generate_codex_rules.py` — `.agents/rules/*.md` generator
- `kb/reference/codex-cli-compatibility.md` — Codex mapping reference
- `kb/reference/mcp-editor-compatibility.md` — native MCP support matrix
- `tests/test_plugin.bats` — runtime-aware plugin install/remove coverage

### Changed
- **Release workflow** — `generate:all` now refreshes tracked Codex rules and uses the directory-based Cline generator that matches the current repository layout
- **Documentation** — README, KB references, maintenance SOPs, and generated artifacts now consistently describe the Claude + global Codex plugin model

---

## v2.0.2 — Clean Legacy Directory Removal (2026-04-12)

### Fixed
- **Migration cleanup** — `~/.ai-toolkit/` is now fully removed after migration instead of leaving an empty directory with a `.migrated` marker

---

## v2.0.1 — Migration Hook Path Fix (2026-04-12)

### Fixed
- **settings.json hook paths** — migration now rewrites ALL hook commands (including plugin hooks with non-toolkit `_source` tags like `memory-pack`, `enterprise-pack`) from `~/.ai-toolkit/hooks/` to `~/.softspark/ai-toolkit/hooks/`

---

## v2.0.0 — SoftSpark Namespace Migration (2026-04-12)

### BREAKING CHANGES
- **Home directory moved** — `~/.ai-toolkit/` → `~/.softspark/ai-toolkit/`. Prepares the namespace for sibling tools (`jira-mcp`, etc.) under `~/.softspark/`
- **Per-project config renamed** — `.ai-toolkit.json` → `.softspark-toolkit.json`
- **Per-project lock file renamed** — `.ai-toolkit.lock.json` → `.softspark-toolkit.lock.json`

### Added
- **Auto-migration** — on first `install`/`update` after upgrade, data is automatically migrated from legacy path. A `.migrated` marker is left in `~/.ai-toolkit/` pointing to the new location
- **`scripts/paths.py`** — centralized path constants module; all scripts import from here instead of hardcoding paths
- **`scripts/migrate.py`** — standalone migration script (`python3 scripts/migrate.py [--dry-run]`)
- **Legacy fallback** — `config_resolver` and `config_lock` transparently read old filenames (`.ai-toolkit.json`, `.ai-toolkit.lock.json`) if new ones don't exist
- **JS CLI fallback** — `ai-toolkit update` checks legacy `state.json` location for seamless first upgrade

### Changed
- All Python scripts, Bash hooks, JS CLI, hooks.json, manifest.json, tests, and documentation updated to use `~/.softspark/ai-toolkit/` paths
- `AI_TOOLKIT_HOME` env var still supported as override

---

## v1.9.0 — Project Registry & Doc Sync (2026-04-12)

### Added
- **Project registry** — `install --local` automatically registers project path in `~/.softspark/ai-toolkit/projects.json`. `ai-toolkit update` propagates updates to all registered projects in parallel via `ThreadPoolExecutor`
- **`ai-toolkit projects`** — list registered projects, `--prune` to remove stale (deleted directories), `remove <path>` to unregister specific project
- **Parallel update propagation** — `ai-toolkit update` (global) now auto-updates all registered local projects concurrently (max 8 workers)

### Fixed
- **README.md** — skill count 91→92 in comparison table, added Augment/Antigravity to cross-tool tables, fixed Notification hook description (inline→`notify-waiting.sh`)
- **README.md** — added Config Inheritance section, Project Registry section, 6 new CLI commands to reference table
- **ARCHITECTURE.md** — added Config Inheritance and Project Registry to Extension Points
- **CLAUDE.md** — added `config` and `projects` commands

---

## v1.8.0 — Enterprise Config Inheritance (2026-04-12)

### Added
- **Configuration inheritance system** — `extends` pattern (like ESLint/TypeScript) for multi-repo AI governance. Organizations define a shared base config published as npm package, git URL, or local path; projects inherit via `.softspark-toolkit.json`
- **`ai-toolkit config validate`** — schema validation + extends resolution + enforcement check
- **`ai-toolkit config diff`** — visual diff of project vs base config (profile, agents, rules, constitution, overrides)
- **`ai-toolkit config init`** — interactive or flag-driven `.softspark-toolkit.json` creation with extends validation
- **`ai-toolkit config create-base`** — scaffolds ready-to-publish npm base config package (package.json, ai-toolkit.config.json, rules/, agents/, README)
- **`ai-toolkit config check`** — CI enforcement gate with JSON output and exit codes (0=pass, 1=fail, 2=no config)
- **Merge engine** — layered deep merge (base → project) with special handling for agents (requiredAgents enforcement), rules (union), constitution (immutability), enforce blocks (cannot weaken)
- **Constitution immutability guard** — Articles I-V absolutely immutable; base config articles immutable; projects can only ADD new articles (6+)
- **Override validation** — `override: true` + justification (min 20 chars) required; `forbidOverride` enforcement
- **Enforce constraints** — 4 types: `minHookProfile`, `requiredPlugins`, `forbidOverride`, `requiredAgents`
- **Lock file** (`.softspark-toolkit.lock.json`) — pins resolved base config versions for reproducible installs across team; generated on `install --local`, updated on `update --local`
- **Audit trail** — extends metadata recorded in `state.json` and `.softspark-toolkit-extends.json`
- **Offline fallback** — uses cached configs from `~/.softspark/ai-toolkit/config-cache/` when registry unavailable
- **Cycle detection** — max 5-level extends chain with circular reference detection
- **Install integration** — `install --local` and `update --local` auto-detect `.softspark-toolkit.json`, resolve extends, merge, validate, inject rules + constitution amendments into generated files
- **New CLI flags** — `--config <path>` (explicit config file), `--refresh-base` (force re-fetch)
- **JSON Schema** — `scripts/schemas/ai-toolkit-config.schema.json` for editor autocompletion
- **Enterprise config guide** — `kb/reference/enterprise-config-guide.md` comprehensive documentation
- **52 new tests** — resolver (7), merger (13), CLI (23), install integration (9)

### Changed
- **`manifest.json`** — added `config_inheritance` section with schema references and v1 field list

---

## v1.7.0 — Offline-First SLM Compilation (2026-04-11)

### Added
- **`compile-slm` command** — compiles full toolkit (20K+ tokens) into a minimal system prompt for Small Language Models (2K-16K tokens). Supports 4 compression levels (ultra-light, light, standard, extended), 4 output formats (raw, ollama, json-string, aider), persona-aware scoring, and language-aware rule filtering. `scripts/compile_slm.py`
- **`offline-slm` profile** — `manifest.json` profile for offline/air-gapped installs
- **Post-compilation validator** — checks constitution presence, budget compliance, guard hooks, output sanity
- **Integration guides** — step-by-step setup for Ollama, LM Studio, Aider, Continue.dev printed after compilation
- **61 tests** for compile-slm (token counter, parser, compression, packer, emitter, formats, CLI, determinism, budget compliance, validator, guides)

### Fixed
- **Skill counts** — synced stale count 91 → 92 across README.md (3 locations) and manifest.json
- **KB frontmatter validation** — `kb/history/` excluded from category-dir match (archived plans keep original category)

---

## v1.6.1 — IDE Rule Format Compliance Audit (2026-04-10)

### Fixed
- **Cline rules path** — changed `.cline/rules/` to `.clinerules/` directory per official Cline 3.7+ docs. Old path was silently ignored by Cline
- **Augment frontmatter type** — changed `auto_attached` to `agent_requested` per official Augment docs
- **Aider config** — added `CONVENTIONS.md` to `read:` list in `.aider.conf.yml` so Aider auto-loads the conventions we generate

### Changed
- **`add-rule` help text** — now lists all supported editors (was missing Augment, Roo, Aider, Antigravity)
- Legacy `.clinerules` single-file is auto-migrated to `.clinerules/` directory on next install

---

## v1.6.0 — IDE Language Rules Propagation, Planning Docs, Cloud Security Pack (2026-04-10)

### Added
- **Language rules propagation to all IDE editors** — shared `dir_rules_shared.py` module now injects language-specific and registered rules into Cursor, Windsurf, Cline, Roo Code, Augment, Antigravity, and Copilot generators. All platforms receive identical rule content from a single source of truth.
- **Enterprise Config Inheritance Plan** — planning doc (`kb/planning/enterprise-config-inheritance-plan.md`) for hierarchical config system
- **Offline SLM Profile Plan** — planning doc (`kb/planning/offline-slm-profile-plan.md`) for offline small language model profiles
- **Cloud Security Pack Plan** — planning doc (`kb/planning/cloud-security-pack-plan.md`) for multi-cloud audit (GCP/AWS/Azure)
- **193 new generator tests** — language rules propagation, content verification, cross-platform parity

### Changed
- **Documentation standards** — added `planning` as a valid KB category in `validate.py`, `documenter` agent, `/docs` and `/documentation-standards` skills
- **Maintenance SOP** — updated to reflect language rules propagation workflow

---

## v1.5.1 — Security Hardening: Script Injection, XSS, Private Data Leak (2026-04-10)

### Fixed
- **`action.yml` script injection** — replaced `${{ inputs.command }}` direct interpolation with `env:` variable to prevent GitHub Actions script injection (OWASP A03)
- **`visual-server.cjs` stored XSS** — extracted inline script to `poll.js`, added `Content-Security-Policy: script-src 'self'` header to block injected scripts in PRD visual preview
- **`strip_private.py` regex** — changed `[^<]*` to `.*?` with `re.DOTALL` flag to correctly handle multi-line `<private>` blocks and inner angle brackets (was leaking private data in edge cases)

---

## v1.5.0 — HIPAA Scanner: Deterministic Script, CI Integration, Self-Exclusion (2026-04-10)

### Added
- **`scripts/hipaa_scan.py`** — deterministic Python scanner (stdlib-only) for `/hipaa-validate`. Replaces LLM-driven regex execution with a reproducible script. 8 check categories, context gate, `.hipaaignore` support, `.hipaa-config` BAA vendor list, deduplication, structured output.
- **`--output json` flag** for `/hipaa-validate` — structured JSON output for CI/CD pipeline integration. Exit code 1 on HIGH findings, 0 otherwise.
- **Self-exclusion** — scanner automatically excludes its own skill directory to prevent flagging its own regex definitions.
- **`.hipaaignore`** — project-level exclusion file (gitignore syntax) for suppressing known false positives.
- **IDE/AI config file exclusions** — `.roomodes`, `.cursorrules`, `.windsurfrules`, `llms.txt`, `llms-full.txt`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `COPILOT.md` automatically skipped (contain pattern examples, not source code).

### Changed
- **`/hipaa-validate` frontmatter** — added `user-invocable: true`, `context: fork`, `agent: security-auditor`, `Bash` in `allowed-tools`.
- **`/hipaa-validate` workflow** — pivoted from "manually execute regex patterns" to "run script, interpret results, suggest specific fixes."
- **Documentation alignment** — updated hipaa-validate descriptions in README.md, ARCHITECTURE.md, skills-catalog.md, llms-full.txt to include all 8 check categories (was missing "temp file exposure" and "missing BAA references").
- Skill count: 91 → 92 in package.json description.

---

## v1.4.2 — --local Scoping Fix, Leading Blank Lines Fix (2026-04-09)

### Fixed
- `--local` now runs only project-local install (no global re-install). Global install runs separately without `--local`.
- Fixed leading blank lines in generated files (copilot-instructions.md, etc.) caused by `inject_section` and `inject_with_rules`.
- Context-aware "Next steps" message (local vs global).

### Changed
- Updated KB docs: global-install-model.md, maintenance-sop.md to reflect `--local` scoping change.

---

## v1.4.1 — Documentation Fix: --local Behavior (2026-04-09)

### Fixed
- README Per-Project Setup, Quick Start, and CLI table now correctly state that `--local` installs Claude Code only by default, with `--editors` flag for other tools.

---

## v1.4.0 — Full Platform Parity: 11 Editors, Directory-Based Rules, --editors Flag (2026-04-09)

### Added
- **Google Antigravity support** — new editor integration with `.agent/rules/` (6 rule files) and `.agent/workflows/` (13 workflow templates with YAML frontmatter). Full agent/skill catalog parity with other platforms.
- **Directory-based rules for all editors** — every platform now gets modern directory-based configs in addition to legacy single-file formats:
  - Cursor: `.cursor/rules/*.mdc` with YAML frontmatter (`alwaysApply`, `globs`, `description`)
  - Windsurf: `.windsurf/rules/*.md`
  - Cline: `.cline/rules/*.md`
  - Roo Code: `.roo/rules/*.md` (shared rules for all modes)
  - Augment: `.augment/rules/ai-toolkit-*.md` with `auto_attached` globs per file type
  - Aider: `CONVENTIONS.md` (auto-loaded as read-only context)
- **`--editors` flag** for `install --local` — selective editor installation:
  - `--editors all` — install all 8 editors
  - `--editors cursor,aider` — install only selected
  - (no flag) — auto-detect from existing project files
  - `update --local` auto-detects editors from existing configs
- **`--lang` flag** — explicit language selection for rules (`--lang typescript`, `--lang go,python`) with aliases (`go`→`golang`, `c++`→`cpp`, `cs`→`csharp`)
- **Two-phase language detection** — marker files (package.json, go.mod, etc.) + source file extension scanning (.py, .ts, .go, etc.)
- **Shared rule content module** (`dir_rules_shared.py`) — all platforms get identical agent/skill catalog, guidelines, and rules from a single source of truth
- **7 new CLI commands**: `cursor-mdc`, `windsurf-dir-rules`, `cline-dir-rules`, `roo-dir-rules`, `augment-dir-rules`, `conventions-md`, `antigravity-rules`
- **71 generator tests** — file existence, content verification, user file preservation, idempotency, stale cleanup, cross-platform parity check

### Changed
- `install --local` now installs only Claude Code configs by default (no editor bloat); editors require `--editors` flag or auto-detect from existing files
- All directory-based generators use `ai-toolkit-` prefix to prevent overwriting user files
- Total test count: 377 → 408

---

## v1.3.15 — Quality Guardrails: Anti-Rationalization, Confidence Scoring, Verification Checklists (2026-04-08)

### Added
- **Anti-rationalization tables** — 15 core skills now include `## Common Rationalizations` sections with domain-specific excuse/rebuttal tables that prevent agent drift and shortcut-taking. Inspired by [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).
- **Confidence scoring** (`/review`) — review findings now include per-issue confidence scores (1-10) and severity classification (critical/major/minor/nit) with a calibration guide.
- **LLM-as-Judge self-evaluation** (`/review`) — structured self-check after review: blind spot detection, anchoring bias check, and confidence calibration.
- **Agent verification checklists** — 10 key agents (`code-reviewer`, `test-engineer`, `security-auditor`, `debugger`, `backend-specialist`, `frontend-specialist`, `database-architect`, `performance-optimizer`, `devops-implementer`, `documenter`) now include `## Verification Checklist` exit criteria.
- **Skill reference routing** — 7 core skills (`/review`, `/debug`, `/plan`, `/refactor`, `/tdd`, `/docs`, `/analyze`) include `## Related Skills` sections for follow-up discoverability.
- **Intent Capture Interview** (`/onboard`) — Step 0 interview phase with 5 targeted questions to capture undocumented project intent before setup.

---

## v1.3.14 — CVE Scanner + Open Contributions (2026-04-08)

### Added
- **`/cve-scan` skill** — auto-detect project ecosystems (npm, pip, composer, cargo, go, ruby, dart) and scan dependencies for known CVEs using native audit tools. Includes `cve_scan.py` scanner script with parsers for npm and pip-audit, unified severity report, `--fix` and `--json` modes.
- **CVE scan in security-auditor agent** — `/cve-scan` is now a mandatory first step in the OWASP A06 (Vulnerable Components) checklist.
- **CVE scan in `/workflow security-audit`** — security-auditor agent runs CVE scan as part of the parallel audit phase.
- **`security-audit` CI job** — `audit_skills.py --ci` now runs in GitHub Actions pipeline.
- **`CODE_OF_CONDUCT.md` in CI** — added to required files check.
- **`.github/CODEOWNERS`** — auto-assigns maintainer for review.
- **`.github/FUNDING.yml`** — GitHub Sponsors configuration.
- **GitHub Security Advisories** — added CVE/advisory procedure to `SECURITY.md`.
- **Open contribution workflow** — full `CONTRIBUTING.md` rewrite (fork, branch naming, commit conventions, CI requirements), PR checklist template, blank issues enabled.

### Removed
- **`close-prs.yml`** — removed auto-close workflow to accept external PRs.

### Fixed
- **Copyright** — `LICENSE` updated from `2024-present` to `2024-2026`.
- **`SECURITY.md`** — removed duplicate Scope section.

---

## v1.3.13 — CLI --version flag (2026-04-08)

### Added
- **`--version` / `-v` / `version` CLI flag** — prints clean semver string and exits 0 (previously fell through to "Unknown command" with exit 1).
- **3 new CLI tests** for `--version`, `-v`, and `version` subcommand.

---

## v1.3.12 — Cross-platform notifications + version check fix (2026-04-08)

### Fixed
- **Version check**: `ai-toolkit status` and session-start hook now read installed version from `state.json` instead of `package.json`, fixing false "up to date" when npm package was upgraded but `ai-toolkit update` not yet run.
- **Version check**: `status` forces a fresh npm check (no 24h cache) so user always sees real state.
- **Session-start hook**: `TOOLKIT_DIR` resolved via `npm root -g` instead of broken `../../` relative path from `~/.softspark/ai-toolkit/hooks/`.

### Changed
- **Notification hook**: replaced inline macOS-only `osascript` with cross-platform `notify-waiting.sh` script (macOS/Linux/Windows WSL).
- **Update notification**: session-start hook now shows desktop notification (macOS/Linux/Windows) when a new version is available.

---

## v1.3.11 — Proactive Context Checkpointing + Augment CLI (2026-04-08)

### Added
- **Constitution Art. I §5: Proactive Context Checkpointing** — agents must checkpoint `.claude/session-context.md` during multi-step tasks (objective, completed/pending steps, files modified, key decisions).
- **`augment-rules` CLI command** — wired `generate_augment.py` into `bin/ai-toolkit.js` GENERATORS + COMMANDS + `generate-all`. Generates `.augment/rules/ai-toolkit.md`.
- **Augment in Platform Support** — added to README table with project scope.

### Changed
- **`save-session.sh`** — enriched with git branch, dirty count, diff stat, and agent-written checkpoint preservation.
- **Language rules count** — corrected 70→68 in README.md (13 dirs × 5 + 3 standalone).
- **Secondary docs** — removed hardcoded rule counts from `language-rules.md`, `architecture-overview.md`, `competitive-features-implementation.md`; reference README for canonical count.
- **README architecture tree** — added missing `track-usage.sh`.

---

## v1.3.10 — Patch (2026-04-07)

### Fixed
- **Version cache**: `install` and `update` now clear `~/.softspark/ai-toolkit/version-check.json` so `status` shows correct "Latest" immediately after upgrade.

---

## v1.3.9 — Single Source of Truth for Counts (2026-04-07)

### Changed
- **Counts policy**: Hardcoded skill/agent/hook/test counts removed from all secondary docs. Only README.md, manifest.json, and package.json contain counts. Rule: `kb/best-practices/no-hardcoded-counts.md`.
- **47 new tests** (327 → 374): MCP manager, language auto-detect, install state, version check, new hooks, orphan cleanup.

### Fixed
- manifest.json version synced (was 1.0.0)
- plugin.json version synced (was 1.2.1)
- agents-catalog.md version aligned
- ARCHITECTURE.md hook event multipliers corrected
- Generator scripts no longer embed counts

---

## v1.3.8 — Language Rules as References (2026-04-07)

### Changed
- **Language rules injection**: Instead of inlining full rule content (~705 lines), `install --local` now injects lightweight reference pointers (~12 lines) with absolute paths to rule files. Claude reads them on demand via Read tool, keeping CLAUDE.md compact.
- **plugin.json**: Version synced from stale 1.2.1 to 1.3.8.

---

## v1.3.7 — Update Notifications (2026-04-07)

### Added
- **Update notifications**: `session-start.sh` hook checks npm for newer versions (cached 24h, non-blocking). `ai-toolkit status` shows installed vs latest version with upgrade command.

---

## v1.3.6 — Patch (2026-04-07)

### Fixed
- **Tests updated**: All hook tests now pass stdin JSON instead of env vars (matching hook changes from v1.3.5). 327/327 tests pass.

---

## v1.3.5 — Patch (2026-04-07)

### Fixed
- **Stats not counting**: `track-usage.sh` and `user-prompt-submit.sh` now read prompt from stdin JSON (`.prompt` field) instead of non-existent `CLAUDE_USER_PROMPT` env var. Skill invocations are now properly tracked in `~/.softspark/ai-toolkit/stats.json`.

---

## v1.3.4 — Patch (2026-04-07)

### Fixed
- **skills-catalog.md**: Added 6 missing language pattern skills (rust, java, csharp, kotlin, swift, ruby) to Development section (10→16). Total now correctly sums to 90.

---

## v1.3.3 — Patch (2026-04-07)

### Fixed
- **manifest.json missing from npm package**: Added `manifest.json` to `package.json` `files` array. Without it, `--auto-detect` and `--modules` could not read module definitions from installed package.

---

## v1.3.2 — Patch (2026-04-07)

### Fixed
- **Orphaned symlinks**: `install` and `update` now auto-clean broken agent/skill symlinks when components are removed or merged. Previously required manual `doctor --fix`.
- **`--auto-detect` without `--local`**: Now auto-adds `--local` with warning instead of scanning `$HOME` for language markers.
- **Session hooks concurrency**: `session-context.sh` writes per-session file (`${SESSION_ID}.json`) instead of single `current-context.json`. `pre-compact-save.sh` includes session ID in filename to avoid collisions.
- **Language rules injection**: `install --local` now actually injects detected language rules into project `.claude/CLAUDE.md` via `<!-- TOOLKIT:language-rules -->` markers.
- **`--local` implies `--auto-detect`**: No need to pass both flags — `install --local` automatically detects project language and installs matching rules.

---

## v1.3.0 — Competitive Features Release (2026-04-07)

### Added
- **Language Rules System**: 70 language-specific coding rules across 13 languages (TypeScript, Python, Go, Rust, Java, Kotlin, Swift, Dart, C#, PHP, C++, Ruby) + 5 common rules. 5 categories per language: coding-style, testing, patterns, frameworks, security.
- **MCP Templates**: 25 ready-to-use MCP server configuration templates (GitHub, PostgreSQL, Slack, Sentry, Context7, etc.) with CLI management (`ai-toolkit mcp add/list/show/remove`).
- **Extension API**: `inject-hook` / `remove-hook` commands for external tools to inject hooks into settings.json with unique `_source` tags. Parallels existing `inject-rule` / `remove-rule`.
- **Manifest-Driven Install**: Module-level install granularity (`--modules`), language auto-detection (`--auto-detect`), install state tracking (`~/.softspark/ai-toolkit/state.json`), `status` and `update` commands.
- **6 new hooks**: `guard-config.sh` (config file protection), `mcp-health.sh` (MCP server health check), `governance-capture.sh` (security audit logging), `commit-quality.sh` (conventional commits advisory), `session-context.sh` (environment snapshot), `pre-compact-save.sh` (pre-compaction backup).
- **`/council` skill**: 4-perspective decision evaluation (Advocate, Critic, Pragmatist, User-Proxy) for architectural decisions.
- **`/introspect` skill**: Agent self-debugging with 7 failure pattern classification and recovery actions.
- **`brand-voice` knowledge skill**: Anti-trope list preventing generic LLM rhetoric, auto-loaded when writing documentation.
- **KB reference docs**: extension-api.md, language-rules.md, mcp-templates.md, manifest-install.md.

### Changed
- Agent count: 47 → 44 (merged 3 overlapping pairs: rag-engineer into ai-engineer, research-synthesizer into technical-researcher, mcp-expert + mcp-server-architect into mcp-specialist)
- Hook count: 14 → 20 global hooks across 12 lifecycle events
- Skill count: 87 → 90 (28 task + 30 hybrid + 32 knowledge)
- Updated hooks-catalog.md, skills-catalog.md with new entries

---

## [1.2.1] - 2026-04-03

### Changed
- **README.md** — added full documentation for all v1.2.0 features:
  - `/persona` runtime switching with usage examples
  - `audit_skills.py` CI pipeline integration with `--json` and `--ci` flags
  - Skill Security Auditing section (severity levels, detection patterns)
  - Persona Presets section (table with focus areas and key skills per role)
  - Smart compaction description in hooks table
  - Fixed section numbering (was duplicated at 4, skipped 10)
- **CLAUDE.md** — added CRITICAL note: documentation/count accuracy is non-negotiable, must run validate + audit before every commit
- **skills-catalog.md** — fixed stale frontmatter (was 85 skills/v1.0.0, now 87 skills/v1.2.1)
- Version bump: 1.2.0 → 1.2.1 (package.json, plugin.json)

[1.2.1]: https://github.com/softspark/ai-toolkit/releases/tag/v1.2.1

---

## [1.2.0] - 2026-04-03

### Added
- **`/skill-audit` skill** — security scanner for skills and agents: detects dangerous code patterns (`eval`, `exec`, `os.system`), hardcoded secrets (AWS keys, GitHub PATs, private keys), overly permissive `allowed-tools`, and missing safety constraints. Supports `--fix` for auto-remediation of safe issues. CI-ready (non-zero exit on HIGH findings).
- **Persona presets** (`--persona` flag) — 4 engineering personas: `backend-lead`, `frontend-lead`, `devops-eng`, `junior-dev`. Each injects role-specific communication style, preferred skills, and code review priorities into CLAUDE.md. Usage: `ai-toolkit install --persona backend-lead`.
- **`/persona` runtime switching** — new hybrid skill to switch persona at runtime without re-install. Usage: `/persona backend-lead`, `/persona --list`, `/persona --clear`. Session-scoped.
- **Augment editor support** — `scripts/generate_augment.py` generates `.augment/rules/ai-toolkit.md` with proper frontmatter (`type: always_apply`). Registered in global install.
- **`scripts/audit_skills.py`** — deterministic Python scanner for CI pipelines. Scans skills/agents for dangerous patterns, secrets, permission issues. JSON output (`--json`), non-zero exit on HIGH (`--ci`). Found 4 real HIGH findings in our own toolkit.

### Changed
- **Smart compaction** (`pre-compact.sh`) — enhanced with prioritized context preservation: instincts (with confidence scores) > session context > git state (branch, dirty files, last commit) > key decisions. Replaces flat output with structured sections.
- Editor count: 8 → 9 (added Augment)
- Skill count: 85 → 87 (added `skill-audit`, `persona`)
- Task skill count: 27 → 28 (`skill-audit`)
- Hybrid skill count: 27 → 28 (`persona`)

[1.2.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.2.0

---

## [1.1.0] - 2026-04-02

### Added
- **Agent Teams auto-enabled** — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is now automatically set in `~/.claude/settings.json` via `env` field during `install` / `update`. No manual `export` needed.
- 2 new install tests: env var injection + user env var preservation

### Fixed
- README test badge count: 308 → 310

[1.1.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.1.0

---

## [1.0.0] - 2026-04-02

### Added
- **85 skills** across task, hybrid, and knowledge categories
  - 27 task skills including `hook-creator`, `command-creator`, `agent-creator`, `plugin-creator`, and `/repeat` (Ralph Wiggum autonomous loop)
  - 27 hybrid skills (including PRD pipeline, TDD, design-an-interface, architecture-audit, QA session, `/subagent-development` with 2-stage review, `/mem-search`)
  - 31 knowledge skills (including 6 language-specific: Rust, Java, C#, Kotlin, Swift, Ruby; plus `verification-before-completion`)
- **47 specialized agents** across architecture, development, security, infrastructure, research, AI/ML, orchestration, and operations domains
- **15 global hook entries** including `UserPromptSubmit`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PreCompact`, `SessionEnd`, `track-usage.sh`, and `guard-path.sh`
- **5 skill-scoped hooks** for commit, test, deploy, migrate, and rollback workflows
- **Output style `Golden Rules`** — enforces critical rules at system prompt level (search-first, tool discipline, path safety, git conventions, language match, minimal changes)
- **`depends-on:` frontmatter field** for skill dependency declaration with validation and metrics
- **`ai-toolkit stats`** command with local usage tracking via `UserPromptSubmit` hook
- **`guard-path.sh` PreToolUse hook** — blocks file operations with wrong-user home directory paths (prevents path hallucination)
- **11 plugin packs** — 4 domain + 6 language-specific (Rust, Java, C#, Kotlin, Swift, Ruby) + memory-pack (SQLite-based persistent memory with FTS5 search)
- **`ai-toolkit plugin` CLI** — install, remove, list, and status for plugin packs (`plugin install <name>`, `plugin install --all`, `plugin remove`, `plugin list`, `plugin status`)
- **`ai-toolkit benchmark --my-config`** — compare installed config vs toolkit defaults vs ecosystem
- **`ai-toolkit create skill --template=TYPE`** — 5 templates: linter, reviewer, generator, workflow, knowledge
- **`ai-toolkit sync`** — config portability via GitHub Gist (`--export`, `--push`, `--pull`, `--import`)
- **Reusable GitHub Action** (`action.yml`) for CI validation
- `ai-toolkit doctor` / `doctor --fix` — install health, auto-repair broken symlinks, hooks, artifacts
- `ai-toolkit eject` — standalone copy, no toolkit dependency
- `benchmark-ecosystem` CLI command plus `scripts/benchmark-ecosystem.sh`
- `scripts/harvest-ecosystem.sh` plus machine-readable benchmark artifacts in `benchmarks/`
- Plugin manifest support in `app/.claude-plugin/plugin.json`
- Cross-tool generated artifacts for Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, and llms indexes
- **Roo Code support** — `ai-toolkit roo-modes` and `generate-roo-modes.sh`
- **Aider support** — `ai-toolkit aider-conf` and `generate-aider-conf.sh`
- **Git hooks safety fallback** — pre-commit hook for non-Claude editors
- **MCP defaults** — `app/mcp-defaults.json` template for `settings.local.json`
- **Install profiles** (`--profile minimal|standard|strict`)
- **`npx @softspark/ai-toolkit install`** — zero-friction trial without global install
- `--dry-run` flag as alias for `--list` in install/update
- MIT license — full open source, use/modify/distribute freely
- Global install into `~/.claude/` with merge-friendly propagation; hooks merged into `settings.json`, scripts copied into `~/.softspark/ai-toolkit/hooks/`
- Idempotent generators with `<!-- TOOLKIT:ai-toolkit START/END -->` markers
- CI: auto-regenerate `AGENTS.md` and `llms.txt` on push to main; publish on tags
- **DRY refactoring**: `scripts/_common.py` shared library for all generators and CLI scripts; `app/hooks/_profile-check.sh` for 9 hooks; CLI uses data-driven `GENERATORS` map
- All hooks standardized to `#!/usr/bin/env bash` shebang
- 310 tests across 16 test files
- **Iron Law enforcement** in TDD, debugging, and verification skills — anti-rationalization tables prevent agents from skipping test-first, root-cause analysis, or claiming completion without evidence
- **`/subagent-development`** — 2-stage review workflow: dispatch implementer → spec compliance review → code quality review per task, with 4-status protocol (DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED) and prompt templates
- **`/repeat`** — Ralph Wiggum autonomous loop pattern with safety controls: max iterations (default 5), circuit breaker (3 consecutive failures → halt), min interval (1 minute), exit detection, stats logging
- **`verification-before-completion`** — knowledge skill enforcing evidence-before-claims protocol: agents must run verification commands and read output before asserting success
- **Visual companion** for `/write-a-prd` and `/design-an-interface` — ephemeral local HTTP server renders mockups, diagrams, and comparisons in browser during brainstorming
- **Memory plugin pack** (`app/plugins/memory-pack/`) — SQLite-based persistent memory across sessions with FTS5 full-text search, PostToolUse observation capture, Stop session summary, `<private>` tag privacy controls, and progressive disclosure (summary → details → full)
- **`validate.py --strict`** — CI-grade validation treating warnings as errors, plus content quality checks (name=directory, non-empty body)
- **`doctor.py` stale rules detection** (Check 8) — detects rules in CLAUDE.md whose source files no longer exist in `~/.softspark/ai-toolkit/rules/`
- **Reasoning engine template** (`app/skills/skill-creator/templates/reasoning-engine/`) — generic Python stdlib search for domain skills with >50 categorized items, anti-pattern filtering, JSON stdout
- **Dashboard template** (`app/skills/skill-creator/templates/dashboard/index.html`) — single-file HTML dashboard parsing `stats.json` with skill usage charts
- **Anti-pattern registry format** documented at `kb/reference/anti-pattern-registry-format.md` — structured JSON schema with severity, auto-fixability, and conflict rules
- **Hierarchical override pattern** documented at `kb/reference/hierarchical-override-pattern.md` — SKILL.md + reference/*.md convention with explicit override semantics
- **Constitution Article I, Section 4** — Autonomous Loop Limits (max 5 iterations, circuit breaker, min interval, mandatory logging)
- **Python type hints and docstrings** on all skill scripts + merge-hooks.py — `from __future__ import annotations`, Google-style docstrings
- **CLI refactored** to data-driven dispatch — 170-line switch/case replaced by 14-line dispatch block
- **All scripts migrated from Bash to Python** — 51 Python scripts (stdlib-only, zero pip dependencies), hooks remain in Bash for startup speed. Shared library `scripts/_common.py` replaces `_generate-common.sh` + `inject-section.sh` + `inject-rule.sh`
- **`scripts/check_deps.py`** — dependency checker detects OS (macOS/Ubuntu/Fedora/Arch/Alpine/WSL), checks python3/git/node/sqlite3/bats, outputs ready-to-copy install commands. Integrated into `install.py` (blocks on missing deps) and `doctor.py` (enhanced environment check)

[1.0.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.0.0
