---
title: "Manifest-Driven Install System"
category: reference
service: ai-toolkit
tags: [install, manifest, modules, profiles, auto-detect, state-tracking, dsh]
version: "1.16.0"
created: "2026-04-07"
last_updated: "2026-09-01"
description: "Reference for manifest-driven project installation, explicit DSH profile lifecycle management, and ownership state in ~/.softspark/ai-toolkit/state.json."
---

# Manifest-Driven Install System

## Overview

ai-toolkit's install system supports module-level granularity on top of the existing profile-based install. Instead of choosing only between minimal/standard/strict, you can select individual modules (specific language rules, MCP templates, etc.) or enable auto-detection of the project language.

All existing `--profile` behavior is preserved and unchanged. The manifest system is an additive opt-in layer.

## Modules

Modules are defined in `manifest.json` at the repository root. There are 17 modules:

| Module | Description | In Profile |
|--------|-------------|-----------|
| `core` | Core hooks and essential skills | minimal, standard, strict, full |
| `agents` | Specialized agents | standard, strict, full |
| `skills` | All skills (task, hybrid, knowledge) | standard, strict, full |
| `rules-common` | Common coding rules (5 files) | standard, strict, full |
| `rules-typescript` | TypeScript-specific rules (5 files) | auto-detect |
| `rules-python` | Python-specific rules (5 files) | auto-detect |
| `rules-golang` | Go-specific rules (5 files) | auto-detect |
| `rules-rust` | Rust-specific rules (5 files) | auto-detect |
| `rules-java` | Java-specific rules (5 files) | auto-detect |
| `rules-kotlin` | Kotlin-specific rules (5 files) | auto-detect |
| `rules-swift` | Swift-specific rules (5 files) | auto-detect |
| `rules-dart` | Dart/Flutter-specific rules (5 files) | auto-detect |
| `rules-csharp` | C#/.NET-specific rules (5 files) | auto-detect |
| `rules-php` | PHP-specific rules (5 files) | auto-detect |
| `rules-cpp` | C++-specific rules (5 files) | auto-detect |
| `rules-ruby` | Ruby-specific rules (5 files) | auto-detect |
| `mcp-templates` | 28 MCP server config templates | strict, full |

## Profiles

Profiles are predefined module sets. They map directly to `--profile` values:

| Profile | Modules |
|---------|---------|
| `minimal` | `core` |
| `standard` | `core`, `agents`, `skills`, `rules-common` |
| `strict` | `core`, `agents`, `skills`, `rules-common`, `mcp-templates` |
| `full` | All modules (same as strict currently; language rules added via `--auto-detect`) |

## CLI

```bash
# Profile-based install (existing behavior, unchanged)
ai-toolkit install --profile standard

# Module-based install (new)
ai-toolkit install --modules core,agents,rules-typescript

# --local implies --auto-detect (language rules auto-detected)
ai-toolkit install --local

# Show currently installed modules and their state
ai-toolkit status

# Incremental update (only re-applies modules with changed content)
ai-toolkit update
```

### --modules

Accepts a comma-separated list of module names. Can be combined with a profile:

```bash
# Start from standard profile, also add TypeScript rules
ai-toolkit install --profile standard --modules rules-typescript
```

### --auto-detect

Scans the current working directory for marker files and selects the matching language module. Implemented in `scripts/install_steps/detect_language.py`.

Detection markers per module:

| Module | Detected when these files exist |
|--------|--------------------------------|
| `rules-typescript` | `package.json` or `tsconfig.json` |
| `rules-python` | `requirements.txt`, `pyproject.toml`, `setup.py`, or `Pipfile` |
| `rules-golang` | `go.mod` |
| `rules-rust` | `Cargo.toml` |
| `rules-java` | `pom.xml` or `build.gradle` |
| `rules-kotlin` | `build.gradle.kts` |
| `rules-swift` | `Package.swift` |
| `rules-dart` | `pubspec.yaml` |
| `rules-csharp` | `*.csproj` or `*.sln` |
| `rules-php` | `composer.json` |
| `rules-cpp` | `CMakeLists.txt` or `Makefile` |
| `rules-ruby` | `Gemfile` |

### status

Lists all currently installed modules with version and install timestamp:

