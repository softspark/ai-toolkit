---
title: "Plan: Cloud Security Pack — Multi-Cloud Audit (GCP/AWS/Azure)"
category: planning
service: ai-toolkit
tags:
  - cloud-security
  - gcp
  - aws
  - azure
  - firebase
  - plugin-pack
  - security-audit
  - credentials
doc_type: plan
status: proposed
created: "2026-04-10"
last_updated: "2026-04-10"
completion: "0%"
council_review: "2026-04-10 — conditional FOR, scope reduction recommended"
description: "Plugin pack for deterministic, read-only security auditing of GCP (Firebase/Cloud Functions), AWS (S3/Lambda/IAM), and Azure (NSG/Functions/CosmosDB). Includes CLI credential management, static+live modes, false positive resolution, SARIF output, incremental scanning, and CI integration."
---

# Plan: Cloud Security Pack — Multi-Cloud Audit

**Status:** Proposed
**Completion:** 0%
**Created:** 2026-04-10
**Origin:** Firebase RTDB/Firestore rules audit, Cloud Functions public exposure, false positive resolution for App Check/Gateway patterns
**Estimated Effort:** 5-6 weeks (council-revised from original 3-4 weeks)

---

## 1. Objective

Create `cloud-security-pack` plugin pack that provides deterministic, read-only security auditing for three major cloud providers. All scripts are stdlib-only Python with zero external dependencies. The pack includes a dedicated agent, multiple scan scripts, CLI credential management, and CI pipeline integration.

**Key design principles:**
- **Read-only** — never modifies cloud resources, only reads state
- **Deterministic** — reproducible results, no LLM-driven regex (same pattern as `hipaa_scan.py`)
- **False positive aware** — context graph resolves "public endpoint behind gateway/App Check/WAF"
- **CI-ready** — `--output json` + `--output sarif` (SARIF v2.1.0 for GitHub Advanced Security), exit code 1 on HIGH, 0 otherwise
- **Credential isolation** — keys stored in `~/.ai-toolkit/credentials/`, accessible only by this pack's scripts
- **Static-first** — static mode (no credentials) is the default, live mode is opt-in upgrade
- **Incremental** — `--changed` flag scans only files modified since last commit (PR workflow)
- **IaC via `terraform show -json`** — wraps Terraform's own JSON output instead of parsing HCL directly

---

## 2. Architecture Overview

```
ai-toolkit credentials add gcp --file ~/sa-viewer.json
ai-toolkit credentials add aws --profile my-audit-profile
ai-toolkit credentials add azure --subscription abc-123

  ┌──────────────────────────────────────────────────────┐
  │              cloud-security-pack                      │
  │                                                      │
  │  Agent: cloud-security-auditor                       │
  │  Tools: Read, Grep, Glob, Bash (read-only commands)  │
  │                                                      │
  │  Skills:                                             │
  │    /cloud-security-audit          (orchestrator)     │
  │    /firebase-rules-audit          (GCP: rules)       │
  │    /cloud-functions-audit         (GCP: CF + IAM)    │
  │    /aws-security-audit            (AWS: S3/Lambda)   │
  │    /azure-security-audit          (Azure: NSG/Fn)    │
  │                                                      │
  │  Scripts (stdlib Python, zero deps):                 │
  │    gcp_auth.py                    (credential helper)│
  │    firebase_rules_scan.py         (static parser)    │
  │    cloud_functions_audit.py       (CF IAM + context) │
  │    aws_security_scan.py           (S3/Lambda/IAM)    │
  │    azure_security_scan.py         (NSG/Fn/RBAC)      │
  │    false_positive_resolver.py     (context graph)    │
  │    sarif_formatter.py             (SARIF v2.1.0)     │
  │    incremental.py                 (git diff filter)  │
  │                                                      │
  │  Modes:                                              │
  │    --static    (no credentials, parse IaC/source)    │
  │    --live      (credentials, deployed state)         │
  │    --output json|sarif  (CI pipeline)                │
  │    --changed <ref>  (incremental, static only)       │
  │    --explain <id>   (remediation lookup)             │
  └──────────────────────────────────────────────────────┘

### YAML Parsing Constraint (BLOCKER)

Python stdlib has NO YAML parser. This affects AWS static mode:
- CloudFormation templates (`.yaml`) — YAML
- `serverless.yml` — YAML
- SAM templates (`template.yaml`) — YAML

**Decision: JSON-only for static IaC parsing.** Rationale:
1. CloudFormation supports both JSON and YAML — JSON variant parseable with `json` module
2. `terraform show -json` outputs JSON — the primary Terraform path
3. `serverless.yml` → recommend users run `sls print --format json` to convert
4. Adding `pyyaml` breaks the stdlib-only constraint for the entire toolkit

**Practical impact:** ~30% of CloudFormation users use JSON, ~70% YAML. For YAML users, live mode (`--mode live`) still works (queries APIs directly, no file parsing needed). The `--explain` output will suggest `sls print --format json` conversion.

**v2 option:** Ship a vendored minimal YAML subset parser (~150 LOC, handles flat key-value and simple nested maps — enough for security-relevant fields like `Principal`, `Effect`, `authLevel`).
```

---

## 3. Progress Tracking

| # | Feature | Priority | Status | Est. Time | Notes |
|---|---------|----------|--------|-----------|-------|
| 1.1 | CLI `credentials` command (add/list/remove/test) | P0 | Proposed | 2d | 0600 perms, allowlist wrapper |
| 1.1b | `credentials init` interactive wizard | P1 | Proposed | 1.5d | **Deferred to Milestone 2** (orchestration-review: saves 1.5d in M1 critical path) |
| 1.2 | `cloud-security-auditor` agent | P0 | Proposed | 1d | Agent definition |
| 1.3 | SARIF + incremental scan infrastructure | P0 | Proposed | 2d | `--output sarif`, `--changed` flag |
| 2.1 | `firebase-rules-audit` skill + script | P0 | Proposed | 4-5d | Recursive descent parser (orchestration-review: +1d vs regex) |
| 2.2 | `cloud-functions-audit` skill + script | P0 | Proposed | 3-4d | CF IAM + App Check context |
| 2.3 | False positive resolver (GCP context) | P0 | Proposed | 3-4d | Context graph engine — GCP only (~8 code paths). **+2d per provider** in later milestones (orchestration-review) |
| 3.1 | `aws-security-audit` skill + script | P1 | Proposed | 4-5d | S3/Lambda/IAM/SG, `terraform show -json` |
| 3.2 | `/cloud-security-audit` orchestrator + plugin.json | P1 | Proposed | 3d | Multi-provider orchestration + pack |
| 4.1 | `azure-security-audit` skill + script | P1 | Proposed | 4-5d | NSG/Functions/RBAC |
| 5.1 | Tests + CI integration docs | P1 | Proposed | 3d | Tests + SARIF + pipeline examples |
| 5.2 | Documentation (kb/) | P2 | Proposed | 1d | Checklists, patterns, KB |

