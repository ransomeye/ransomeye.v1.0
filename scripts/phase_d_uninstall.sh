#!/usr/bin/env bash
set -euo pipefail

# PHASE D.2 — CLEAN REMOVAL
# Complete removal of all RansomEye components

echo "=== PHASE D.2 — CLEAN REMOVAL ==="
echo
echo "⚠️  WARNING: This will completely remove RansomEye from this system."
echo
read -p "Have you created a backup? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "Aborting. Please run phase_d_backup.sh first."
    exit 1
fi

echo
read -p "Type 'REMOVE' to proceed: " final_confirm

if [[ "$final_confirm" != "REMOVE" ]]; then
    echo "Aborting."
    exit 1
fi

echo
echo "Proceeding with removal..."
echo

# D.2.1 — Stop all services
echo "[STOP] Stopping all RansomEye services..."

for service in $(systemctl list-units 'ransomeye*' --all --no-legend | awk '{print $1}'); do
    echo "  Stopping: ${service}"
    sudo systemctl stop "${service}" || true
done

sleep 2

# D.2.2 — Disable all units
echo
echo "[DISABLE] Disabling all RansomEye systemd units..."

for unit in /etc/systemd/system/ransomeye*; do
    if [[ -e "$unit" ]]; then
        unit_name=$(basename "$unit")
        echo "  Disabling: ${unit_name}"
        sudo systemctl disable "${unit_name}" || true
    fi
done

# D.2.3 — Remove systemd units
echo
echo "[REMOVE] Removing systemd unit files..."

sudo rm -fv /etc/systemd/system/ransomeye*.service
sudo rm -fv /etc/systemd/system/ransomeye*.target
sudo rm -fv /etc/systemd/system/ransomeye*.timer

sudo systemctl daemon-reload

# D.2.4 — Remove binaries and installations
echo
echo "[REMOVE] Removing installation directories..."

if [[ -d /opt/ransomeye ]]; then
    echo "  Removing: /opt/ransomeye"
    sudo rm -rf /opt/ransomeye
fi

if [[ -d /opt/ransomeye-agent ]]; then
    echo "  Removing: /opt/ransomeye-agent"
    sudo rm -rf /opt/ransomeye-agent
fi

if [[ -d /etc/ransomeye ]]; then
    echo "  Removing: /etc/ransomeye"
    sudo rm -rf /etc/ransomeye
fi

# D.2.5 — Remove log directories (optional)
echo
read -p "Remove logs in /var/log/ransomeye*? (yes/no): " remove_logs

if [[ "$remove_logs" == "yes" ]]; then
    sudo rm -rf /var/log/ransomeye*
    echo "  Logs removed"
else
    echo "  Logs preserved"
fi

# D.2.6 — Drop database
echo
read -p "Drop PostgreSQL database 'ransomeye'? (yes/no): " drop_db

if [[ "$drop_db" == "yes" ]]; then
    if command -v sudo &> /dev/null && id -u postgres &> /dev/null; then
        echo "  Dropping database..."
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS ransomeye;" || true
        sudo -u postgres psql -c "DROP USER IF EXISTS ransomeye;" || true
        echo "  Database dropped"
    else
        echo "  ⚠️  Cannot access PostgreSQL (manual cleanup required)"
    fi
else
    echo "  Database preserved"
fi

# D.2.7 — Remove users and groups
echo
echo "[REMOVE] Removing system users and groups..."

if id ransomeye &> /dev/null; then
    echo "  Removing user: ransomeye"
    sudo userdel ransomeye || true
fi

if getent group ransomeye &> /dev/null; then
    echo "  Removing group: ransomeye"
    sudo groupdel ransomeye || true
fi

# D.2.8 — Verify clean state
echo
echo "=== VERIFICATION ==="
echo

echo "Systemd units:"
systemctl list-units 'ransomeye*' --all --no-pager || echo "  ✅ No ransomeye units found"

echo
echo "Installation directories:"
ls -ld /opt/ransomeye* 2>&1 || echo "  ✅ No /opt/ransomeye* directories"

echo
echo "Users/groups:"
id ransomeye 2>&1 || echo "  ✅ User 'ransomeye' removed"

echo
echo "PostgreSQL database:"
if command -v sudo &> /dev/null && id -u postgres &> /dev/null; then
    sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -w ransomeye && echo "  ⚠️  Database still exists" || echo "  ✅ Database removed"
else
    echo "  ⚠️  Cannot verify (manual check required)"
fi

echo
echo "=== REMOVAL COMPLETE ==="
echo "System is ready for clean installation."
echo