```bash
ai-toolkit status
# Installed modules (from ~/.softspark/ai-toolkit/state.json):
#   core            v1.3.0   installed 2026-04-07T10:00:00Z
#   agents          v1.3.0   installed 2026-04-07T10:00:00Z
#   skills          v1.3.0   installed 2026-04-07T10:00:00Z
#   rules-common    v1.3.0   installed 2026-04-07T10:00:00Z
#   rules-typescript v1.3.0  installed 2026-04-07T10:00:00Z
```

### update

Re-applies installed modules, skipping files whose content hash has not changed since last install. Implemented in `scripts/install_steps/install_state.py`.

## Explicit DSH Profile Lifecycle

The DSH project target and the DSH profile lifecycle are separate operations:

```bash
# Generic local outputs plus DSH-specific project skills. No DSH profile change.
ai-toolkit install --local --editors dsh

# Read-only project plan, including extends resolution.
ai-toolkit install --local --editors dsh --dry-run

# Explicit global DSH profile mutation. The default profile is web.
ai-toolkit dsh install --profile web
ai-toolkit dsh update --profile web
ai-toolkit dsh doctor --profile web
ai-toolkit dsh uninstall --profile web --yes
```

The project command is explicit-only. DSH is excluded from `--editors all`, auto-detection, default profiles, and default editor selection. Its DSH-specific output is `.agents/skills`; the generic `--local` Claude files, detected language rules, and other project outputs still apply. It never writes below `DSH_HOME`.

Project `--dry-run` resolves and validates `extends` without persisting `.softspark-toolkit.lock.json`, then plans every generic and DSH-specific project output without changing the project tree. Existing lock bytes and metadata remain unchanged. It also makes no DSH package, profile, state, or authentication change.

`DSH_HOME` selects the DSH root. The default is `~/.dsh`. It must resolve to an absolute, non-symlink managed root. Profile identifiers accept 1 to 64 lowercase letters, digits, periods, underscores, or hyphens.

The lifecycle supports DSH `0.1.1-rc.2`, stable pnpm `>=11.7.0,<12.0.0`, `@softspark/dsh-codex@1.0.0`, and `@softspark/dsh-orchestrator@1.0.1`. The DSH tag declares `pnpm@11.7.0`, while isolated cold-install qualification used Corepack pnpm `11.24.0`. It invokes the plugin manager with bounded argv-array subprocesses:

```text
dsh plugin --profile web add @softspark/dsh-codex@1.0.0 --save-exact
dsh plugin --profile web add @softspark/dsh-orchestrator@1.0.1 --save-exact
```

The orchestrator preset is copied from the installed package:

```text
$DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator
  -> $DSH_HOME/.agent-presets/softspark-orchestrator
```

The lifecycle refuses unowned same-name plugins and presets. An unchanged owned install is idempotent. Update and uninstall require every recorded package-tree entry and the preset tree to match current bytes, types, paths, links, and POSIX modes. Generic `ai-toolkit uninstall` does not mutate DSH profiles or remove their ownership state. Use `ai-toolkit dsh uninstall` explicitly.

The persisted `packages` map is the ownership baseline, not the desired version target. Its key set must contain exactly the two managed package names, each value must be an exact version, and its keys must match the stored package-tree inventories. After a reviewed pin bump, `update` verifies the on-disk manifest and trees against those recorded versions, installs the current reviewed pins, and replaces the state record only after all postconditions pass. `uninstall` verifies and removes the recorded owned package names even when the current reviewed pins are newer. Rollback always restores the exact versions captured before the operation.

A zero exit status from DSH is not sufficient to commit a lifecycle operation. Immediately before and after every plugin add or remove, ai-toolkit rereads the profile manifest and the complete managed package trees under the lifecycle lock. A changed, malformed, unexpected, or newly introduced managed entry stops the next external mutation and preserves the concurrent bytes. The managed packages must have the exact recorded pins or be fully absent for uninstall. Dependency entries outside the two managed package names must remain unchanged. A false-success postcondition leaves ownership state uncommitted.

Each stored package inventory uses a domain-separated SHA-256 over stable, length-prefixed records. A record contains the entry type, relative path, POSIX mode, and type-specific metadata. Regular-file metadata contains the byte length and per-file SHA-256. Symlink metadata contains the target text. Traversal is bounded to 100,000 entries and 128 levels, never follows symlinks, and rejects special files. The state stores hashes and metadata only. It stores no package contents, credentials, authentication paths, or child-process environment.

