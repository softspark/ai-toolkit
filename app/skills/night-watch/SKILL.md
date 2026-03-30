---
name: night-watch
description: "Run autonomous maintenance and dependency updates"
effort: medium
disable-model-invocation: true
context: fork
agent: night-watchman
allowed-tools: Bash, Read, Edit, Grep
---

# Night Watch Command

Triggers the autonomous maintenance agent.

## Usage

```bash
/night-watch [scope]
# Example: /night-watch deps
# Example: /night-watch cleanup
# Default: runs full suite
```

## Protocol
1. **Checkout**: Create `maintenance/` branch.
2. **Execute**: Run `night-watchman` agent skills.
3. **Verify**: Run full test suite.
4. **Report**: Generate Shift Report.
