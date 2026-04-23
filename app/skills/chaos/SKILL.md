---
name: chaos
description: "Inject controlled faults for resilience testing on non-production targets. Use when the user explicitly asks for a chaos experiment, latency injection, or dependency kill — never implicit."
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

## Rules

- **MUST** verify target environment is non-production before injecting
- **NEVER** run against a system without a healthy baseline
- **CRITICAL**: abort immediately if recovery does not complete within the observation window
- **MANDATORY**: log every injected fault with timestamp and scope

## Gotchas

- `NODE_ENV=production` on a developer's machine is common — checking that env var alone is not enough proof of non-prod. Combine with kubeconfig context, cloud account ID, or a project-specific env file check before injecting.
- `docker stats` reports cached values; the first sample immediately after injection is often pre-fault. Wait at least 5 seconds before reading metrics.
- Kubernetes liveness probes may self-heal the faulted pod inside the 60s observation window — the report shows green while the workload is still flapping. Check pod restart counters, not just health endpoints.
- Latency injected with `tc` (Linux traffic control) persists across container restarts on the host and across SIGTERM. Always pair the inject step with an explicit `tc qdisc del dev <iface> root` cleanup in the recover step — the `fork` context will not undo it for you.

## When NOT to Use

- In production without an explicit, written runbook — use `/workflow incident-response` for real incidents
- When the system has no observability (no metrics, no logs) — fix observability first
- For load testing — use dedicated load-test tooling, not chaos injection
- During an active incident — stabilize first with `/panic`, then investigate
