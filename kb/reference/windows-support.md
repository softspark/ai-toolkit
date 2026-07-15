---
title: "Windows Support"
category: reference
service: ai-toolkit
tags: [windows, wsl, install, uninstall, dependencies, hooks, security]
created: "2026-04-24"
last_updated: "2026-07-15"
description: "Windows support model for ai-toolkit: WSL, Git Bash, dependency detection, hooks, and fail-closed managed mutations."
---

# Windows Support

ai-toolkit supports Windows through two practical modes:

1. **WSL recommended** — best compatibility for Bash hooks, POSIX paths, symlinks, and editor configs.
2. **Native Windows with Git Bash** — supported for CLI usage when Bash is available on `PATH`.

## Dependency Detection

`scripts/check_deps.py` now emits install hints for Windows package managers:

| Manager | Command Prefix |
|---------|----------------|
| winget | `winget install` |
| Chocolatey | `choco install -y` |
| Scoop | `scoop install` |

Required dependency package IDs:

| Dependency | winget | Chocolatey | Scoop |
|------------|--------|------------|-------|
| Python 3 | `Python.Python.3` | `python` | `python` |
| Git | `Git.Git` | `git` | `git` |
| Node.js | `OpenJS.NodeJS` | `nodejs` | `nodejs` |

## Hook Runtime

ai-toolkit hooks are Bash scripts. On Windows, use WSL or Git Bash so Claude Code can execute `~/.softspark/ai-toolkit/hooks/*.sh`.

Cross-platform hooks should keep the Bash entrypoint small and delegate complex work to Python or Node when Windows behavior diverges.

## Managed Mutation Safety

Managed cleanup by `ai-toolkit uninstall`, Copilot profile downgrade cleanup,
external hook injection/removal, and native Codex hook generation require POSIX
`dir_fd` and `O_NOFOLLOW` support.
These primitives are the platform prerequisite for pinning directories between
a trusted configuration root and the file being changed, so a symlink swap
cannot redirect a mutation outside that root. Absolute trusted roots are opened
component by component from a stable filesystem-root descriptor; all target
parsing, mutation, and rollback then use the pinned descriptors.

- **WSL:** managed cleanup is supported.
- **Native Windows Python, including invocation from Git Bash:** managed cleanup
  is unavailable because Windows CPython does not expose the required POSIX
  traversal primitives. Git Bash provides a shell, but it does not add those
  primitives to Python.

On an unsupported runtime, help, dry-run modes where available, component
discovery, validation, cancellation, and other read-only operations remain
available. A requested mutation exits non-zero before its transaction starts
and reports `No files were changed`. Run the command from WSL to remove managed
customizations, inject or remove external hooks, and generate/update native
Codex hooks safely.

## Verification

```bash
ai-toolkit doctor
python3 scripts/check_deps.py
python3 scripts/validate.py
```

The Windows support contract is covered by `tests/test_windows_support.bats`.
