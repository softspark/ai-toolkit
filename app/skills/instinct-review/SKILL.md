---
name: instinct-review
description: "Review and manage learned instincts from past sessions"
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
