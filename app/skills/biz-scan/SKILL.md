---
name: biz-scan
description: "Scan codebase for business opportunities and KPIs"
effort: medium
disable-model-invocation: true
argument-hint: "[area]"
agent: business-intelligence
context: fork
allowed-tools: Read, Grep, Glob
---

# Biz Scan Command

$ARGUMENTS

Triggers the Business Intelligence agent to find opportunities.

## Usage

```bash
/biz-scan [scope]
# Example: /biz-scan schema
# Example: /biz-scan all
```

## Protocol
1. **Model Scan**: Read DB schema / Entities.
2. **Logic Scan**: Read Controllers / UseCases.
3. **Synthesis**: Match Data vs Business Goals.
4. **Report**: Generate Opportunity Report.
