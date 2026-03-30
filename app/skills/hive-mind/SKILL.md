---
name: hive-mind
description: "Loaded when orchestrating multi-agent swarms or consensus workflows"
effort: medium
user-invocable: false
---

# Hive Mind Skill

You are part of a Swarm. You are not alone.

## 🔴 Swarm Protocols

### 1. Consensus (The Vote)
When agents disagree:
1. Each agent generates a solution + confidence score.
2. **Weighted Voting**: Higher confidence = Higher weight.
3. **Majority Rule**: >50% wins.

### 2. Aggregation (The Merge)
When multiple agents produce outputs:
1. **Format Standardization**: Ensure all JSON/Markdown matches.
2. **De-duplication**: Remove identical findings.
3. **Synthesis**: Combine unique insights into one report.

### 3. File Ownership (Agent Teams Mode)

**With Agent Teams enabled**: File conflicts are prevented by **file ownership assignment** at spawn time. Each teammate gets distinct files/directories. No locking needed.

- Lead assigns ownership when creating the team
- Teammates respect boundaries in their prompts
- Quality hooks verify completeness on `TaskCompleted`

**Without Agent Teams** (fallback):
1. Before editing a file: Check if another agent is editing.
2. Use `touch .lock.{filename}`.
3. Remove lock after edit.

### 4. Communication (Agent Teams Mode)

- **message**: Send to ONE specific teammate (targeted, low cost)
- **broadcast**: Send to ALL teammates (use sparingly — costs N×)
- **Shared task list**: `~/.claude/tasks/{team-name}/` — all agents can see/claim

## Example Workflow (Map-Reduce)

### With Agent Teams
1. **Map**: Lead spawns 5 teammates, each scanning 20 files
2. **Parallel**: All teammates execute simultaneously in tmux panes
3. **Reduce**: Lead waits, collects results, applies Aggregation protocol
4. **Report**: `final_report.md` synthesized from all findings

### Without Agent Teams (Fallback)
1. **Map**: "Scan 100 files for leaks." → 10 Agents × 10 Files.
2. **Reduce**: Agents output `leaks_{i}.json`.
3. **Hive Mind**: Merge all `leaks_*.json` → `final_report.json`.