**Phasing (full delivery, all 3 providers):**
- **Phase 1 (week 1-2):** Foundation + GCP — credentials CLI, agent, SARIF/incremental infra, firebase-rules, cloud-functions, false positive resolver (GCP context)
- **Phase 2 (week 3-4):** AWS + orchestrator — AWS security audit, `terraform show -json`, orchestrator skill, plugin pack, `credentials init`
- **Phase 3 (week 5-6):** Azure + polish — Azure security audit, false positive resolver (Azure context), full test suite, documentation

---

## 4. Dependency Graph

```
                         Phase 1: Foundation + GCP (week 1-2)
                         ====================================
credentials CLI (1.1) ─────┐
                            ├──► firebase-rules-audit (2.1)
SARIF + incremental (1.3) ──┤
                            ├──► cloud-functions-audit (2.2) ──► false-positive-resolver (2.3)
agent definition (1.2) ─────┘

                         Phase 2: AWS + Orchestrator (week 3-4)
                         ======================================
credentials init (1.1b) ───┐
                            ├──► aws-security-audit (3.1) ─────► false-positive-resolver (+AWS context)
                            └──► orchestrator skill + plugin.json (3.2)

                         Phase 3: Azure + Polish (week 5-6)
                         ==================================
                            ├──► azure-security-audit (4.1) ───► false-positive-resolver (+Azure context)
                            └──► tests + docs (5.1, 5.2)
```

**All 3 providers ship.** No conditional gates — full delivery in 6 weeks.

---

## 5. Detailed Implementation

### Faza 1: Foundation (tydzien 1)

#### 1.1 CLI `credentials` Command

**Purpose:** Secure credential storage for cloud provider API access. Credentials live outside any project directory and are only accessible by this pack's scripts.

**CLI interface:**
```bash
# GCP — Service Account JSON
ai-toolkit credentials add gcp --file ~/sa-viewer.json
ai-toolkit credentials add gcp --file ~/sa-viewer.json --project my-project-id

# GCP — use existing gcloud session (no file needed)
ai-toolkit credentials add gcp --gcloud --project my-project-id

# AWS — named profile (reads from ~/.aws/credentials)
ai-toolkit credentials add aws --profile audit-readonly
ai-toolkit credentials add aws --profile audit-readonly --region eu-west-1

# AWS — explicit keys (interactive, never on CLI args)
ai-toolkit credentials add aws --interactive

# Azure — subscription
ai-toolkit credentials add azure --subscription abc-123-def

# Azure — use existing az login session
ai-toolkit credentials add azure --az-cli

# Interactive guided setup (reduces onboarding from 4 steps to 1)
ai-toolkit credentials init           # auto-detect provider, interactive wizard
ai-toolkit credentials init --provider gcp  # skip auto-detect, go straight to GCP setup

# Management
ai-toolkit credentials list
ai-toolkit credentials remove gcp
ai-toolkit credentials remove aws
ai-toolkit credentials remove azure
ai-toolkit credentials test gcp       # verify read-only access works
ai-toolkit credentials test aws
```

**Storage structure:**
```
~/.ai-toolkit/
  credentials/
    gcp.json              # SA key file (copied, chmod 0600)
    gcp.meta.json         # { project_id, added_at, method: "file"|"gcloud" }
    aws.json              # { profile, region, method: "profile"|"keys" }
    azure.json            # { subscription_id, method: "subscription"|"az-cli" }
```

**`credentials init` interactive flow:**
1. Auto-detect providers from project files (`firebase.json` → GCP, `*.tf` with `provider "aws"` → AWS, etc.)
2. If multiple detected → ask user: "Found GCP and AWS markers. Which provider to configure first? [gcp/aws/both]"
3. Per provider:
   - GCP: "Do you have a Service Account JSON file? [y/n]" → if yes: ask path → if no: "Run `gcloud auth application-default login` and we'll use that"
   - AWS: "Do you have a named profile in ~/.aws/credentials? [y/n]" → if yes: ask profile name → if no: "Run `aws configure` first"
   - Azure: "Do you have an active `az login` session? [y/n]" → if yes: ask subscription ID → if no: "Run `az login` first"
4. Run `credentials test` automatically after setup
5. Generate `.cloud-security.json` scaffold with detected context

**Security requirements:**
- All credential files: `chmod 0600` (owner read/write only)
- Never log credential contents to stdout/stderr
- `credentials test` validates:
  - Connection works (GCP: `gcloud auth list`, AWS: `aws sts get-caller-identity`, Azure: `az account show`)
  - SA/role has **only read permissions** — **REFUSE to store** if write access detected (orchestration-review: warn-only is ignored by users). Override: `--force` flag with explicit acknowledgment
  - Project/subscription exists
- `.gitignore`-proof — lives in `~/.ai-toolkit/`, never in project directory
- Scripts access credentials via `gcp_auth.py` helper — single entry point, no direct file reads

**Files to create/modify:**

| File | Action | Description |
|------|--------|-------------|
| `scripts/credentials_cli.py` | CREATE | CLI: add/list/remove/test credentials |
| `bin/ai-toolkit.js` | EDIT | Register `credentials` subcommand |
| `tests/test_credentials.bats` | CREATE | Tests: add, remove, permissions, test |

**Success Criteria:**
- [ ] `credentials add gcp --file` copies and secures SA key
- [ ] `credentials add aws --profile` stores profile reference
- [ ] `credentials add azure --subscription` stores subscription
- [ ] `credentials test` validates read access + warns on write perms
- [ ] `credentials list` shows providers without exposing secrets
- [ ] `credentials remove` cleans up securely
- [ ] All files created with 0600 permissions
- [ ] Tests: >= 8

---

#### 1.3 SARIF Output + Incremental Scanning (Council addition)

**SARIF v2.1.0 output** — industry standard consumed by GitHub Advanced Security (inline PR annotations), VS Code SARIF Viewer, Azure DevOps, and SonarQube.

