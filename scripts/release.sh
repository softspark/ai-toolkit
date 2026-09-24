#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# The only supported way to cut an ai-toolkit release. Every gate runs here,
# on the maintainer's machine and in throwaway Linux containers; GitHub
# Actions only publishes the tag this script pushes.
#
#   npm run release -- X.Y.Z               full release: gates, tag, push, watch
#   npm run release -- X.Y.Z --dry-run     steps 1-5, then print steps 6-7
#   npm run release -- X.Y.Z --gates-only  steps 3-5 on the working tree, no
#                                          git preconditions, no tag
#
# Procedure and rationale: kb/procedures/sop-release.md
# Not shipped: package.json "files" excludes this file.

set -euo pipefail

readonly REPO_SLUG="softspark/ai-toolkit"
readonly PKG_NAME="@softspark/ai-toolkit"
readonly BRANCH="main"
readonly PUBLISH_WORKFLOW="publish.yml"
readonly LINUX_IMAGE="ubuntu:24.04"
readonly LINUX_TOOLCHAIN_IMAGE="ai-toolkit-release-linux:ubuntu24.04"
readonly PY_FLOOR_IMAGE="python:3.11-slim"
readonly PY_CEILING_IMAGE="python:3.13-slim"
readonly WAIT_ATTEMPTS=5
readonly WAIT_SECONDS=30
# npm lists a new version 3 to 6 minutes after the publish job ends (v5.0.0
# and v5.0.1 both took about 5); 20 x 30 s leaves margin.
readonly NPM_WAIT_ATTEMPTS=20

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

VERSION=""
MODE="release"

usage() {
    sed -n '10,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() {
    printf 'release: %s\n' "$*" >&2
    exit 1
}

step() {
    printf '\n== %s\n' "$*"
}

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --dry-run) MODE="dry-run" ;;
            --gates-only) MODE="gates-only" ;;
            -h|--help) usage; exit 0 ;;
            -*) die "unknown option: $1" ;;
            *)
                [ -z "$VERSION" ] || die "more than one version given: $VERSION, $1"
                VERSION="$1"
                ;;
        esac
        shift
    done
    [ -n "$VERSION" ] || { usage >&2; die "missing version"; }
    [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "not a semver X.Y.Z version: $VERSION"
}

# Runs one gate with its output in its own log file. Gate functions chain
# their commands with && or `|| return 1`: errexit does not apply inside a
# function called as an `if` condition.
run_gate() {
    local name="$1"
    shift
    printf '  %-36s' "$name"
    if "$@" >"$LOG_DIR/$name.log" 2>&1; then
        printf 'ok\n'
    else
        printf 'FAIL\n'
        tail -n 40 "$LOG_DIR/$name.log" >&2
        die "gate '$name' failed; full log: $LOG_DIR/$name.log"
    fi
}

json_field() {
    node -p "require('./$1')$2"
}

require_tools() {
    local tool
    for tool in git node npm python3 bats parallel shellcheck docker tar; do
        command -v "$tool" >/dev/null 2>&1 || die "required tool not on PATH: $tool"
    done
    docker info >/dev/null 2>&1 || die "docker daemon is not running (needed for the Linux gates)"
    if [ "$MODE" = "release" ]; then
        command -v gh >/dev/null 2>&1 || die "required tool not on PATH: gh"
        gh auth status >/dev/null 2>&1 || die "gh is not authenticated (needed to watch the publish run)"
    fi
}

# ---------------------------------------------------------------------------
# Step 1: preconditions
# ---------------------------------------------------------------------------

check_preconditions() {
    step "1. Preconditions"
    local branch
    branch="$(git rev-parse --abbrev-ref HEAD)"
    [ "$branch" = "$BRANCH" ] || die "on branch '$branch', releases are cut from '$BRANCH'"
    [ -z "$(git status --porcelain)" ] || die "working tree is not clean"
    git fetch --quiet origin "$BRANCH" || die "git fetch origin $BRANCH failed"
    git merge-base --is-ancestor "origin/$BRANCH" HEAD \
        || die "local $BRANCH is behind or diverged from origin/$BRANCH"
    if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
        die "tag $TAG already exists locally"
    fi
    if [ -n "$(git ls-remote --tags origin "refs/tags/$TAG")" ]; then
        die "tag $TAG already exists on origin"
    fi
    if [ -n "$(npm view "$PKG_NAME@$VERSION" version 2>/dev/null)" ]; then
        die "$PKG_NAME@$VERSION is already on npm"
    fi
    echo "  branch $BRANCH, clean, not behind origin, $TAG unused"
}

