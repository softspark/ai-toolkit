# State helper operations

The helper is a standard-library Python CLI, bundled beside the skill. Run it
with `--repo` naming the working tree used by this run. Its SQLite transactions
protect ownership and journal updates; no command runs tests, changes Git or
publishes to a tracker. JSON output is the integration boundary. Nonzero exit
means the requested operation did not succeed; read its error before proceeding.

Resolve the helper's absolute path from the installed `SKILL.md` entrypoint and
assign that verified path to the task-specific shell variable `RUN_STATE`.
The entrypoint is adapted by each client; this shared reference deliberately
uses the resolved variable rather than a client-specific skill-directory token.
For example, after setting `RUN_STATE`:

```bash
python3 "$RUN_STATE" --repo /absolute/worktree --help
```

In the examples below, replace `RUN_ID` and `OWNER_TOKEN` with the returned
values, and use existing absolute report paths. Do not paste literal placeholders
into an actual run. The optional `--store` changes the state location for an
isolated fixture; normal sessions use the default ai-toolkit per-repository store.
The repository identity is the canonical Git common directory, shared by linked
worktrees. State records the actual worktree and branch separately.

## Initialize or inspect

```bash
python3 "$RUN_STATE" --repo /absolute/worktree list
python3 "$RUN_STATE" --repo /absolute/worktree list --subject issue:https://github.com/organization/project/issues/42
python3 "$RUN_STATE" --repo /absolute/worktree init --subject issue:https://github.com/organization/project/issues/42 --objective "Correct the reported export failure" --source-kind issue --source https://github.com/organization/project/issues/42 --target-branch develop
python3 "$RUN_STATE" --repo /absolute/worktree status --run RUN_ID
```

`init` returns the run ID, a per-session owner token and artifact directory. Its
target branch is the PR base, not the task branch. Duplicate subjects must reuse
their recorded run rather than overwrite it. A run with truly inapplicable QA
or CI uses `--qa-optional` or `--ci-optional` at creation, with the rationale in
the plan. A failed or inaccessible gate is not inapplicable.

`--plan` is an existing nonempty local file path. The journal hashes its content.
Changing the plan or attaching a replacement invalidates previous verification
and the successful-attempt marker; checkpoint the revised plan and rerun gates.

`list` discovers runs without requiring an ID, optionally filtering by exact
subject. It reads only the current repository's runs and does not create a store
when none exists. `list` and `status` do not disclose owner credentials. When
using a custom `--store`, preserve its absolute path with the resume instructions;
the default lookup cannot discover a separately located fixture store.

## Claim and checkpoint

```bash
python3 "$RUN_STATE" --repo /absolute/worktree claim --run RUN_ID --owner OWNER_TOKEN
python3 "$RUN_STATE" --repo /absolute/worktree checkpoint --run RUN_ID --owner OWNER_TOKEN --stage plan --plan /absolute/run/plan.md
python3 "$RUN_STATE" --repo /absolute/worktree checkpoint --run RUN_ID --owner OWNER_TOKEN --stage publish --pr-url https://github.com/organization/project/pull/43
```

Stages are `discover`, `plan`, `implement`, `validate`, `review`, `qa`, `publish`,
`ci` and `blocked`. Only `complete` can set `ready-pr`. A stage describes progress;
it is not evidence that earlier gates passed.

A released run can be claimed by the next session's token. An active foreign
claim requires an explicit handoff or an authorized takeover using
`--previous-owner` with the `run.owner_id` returned by `status`, and `--reason`.
The previous owner ID is a digest prefix, not the previous owner's token.
Read `claim --help` for the exact invocation.
Use `--rebind-worktree` only when intentionally resuming in a different linked
worktree on the same clean branch and commit. A rejected rebind is a real
identity conflict: inspect the retained work and resolve it rather than deleting
the run or pretending the source is unchanged.

## Count attempts

```bash
python3 "$RUN_STATE" --repo /absolute/worktree attempt --run RUN_ID --owner OWNER_TOKEN --action start
python3 "$RUN_STATE" --repo /absolute/worktree attempt --run RUN_ID --owner OWNER_TOKEN --action fail --summary "Regression test fails on the empty-filter case"
```

Start once per implementation/recovery cycle. `record` does not close a cycle;
record all findings and then close the unsuccessful cycle once with `fail`.
The next start requires at least 60 seconds since the previous start. At most
five cycles may start, and three consecutive failed cycles halt the run. These
counters persist through release, takeover and interruption.

An active cycle survives an interrupted host. Continue it on resume instead of
calling `start` again. Close a successful cycle with `--action pass` only after
current validation, review and applicable QA reports pass. A passing linter
alone cannot reset the failure count of an unsuccessful delivery cycle.

## Record real evidence

```bash
python3 "$RUN_STATE" --repo /absolute/worktree record --run RUN_ID --owner OWNER_TOKEN --kind validation --result pass --report /absolute/run/validation.md --summary "Configured validation commands exited zero"
```

Kinds: `validation`, `review`, `qa`, `ci`. Results: `pass`, `fail`, `pending`,
`not-applicable`. Each report must exist and be nonempty. It must describe the
actual check, observed result and tested commit. The helper binds the record to
the current source fingerprint; it does not infer the check's truth from prose.
Never record an old report after switching to a new commit.

Keep evidence immutable once recorded. If a report needs correction, write a
new artifact and record it, preserving the audit history. Final source changes
require fresh checks. `not-applicable` needs a concrete report and is accepted
only for QA/CI declared optional at initialization.

## Complete or hand off

```bash
python3 "$RUN_STATE" --repo /absolute/worktree attempt --run RUN_ID --owner OWNER_TOKEN --action pass --summary "Current local gates verified"
python3 "$RUN_STATE" --repo /absolute/worktree complete --run RUN_ID --owner OWNER_TOKEN
```

`complete` requires a clean current checkout, current passing evidence, applicable
QA and CI, a successfully closed latest attempt for this source, the unchanged
plan and the persisted PR URL. Hidden Git index flags (`assume-unchanged` or
`skip-worktree`), dirty or uninitialized submodules make source verification
incomplete. Resolve them intentionally; the helper never changes index flags.
Check external tracker gates separately:
the helper does not query required reviewers or branch protection.
Before `complete`, require zero `status` blockers, finish any authorized draft
promotion and reread the PR's ready state/current head. Completed journals are
immutable, so a pending external mutation must remain a resumable run.

For a blocker, checkpoint its reason and report location, then release ownership
deliberately so another authorized session can resume:

```bash
python3 "$RUN_STATE" --repo /absolute/worktree checkpoint --run RUN_ID --owner OWNER_TOKEN --stage blocked --artifact /absolute/run/blocker.md
python3 "$RUN_STATE" --repo /absolute/worktree release --run RUN_ID --owner OWNER_TOKEN --reason "Waiting for required CI; handoff checkpoint saved"
```

`status` is read-only and reports current blockers and the next action. It does
not launch an agent or continue a run in the background.