```bash
/cloud-security-audit --output sarif > results.sarif

# GitHub Actions: upload SARIF for inline PR annotations
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

**SARIF structure (per finding):**
```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": { "driver": {
      "name": "cloud-security-audit", "version": "1.0.0",
      "rules": [{ "id": "GCP-CF-001", "shortDescription": { "text": "Public Cloud Function invoker" }, "helpUri": "https://cloud.google.com/functions/docs/securing" }]
    } },
    "results": [{
      "ruleId": "GCP-CF-001",
      "level": "error",
      "message": { "text": "Cloud Function 'adminEndpoint' has allUsers invoker with no protection layer" },
      "locations": [{ "physicalLocation": { "artifactLocation": { "uri": "functions/src/admin.ts" }, "region": { "startLine": 42 } } }],
      "properties": { "resolved_severity": "HIGH", "context_chain": [], "provider": "gcp" }
    }]
  }]
}
```

**Incremental scan mode** — scan only changed files since last commit:

```bash
/cloud-security-audit --changed              # files changed vs HEAD~1
/cloud-security-audit --changed HEAD~5       # files changed in last 5 commits
/cloud-security-audit --changed main         # files changed vs main branch (PR workflow)
```

Implementation: use `git diff --name-only <ref>` to get changed files, filter to relevant extensions (.rules, .tf, .json, .ts, .py, .bicep), scan only those. Falls back to full scan if no git repo detected.

**`--changed` applies to static mode ONLY.** Live mode always scans all deployed resources (it queries cloud APIs, not files). If user passes `--changed` with `--mode live`, emit warning: "Incremental scan applies to static analysis only. Live mode will scan all resources." and proceed with full live scan.

**`--explain` flag** — detailed remediation for a specific finding:

```bash
/cloud-security-audit --explain GCP-CF-001
# Output: what the finding means, why it matters, exact fix steps,
# links to GCP documentation, CIS Benchmark reference
```

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/cloud-security-audit/scripts/sarif_formatter.py` | CREATE | SARIF v2.1.0 output |
| `app/skills/cloud-security-audit/scripts/incremental.py` | CREATE | Git diff + file filter |
| `app/skills/cloud-security-audit/reference/rule-explanations.json` | CREATE | Per-rule remediation guides |

**Success Criteria:**
- [ ] `--output sarif` produces valid SARIF v2.1.0 JSON with `driver.rules[]` array (orchestration-review: GitHub silently drops annotations without rule metadata)
- [ ] SARIF upload to GitHub Advanced Security works (inline PR annotations)
- [ ] SARIF `level` mapping: HIGH→`error`, WARN→`warning`, INFO→`note`
- [ ] `--changed main` scans only PR-changed files
- [ ] `--explain <rule-id>` shows detailed remediation
- [ ] Tests: >= 6

---

#### 1.2 Agent Definition: `cloud-security-auditor`

**File:** `app/agents/cloud-security-auditor.md`

```markdown
---
name: cloud-security-auditor
description: "Multi-cloud security auditor (GCP/AWS/Azure). Read-only deterministic scans
  for IAM, network, storage, serverless, and compliance. False positive resolution
  via security context graph."
model: opus
color: red
tools: Read, Grep, Glob, Bash
skills: security-patterns, cloud-security-audit
---

# Cloud Security Auditor Agent

You are the **Cloud Security Auditor**. You perform read-only security assessments
across GCP, AWS, and Azure. You never modify cloud resources.

## Core Philosophy
**"Read everything, change nothing. Context before verdict."**

## Mandatory Protocol
Before any audit:
1. Check credentials: `ai-toolkit credentials test <provider>`
2. Determine mode: `--static` (IaC/source only) or `--live` (deployed state)
3. Run deterministic scripts first, then interpret results

## Responsibilities

### 1. Static Analysis (no credentials needed)
- Parse IaC: Terraform (.tf), CloudFormation (.yaml/.json), Bicep (.bicep)
- Parse Firebase rules: firestore.rules, database.rules.json
- Parse source: Cloud Functions (onCall vs onRequest), Lambda handlers, Azure Functions
- Parse configs: firebase.json, serverless.yml, sam-template.yaml

### 2. Live Analysis (credentials required, READ-ONLY)
- GCP: `gcloud` CLI commands (list, describe, get-iam-policy)
- AWS: `aws` CLI commands (s3api, lambda, iam, ec2 — get/list/describe only)
- Azure: `az` CLI commands (network nsg, functionapp, cosmosdb — list/show only)

### 3. False Positive Resolution
Build security context graph before rendering verdict:
- Public endpoint → check: API Gateway? WAF? App Check? CDN?
- Open port → check: behind Load Balancer? VPN? private subnet?
- Broad IAM role → check: scoped to specific resource? temporary?

## Allowed CLI Commands (WHITELIST — read-only only)

### GCP
- gcloud functions list / describe / get-iam-policy
- gcloud projects get-iam-policy
- gcloud app-check services list
- gcloud firestore indexes list
- gcloud compute firewall-rules list
- gcloud run services list / describe
- firebase apps:list

### AWS
- aws s3api get-bucket-policy / get-bucket-acl / get-public-access-block
- aws lambda get-policy / get-function-configuration / list-functions
- aws iam list-roles / list-policies / get-role / get-policy-version
- aws ec2 describe-security-groups / describe-network-acls
- aws apigateway get-rest-apis / get-resources
- aws elbv2 describe-load-balancers / describe-listeners

### Azure
- az network nsg list / show / rule list
- az functionapp list / show / config show
- az cosmosdb list / show / keys list
- az role assignment list
- az webapp show / config show
- az network application-gateway list

### NEVER ALLOWED
- Any create/update/delete/put/set/deploy/push command
- Any command that modifies state
- `gcloud auth activate-service-account` (credential pivot)
- `aws sts assume-role` (lateral movement)
- `az login` (session hijack)
- `terraform apply` / `terraform destroy`

## Output Format
(see skill SKILL.md for detailed format)
```

**SECURITY: Programmatic Bash Allowlist (orchestration-review P0 BLOCKER)**

The read-only whitelist above lives in the agent's system prompt. An LLM can be prompt-injected via malicious IaC files or source code comments. **The prompt-only approach is insufficient.**

**Required:** A shell wrapper script (`scripts/cloud_security_allowlist.sh`) that validates every CLI invocation against a compiled allowlist regex BEFORE execution, independent of the LLM:

```bash
#!/bin/bash
# cloud_security_allowlist.sh — wraps Bash calls from cloud-security-auditor
# Rejects any command not matching read-only patterns

ALLOWED_PATTERNS=(
  '^gcloud (functions|projects|app-check|firestore|compute|run) (list|describe|get-iam-policy|indexes)'
  '^gcloud auth list$'
  '^firebase apps:list'
  '^aws (s3api|lambda|iam|ec2|apigateway|elbv2|sts|cloudfront) (get-|list-|describe-|generate-credential-report)'
  '^aws sts get-caller-identity$'
  '^az (network|functionapp|cosmosdb|role|webapp|storage) (list|show|rule list|config show|assignment list|account show)'
  '^az account show$'
  '^terraform show -json'
  '^git diff --name-only'
  '^python3 .*/scripts/.*\.(py)$'
)

CMD="$*"
for pattern in "${ALLOWED_PATTERNS[@]}"; do
  if [[ "$CMD" =~ $pattern ]]; then
    exec $CMD
  fi
done

echo "BLOCKED: Command not in read-only allowlist: $CMD" >&2
exit 1
```

