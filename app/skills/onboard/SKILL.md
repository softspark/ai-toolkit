---
name: onboard
description: "Generate project onboarding materials"
effort: medium
disable-model-invocation: true
argument-hint: "[project-path]"
allowed-tools: Bash, Read, Write, Glob
---

# /onboard - Project Setup Guide

$ARGUMENTS

## What This Command Does

Guide the user through setting up the ai-toolkit in their project, including configuration and customization.

## Setup Steps

### Step 1: Prerequisites Check
- [ ] Claude Code CLI installed
- [ ] ai-toolkit repository cloned
- [ ] Current directory is the target project

### Step 2: Install Toolkit
```bash
# Run the installer from the toolkit directory
/path/to/ai-toolkit/install.sh
```

This creates symlinks in `.claude/`:
- `agents/` -> toolkit agents
- `skills/` -> toolkit skills (slash commands + knowledge skills)
- `hooks.json` -> quality gates
- `constitution.md` -> safety rules

### Step 3: Configure CLAUDE.md
Create a project-specific `CLAUDE.md` from the template:
```bash
cp /path/to/ai-toolkit/CLAUDE.md.template ./CLAUDE.md
```

Customize with:
- Project description and tech stack
- Coding standards specific to this project
- Common development commands
- Architecture notes

### Step 4: Configure Settings
Edit `.claude/settings.local.json` for project-specific settings:
- MCP server connections
- Permission overrides
- Environment variables

### Step 5: Verify Installation
```bash
/path/to/ai-toolkit/validate.sh
```

### Step 6: Quick Start Guide

| Command | Purpose |
|---------|---------|
| `/explore` | Understand the codebase |
| `/plan` | Plan a new feature |
| `/test` | Run tests |
| `/review` | Code review |
| `/commit` | Create a structured commit |



## Usage Examples

```
/onboard              # Full guided setup
/onboard verify       # Just verify existing installation
/onboard update       # Update toolkit symlinks
```
