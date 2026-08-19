#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/ai-toolkit-cve-scan.XXXXXX")"
    mkdir -p "$TEST_TMP/bin" "$TEST_TMP/project"
    printf '%s\n' '{"name":"fixture","dependencies":{"lodash":"4.17.20"}}' \
        > "$TEST_TMP/project/package.json"
    printf '%s\n' '{"lockfileVersion":3}' > "$TEST_TMP/project/package-lock.json"

    cat > "$TEST_TMP/bin/npm" <<'SH'
#!/bin/sh
cat <<'JSON'
{
  "advisories": {
    "100": {
      "module_name": "lodash",
      "severity": "high",
      "title": "Command Injection in lodash",
      "cves": ["CVE-2021-23337"],
      "url": "https://github.com/advisories/GHSA-35jh-r3h4-6jhm",
      "findings": [{"version": "4.17.20", "paths": ["lodash"]}],
      "patched_versions": ">=4.17.21",
      "recommendation": "Upgrade to version 4.17.21 or later"
    },
    "101": {
      "module_name": "lodash",
      "severity": "moderate",
      "title": "ReDoS in lodash",
      "cves": ["CVE-2020-28500"],
      "url": "https://github.com/advisories/GHSA-29mw-wpgm-hmr9",
      "findings": [{"version": "4.17.20", "paths": ["lodash"]}],
      "patched_versions": ">=4.17.21",
      "recommendation": "Upgrade to version 4.17.21 or later"
    }
  }
}
JSON
exit 1
SH
    chmod +x "$TEST_TMP/bin/npm"
}

teardown() {
    python3 - "$TEST_TMP" <<'PY'
import pathlib
import shutil
import sys

target = pathlib.Path(sys.argv[1]).resolve()
assert target.name.startswith("ai-toolkit-cve-scan."), target
assert str(target).startswith(
    ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
), target
shutil.rmtree(target)
PY
}

@test "cve-scan reports vulnerabilities from legacy npm audit advisories" {
    run env PATH="$TEST_TMP/bin:$PATH" python3 \
        "$TOOLKIT_DIR/app/skills/cve-scan/scripts/cve_scan.py" \
        "$TEST_TMP/project" --json

    [ "$status" -eq 1 ]
    SCAN_OUTPUT="$output" python3 - <<'PY'
import json
import os

report = json.loads(os.environ["SCAN_OUTPUT"])
assert report["total_findings"] == 2, report
assert [finding["severity"] for finding in report["findings"]] == ["HIGH", "MODERATE"]
assert report["findings"][0]["package"] == "lodash"
assert report["findings"][0]["installed"] == "4.17.20"
assert report["findings"][0]["cve"] == ["CVE-2021-23337"]
assert report["findings"][0]["fixed_in"] == ">=4.17.21"
PY
}