The agent's `allowed-tools` in SKILL.md references this wrapper instead of raw Bash. All cloud CLI calls go through the allowlist.

**`terraform plan` risk (orchestration-review):** `terraform plan -json` executes providers and provisioners. A malicious `.tf` file with `local-exec` provisioner runs arbitrary code during plan. **Decision: use `terraform show -json` ONLY (reads existing state), NOT `terraform plan -json`.** Document this prominently.

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/cloud-security-audit/scripts/cloud_security_allowlist.sh` | CREATE | Bash allowlist wrapper |

**Success Criteria:**
- [ ] Agent file created in `app/agents/`
- [ ] Read-only command whitelist documented
- [ ] NEVER ALLOWED section explicit
- [ ] Programmatic Bash allowlist enforced (not just prompt)
- [ ] `terraform plan` excluded — only `terraform show -json` allowed
- [ ] Allowlist tested: blocked commands return exit 1

---

### Faza 2: GCP / Firebase (Phase 1, tydzien 1-2)

#### 2.1 Skill: `firebase-rules-audit`

**Purpose:** Static analysis of Firestore rules and RTDB rules. No credentials needed.

**What it scans:**

| Check | Severity | Description |
|-------|----------|-------------|
| `allow read, write: if true` | HIGH | World-readable/writable collection |
| `allow read: if true` without `write` guard | WARN | Public read — may be intentional |
| `allow write: if request.auth != null` without field validation | WARN | Authenticated but no field-level validation |
| Missing `request.resource.data` validation on writes | WARN | No schema enforcement |
| Wildcard collection `/{document=**}` with broad permissions | HIGH | Recursive wildcard + open access |
| RTDB `.read: true` or `.write: true` at root | HIGH | Entire database public |
| RTDB `.read: "auth != null"` without path scoping | WARN | All authenticated users can read everything |
| Timestamp/TTL rules missing for sensitive collections | WARN | No data lifecycle enforcement |
| `get()` / `exists()` cross-collection reads without auth check | WARN | Privilege escalation via rule chaining |
| Rules file > 256KB (approaching Firebase limit) | WARN | May hit deployment limit |

**Script:** `scripts/firebase_rules_scan.py`
- Parses `firestore.rules` via **recursive descent parser** (not regex — orchestration-review P1)
  - Grammar: ~8 production rules (service, match, allow, function, condition)
  - Tracks: brace depth, current match path, accumulated allow blocks
  - Handles: nested `match` blocks, multi-line conditions with `&&`/`||`, custom `function` declarations
  - Estimated: 550-650 LOC for parser + check logic
  - Unsupported (documented): CEL ternary expressions, complex `get()`/`exists()` chains with computed paths
- Parses `database.rules.json` (JSON rules — stdlib `json` module)
- Outputs findings as JSON or text
- Exit code 1 on HIGH, 0 otherwise
- Supports `.cloud-security-ignore` for suppressions

**Reference file:** `reference/firebase-rules-patterns.md` — safe/unsafe patterns with examples

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/firebase-rules-audit/SKILL.md` | CREATE | Skill definition |
| `app/skills/firebase-rules-audit/scripts/firebase_rules_scan.py` | CREATE | Deterministic scanner |
| `app/skills/firebase-rules-audit/reference/firebase-rules-patterns.md` | CREATE | Safe/unsafe patterns |

**Success Criteria:**
- [ ] Parses `firestore.rules` — detects 10+ check patterns
- [ ] Parses `database.rules.json` — detects root-level open access
- [ ] `--output json` for CI
- [ ] `.cloud-security-ignore` support
- [ ] Tests: >= 10 (one per check pattern + edge cases)

---

#### 2.2 Skill: `cloud-functions-audit`

**Purpose:** Audit Cloud Functions permissions and detect false positives.

**Static mode (no credentials):**

| Check | Severity | Description |
|-------|----------|-------------|
| `onRequest` handler without auth middleware | WARN | Potentially public — needs context |
| `onCall` handler (inherently authenticated) | INFO | Informational — callable is auth'd |
| Hardcoded API keys / secrets in source | HIGH | Secrets in code |
| CORS `origin: '*'` in CF handler | WARN | Unrestricted CORS |
| Missing rate limiting patterns | WARN | No throttling on public endpoint |
| `functions.https.onRequest` + no `validateFirebaseIdToken` | WARN | HTTP function without Firebase Auth check |

**Live mode (credentials required):**

| Check | Severity | CLI Command | Description |
|-------|----------|-------------|-------------|
| `allUsers` invoker on CF | CONTEXT | `gcloud functions get-iam-policy` | Public — resolve with context graph |
| `allAuthenticatedUsers` invoker | WARN | `gcloud functions get-iam-policy` | Any Google account can invoke |
| App Check enforcement status | CONTEXT | `gcloud app-check services list` | Feeds into false positive resolution |
| Deployed rules vs local rules diff | WARN | `gcloud firestore indexes` + local | Rules drift detection |
| Cloud Run public ingress | CONTEXT | `gcloud run services describe` | Public — resolve with context graph |
| Overly broad IAM roles on SA | HIGH | `gcloud projects get-iam-policy` | CF service account with editor/owner |

**Script:** `scripts/cloud_functions_audit.py`

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/cloud-functions-audit/SKILL.md` | CREATE | Skill definition |
| `app/skills/cloud-functions-audit/scripts/cloud_functions_audit.py` | CREATE | Scanner |
| `app/skills/cloud-functions-audit/scripts/gcp_auth.py` | CREATE | Credential loader |
| `app/skills/cloud-functions-audit/reference/false-positives-gcp.md` | CREATE | False positive patterns |

**Success Criteria:**
- [ ] Static: parses CF source for auth patterns
- [ ] Live: checks IAM bindings via `gcloud`
- [ ] False positive resolution for App Check + Gateway patterns
- [ ] Tests: >= 8

---

#### 2.3 False Positive Resolver

**Purpose:** Central engine that resolves "is this actually a problem?" by building a security context graph.

**How it works:**
```
Input: Finding { resource, severity, type }

