#!/usr/bin/env bash
set -euo pipefail

# PHASE D.3 — CLEAN INSTALL
# Fresh installation: Core + Linux Agent (DPI deferred)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== PHASE D.3 — CLEAN INSTALL ==="
echo "Repository: ${REPO_ROOT}"
echo

# Verify clean state
echo "[VERIFY] Checking for existing installation..."

if systemctl list-units 'ransomeye*' --all --no-legend | grep -q ransomeye; then
    echo "❌ ERROR: RansomEye services still present."
    echo "   Run phase_d_uninstall.sh first."
    exit 1
fi

if [[ -d /opt/ransomeye ]] || [[ -d /opt/ransomeye-agent ]]; then
    echo "❌ ERROR: Installation directories still present."
    echo "   Run phase_d_uninstall.sh first."
    exit 1
fi

echo "✅ System is clean"
echo

# D.3.1 — Install Core
echo "[INSTALL] Core services (ingest, correlation, policy, ai-core)..."
echo

if [[ ! -x "${REPO_ROOT}/installer/core/install_core.sh" ]]; then
    echo "❌ ERROR: Core installer not found or not executable"
    exit 1
fi

"${REPO_ROOT}/installer/core/install_core.sh"

echo
echo "✅ Core installation complete"
echo

# D.3.2 — Install Linux Agent
echo "[INSTALL] Linux Agent..."
echo

if [[ ! -x "${REPO_ROOT}/installer/agent-linux/install_agent_linux.sh" ]]; then
    echo "❌ ERROR: Linux agent installer not found or not executable"
    exit 1
fi

"${REPO_ROOT}/installer/agent-linux/install_agent_linux.sh"

echo
echo "✅ Linux Agent installation complete"
echo

# D.3.3 — Verify installation
echo "=== INSTALLATION VERIFICATION ==="
echo

echo "Systemd units:"
systemctl list-units 'ransomeye*' --no-pager

echo
echo "Services status:"
for service in ransomeye-ingest ransomeye-correlation ransomeye-policy ransomeye-ai-core ransomeye-linux-agent; do
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        status=$(systemctl is-active "${service}" || echo "inactive")
        echo "  ${service}: ${status}"
    fi
done

echo
echo "Installation directories:"
ls -ld /opt/ransomeye* 2>/dev/null || echo "  ⚠️  No installation directories found"

echo
echo "=== INSTALLATION COMPLETE ==="
echo
echo "Next: Run phase_d_validation.sh for basic checks"
echo "Then: Run phase_d_simulation.sh for minimal Phase B replay"
echo
