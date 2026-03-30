---
name: chaos
description: "Inject controlled faults for resilience testing"
effort: medium
disable-model-invocation: true
argument-hint: "[target]"
context: fork
agent: chaos-monkey
allowed-tools: Bash, Read
---

# Chaos Command

$ARGUMENTS

Triggers a controlled resilience experiment.

## Usage

```bash
/chaos <experiment> [target]
# Example: /chaos latency backend-api
# Example: /chaos kill redis
```

## Protocol
1. **Safety Check**: Verify env != PROD.
2. **Baseline**: Check system health is green.
3. **Inject**: Run the fault injection.
4. **Observe**: Monitor logs/metrics for 60s.
5. **Recover**: Restore system health.
6. **Report**: Did we survive?
