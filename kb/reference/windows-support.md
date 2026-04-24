---
title: "Windows Support"
category: reference
service: ai-toolkit
tags: [windows, wsl, install, dependencies, hooks]
created: "2026-04-24"
last_updated: "2026-04-24"
description: "Windows support model for ai-toolkit: WSL, Git Bash, dependency detection, and hook runtime constraints."
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

## Verification

```bash
ai-toolkit doctor
python3 scripts/check_deps.py
python3 scripts/validate.py
```

The Windows support contract is covered by `tests/test_windows_support.bats`.
