#!/usr/bin/env bats
# Tests for /review diff-analyzer hardening — category ordering, secret
# false-positive guard, and rename parsing in `git diff --numstat -z`.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
DA_SCRIPT="$TOOLKIT_DIR/app/skills/review/scripts/diff-analyzer.py"

_load_da() {
    # The module file has a hyphen, so we use importlib.
    python3 - <<'PY' "$DA_SCRIPT" "$@"
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("da", sys.argv[1])
da = importlib.util.module_from_spec(spec)
spec.loader.exec_module(da)
# remaining argv is the test payload — pass into globals
if len(sys.argv) > 2:
    exec(sys.argv[2], {"da": da})
PY
}

@test "categorize prefers docs over security for docs/role-permissions.md" {
    run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('da', '$DA_SCRIPT')
da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)
assert da.categorize('docs/role-permissions.md') == 'docs', da.categorize('docs/role-permissions.md')
assert da.categorize('src/roles_and_responsibilities.md') == 'docs'
assert da.categorize('tests/test_auth.py') == 'test'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *OK* ]]
}

@test "secret scan does not flag unquoted identifiers without assignment value" {
    run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('da', '$DA_SCRIPT')
da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)
diff = '''diff --git a/src/api.py b/src/api.py
--- a/src/api.py
+++ b/src/api.py
@@ -1,2 +1,4 @@
 context
+request_token = generate_token_v2_legacy()
+password_policy = build_policy()
+legit_var = other_value
'''
findings = da._scan_secrets(diff)
# Calls to functions (no quoted literal, no long alphanumeric RHS) must NOT match.
assert findings == [], findings
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *OK* ]]
}

@test "secret scan flags quoted secrets and unquoted env-style with file+line tracking" {
    run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('da', '$DA_SCRIPT')
da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)
diff = '''diff --git a/src/settings.py b/src/settings.py
--- a/src/settings.py
+++ b/src/settings.py
@@ -1,1 +10,4 @@
 existing
+API_KEY=abcdefghijklmnop
+password = \"supersecretvalue123\"
+benign = 42
'''
findings = da._scan_secrets(diff)
assert len(findings) == 2, findings
assert findings[0]['file'] == 'src/settings.py'
assert findings[0]['line'] == 11  # first added line after hunk start 10 + context
assert findings[1]['line'] == 12
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *OK* ]]
}

@test "numstat-z parser extracts new path from rename record" {
    run python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('da', '$DA_SCRIPT')
da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)
# numstat -z rename layout: 'adds\tdels\t' NUL old_path NUL new_path NUL
raw = '5\t3\t\x00old/path.py\x00new/path.py\x00'
recs = da._parse_numstat_z(raw)
assert recs == [(5, 3, 'new/path.py')], recs
# Mixed: normal entry + rename entry
raw2 = '10\t2\tsrc/a.py\x004\t1\t\x00old/b.py\x00new/b.py\x00'
recs2 = da._parse_numstat_z(raw2)
assert recs2 == [(10, 2, 'src/a.py'), (4, 1, 'new/b.py')], recs2
# Binary files produce '-' counts
raw3 = '-\t-\tbin/file.bin\x00'
recs3 = da._parse_numstat_z(raw3)
assert recs3 == [(0, 0, 'bin/file.bin')], recs3
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *OK* ]]
}