Step 1: Gather context
  ├── Check API Gateway routes (firebase.json rewrites, API Gateway configs)
  ├── Check WAF/CDN (Cloudflare, CloudFront, Azure Front Door)
  ├── Check App Check / AppArmor / Shield
  ├── Check callable vs HTTP function type
  ├── Check VPC / private subnet placement
  └── Check Load Balancer + auth middleware

Step 2: Apply resolution rules
  ├── Public CF + App Check ENFORCED → SUPPRESSED (protected)
  ├── Public CF + API Gateway route → SUPPRESSED (gateway handles auth)
  ├── Public CF + onCall() → SUPPRESSED (callable is auth'd by SDK)
  ├── Public S3 + CloudFront OAI → SUPPRESSED (not directly accessible)
  ├── Open SG port + ALB → SUPPRESSED (ALB handles TLS + auth)
  ├── Open NSG + Application Gateway → SUPPRESSED (WAF handles filtering)
  └── No context found → KEEP ORIGINAL SEVERITY

Step 3: Output
  ├── Original severity
  ├── Resolved severity (SUPPRESSED / DOWNGRADED / CONFIRMED)
  ├── Context chain (what protections were found)
  └── Confidence (high if multiple protections, low if single)
```

**Output example:**
```json
{
  "resource": "processPayment",
  "provider": "gcp",
  "type": "cloud-function-public-invoker",
  "original_severity": "HIGH",
  "resolved_severity": "SUPPRESSED",
  "confidence": "high",
  "context_chain": [
    { "layer": "app_check", "status": "ENFORCED", "source": "gcloud app-check services list" },
    { "layer": "function_type", "status": "onCall", "source": "source:index.ts:42" },
    { "layer": "api_gateway", "status": "ROUTED", "source": "firebase.json:rewrites" }
  ],
  "verdict": "3/3 protection layers active. Suppressing finding."
}
```

**Script:** `scripts/false_positive_resolver.py`

**Resolution rules stored in:** `reference/resolution-rules.json`
```json
{
  "rules": [
    {
      "id": "gcp-cf-appcheck",
      "finding_type": "cloud-function-public-invoker",
      "provider": "gcp",
      "context_required": ["app_check:ENFORCED"],
      "action": "SUPPRESS",
      "reason": "App Check enforced — only verified app instances can invoke"
    },
    {
      "id": "gcp-cf-callable",
      "finding_type": "cloud-function-public-invoker",
      "provider": "gcp",
      "context_required": ["function_type:onCall"],
      "action": "SUPPRESS",
      "reason": "onCall functions require Firebase Auth token from client SDK"
    },
    {
      "id": "aws-s3-cloudfront-oai",
      "finding_type": "s3-bucket-public-access",
      "provider": "aws",
      "context_required": ["cloudfront_oai:ACTIVE"],
      "action": "SUPPRESS",
      "reason": "Bucket accessed only via CloudFront Origin Access Identity"
    },
    {
      "id": "azure-func-apigw",
      "finding_type": "function-app-public",
      "provider": "azure",
      "context_required": ["application_gateway:ACTIVE"],
      "action": "SUPPRESS",
      "reason": "Function behind Application Gateway with WAF"
    }
  ]
}
```

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/cloud-security-audit/scripts/false_positive_resolver.py` | CREATE | Context graph engine |
| `app/skills/cloud-security-audit/reference/resolution-rules.json` | CREATE | Configurable rules |

**Success Criteria:**
- [ ] Resolves GCP: App Check, Gateway, callable patterns
- [ ] Resolves AWS: CloudFront OAI, ALB, WAF patterns
- [ ] Resolves Azure: App Gateway, Front Door, VNET patterns
- [ ] JSON output with context chain
- [ ] User can add custom rules to `.cloud-security.json` `context` section
- [ ] Tests: >= 12 (4 per provider)

---

### Faza 3: AWS (Phase 2, tydzien 3-4)

#### 3.1 Skill: `aws-security-audit`

**Static mode (IaC parsing):**

| Check | Severity | Source | Description |
|-------|----------|--------|-------------|
| S3 bucket `"Effect": "Allow", "Principal": "*"` | HIGH | .tf / .json | Public bucket policy |
| S3 `BlockPublicAccess` all false | HIGH | .tf / .json | Public access not blocked |
| Lambda `resource-based policy` with `Principal: "*"` | HIGH | .tf / .json | Public Lambda |
| Security Group `0.0.0.0/0` ingress on non-80/443 | HIGH | .tf / .json | Open port to world |
| IAM policy with `Action: "*"` | HIGH | .tf / .json | God-mode IAM |
| IAM policy with `Resource: "*"` + sensitive actions | WARN | .tf / .json | Broad resource scope |
| Unencrypted RDS/DynamoDB | WARN | .tf / .json | Missing encryption at rest |
| CloudTrail disabled | HIGH | .tf / .json | No audit logging |
| Missing VPC Flow Logs | WARN | .tf / .json | No network monitoring |

**Live mode:**

| Check | CLI Command | Description |
|-------|-------------|-------------|
| S3 public buckets | `aws s3api get-public-access-block` | Per-bucket public access |
| Lambda public policies | `aws lambda get-policy` | Resource-based policies |
| Open Security Groups | `aws ec2 describe-security-groups` | Ingress from 0.0.0.0/0 |
| Overly permissive IAM | `aws iam list-roles` + `get-role` | Roles with admin/broad access |
| Unused IAM credentials | `aws iam generate-credential-report` | Stale access keys |
| API Gateway without auth | `aws apigateway get-rest-apis` | Endpoints without authorizer |

**Script:** `scripts/aws_security_scan.py`

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/aws-security-audit/SKILL.md` | CREATE | Skill definition |
| `app/skills/aws-security-audit/scripts/aws_security_scan.py` | CREATE | Scanner |
| `app/skills/aws-security-audit/scripts/aws_auth.py` | CREATE | Credential loader |
| `app/skills/aws-security-audit/reference/aws-security-checklist.md` | CREATE | CIS Benchmark mapping |
| `app/skills/aws-security-audit/reference/false-positives-aws.md` | CREATE | ALB/CloudFront/WAF patterns |

**Terraform approach (council revision):** Do NOT parse HCL directly (stdlib-only Python cannot handle heredocs, variable interpolation, modules, `for_each`). Instead wrap `terraform show -json` / `terraform plan -json` which outputs clean JSON. Fallback to flat-resource regex for projects without `terraform` CLI.

**Success Criteria:**
- [ ] Static: `terraform show -json` wrapper + CloudFormation/SAM JSON parsing
- [ ] Live: checks S3, Lambda, IAM, SG via `aws` CLI
- [ ] False positive resolution for CloudFront/ALB/WAF
- [ ] CIS Benchmark mapping in reference
- [ ] Tests: >= 10

---

### Faza 4: Azure (Phase 3, tydzien 5-6)

#### 4.1 Skill: `azure-security-audit`

**Static mode (IaC parsing):**

| Check | Severity | Source | Description |
|-------|----------|--------|-------------|
| NSG rule `0.0.0.0/0` source on management ports | HIGH | .tf / .bicep | Open RDP/SSH to world |
| Function App `authLevel: "anonymous"` | WARN | source / .tf | Public Azure Function |
| Cosmos DB `publicNetworkAccess: enabled` | WARN | .tf / .bicep | Public database access |
| Storage Account `allowBlobPublicAccess: true` | HIGH | .tf / .bicep | Public blob storage |
| Missing Key Vault references (hardcoded secrets) | HIGH | source | Secrets not in Key Vault |
| Missing RBAC (classic co-admin model) | WARN | .tf | Legacy access model |

**Live mode:**

| Check | CLI Command | Description |
|-------|-------------|-------------|
| Open NSG rules | `az network nsg rule list` | Broad inbound rules |
| Function App auth | `az functionapp show` + `config` | Auth level and provider |
| Cosmos DB access | `az cosmosdb show` | Network access settings |
| RBAC assignments | `az role assignment list` | Owner/Contributor sprawl |
| Storage public access | `az storage account show` | Blob public access |
| App Service auth | `az webapp auth show` | Auth configuration |

**Script:** `scripts/azure_security_scan.py`

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/skills/azure-security-audit/SKILL.md` | CREATE | Skill definition |
| `app/skills/azure-security-audit/scripts/azure_security_scan.py` | CREATE | Scanner |
| `app/skills/azure-security-audit/scripts/azure_auth.py` | CREATE | Credential loader |
| `app/skills/azure-security-audit/reference/azure-security-checklist.md` | CREATE | CIS Benchmark mapping |
| `app/skills/azure-security-audit/reference/false-positives-azure.md` | CREATE | App Gateway/Front Door patterns |

**Success Criteria:**
- [ ] Static: parses Terraform, Bicep, ARM templates
- [ ] Live: checks NSG, Functions, CosmosDB, RBAC via `az` CLI
- [ ] False positive resolution for App Gateway/Front Door/VNET
- [ ] Tests: >= 10

---

### Faza 3 (cont.): Orchestration + Pack Integration (Phase 2, tydzien 3-4)

#### 3.2 Orchestrator Skill: `/cloud-security-audit`

**Purpose:** Single entry point that runs all provider audits detected in the project.

**Behavior:**
1. Auto-detect providers from project files:
   - `firebase.json` / `firestore.rules` / `.firebaserc` → GCP
   - `serverless.yml` / `template.yaml` / `*.tf` with `provider "aws"` → AWS
   - `*.bicep` / `*.tf` with `provider "azurerm"` / `azure-pipelines.yml` → Azure
2. Check available credentials: `ai-toolkit credentials list`
3. Run detected provider scans in parallel
4. Merge results through false positive resolver
5. Output unified report

**Skill frontmatter:**
```yaml
---
name: cloud-security-audit
description: "Multi-cloud security audit — auto-detects GCP/AWS/Azure and runs
  deterministic scans with false positive resolution"
user-invocable: true
effort: high
disable-model-invocation: true
context: fork
agent: cloud-security-auditor
argument-hint: "[path] [--provider gcp|aws|azure|auto] [--mode static|live] [--severity high|warn] [--output json]"
allowed-tools: Read, Grep, Glob, Bash
---
```

**CLI usage:**
```bash
/cloud-security-audit                            # auto-detect providers, static mode (default)
/cloud-security-audit --provider gcp             # GCP only
/cloud-security-audit --provider aws,azure       # AWS + Azure
/cloud-security-audit --mode static              # no credentials, IaC/source only (DEFAULT)
/cloud-security-audit --mode live                # deployed state (requires credentials)
/cloud-security-audit --severity high            # HIGH findings only
/cloud-security-audit --output json              # CI pipeline output
/cloud-security-audit --output sarif             # SARIF v2.1.0 for GitHub Advanced Security
/cloud-security-audit --changed main             # incremental: only files changed vs main
/cloud-security-audit --explain GCP-CF-001       # detailed remediation for specific rule
/cloud-security-audit src/functions/             # scan specific path
```

**Unified report format:**
```markdown
## Cloud Security Audit Report

### Summary
| Metric | GCP | AWS | Azure | Total |
|--------|-----|-----|-------|-------|
| Mode | live | static | n/a | — |
| Resources scanned | 12 | 8 | 0 | 20 |
| HIGH | 2 | 1 | 0 | 3 |
| WARN | 4 | 3 | 0 | 7 |
| SUPPRESSED (false positive) | 3 | 1 | 0 | 4 |

### Findings (sorted by severity)

#### [HIGH] GCP: Cloud Function "adminEndpoint" — public invoker, no protection
...

#### [SUPPRESSED] GCP: Cloud Function "processPayment" — public invoker
Context: App Check ENFORCED + onCall + API Gateway routed (3/3 layers)
...
```

---

#### 3.2.1 Plugin Pack Manifest

**File:** `app/plugins/cloud-security-pack/plugin.json`

```json
{
  "name": "cloud-security-pack",
  "description": "Multi-cloud security auditing for GCP, AWS, and Azure",
  "version": "1.0.0",
  "domain": "cloud-security",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": [],
  "includes": {
    "agents": ["cloud-security-auditor"],
    "skills": [
      "cloud-security-audit",
      "firebase-rules-audit",
      "cloud-functions-audit",
      "aws-security-audit",
      "azure-security-audit"
    ],
    "rules": [],
    "hooks": []
  },
  "credentials": {
    "supported_providers": ["gcp", "aws", "azure"],
    "setup_command": "ai-toolkit credentials add <provider>"
  }
}
```

**Directory structure:**
```
app/plugins/cloud-security-pack/
├── plugin.json
├── README.md
└── (skills and agent live in core app/ dirs, referenced by name)
```

---

### Faza 5: Tests + Documentation (ongoing, ships with each milestone)

#### 5.1 Tests

| Test file | Count | Description |
|-----------|-------|-------------|
| `tests/test_credentials.bats` | 8+ | CLI credentials management |
| `tests/test_firebase_rules_scan.py` | 10+ | Firestore/RTDB rules patterns |
| `tests/test_cloud_functions_audit.py` | 8+ | CF static + live checks |
| `tests/test_aws_security_scan.py` | 10+ | S3/Lambda/IAM/SG checks |
| `tests/test_azure_security_scan.py` | 10+ | NSG/Functions/CosmosDB checks |
| `tests/test_false_positive_resolver.py` | 12+ | Context graph resolution |
| `tests/test_sarif_formatter.py` | 4+ | SARIF v2.1.0 output validation |
| `tests/test_incremental.py` | 4+ | Git diff filtering, fallback |
| `tests/test_credentials_init.py` | 4+ | Interactive wizard, auto-detect |
| **Total** | **70+** | |

#### 5.2 Documentation

| File | Description |
|------|-------------|
| `kb/planning/cloud-security-pack-plan.md` | This document |
| `kb/reference/cloud-security-checklist.md` | Unified multi-cloud checklist (created when Milestone 1 ships) |
| Skills `reference/` dirs | Per-provider patterns and false positives |

---

## 6. Configuration & Suppression (Unified)

**Council revision:** merged `.cloud-security-ignore` + `.cloud-security-config` into a single `.cloud-security.json`. Two config files is one too many — developers expect one file.

Scaffold interactively: `ai-toolkit credentials init` generates this file.

**Suppression Governance (orchestration-review P0):**
- **Wildcard ignores** (e.g., `GCP-CF-*`) REQUIRE a `justification` field — scanner refuses to suppress without one
- **All ignore entries** require `justification` — enforced by schema validation
- **CI diff detection:** When `.cloud-security.json` is modified in a PR, scanner emits a `SUPPRESSION_CHANGED` finding (severity: WARN) listing added/removed/modified ignore rules. This prevents silent suppression of vulnerabilities via committed config changes.
- **In live mode:** context claims (e.g., `app_check_enforced: true`) are verified against actual cloud state. If claim doesn't match reality, emit `CONTEXT_MISMATCH` finding (severity: HIGH)

```json
{
  "$schema": "https://softspark.github.io/ai-toolkit/schemas/cloud-security.json",

  "ignore": [
    { "rule": "GCP-CF-001:processPayment", "justification": "Behind App Check + API Gateway, verified 2026-04-10" },
    { "rule": "AWS-S3-001:static-assets", "justification": "Intentionally public static bucket, CloudFront OAI active" },
    { "rule": "GCP-CF-*", "justification": "REQUIRED for wildcard suppression — reviewed by @jacek in PR #142" }
  ],

  "context": {
    "gcp": {
      "app_check_enforced": true,
      "api_gateway": "projects/my-proj/locations/us-central1/gateways/main",
      "known_public_functions": ["healthCheck", "webhookReceiver"]
    },
    "aws": {
      "waf_enabled": true,
      "cloudfront_distributions": ["E1234567890"],
      "known_public_buckets": ["static-assets-prod"]
    },
    "azure": {
      "front_door_enabled": true,
      "application_gateway": "my-app-gw",
      "known_public_functions": ["webhookHandler"]
    }
  }
}
```

---

## 7. CI Pipeline Integration

### Basic: JSON output + fail on HIGH

```yaml
- name: Cloud Security Audit
  run: |
    python3 scripts/cloud_security_audit.py \
      --mode static --output json --severity high \
      > security-report.json
    # Exit code 1 = HIGH findings → fail pipeline
```

### Recommended: SARIF + GitHub Advanced Security (inline PR annotations)

```yaml
- name: Cloud Security Audit
  run: |
    python3 scripts/cloud_security_audit.py \
      --mode static --output sarif --changed ${{ github.event.pull_request.base.sha }} \
      > results.sarif
  continue-on-error: true

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

### Live mode with credentials (hardened — orchestration-review P0)

```yaml
- name: Cloud Security Audit (Live)
  env:
    GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
  run: |
    TMPFILE=$(mktemp -m 0600)
    trap 'rm -f "$TMPFILE"' EXIT
    echo "$GCP_SA_KEY" > "$TMPFILE"
    ai-toolkit credentials add gcp --file "$TMPFILE"
    python3 scripts/cloud_security_audit.py \
      --mode live --output sarif --changed "${{ github.event.pull_request.base.sha }}" \
      > results.sarif

- name: Validate & Upload SARIF
  if: always()
  run: python3 -c "import json; d=json.load(open('results.sarif')); assert d.get('version')=='2.1.0', 'Invalid SARIF'"
  continue-on-error: false

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

**CI Security Notes (orchestration-review):**
- `mktemp -m 0600` creates file with owner-only permissions (not world-readable `/tmp/sa.json`)
- `trap 'rm -f' EXIT` ensures cleanup even on script failure
- SARIF schema validated before upload to prevent injected/corrupted annotations
- `${{ github.event.pull_request.base.sha }}` quoted to prevent shell injection via crafted refs
- Consider GitHub OIDC workload identity federation instead of long-lived SA keys for production

---

## 8. Success Criteria (Overall)

| Metric | Target |
|--------|--------|
| Providers supported | 3 (GCP, AWS, Azure) |
| Check patterns (total) | 40+ (GCP: 16, AWS: 15, Azure: 12) |
| False positive rules | 10+ |
| Output formats | 3 (text, JSON, SARIF v2.1.0) |
| CLI commands | 7 (add, list, remove, test, init per provider) |
| Scripts (stdlib Python) | 9 (auth + scanners + resolver + sarif + incremental) |
| Tests | 70+ |
| External dependencies | 0 (stdlib only, CLI tools: gcloud/aws/az/terraform) |
| CI exit codes | 0=clean, 1=HIGH findings, 2=credential error |
| Incremental scan | `--changed` flag works with git refs |
| GitHub integration | SARIF upload → inline PR annotations |

---

## 9. Fix Strategy

**Same approach as HIPAA scanner v1: No auto-fix. Agent interprets and suggests.**

The deterministic scripts produce findings. The `cloud-security-auditor` agent then:
1. **Reads** the flagged file/resource to understand actual context
2. **Suggests** a specific fix (not generic advice — concrete code/config change)
3. **Never** auto-applies changes — the user reviews and applies manually

Examples:
- Firestore rules finding → agent suggests the exact `allow read: if request.auth != null` rule change
- Public CF finding → agent suggests adding `validateFirebaseIdToken` middleware with code snippet
- Open S3 bucket → agent suggests the exact bucket policy JSON to add `BlockPublicAccess`
- Broad IAM role → agent suggests the minimal policy document with only required permissions

**Why no auto-fix in v1:**
- Cloud security fixes require project-specific knowledge (which SA, which bucket, which auth flow)
- Wrong auto-fix on IAM can lock out real users
- Firestore rules changes can break client apps
- The agent's context-aware suggestion is more valuable than a blind auto-fix

**v2 option:** `--fix-mode suggest` generates a `.cloud-security-fixes.patch` file that users can review and apply with `git apply`.

---

## 10. Risks and Mitigation (updated)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CLI tools (gcloud/aws/az) not installed | Medium | Medium | Graceful fallback to static-only mode, clear error message |
| Cloud APIs change breaking audit commands | Low | Medium | Version-pin CLI output format parsing, test with CI |
| False positive rules too aggressive (suppress real issues) | Low | High | Default to WARN not SUPPRESS, require `.cloud-security-config` for suppression |
| Credential leakage in logs | Low | Critical | Never log credentials, 0600 perms, `/tmp` cleanup in CI |
| Scope creep (too many checks) | Medium | Medium | Start with top-10 per provider, expand based on feedback |
| YAML IaC not parseable (stdlib-only) | High | Medium | JSON-only for static IaC; live mode unaffected; v2: vendored YAML subset parser |
| `--changed` confused with live mode | Low | Low | Explicit warning: incremental applies to static only |

---

## 11. Pre-Mortem

1. **Firebase rules parser too simplistic** — Firestore rules use CEL-like syntax with nested `match` blocks. Parser needs proper recursive descent, not just regex. Mitigation: build minimal CEL parser or use line-by-line pattern matching with scope tracking.
2. **False positive resolver gives false confidence** — Users may trust SUPPRESSED status and miss real issues. Mitigation: always show context chain, require explicit `.cloud-security-config` for auto-suppression, default to WARN.
3. **AWS credential scope too broad** — User provides admin-level AWS profile. Mitigation: `credentials test` checks actual permissions, WARN if write access detected, suggest read-only IAM policy in docs.
4. **Three providers = 3x maintenance** — Each provider's CLI evolves independently. Mitigation: abstract provider interface, single test matrix, version tracking per provider.
5. **Terraform parsing incomplete** — HCL syntax is complex (modules, variables, conditionals). Mitigation: wrap `terraform show -json` instead of parsing HCL. Fallback to flat regex for projects without `terraform` CLI.
6. **SARIF adoption low** — Users may not know how to use SARIF with GitHub. Mitigation: provide copy-paste GitHub Actions workflow in docs and `--explain` for onboarding.

---

## 12. Council Review Summary (2026-04-10)

**Verdict:** CONDITIONAL FOR — implement with scope reduction.
**Confidence:** MEDIUM (weighted score: FOR 3.1 vs AGAINST 2.9)

**Key insights applied to this plan:**
- [x] Timeline revised from 3-4 → 5-6 weeks
- [x] ~~Azure deferred to Milestone 3~~ → **reinstated: full 3-provider delivery**
- [x] SARIF v2.1.0 output added — essential for GitHub Advanced Security integration
- [x] Incremental scan mode added (`--changed`) — how developers actually use security tools
- [x] `terraform show -json` wrapper instead of HCL parsing — realistic path
- [x] Single config file `.cloud-security.json` (merged ignore + context)
- [x] `credentials init` interactive wizard — reduce onboarding friction
- [x] `--explain <rule-id>` for on-demand remediation guidance
- [x] Static mode as default — zero-setup first experience

**Deferred to v2:**
- Kubernetes/container security (separate pack candidate)
- Secret scanning with entropy detection
- Compliance framework mapping (SOC2, PCI-DSS, NIST 800-53)
- Visual security dashboard in browser
- GitHub PR comment integration beyond SARIF
- Vendored YAML subset parser for CloudFormation YAML static scanning

**Council strongest agreement:** False positive resolver is the killer feature and primary differentiator vs Checkov/Trivy/Prowler. No existing tool combines deterministic scanning with context-aware resolution.

---

## 13. Orchestration Review Summary (2026-04-10)

**Agents:** tech-lead, security-architect, product-manager, code-reviewer (4 parallel)

**Verdict:** Plan structurally complete (14/14 elements). Three P0 security blockers identified and resolved.

**Applied changes:**

| # | Action | Source | Priority | Applied? |
|---|--------|--------|----------|----------|
| 1 | Programmatic Bash allowlist | security-architect | P0 | Yes — allowlist.sh + agent integration |
| 2 | CI hardening (mktemp/trap/SARIF validation) | security-architect | P0 | Yes — CI examples rewritten |
| 3 | Suppression governance (justification + diff detection) | security-architect | P0 | Yes — schema + SUPPRESSION_CHANGED finding |
| 4 | Recursive descent parser for Firestore | code-reviewer | P1 | Yes — replaced regex approach, +1d estimate |
| 5 | SARIF `driver.rules[]` for GitHub annotations | code-reviewer | P1 | Yes — schema + success criteria |
| 6 | Task 4.1→3.2 numbering fix | tech-lead | P1 | Yes — renumbered |
| 7 | `terraform plan` execution risk documented | security-architect | P1 | Yes — only `show -json` allowed |
| 8 | `credentials init` deferred to M2 | code-reviewer | P2 | Yes — saves 1.5d in M1 |
| 9 | False positive resolver budgeted +2d/provider | code-reviewer | P2 | Yes — estimate updated |
| 10 | `SUPPRESSION_CHANGED` finding type | security-architect | P2 | Yes — in governance section |

**Market positioning (product-manager):**
- Not competing with Checkov on check count (40 vs 3000)
- Competing on: zero-noise (false positive resolver), zero-setup (static-first), IDE-native (10 platforms), AI interpretation
- Target: developers in ai-toolkit ecosystem, not enterprise security teams
- Value as ecosystem feature, not standalone product

**Timeline revision (code-reviewer):**
- 1 person: 6-7 weeks realistic (was 5-6)
- 2 people: 4-5 weeks (parallel GCP + AWS tracks)
- All 3 providers ship in 6 weeks — no conditional gates

---

## 14. Next Actions

1. [ ] Approve plan
2. [ ] Implement `credentials` CLI command (1.1) + Bash allowlist
3. [ ] Create `cloud-security-auditor` agent (1.2)
4. [ ] Implement SARIF formatter + incremental scan (1.3)
5. [ ] Implement `firebase-rules-audit` — recursive descent parser (2.1)
6. [ ] Implement `cloud-functions-audit` + false positive resolver GCP (2.2, 2.3)
7. [ ] Implement `aws-security-audit` + `terraform show -json` wrapper (3.1)
8. [ ] Implement orchestrator + plugin pack + `credentials init` (3.2, 1.1b)
9. [ ] Implement `azure-security-audit` + false positive resolver Azure (4.1)
10. [ ] Full test suite (70+) + documentation + release

---

**Last Updated:** 2026-04-10
**Council Reviewed:** 2026-04-10
**Orchestration Reviewed:** 2026-04-10 (4 agents: tech-lead, security-architect, product-manager, code-reviewer)
