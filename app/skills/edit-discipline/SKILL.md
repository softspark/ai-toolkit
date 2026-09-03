---
name: edit-discipline
description: "Change files with the edit and write tools, never by rewriting them through bash (sed, awk, tee, heredoc, redirection), and show `git diff` before reporting a file-changing task as done. Triggers: edit, write, modify, refactor, patch, fix, diff, review changes."
effort: low
user-invocable: false
allowed-tools: Read
---

# Edit Discipline

This rule comes from `app/rules/edit-discipline.md` in ai-toolkit. It applies to
every task in this workspace, not only when it is loaded.

# Edit Discipline & Reviewable Changes

## Edit files with the editing tools, not the shell

Use the `edit` and `write` tools to change a file. Do not rewrite tracked files
through `bash` with `sed`, `awk`, `tee`, a heredoc, or `>` redirection.

This is not a style preference. A shell rewrite is opaque to the host: the
session records a command, not a change. An `edit` call records which file
changed and how, so the interface can render it, a reviewer can read it, and a
later turn can cite it. A `sed` line records none of that, and the only way to
find out what happened is to read the file again.

The shell remains correct for what it is for: running builds, tests, linters,
git, package managers, and generators that own their own output.

## Show the change before calling the work done

Before reporting a file-changing task as finished, show what changed:

```bash
git diff -- <paths>          # tracked files
git status --short           # what is new or removed
```

Paste the diff into the reply, or state precisely why it is too large and
summarise it by file with the counts. A task that reports success without
showing the change asks the reader to take the result on trust, and the reader
is the one who has to decide whether to commit it.

For an untracked file, show the content you wrote, not a description of it.

## Why both halves matter together

Editing through the tools makes a change *recordable*; showing the diff makes it
*reviewed*. Either alone leaves the person deciding whether to ship blind to
something they are accountable for.
