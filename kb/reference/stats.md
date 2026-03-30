---
title: "AI Toolkit - Usage Statistics"
category: reference
service: ai-toolkit
tags: [stats, usage, tracking, analytics]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-03-29"
description: "Local usage tracking for skill invocations. CLI command, JSON format, hook mechanism."
---

# Usage Statistics

## Overview

`ai-toolkit stats` tracks how often each skill is invoked via slash commands. All data is local — stored in `~/.ai-toolkit/stats.json`. No telemetry, no network calls.

## CLI Commands

```bash
ai-toolkit stats           # Show usage table (sorted by count)
ai-toolkit stats --reset   # Clear all stats
ai-toolkit stats --json    # Output raw JSON
```

## How It Works

A `UserPromptSubmit` hook (`track-usage.sh`) fires on every prompt. When the prompt starts with `/skill-name`, it increments the counter in `stats.json`.

### Hook Details
- **Event**: `UserPromptSubmit`
- **Script**: `~/.ai-toolkit/hooks/track-usage.sh`
- **Detection**: `grep -oE '^/[a-z][a-z0-9-]*'`
- **Storage**: Atomic write via python3 `os.replace()`
- **Overhead**: ~50ms (python3 startup + JSON read/write)

## JSON Format

```json
{
  "commit": {
    "count": 42,
    "last_used": "2026-03-29 14:30:00"
  },
  "review": {
    "count": 15,
    "last_used": "2026-03-28 09:12:00"
  }
}
```

## Output Example

```
AI Toolkit Usage Stats
========================

Skill                           Count  Last Used
------------------------------------------------------------
commit                             42  2026-03-29 14:30:00
review                             15  2026-03-28 09:12:00
debug                               8  2026-03-27 16:45:00

Total invocations: 65
Unique skills: 3

File: ~/.ai-toolkit/stats.json
Reset: ai-toolkit stats --reset
```