Rollback gives every package-manager recovery command an explicit target derived from the immutable pre-operation snapshot. The target contains the managed package inventory, the exact target package tree, the unchanged non-target package trees, and the pre-operation unrelated dependencies. A successful child exit is accepted only when all four match. A post-command observation is evidence, never a new target. Target drift or unreadable state blocks every later package-manager recovery call, preserves the current bytes, creates a transaction-unique doctor-visible recovery marker, and prints `ai-toolkit dsh doctor --profile <name>` plus deterministic manual inspection paths. This rule applies to install, update, and uninstall rollback.

Before the first mutation, the lifecycle resolves exact DSH and pnpm command paths from the minimal child `PATH`. It records each command path, resolved path, device, inode, type, mode, size, timestamps, and symlink target when applicable. It runs both version probes with a five-second bound and requires pnpm to parse inside the supported range. Missing, nonzero, timed-out, malformed, or unsupported pnpm probes fail before the lifecycle lock and leave no package, preset, state, or lock artifact.

Profile lifecycle `--dry-run` performs read-only runtime, package-manager, and ownership preflight. It prints the exact planned argv and paths. It does not acquire a lifecycle or state lock, create a directory, write state, or start a package-manager mutation. Mutating install, update, and uninstall operations first acquire a nonblocking exclusive POSIX `flock` on the pinned `DSH_HOME` directory descriptor, then hold `$DSH_HOME/.ai-toolkit-lifecycle.lock` from preflight through mutation, rollback, cleanup, and recovery. The directory lock is independent of that replaceable filename. It remains held while a recovery sentinel is created with `O_EXCL` and while both its file and parent directory are synced; release occurs only after normal canonical-lock release or durable sentinel publication. Every competing lifecycle must acquire the same directory lock before sentinel scans and canonical claim. Lock acquisition pins the exact lexical `DSH_HOME` parent and root directory descriptors and passes that one resolved home through the full operation. The prerequisite record is revalidated after the lock and before every package mutation or rollback. Replacement, removal, in-place identity drift, and a new earlier PATH shadow fail closed. The verified pnpm command directory leads the child PATH. Every internal mutation and each external DSH command verifies that the lexical path still names the pinned device, inode, and directory kind. Preset parents, staging trees, recovery containers, copied children, and recovery markers are opened by walking from that root descriptor with no-follow operations. Creation, copy, cleanup, and recovery use descriptor-relative system calls and retain the parent and child device and inode identities through postcondition checks. A mismatch blocks state success and later package commands, preserves both roots, and reports recovery. The child process receives only the verified canonical path. The canonical lock is claimed as a regular non-symlink with exclusive descriptor-relative creation and waits for at most one second. A write, `fsync`, close, or interruption during lock initialization removes only the captured lock inode. If that cleanup cannot complete, the command reports a doctor-visible lock recovery artifact and the next lifecycle command remains fail-closed. Release uses the pinned root descriptor, atomically relocates the lock without replacement, and deletes it only after its device and inode still match the transaction. A displaced root never redirects lock cleanup into its replacement. `doctor` is read-only and does not acquire the lifecycle lock.

If process-tree termination cannot be confirmed, the lifecycle does not enter package rollback or normal lock release. Before writing recovery metadata it verifies that the canonical lock still names the held device and inode, then creates and syncs a transaction-unique `unconfirmed-process-tree` sentinel in the pinned DSH root. It rewrites the held inode only after a second canonical identity check. A removed or renamed canonical lock therefore leaves the recognized sentinel, while a foreign replacement remains byte-identical. Lock acquisition checks process-tree sentinels before and after claiming the canonical name, and every later install, update, or uninstall fails before DSH invocation. `doctor` prints the recorded process group, original profile path, and every exact gate file. Recovery is deliberately manual: verify that the process group has exited, inspect the preserved profile, and only then remove every named gate. Group signaling is permitted only while the unreaped DSH supervisor still binds the group identifier; after that identity is lost, the command preserves the gate rather than risk signaling a reused PGID. Repeated `SIGINT` is deferred or retried through the bounded TERM, KILL, and wait sequence.

Doctor reports runtime compatibility, pnpm availability and version, installed package versions, complete package-tree ownership, preset ownership and hash drift, state consistency, legacy recovery collisions, transaction-unique recovery containers, preserved staging, and whether recovery is required.

