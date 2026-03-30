---
name: predict
description: "Predict regressions and impact before changes land"
effort: medium
disable-model-invocation: true
argument-hint: "[change description]"
agent: predictive-analyst
context: fork
allowed-tools: Read, Grep, Glob
---

# Predict Command

$ARGUMENTS

Triggers the Predictive Analyst to assess impact.

## Usage

```bash
/predict [path_or_diff]
# Example: /predict src/auth
# Example: /predict --diff (analyzes uncommitted changes)
```

## Protocol
1. **Scope**: Identify target files.
2. **Trace**: Build dependency graph.
3. **Assess**: Calculate risk score.
4. **Report**: Generate Impact Prediction.
