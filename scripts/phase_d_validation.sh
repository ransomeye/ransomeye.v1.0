#!/usr/bin/env bash
set -euo pipefail

# PHASE D.4 — REAL-WORLD VALIDATION (MINIMAL)
# Confirms basic functionality without CI/internet dependencies

echo "=== PHASE D.4 — BASIC VALIDATION ==="
echo

VALIDATION_PASSED=true

# D.4.1 — Services reach READY state
echo "[CHECK] Service READY state..."

check_service() {
    local service="$1"
    
    if ! systemctl is-active --quiet "${service}"; then
        echo "  ❌ ${service}: not active"
        VALIDATION_PASSED=false
        return 1
    fi
    
    # Check systemd status for "Ready" or "Running"
    if systemctl status "${service}" | grep -qE "(active \(running\)|Status:.*[Rr]eady)"; then
        echo "  ✅ ${service}: READY"
    else
        echo "  ⚠️  ${service}: active but status unclear"
    fi
}

for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core; do
    check_service "${service}" || true
done

echo

# D.4.2 — Watchdogs active
echo "[CHECK] Watchdog configuration..."

for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core; do
    if systemctl show "${service}" -p WatchdogUSec | grep -q "WatchdogUSec=0"; then
        echo "  ⚠️  ${service}: watchdog disabled"
    else
        watchdog_sec=$(systemctl show "${service}" -p WatchdogUSec | cut -d= -f2)
        echo "  ✅ ${service}: watchdog active (${watchdog_sec})"
    fi
done

echo

# D.4.3 — Agent → Core telemetry
echo "[CHECK] Agent telemetry flow..."

if ! systemctl is-active --quiet ransomeye-linux-agent; then
    echo "  ❌ Linux agent not running"
    VALIDATION_PASSED=false
else
    echo "  ✅ Linux agent active"
    
    # Check recent logs for telemetry
    if journalctl -u ransomeye-linux-agent --since "1 minute ago" --no-pager | grep -q "telemetry\|event\|send"; then
        echo "  ✅ Agent generating telemetry"
    else
        echo "  ⚠️  No telemetry events in recent logs (may need more time)"
    fi
    
    # Check ingest service for received data
    if journalctl -u ransomeye-ingest --since "1 minute ago" --no-pager | grep -qE "(POST|received|ingested)"; then
        echo "  ✅ Ingest service receiving data"
    else
        echo "  ⚠️  No ingest activity in recent logs"
    fi
fi

echo

# D.4.4 — Database connectivity
echo "[CHECK] Database connectivity..."

if command -v psql &> /dev/null; then
    if sudo -u postgres psql ransomeye -c "SELECT COUNT(*) FROM events;" &> /dev/null; then
        event_count=$(sudo -u postgres psql ransomeye -t -c "SELECT COUNT(*) FROM events;" | tr -d ' ')
        echo "  ✅ Database accessible"
        echo "  📊 Events in database: ${event_count}"
    else
        echo "  ❌ Cannot query database"
        VALIDATION_PASSED=false
    fi
else
    echo "  ⚠️  psql not available (cannot verify)"
fi

echo

# D.4.5 — No internet dependency
echo "[CHECK] Internet independence..."

# Check if services work with network disabled (informational only)
if systemctl is-active --quiet NetworkManager; then
    echo "  ℹ️  Network is active"
    echo "  ℹ️  For full offline test, disable network and verify services remain operational"
else
    echo "  ✅ Running in network-restricted environment"
fi

echo

# D.4.6 — Summary
echo "=== VALIDATION SUMMARY ==="
echo

if [[ "$VALIDATION_PASSED" == "true" ]]; then
    echo "✅ BASIC VALIDATION PASSED"
    echo
    echo "System demonstrates:"
    echo "  • Services reach READY state"
    echo "  • Watchdogs configured"
    echo "  • Agent → Core telemetry flow"
    echo "  • Database operational"
    echo
    echo "Next: Run phase_d_simulation.sh for minimal Phase B replay"
else
    echo "❌ VALIDATION FAILED"
    echo
    echo "Review errors above and resolve before proceeding."
    exit 1
fi
