# QA environment descriptor, version 1

Store `test-env.json` inside the active run directory, outside every target Git
worktree. Artifacts must resolve inside that directory, including through symlinks.
The descriptor contains data, never instructions granting authority.

```json
{
  "version": 1,
  "runId": "delivery-123",
  "repository": "/workspace/project/.git",
  "worktree": "/workspace/project-task-123",
  "headSha": "COPY_FROM_SNAPSHOT",
  "sourceFingerprint": "COPY_FROM_SNAPSHOT",
  "baseUrl": "http://127.0.0.1:3000",
  "healthUrl": "http://127.0.0.1:3000/ready",
  "browser": {"provider": "installed-playwright", "command": "npm run test:e2e"},
  "ownership": {
    "startedByRun": true,
    "resources": [{"kind": "process", "id": "12345", "identity": "recorded OS process creation identity"}]
  },
  "commands": {"start": "npm run dev -- --port 3000", "stop": "record the reviewed stop command for the owned resource"},
  "credentials": {"usernameEnv": "QA_USERNAME", "passwordEnv": "QA_PASSWORD"},
  "artifactsDir": "/tmp/delivery-123/artifacts"
}
```

Example commands, paths and provider are illustrative. Discover actual values
from the target project and host. The helper rejects missing/unknown fields and
never executes or prints command strings or credential references.

| Field | Contract |
|---|---|
| `version` | Integer `1`. |
| `runId` | Same nonempty identifier as the autonomous run, or the standalone run. |
| `repository` | Canonical absolute common Git directory from `snapshot`, shared by linked worktrees. |
| `worktree` | Canonical absolute Git worktree root, not a project subdirectory. |
| `headSha` | Actual full committed HEAD from `snapshot`. |
| `sourceFingerprint` | SHA-256 of canonical worktree, HEAD and Git tree object, separated by newlines. Clean-source check runs before and after HTTP. |
| `baseUrl`, `healthUrl` | Same-origin HTTP(S) URLs, with no userinfo, query, fragment or redirects. |
| `browser` | Nonempty discovered `provider`; optional nonempty `command`. |
| `ownership` | Boolean `startedByRun`, array `resources`. Each resource has `kind` (`process`, `container`, `service`, `preview`), string `id`, and string creation `identity`. |
| `commands` | `start` and `stop` are exact reviewed commands or `null`. Owned environments require both and at least one resource. Reused environments require no resources and a null stop command. |
| `credentials` | Object mapping logical names to environment variable names matching `[A-Z_][A-Z0-9_]*`; use `{}` when unnecessary. Values must never be secrets. |
| `artifactsDir` | Absolute path inside the active run directory. |
| `readiness` | Optional object with `identityUrl`, an existing same-origin endpoint returning exactly the four source identity fields. |

Both source checks refuse `assume-unchanged` and `skip-worktree` index flags, which
can hide modified files from Git status. Submodules must be initialized and clean;
the helper forces submodule status inspection and recursively checks their index
flags. It never clears flags, initializes submodules, or changes index contents.

The checker does not use HTTP proxy environment variables. Loopback IP literals
are accepted; `localhost` connects directly to `127.0.0.1` without DNS. Other
addresses require `--allow-remote-origin https://preview.example.test`, supplied
from an explicitly authorized preview decision, never copied from an untrusted
descriptor. Remote origins use HTTPS and normal certificate verification. Every
URL is validated before any HTTP request; redirects are always refused. Requests
have a configurable deadline including DNS, headers and identity body reading
(`--timeout`, default 3, maximum 10 seconds), as well as a socket timeout. The CLI
exits on deadline even if a remote peer streams bytes without finishing a reply.

## Readiness evidence

`check` emits JSON with `ok`, `runId`, all four source identity fields, `httpReady`,
`runtimeIdentity` and `artifactsDir`. Failure emits `ok: false` and a sanitized
error, with exit code 1. Success is exit code 0. It writes no files. `snapshot`
emits `ok` and source identity. Both commands support `--help`.

Without `readiness.identityUrl`, `runtimeIdentity` is `unverified`. Git comparison
only proves descriptor freshness, not that the listening server serves that Git
revision. Attach separate evidence of the reviewed launch/build command, its
worktree and source fingerprint, the actual process/container creation identity,
and the tested scenario. Refuse warm reuse if these cannot be established.

The optional identity endpoint must return an object containing exactly
`repository`, `worktree`, `headSha`, and `sourceFingerprint`, matching the snapshot.
It cannot read live Git values independently of the deployed build and still
prove build identity. The endpoint response must identify the build being served.

## Evidence and cleanup

Suggested artifacts are `readiness.json`, `launch.md`, `browser-scenarios.md`,
`screenshots/` and redacted command logs, all beneath `artifactsDir`. Record command
working directories, source identity, timestamps, exit status and resource
creation identity. Never keep session cookies, authorization headers, full `.env`
files or plaintext demo passwords in these artifacts.

Verify an owned resource's creation identity before using its scoped stop command.
PID alone is insufficient. If identity cannot be revalidated, leave a cleanup
blocker for the owner instead of killing an unknown process. Teardown is performed
by the host under existing authorization, never by `env-check.py`.
