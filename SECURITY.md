# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues by emailing: biuro@softspark.eu

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

You will receive a response within 48 hours. We will:
1. Confirm receipt of your report
2. Investigate and validate the issue
3. Release a fix and disclose the vulnerability (with credit to you unless you prefer anonymity)

## Security Design

### Constitution Enforcement

The toolkit enforces a 5-article safety constitution via `PreToolUse` hooks. Article 1 (Safety First) blocks:
- `rm -rf` and mass deletion commands
- `DROP TABLE` and destructive database operations
- Any command that could cause irreversible data loss without explicit confirmation

### Hook Security

Hooks execute in the user's local environment. They do NOT:
- Phone home or send telemetry
- Execute network requests
- Store or transmit any code or data externally

### Script Security

All bundled scripts (`scripts/*.py`, `scripts/*.sh`) use stdlib only — no external dependencies, no network calls. Review them directly: they are short and readable.

### Installation Security

`install.sh` creates symlinks only. It does NOT:
- Execute arbitrary code from the network
- Modify system files outside of the target project's `.claude/` directory
- Request elevated permissions

## Scope

In scope:
- Command injection in hook scripts
- Privilege escalation via agent definitions
- Unsafe default permissions in settings templates
- Constitution bypass vectors

Out of scope:
- Issues in Claude Code itself (report to Anthropic)
- Social engineering attacks
- Denial of service