# ---------------------------------------------------------------------------
# Step 2: version files, notes, release commit
# ---------------------------------------------------------------------------

check_version_and_notes() {
    step "2. Version and notes"
    local file actual subject
    for file in package.json manifest.json app/.claude-plugin/plugin.json package-lock.json; do
        actual="$(json_field "$file" ".version")"
        [ "$actual" = "$VERSION" ] || die "$file says $actual, expected $VERSION"
    done
    actual="$(json_field package-lock.json ".packages['']?.version")"
    [ "$actual" = "$VERSION" ] || die "package-lock.json packages[\"\"] says $actual, expected $VERSION"
    grep -qE "^## v${VERSION//./\\.}( |$)" CHANGELOG.md || die "CHANGELOG.md has no '## v$VERSION' heading"
    grep -qF "## What's New in v$VERSION" README.md || die "README.md has no 'What's New in v$VERSION' section"
    subject="$(git log -1 --format=%s HEAD)"
    [ "$subject" = "chore: release v$VERSION" ] || die "HEAD is '$subject', expected 'chore: release v$VERSION'"
    echo "  versions, CHANGELOG, README and release commit agree on $VERSION"
}

# ---------------------------------------------------------------------------
# Step 3: local gates (macOS host)
# ---------------------------------------------------------------------------

gate_required_files() {
    local f
    for f in LICENSE NOTICE CHANGELOG.md SECURITY.md CODE_OF_CONDUCT.md \
             README.md CLAUDE.md .gitignore .npmignore .npmrc \
             .github/CONTRIBUTING.md .github/PULL_REQUEST_TEMPLATE.md \
             .github/CODEOWNERS .github/FUNDING.yml .github/dependabot.yml \
             .github/ISSUE_TEMPLATE/bug_report.md \
             .github/ISSUE_TEMPLATE/feature_request.md \
             .github/ISSUE_TEMPLATE/config.yml \
             kb/procedures/sop-pre-commit.md \
             kb/procedures/sop-release.md \
             kb/procedures/sop-post-release-testing.md; do
        [ -f "$f" ] || { echo "missing: $f"; return 1; }
    done
    echo "all required files present"
}

# Content fingerprint of every tracked and untracked (not ignored) file, so a
# gate that rewrites or deletes a file is caught even on a dirty --gates-only
# tree. Index state is left out on purpose: staging changes nothing that ships.
tree_fingerprint() {
    { git ls-files -z --cached --others --exclude-standard | sort -zu \
        | xargs -0 shasum 2>/dev/null || true; } | shasum | cut -d' ' -f1
}

gate_generate_all() {
    local before after
    before="$(tree_fingerprint)"
    npm run generate:all || return 1
    test -s AGENTS.md || { echo "AGENTS.md is empty after generate:all"; return 1; }
    after="$(tree_fingerprint)"
    if [ "$before" != "$after" ]; then
        git status --short
        echo "generate:all changed committed files: commit the regenerated artefacts"
        return 1
    fi
}

gate_sarif() {
    python3 scripts/audit_skills.py --sarif >"$LOG_DIR/audit.sarif" || return 1
    python3 - "$LOG_DIR/audit.sarif" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert d["version"] == "2.1.0", d["version"]
assert d["runs"][0]["tool"]["driver"]["name"] == "ai-toolkit-audit-skills"
assert d["runs"][0]["tool"]["driver"]["rules"], "no SARIF rules"
print(f"SARIF OK: {len(d['runs'][0]['results'])} results")
PY
}

