---
name: instinct-review
description: "Review, promote, or remove learned instincts extracted from past sessions (`.claude/instincts/*.md`). Use when the user wants to curate the instinct list — not to extract new instincts or edit memory."
effort: low
user-invocable: true
argument-hint: "[--list | --promote <id> | --remove <id> | --clear]"
allowed-tools: Bash, Read, Write, Glob
---

# /instinct-review - Manage Learned Instincts

$ARGUMENTS

## What This Does

Manages the instinct system that learns patterns from your sessions.

Instincts are stored in `.claude/instincts/` and loaded at session start.

## Commands

### List all instincts
```
/instinct-review --list
```
Shows all instincts with confidence scores and source sessions.

### Review and curate
```
/instinct-review
```
Interactive review: shows each instinct and asks promote/remove/keep.

### Promote instinct (always apply)
```
/instinct-review --promote <filename>
```

### Remove instinct
```
/instinct-review --remove <filename>
```

### Clear all instincts
```
/instinct-review --clear
```

## How Instincts Work

1. **Extraction**: At session end, the Stop hook extracts patterns from the session
2. **Storage**: Saved as `.claude/instincts/<pattern-name>.md` with confidence score
3. **Loading**: At session start, instincts are loaded and shown to Claude
4. **Curation**: Use `/instinct-review` to promote good ones and remove bad ones

## Instinct Format

```markdown
# Pattern: [pattern name]
Confidence: 0.85
Sessions: 3
Last seen: 2026-03-25

[Description of the pattern or preference]
```

## Steps

1. Run `ls .claude/instincts/ 2>/dev/null || echo "No instincts yet"`
2. For each instinct file, read it and display confidence/summary
3. Based on `$ARGUMENTS`:
   - `--list`: display table of all instincts
   - `--promote <id>`: set confidence to 1.0, add "pinned" tag
   - `--remove <id>`: delete the file
   - `--clear`: delete all files in `.claude/instincts/`
   - no args: interactive review of each instinct
4. Report summary of changes made

## Rules

- **MUST** list instincts with their source (session ID or date) so the user can judge provenance — anonymous instincts cannot be curated
- **MUST** confirm before `--clear` — this action is irreversible without a backup
- **NEVER** invent or edit instinct content — this skill curates existing files, it does not generate new ones
- **NEVER** promote an instinct with confidence < 0.7 without explicit user approval — low-confidence patterns are often one-off noise
- **CRITICAL**: the user owns the instinct list. Propose changes in interactive mode; apply silently only for explicit `--promote`, `--remove`, `--clear` flags.
- **MANDATORY**: after any destructive operation, print the deleted or modified filenames so the user has an audit trail

## Gotchas

- Instincts live in **project-local** `.claude/instincts/`, not in `~/.softspark/ai-toolkit/`. Running this skill in a different project sees a different set — do not treat the list as global state.
- The Stop hook that extracts instincts may write draft files even when no meaningful pattern was observed. A `.claude/instincts/` with 40 files is usually 35 noise + 5 signal — curate ruthlessly.
- Promoted instincts (confidence = 1.0) load into every session's context, costing tokens. Too many pinned instincts bloat startup. Keep ≤10 pinned.
- Instinct files are plain markdown but the extraction format may evolve between ai-toolkit versions. A `--clear` after a version bump is often cleaner than trying to migrate old formats.
- The filename (`<pattern-name>.md`) is the identity used by `--promote` and `--remove`. Renaming files manually breaks those flags until the user reopens the review UI.

## When NOT to Use

- To **extract** new instincts — extraction is automatic via the Stop hook
- To search past session memory — use `/mem-search`
- To edit global toolkit memory files — those live in `~/.claude/projects/*/memory/` and are managed by the auto-memory system, not this skill
- To permanently disable the instinct system — edit `settings.json` to remove the Stop hook; `--clear` only wipes current state, extraction continues on the next session
