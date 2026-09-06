# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest published 4.x release | Yes |
| Earlier releases | Upgrade to the latest 4.x release |

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

The toolkit distributes a 7-article safety constitution and command guards through supported client hooks. The destructive-command guard checks patterns including:
- `rm -rf` and mass deletion commands
- `DROP TABLE` and destructive database operations
- Known destructive command patterns that require explicit confirmation

These guards complement the coding client's approval controls. They are not an operating-system sandbox and do not identify every possible way a command can cause damage.

### Hook Security

Hooks execute in the user's local environment with that user's permissions. Review the enabled hook scripts and optional plugin configuration when selecting integrations. Client approval controls and the permissions of invoked tools remain part of the execution boundary.

### Script Security

Published Python runtime scripts use the standard library. Explicit commands can fetch remote metadata or configuration and invoke external tools, including package managers and vendor CLIs. Remote-configuration fetches record SHA256 pins; strict-pin mode rejects changed payloads. Development tools such as pytest, ruff, and mypy are separate from the published runtime.

### Installation Security

Installation manages the files required by the selected developer-tool integrations, using generated files, copies, and symlinks as appropriate. Its scope includes project and user configuration locations, depending on the command and target. Review the command's dry-run output and ownership checks before changing an existing installation.

DSH package installation and updates are explicit profile lifecycle operations. They invoke the supported package manager and preserve unrelated profile dependencies and files. Vendor authentication stays with the vendor's own CLI; the toolkit does not implement a credential broker.

## GitHub Security Advisories

For confirmed vulnerabilities, we use [GitHub Security Advisories](https://github.com/softspark/ai-toolkit/security/advisories) to:
1. Coordinate private disclosure and fix development
2. Request a CVE identifier when applicable
3. Publish the advisory alongside the patched release

If you believe a vulnerability warrants a CVE, mention it in your report email — we will initiate the process.

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