The lifecycle never runs login commands, reads vendor credential stores, accepts provider API keys, or forwards provider and registry secret environment variables. Codex, Claude Code, and GitHub Copilot own login state. GitHub AI credits apply to Copilot Gemini delegation. Direct Google AI Pro or Ultra, Gemini CLI OAuth, Antigravity, and Gemini API-key routes are unsupported. Prerequisite probes have a five-second bound. DSH plugin mutations and package rollback commands have a separate 300-second bound suitable for cold resolution, without promising registry or network latency. Each mutation uses a dedicated POSIX session and process group on Linux, WSL, or macOS. The calling thread blocks `SIGINT` with `pthread_sigmask` before `Popen`, restores its previous mask inside one catchable region covering communication and final PGID checks, and restores the mask in `finally`. Every `BaseException` after spawn triggers complete process-tree teardown before propagation. Timeout and interruption require confirmed group exit before rollback; an unconfirmed exit blocks rollback. POSIX directory `flock`, process groups, and thread signal masks are mandatory mutation primitives. Native Windows mutation is unsupported and fails before lifecycle writes. Failed child-process stdout and stderr are never included in user-facing errors. Errors expose only the safe command outcome, such as exit status, timeout, or interruption. Recovery argv contains only the validated DSH executable, profile, fixed package names, and exact pinned versions.

## State Tracking

Installed module state is persisted to `~/.softspark/ai-toolkit/state.json`:

```json
{
  "installed_version": "1.3.0",
  "installed_modules": ["core", "agents", "skills", "rules-common", "rules-typescript"],
  "installed_at": "2026-04-07T10:00:00Z",
  "last_updated": "2026-04-07T10:00:00Z",
  "file_hashes": {
    "app/hooks/session-start.sh": "abc123..."
  },
  "dsh": {
    "profiles": {
      "web": {
        "dsh_home": "/Users/example/.dsh",
        "profile": "web",
        "packages": {
          "@softspark/dsh-codex": "1.0.0",
          "@softspark/dsh-orchestrator": "1.0.1"
        },
        "package_trees": {
          "@softspark/dsh-codex": {
            "digest": "<canonical-tree-sha256>",
            "entries": [
              {"type": "directory", "path": ".", "mode": 493},
              {"type": "file", "path": "package.json", "mode": 420, "size": 53, "sha256": "<file-sha256>"}
            ]
          },
          "@softspark/dsh-orchestrator": {
            "digest": "<canonical-tree-sha256>",
            "entries": [
              {"type": "directory", "path": ".", "mode": 493}
            ]
          }
        },
        "preset_path": "/Users/example/.dsh/.agent-presets/softspark-orchestrator",
        "preset_hash": "<sha256>",
        "owned": true,
        "installed_at": "2026-08-29T08:00:00Z",
        "last_updated": "2026-08-29T08:00:00Z"
      }
    }
  }
}
```

- `installed_modules` — used by `update` to know which modules to re-apply
- `file_hashes` — used to skip unchanged files during `update`
- `dsh.profiles` records the DSH home, profile, exact package versions, canonical package-tree inventories, preset path and hash, ownership, and timestamps
- The file is written after every successful install or update

Every shared state writer uses the canonical path from `AI_TOOLKIT_HOME`, `SOFTSPARK_HOME`, or the default `~/.softspark/ai-toolkit/state.json` and cooperates through the same bounded `.state.lock`. Where the host provides descriptor-relative atomic primitives, the lock context pins the state parent device and inode. Transaction reads, snapshots, compare-and-swap merges, private temporary creation, writes, `fsync`, publication, mode changes, cleanup, and lock release then address entries relative to that same open parent descriptor. A DSH lifecycle snapshot also records this parent identity and requires the final install, update, uninstall, and rollback state transaction to reopen that exact lexical path and match the same device and inode. The lexical parent binding is checked before publication and release. Replacing the state directory therefore fails without publishing into the replacement or losing either root. Generic install, MCP, and editor state writers retain the portable state contract on every supported Python platform. They use this pinned atomic publisher when available and otherwise publish a private temporary with the platform's atomic replacement primitive while holding the shared lock.

DSH ownership mutation has a stricter platform gate. It requires Linux, WSL, or macOS support for pinned-directory, no-follow, no-replace, and atomic-exchange operations. The lifecycle checks both its DSH filesystem primitives and the state publisher before it creates the state root, state lock, lifecycle lock, temporary, or profile artifact. Secure state lock creation addresses `.state.lock` relative to a pinned no-follow parent descriptor and keeps that descriptor open through release. DSH state publication uses an atomic exchange for an existing file or a no-replace rename for first creation. The writer validates the displaced device, inode, and content digest before cleanup. A mismatched inode is restored or preserved for manual recovery instead of being overwritten or deleted. A bounded retry merges unrelated concurrent state keys. A concurrent change to the same DSH profile is preserved and reported as a recovery conflict.

