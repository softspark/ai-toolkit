#!/usr/bin/env bats
# Tests for hipaa-validate scanner — fixture-driven positive/negative cases.
# Focuses on Python pattern tightening and cross-language isolation.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HIPAA_SCRIPT="$TOOLKIT_DIR/app/skills/hipaa-validate/scripts/hipaa_scan.py"

_mk_python_fixture() {
    local dir="$1"
    mkdir -p "$dir"
    cat > "$dir/pyproject.toml" <<'EOF'
[project]
name = "fixture"
EOF
}

setup() {
    FIXTURE="$(mktemp -d)"
    _mk_python_fixture "$FIXTURE"
}

teardown() {
    rm -rf "$FIXTURE"
}

_scan() {
    python3 "$HIPAA_SCRIPT" --mode compliance --output json "$FIXTURE"
}

# ── Cat 1: Python logger/pprint (merged pattern) ────────────────────────────

@test "cat1: logger.info with patient triggers HIGH" {
    cat > "$FIXTURE/app.py" <<'EOF'
import logging
logger = logging.getLogger("phi")
def handle(patient):
    logger.info(f"got patient {patient.ssn}")
EOF
    run _scan
    [ "$status" -eq 1 ]
    echo "$output" | grep -q '"category": 1'
    echo "$output" | grep -q 'PHI in Python logger'
}

@test "cat1: pprint.pprint with patient triggers HIGH" {
    cat > "$FIXTURE/dump.py" <<'EOF'
import pprint
def dump(patient):
    pprint.pprint(patient)  # leaks ssn + mrn
EOF
    run _scan
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'pprint'
}

@test "cat1: repr(patient) triggers WARN" {
    cat > "$FIXTURE/log.py" <<'EOF'
def log_patient(patient):
    print(repr(patient))
EOF
    run _scan
    echo "$output" | grep -q 'repr'
}

# ── Cat 3: TLS patterns (tightened anchors) ─────────────────────────────────

@test "cat3: ssl=False in connector call triggers HIGH" {
    cat > "$FIXTURE/db.py" <<'EOF'
# patient data layer
import asyncpg
async def connect():
    return await asyncpg.connect("postgres://h/patient_db", ssl=False)
EOF
    run _scan
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'SSL disabled in connector call'
}

@test "cat3: is_ssl_enabled=False does NOT trigger (false-positive guard)" {
    cat > "$FIXTURE/config.py" <<'EOF'
# patient config
is_ssl_enabled = False  # feature flag, not a connector arg
EOF
    run _scan
    if echo "$output" | grep -q 'SSL disabled in connector call'; then
        echo "unexpected false positive: $output"
        false
    fi
}

@test "cat3: ssl.CERT_NONE triggers HIGH (anchored)" {
    cat > "$FIXTURE/http.py" <<'EOF'
import ssl
# patient fetch
ctx = ssl.create_default_context()
ctx.verify_mode = ssl.CERT_NONE
EOF
    run _scan
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'ssl.CERT_NONE'
}

@test "cat3: USE_CERT_NONE_MODE variable does NOT trigger" {
    cat > "$FIXTURE/flags.py" <<'EOF'
# patient flags
USE_CERT_NONE_MODE = True
EOF
    run _scan
    if echo "$output" | grep -q 'TLS certificate verification disabled'; then
        echo "unexpected false positive: $output"
        false
    fi
}

@test "cat3: SECURE_SSL_REDIRECT=False reports WARN (not HIGH)" {
    cat > "$FIXTURE/settings.py" <<'EOF'
# patient portal settings
SECURE_SSL_REDIRECT = False
EOF
    run _scan
    # WARN does not force exit 1 under --severity all unless HIGH present
    echo "$output" | grep -q '"severity": "WARN"'
    echo "$output" | grep -q 'SECURE_SSL_REDIRECT'
    # And it must NOT be HIGH
    if echo "$output" | grep -B1 'SECURE_SSL_REDIRECT' | grep -q '"severity": "HIGH"'; then
        echo "SECURE_SSL_REDIRECT wrongly HIGH: $output"
        false
    fi
}

# ── Cat 7: pickle / shelve ──────────────────────────────────────────────────

@test "cat7: pickle.dump of patient triggers HIGH" {
    cat > "$FIXTURE/cache.py" <<'EOF'
import pickle
def store(patient):
    with open("/tmp/p", "wb") as f:
        pickle.dump(patient, f)
EOF
    run _scan
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'pickle'
}

# ── Cross-language isolation ────────────────────────────────────────────────

@test "python logger pattern does NOT fire on .java file" {
    # Simulate mixed project
    cat > "$FIXTURE/pom.xml" <<'EOF'
<project><modelVersion>4.0.0</modelVersion></project>
EOF
    cat > "$FIXTURE/Svc.java" <<'EOF'
// patient service
import org.slf4j.Logger;
class Svc {
    Logger logger;
    void go(Patient patient) { logger.info("ssn " + patient); }
}
EOF
    run _scan
    # Java pattern fires (HIGH) — but we must see only ONE finding for this line,
    # not a duplicate tagged Python.
    local py_hits
    py_hits=$(echo "$output" | grep -c 'PHI in Python logger' || true)
    [ "$py_hits" -eq 0 ]
}

# ── Cat 5: DRF AllowAny ─────────────────────────────────────────────────────

@test "cat5: permission_classes=AllowAny triggers WARN" {
    cat > "$FIXTURE/views.py" <<'EOF'
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
# patient viewset
class PatientView(APIView):
    permission_classes = [AllowAny]
    def get(self, request): pass
EOF
    run _scan
    echo "$output" | grep -q 'AllowAny'
}
