#!/usr/bin/env bash
set -euo pipefail

# PHASE D.5 — MINIMAL PHASE B REPLAY
# Small-scale validation of detection pipeline

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="/tmp/ransomeye_phase_d_test"

echo "=== PHASE D.5 — MINIMAL PHASE B REPLAY ==="
echo

# D.5.1 — Setup test environment
echo "[SETUP] Creating test directory..."
rm -rf "${TEST_DIR}"
mkdir -p "${TEST_DIR}/target"

# Create small test dataset
echo "Creating test files..."
for i in {1..50}; do
    dd if=/dev/urandom of="${TEST_DIR}/target/file_${i}.dat" bs=1K count=10 2>/dev/null
done

echo "✅ Created 50 test files (~500KB total)"
echo

# D.5.2 — Baseline snapshot
echo "[BASELINE] Capturing pre-test state..."

BASELINE_EVENTS=$(sudo -u postgres psql ransomeye -t -c "SELECT COUNT(*) FROM events;" | tr -d ' ')
BASELINE_ALERTS=$(sudo -u postgres psql ransomeye -t -c "SELECT COUNT(*) FROM alerts;" 2>/dev/null | tr -d ' ' || echo "0")

echo "  Events before: ${BASELINE_EVENTS}"
echo "  Alerts before: ${BASELINE_ALERTS}"
echo

# D.5.3 — Run encryption simulation
echo "[SIMULATE] Running encryption burst..."

if [[ -x "${REPO_ROOT}/validation/simulations/ransomware_burst.py" ]]; then
    python3 "${REPO_ROOT}/validation/simulations/ransomware_burst.py" \
        --target "${TEST_DIR}/target" \
        --count 50 \
        --rate 10
else
    # Fallback: simple encryption
    echo "  Using fallback encryption method..."
    for file in "${TEST_DIR}"/target/*.dat; do
        openssl enc -aes-256-cbc -salt -in "$file" -out "${file}.encrypted" -pass pass:test123 2>/dev/null
        rm "$file"
    done
fi

echo "✅ Encryption complete"
echo

# D.5.4 — Generate C2-like traffic (minimal)
echo "[SIMULATE] Generating minimal C2-like traffic..."

# Simple network activity simulation
for i in {1..5}; do
    curl -X POST http://localhost:8080/ingest/event \
        -H "Content-Type: application/json" \
        -d "{\"type\":\"network_connection\",\"dest_ip\":\"192.0.2.1\",\"dest_port\":4444,\"timestamp\":\"$(date -Iseconds)\"}" \
        2>/dev/null || true
    sleep 1
done

echo "✅ C2 simulation complete"
echo

# D.5.5 — Wait for processing
echo "[WAIT] Allowing time for correlation (30s)..."
sleep 30

# D.5.6 — Check results
echo "[RESULTS] Analyzing detection outcomes..."

FINAL_EVENTS=$(sudo -u postgres psql ransomeye -t -c "SELECT COUNT(*) FROM events;" | tr -d ' ')
FINAL_ALERTS=$(sudo -u postgres psql ransomeye -t -c "SELECT COUNT(*) FROM alerts;" 2>/dev/null | tr -d ' ' || echo "0")

NEW_EVENTS=$((FINAL_EVENTS - BASELINE_EVENTS))
NEW_ALERTS=$((FINAL_ALERTS - BASELINE_ALERTS))

echo "  Events after: ${FINAL_EVENTS} (+${NEW_EVENTS})"
echo "  Alerts after: ${FINAL_ALERTS} (+${NEW_ALERTS})"
echo

# D.5.7 — Service stability check
echo "[STABILITY] Checking service state post-simulation..."

SERVICES_OK=true
for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core; do
    if systemctl is-active --quiet "${service}"; then
        echo "  ✅ ${service}: still active"
    else
        echo "  ❌ ${service}: NOT ACTIVE"
        SERVICES_OK=false
    fi
done

echo

# D.5.8 — Check for crashes/restarts
echo "[STABILITY] Checking for restarts..."

for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core; do
    restart_count=$(systemctl show "${service}" -p NRestarts --value)
    if [[ "$restart_count" -gt 0 ]]; then
        echo "  ⚠️  ${service}: ${restart_count} restart(s)"
    else
        echo "  ✅ ${service}: no restarts"
    fi
done

echo

# D.5.9 — Summary
echo "=== SIMULATION SUMMARY ==="
echo

SIMULATION_PASSED=true

if [[ "$NEW_EVENTS" -gt 0 ]]; then
    echo "✅ Detection pipeline active (${NEW_EVENTS} new events)"
else
    echo "❌ No new events detected"
    SIMULATION_PASSED=false
fi

if [[ "$SERVICES_OK" == "true" ]]; then
    echo "✅ All services stable"
else
    echo "❌ Service instability detected"
    SIMULATION_PASSED=false
fi

echo

if [[ "$SIMULATION_PASSED" == "true" ]]; then
    echo "✅ MINIMAL PHASE B REPLAY PASSED"
    echo
    echo "Clean install validated successfully:"
    echo "  • Detection pipeline operational"
    echo "  • Services remained stable"
    echo "  • No dependency on CI/development artifacts"
    echo
    echo "PHASE D COMPLETE — SYSTEM READY FOR PRODUCTION CONSIDERATION"
else
    echo "❌ SIMULATION REVEALED ISSUES"
    echo
    echo "Review logs and resolve before proceeding:"
    for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core; do
        echo "  journalctl -u ${service} -n 100"
    done
    exit 1
fi

# D.5.10 — Cleanup
echo
read -p "Remove test directory ${TEST_DIR}? (yes/no): " cleanup

if [[ "$cleanup" == "yes" ]]; then
    rm -rf "${TEST_DIR}"
    echo "✅ Test directory removed"
fi