Records created before package-tree inventories were introduced are intentionally not migrated by assumption. `doctor` reports the invalid ownership state. Reinstall the explicit DSH integration after inspecting or removing the old record. Update and uninstall never claim unknown package bytes as owned.

DSH mutations snapshot the profile manifest, managed package trees, base-directory existence, prior state, and preset before the first external mutation. Interruption and cleanup failure run the same rollback as package failure. Cleanup uses an entry-level inventory of device, inode, kind, digest, and symlink target. Snapshot recreation walks every ancestor without following symlinks, pins the destination parent, and uses descriptor-relative no-clobber creation for files, directories, and symlinks. File and directory modes are restored with `fchmod` only after pinning the exact inode. Post-creation and post-mode checks bind type, inode, mode, digest, and link target to the pinned parent. Unsupported primitives fail before any write, and an inode or ancestor mismatch remains untouched and doctor-visible. Manifest removal, manifest restoration, and transaction-created profile-directory pruning first relocate the candidate without replacement through pinned parent descriptors, then validate the moved inode and content before cleanup. A mismatch remains at its concurrent path or in a reported recovery container. Cleanup never unlinks, replaces, or removes a concurrently substituted file, symlink, or directory. A transaction-created `.agent-presets` parent is removed only when its identity is unchanged and it remains empty.

Update and uninstall revalidate the owned preset identity and content immediately before relocation. The transaction atomically claims a private mode-0700 recovery container with a cryptographically random suffix, then moves the preset to its previously absent `managed-preset` child. It never replaces a caller-provided recovery path. The relocated payload remains bound to the captured device, inode, kind, digest, and symlink target; that same identity is checked immediately and again before every restore or removal. A byte-identical replacement is therefore preserved and reported instead of being treated as transaction-owned. Managed dependency entries must contain exact semantic versions; malformed or non-string values fail before DSH is invoked. A clean-profile rollback removes transaction-created manifest and base directories when they remain unchanged. Existing profile manifests are restored byte-for-byte, and missing pre-existing package entries are recreated without overwriting collisions.

If byte-identical rollback cannot finish, the command returns nonzero and prints every exact safely quoted residual path plus deterministic recovery steps. One failed package recovery command does not authorize the next package command: the loop immediately rechecks the rollback-blocked flag and complete package identity after success or failure, records doctor and inspection actions, and stops package mutation on drift. Independent preset cleanup and state restoration still run, so their failures are aggregated without replacing the original error. Every surviving staging or recovery path remains listed and doctor-visible, so no operation reports success while its owned recovery data survives. Update staging cleanup removes only transaction-owned entries and reports every surviving staging path, including concurrent additions. Package-filesystem and cleanup residuals create transaction-unique `.softspark-orchestrator.ai-toolkit-package.<token>` containers. `ai-toolkit dsh doctor --profile <name>` reports `Recovery needed: yes` until manual recovery is complete.

Real-profile qualification with the published packages and native subscription logins remains pending Phase 3. Static, fixture, and dry-run success is not evidence that this qualification has completed.

## Implementation Files

| File | Purpose |
|------|---------|
| `manifest.json` | Module and profile definitions |
| `scripts/install_steps/detect_language.py` | Auto-detect project language from marker files |
| `scripts/install_steps/install_state.py` | Read/write `~/.softspark/ai-toolkit/state.json` |
| `scripts/install_steps/dsh.py` | Explicit DSH install, update, doctor, uninstall, and recovery lifecycle |

## Backward Compatibility

Existing `--profile` usage works identically. The manifest system does not change what gets installed when you use `--profile minimal/standard/strict`. It only adds:

1. `--modules` for granular selection
2. `--auto-detect` for language rules
3. `state.json` tracking for incremental updates
4. `status` command to inspect installed state

No existing install scripts or CI configurations need changes.

## Related Documentation

- [PATH: kb/reference/language-rules.md] — language rules structure and auto-detection detail
- [PATH: kb/reference/mcp-templates.md] — MCP server templates (the `mcp-templates` module)
- [PATH: kb/reference/architecture-overview.md] — overall install model
- [PATH: kb/reference/dsh-compatibility.md] - DSH commands, topology, authentication, and preview limits