gate_shellcheck() {
    shellcheck --severity=warning app/hooks/*.sh app/plugins/*/hooks/*.sh scripts/release.sh
}

gate_registry_drift() {
    local meta='generate_agents_md\.py|generate_llms_txt\.py|generate_language_rules_skills\.py|generate_toolkit_rules_skills\.py'
    diff \
        <(grep -oE 'scripts/generate_[a-z_]+\.py' kb/reference/supported-tools-registry.md | sort -u) \
        <(printf '%s\n' scripts/generate_*.py | grep -vE "$meta" | sort -u)
}

gate_publish_workflow() {
    local wf=".github/workflows/$PUBLISH_WORKFLOW"
    grep -q -- '--provenance' "$wf" || { echo "$wf lost --provenance"; return 1; }
    grep -q 'id-token: write' "$wf" || { echo "$wf lost id-token: write"; return 1; }
}

gate_bats_host() {
    npm test || return 1
    ! grep -q '^not ok' "$LOG_DIR/bats-macos.log"
}

run_host_gates() {
    step "3. Gates (host: $(uname -s)), logs in $LOG_DIR"
    local before
    before="$(tree_fingerprint)"
    run_gate required-files gate_required_files
    run_gate generate-all gate_generate_all
    run_gate ecosystem-doctor python3 scripts/ecosystem_doctor.py --offline --check
    run_gate validate-strict python3 scripts/validate.py --strict
    run_gate evaluate-skills python3 scripts/evaluate_skills.py
    run_gate audit-ci python3 scripts/audit_skills.py --ci
    run_gate audit-sarif gate_sarif
    run_gate audit-permissions python3 scripts/audit_skills.py --permissions
    run_gate shellcheck gate_shellcheck
    run_gate registry-drift gate_registry_drift
    run_gate publish-workflow gate_publish_workflow
    run_gate bats-macos gate_bats_host
    printf '  bats-macos: %s ok, %s not ok\n' \
        "$(grep -c '^ok ' "$LOG_DIR/bats-macos.log" || true)" \
        "$(grep -c '^not ok' "$LOG_DIR/bats-macos.log" || true)"
    [ "$(tree_fingerprint)" = "$before" ] || { git status --short; die "the gates modified the working tree"; }
    echo "  review the permission footprint: $LOG_DIR/audit-permissions.log"
}

# ---------------------------------------------------------------------------
# Step 4: Linux gates (throwaway containers, repository copied in)
# ---------------------------------------------------------------------------

# Tracked plus untracked-but-not-ignored files that exist on disk, plus .git.
# Equals HEAD on a release (clean tree); on --gates-only it is the working tree.
write_source_tarball() {
    local list="$LOG_DIR/source-files.list" f
    git ls-files -z --cached --others --exclude-standard | while IFS= read -r -d '' f; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        printf '%s\0' "$f"
    done >"$list"
    printf '.git\0' >>"$list"
    if tar --version 2>/dev/null | grep -q bsdtar; then
        # macOS: no AppleDouble files or xattr headers in the archive.
        COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -cf "$SOURCE_TAR" --null -T "$list"
    else
        tar -cf "$SOURCE_TAR" --null -T "$list"
    fi
}

# Toolchain layer, cached by Docker after the first release. The repository
# itself never enters the image: it is streamed into a throwaway container.
build_linux_image() {
    docker build --quiet -t "$LINUX_TOOLCHAIN_IMAGE" - <<EOF
FROM $LINUX_IMAGE
RUN export DEBIAN_FRONTEND=noninteractive \\
    && apt-get update -qq \\
    && apt-get install -y -qq bats git python3 nodejs npm jq unzip zip parallel shellcheck >/dev/null \\
    && rm -rf /var/lib/apt/lists/* \\
    && useradd --create-home tester
EOF
}

# bats in Ubuntu as a non-root user: some tests misbehave as root, and macOS
# bash 3.2 does not fail a bare [[ ]] assertion in bats while Linux does.
gate_bats_linux() {
    build_linux_image || return 1
    docker run --rm -i "$LINUX_TOOLCHAIN_IMAGE" bash -euc '
        mkdir -p /home/tester/repo && tar --no-same-owner -xf - -C /home/tester/repo
        chown -R tester:tester /home/tester/repo
        cd /home/tester/repo
        runuser -u tester -- env HOME=/home/tester bats tests/ --jobs 4 --no-parallelize-within-files
    ' <"$SOURCE_TAR"
}

# The scripts must import on the declared Python floor (PYTHON_MIN) and on a
# newer interpreter: py_compile only catches syntax, version-gated runtime
# features surface on import.
readonly PY_IMPORT_CHECK='
import importlib, pathlib, sys, traceback
root = pathlib.Path("scripts")
sys.path[:0] = [str(root), str(root / "install_steps")]
failed = []
for path in sorted(root.rglob("*.py")):
    if "__pycache__" in path.parts:
        continue
    module = ".".join(path.relative_to(root).with_suffix("").parts)
    try:
        importlib.import_module(module)
    except Exception:
        failed.append(module)
        print(f"{module} failed to import on Python {sys.version.split()[0]}")
        traceback.print_exc()
sys.exit(1 if failed else 0)
'

gate_python_ceiling() {
    docker run --rm -i -e PY_IMPORT_CHECK="$PY_IMPORT_CHECK" "$PY_CEILING_IMAGE" bash -euc '
        mkdir -p /src && tar --no-same-owner -xf - -C /src && cd /src
        python3 --version
        python3 -m py_compile scripts/*.py app/skills/*/scripts/*.py
        python3 -c "$PY_IMPORT_CHECK"
    ' <"$SOURCE_TAR"
}

# Dev tooling (pytest, ruff, mypy) runs on the floor interpreter, with the
# commands read from package.json so this script and `npm run` cannot drift.
gate_python_floor() {
    local test_py lint_py typecheck_py
    test_py="$(json_field package.json ".scripts['test:py']")" || return 1
    lint_py="$(json_field package.json ".scripts['lint:py']")" || return 1
    typecheck_py="$(json_field package.json ".scripts['typecheck:py']")" || return 1
    docker run --rm -i \
        -e PY_IMPORT_CHECK="$PY_IMPORT_CHECK" -e TEST_PY="$test_py" \
        -e LINT_PY="$lint_py" -e TYPECHECK_PY="$typecheck_py" \
        "$PY_FLOOR_IMAGE" bash -euc '
        mkdir -p /src && tar --no-same-owner -xf - -C /src && cd /src
        python3 --version
        python3 -m py_compile scripts/*.py app/skills/*/scripts/*.py
        python3 -c "$PY_IMPORT_CHECK"
        python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements-dev.txt
        sh -c "$TEST_PY"
        sh -c "$LINT_PY"
        sh -c "$TYPECHECK_PY"
    ' <"$SOURCE_TAR"
}

run_linux_gates() {
    step "4. Linux gates ($LINUX_IMAGE bats, $PY_FLOOR_IMAGE, $PY_CEILING_IMAGE)"
    SOURCE_TAR="$LOG_DIR/source.tar"
    write_source_tarball || die "could not build the source tarball"
    run_gate python-floor gate_python_floor
    run_gate python-ceiling gate_python_ceiling
    run_gate bats-linux gate_bats_linux
    printf '  bats-linux: %s ok, %s not ok\n' \
        "$(grep -c '^ok ' "$LOG_DIR/bats-linux.log" || true)" \
        "$(grep -c '^not ok' "$LOG_DIR/bats-linux.log" || true)"
    rm -f "$SOURCE_TAR"
}

# ---------------------------------------------------------------------------
# Step 5: build the tarball the tag publishes, start it once
# ---------------------------------------------------------------------------

gate_pack() {
    rm -f "$LOG_DIR"/softspark-ai-toolkit-*.tgz
    npm pack --pack-destination "$LOG_DIR" || return 1
    TARBALL="$(ls "$LOG_DIR"/softspark-ai-toolkit-*.tgz)"
    local entries
    entries="$(tar -tzf "$TARBALL")" || return 1
    printf '%s\n' "$entries" | grep -qx 'package/AGENTS.md' || { echo "AGENTS.md missing from tarball"; return 1; }
    printf '%s\n' "$entries" | grep -qx 'package/NOTICE' || { echo "NOTICE missing from tarball"; return 1; }
    ! printf '%s\n' "$entries" | grep -qx 'package/scripts/release.sh' || { echo "release.sh leaked into tarball"; return 1; }
}

gate_smoke() {
    local sandbox="$LOG_DIR/smoke" reported
    rm -rf "$sandbox" && mkdir -p "$sandbox/home" "$sandbox/prefix" || return 1
    HOME="$sandbox/home" npm install --global --prefix "$sandbox/prefix" --no-audit --no-fund "$TARBALL" || return 1
    reported="$(HOME="$sandbox/home" "$sandbox/prefix/bin/ai-toolkit" --version)" || return 1
    [ "$reported" = "$(json_field package.json ".version")" ] || { echo "installed CLI reports $reported"; return 1; }
    HOME="$sandbox/home" "$sandbox/prefix/bin/ai-toolkit" help || return 1
    rm -rf "$sandbox"
}

run_build_and_smoke() {
    step "5. Build and smoke"
    run_gate npm-pack gate_pack
    run_gate smoke-install gate_smoke
    echo "  tarball: $TARBALL"
}

# ---------------------------------------------------------------------------
# Steps 6-7: tag, push, watch publish
# ---------------------------------------------------------------------------

tag_and_push() {
    step "6. Tag and push"
    local head
    head="$(git rev-parse HEAD)"
    git tag "$TAG" "$head"
    [ "$(git rev-parse "$TAG^{commit}")" = "$head" ] || die "tag $TAG is not on HEAD"
    [ "$(git show --no-patch --format=%s "$TAG")" = "chore: release $TAG" ] || die "tag $TAG is not on the release commit"
    git push origin "$BRANCH"
    git push origin "refs/tags/$TAG"
    echo "  pushed $BRANCH and $TAG ($head)"
}

find_publish_run() {
    local sha="$1" attempt run_id
    for attempt in $(seq 1 "$WAIT_ATTEMPTS"); do
        run_id="$(gh run list --repo "$REPO_SLUG" --workflow "$PUBLISH_WORKFLOW" --event push \
            --commit "$sha" --limit 1 --json databaseId --jq '.[0].databaseId // empty')"
        [ -n "$run_id" ] && { echo "$run_id"; return 0; }
        echo "  waiting for the publish run to register ($attempt/$WAIT_ATTEMPTS)" >&2
        sleep "$WAIT_SECONDS"
    done
    return 1
}

verify_npm() {
    local attempt published provenance
    for attempt in $(seq 1 "$NPM_WAIT_ATTEMPTS"); do
        published="$(npm view "$PKG_NAME@$VERSION" version 2>/dev/null || true)"
        [ "$published" = "$VERSION" ] && break
        echo "  waiting for npm to list $PKG_NAME@$VERSION ($attempt/$NPM_WAIT_ATTEMPTS)"
        sleep "$WAIT_SECONDS"
    done
    [ "$published" = "$VERSION" ] || die "$PKG_NAME@$VERSION is not on npm"
    provenance="$(npm view "$PKG_NAME@$VERSION" dist.attestations.provenance.predicateType 2>/dev/null || true)"
    [ "$provenance" = "https://slsa.dev/provenance/v1" ] || die "$PKG_NAME@$VERSION has no SLSA provenance attestation"
    echo "  npm: $PKG_NAME@$VERSION published with provenance"
}

# The publish workflow no longer runs the audit, so the SARIF this script
# produced in step 3 is uploaded here, against the tagged commit.
upload_sarif() {
    local sha="$1"
    gzip -c "$LOG_DIR/audit.sarif" | base64 | tr -d '\n' >"$LOG_DIR/audit.sarif.gz.b64"
    if gh api --method POST "repos/$REPO_SLUG/code-scanning/sarifs" \
        -f commit_sha="$sha" -f ref="refs/tags/$TAG" -F sarif=@"$LOG_DIR/audit.sarif.gz.b64" >/dev/null; then
        echo "  SARIF uploaded to code scanning"
    else
        echo "  WARNING: SARIF upload failed; the package is published. Retry by hand:" >&2
        echo "    gh api --method POST repos/$REPO_SLUG/code-scanning/sarifs -f commit_sha=$sha -f ref=refs/tags/$TAG -F sarif=@$LOG_DIR/audit.sarif.gz.b64" >&2
    fi
}

watch_publish() {
    step "7. Watch publish"
    local sha run_id
    sha="$(git rev-parse "$TAG^{commit}")"
    run_id="$(find_publish_run "$sha")" || die "no $PUBLISH_WORKFLOW run found for $TAG"
    gh run watch "$run_id" --repo "$REPO_SLUG" --exit-status \
        || die "publish run $run_id failed: gh run view $run_id --repo $REPO_SLUG --log-failed"
    echo "  publish run $run_id succeeded"
    verify_npm
    gh release view "$TAG" --repo "$REPO_SLUG" >/dev/null || die "GitHub Release $TAG is missing"
    echo "  GitHub Release $TAG exists"
    upload_sarif "$sha"
}

print_remaining_steps() {
    step "6-7. Dry run: not executed"
    cat <<EOF
  git tag $TAG $(git rev-parse HEAD)
  assert $TAG^{commit} = HEAD and its subject is 'chore: release $TAG'
  git push origin $BRANCH
  git push origin refs/tags/$TAG
  gh run watch <$PUBLISH_WORKFLOW run for $TAG> --exit-status
  npm view $PKG_NAME@$VERSION version + SLSA provenance, gh release view $TAG
  upload $LOG_DIR/audit.sarif to code scanning
EOF
}

main() {
    parse_args "$@"
    cd "$REPO_ROOT"
    TAG="v$VERSION"
    LOG_DIR="${TMPDIR:-/tmp}"
    LOG_DIR="${LOG_DIR%/}/ai-toolkit-release-$VERSION"
    mkdir -p "$LOG_DIR"
    printf 'ai-toolkit release %s (%s), logs in %s\n' "$TAG" "$MODE" "$LOG_DIR"

    require_tools
    if [ "$MODE" != "gates-only" ]; then
        check_preconditions
        check_version_and_notes
    fi
    run_host_gates
    run_linux_gates
    run_build_and_smoke
    case "$MODE" in
        release)
            tag_and_push
            watch_publish
            printf '\nReleased %s. Next: kb/procedures/sop-release-verification.md\n' "$TAG"
            ;;
        dry-run) print_remaining_steps ;;
        gates-only) printf '\nAll gates passed on the working tree. Nothing was tagged.\n' ;;
    esac
}

main "$@"
