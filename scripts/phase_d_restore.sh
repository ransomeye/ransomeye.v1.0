#!/usr/bin/env bash
set -euo pipefail

# PHASE D.4 — DISASTER RECOVERY RESTORE
# Restores RansomEye from Phase D.1 backup with integrity verification

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup_directory>"
    echo "Example: $0 /tmp/ransomeye_phase_d_backup_20260118_144910"
    exit 1
fi

BACKUP_DIR="$1"
ARCHIVE_PATH="/tmp/$(basename "${BACKUP_DIR}").tar.gz"

echo "=== PHASE D.4 — DISASTER RECOVERY RESTORE ==="
echo "Backup directory: ${BACKUP_DIR}"
echo "Archive path: ${ARCHIVE_PATH}"
echo

# D.4.1 — Locate and verify archive
if [[ ! -f "${ARCHIVE_PATH}" ]]; then
    # Try to find archive in /tmp
    ARCHIVE_PATH=$(find /tmp -name "ransomeye_phase_d_backup_*.tar.gz" -type f | head -1)
    if [[ -z "${ARCHIVE_PATH}" ]] || [[ ! -f "${ARCHIVE_PATH}" ]]; then
        echo "❌ ERROR: Backup archive not found"
        echo "   Expected: ${ARCHIVE_PATH}"
        exit 1
    fi
fi

echo "[VERIFY] Checking archive integrity..."
ARCHIVE_SHA256=$(sha256sum "${ARCHIVE_PATH}" | cut -d' ' -f1)
echo "   Archive SHA256: ${ARCHIVE_SHA256}"

# Expected checksum from Phase D.1
EXPECTED_SHA256="664ce5dd13c05336949cf80158553cecf29f0d0f99631127a00a8f937642fb49"

if [[ "${ARCHIVE_SHA256}" != "${EXPECTED_SHA256}" ]]; then
    echo "❌ ERROR: Checksum mismatch"
    echo "   Expected: ${EXPECTED_SHA256}"
    echo "   Got:      ${ARCHIVE_SHA256}"
    echo "   BACKUP INTEGRITY COMPROMISED - RESTORE ABORTED"
    exit 1
fi

echo "✅ Archive checksum verified"
echo

# D.4.2 — Extract backup
EXTRACT_DIR="/tmp/ransomeye_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${EXTRACT_DIR}"

echo "[EXTRACT] Extracting backup archive..."
tar -xzf "${ARCHIVE_PATH}" -C "${EXTRACT_DIR}"

# Find extracted backup directory
RESTORE_ROOT=$(find "${EXTRACT_DIR}" -type d -name "ransomeye_phase_d_backup_*" | head -1)
if [[ -z "${RESTORE_ROOT}" ]]; then
    echo "❌ ERROR: Backup directory structure not found in archive"
    exit 1
fi

echo "✅ Backup extracted: ${RESTORE_ROOT}"
echo

# D.4.3 — Verify manifest
MANIFEST="${RESTORE_ROOT}/BACKUP_MANIFEST.txt"
if [[ ! -f "${MANIFEST}" ]]; then
    echo "❌ ERROR: Backup manifest not found"
    exit 1
fi

echo "[VERIFY] Backup manifest:"
cat "${MANIFEST}"
echo

# D.4.4 — Restore files
echo "[RESTORE] Restoring installation directories..."

if [[ -d "${RESTORE_ROOT}/opt/ransomeye" ]]; then
    echo "  Restoring: /opt/ransomeye"
    sudo mkdir -p /opt
    sudo cp -a "${RESTORE_ROOT}/opt/ransomeye" /opt/
    echo "  ✅ /opt/ransomeye restored"
else
    echo "  ⚠️  /opt/ransomeye not in backup"
fi

if [[ -d "${RESTORE_ROOT}/opt/ransomeye-agent" ]]; then
    echo "  Restoring: /opt/ransomeye-agent"
    sudo mkdir -p /opt
    sudo cp -a "${RESTORE_ROOT}/opt/ransomeye-agent" /opt/
    echo "  ✅ /opt/ransomeye-agent restored"
else
    echo "  ⚠️  /opt/ransomeye-agent not in backup"
fi

if [[ -d "${RESTORE_ROOT}/etc/ransomeye" ]]; then
    echo "  Restoring: /etc/ransomeye"
    sudo mkdir -p /etc
    sudo cp -a "${RESTORE_ROOT}/etc/ransomeye" /etc/
    echo "  ✅ /etc/ransomeye restored"
fi

echo

# D.4.5 — Restore systemd units
echo "[RESTORE] Restoring systemd units..."

if [[ -d "${RESTORE_ROOT}/etc/systemd/system" ]]; then
    sudo mkdir -p /etc/systemd/system
    
    for unit in "${RESTORE_ROOT}/etc/systemd/system/ransomeye"*; do
        if [[ -f "$unit" ]]; then
            unit_name=$(basename "$unit")
            echo "  Restoring: ${unit_name}"
            sudo cp -a "$unit" /etc/systemd/system/
        fi
    done
    
    echo "  ✅ Systemd units restored"
else
    echo "  ⚠️  Systemd units not in backup"
fi

echo

# D.4.6 — Restore database
echo "[RESTORE] Restoring PostgreSQL database..."

DB_DUMP=$(find "${RESTORE_ROOT}/database" -name "*.sql" -not -name "schema_only.sql" | head -1)

if [[ -n "${DB_DUMP}" ]] && [[ -f "${DB_DUMP}" ]]; then
    echo "  Database dump found: $(basename "${DB_DUMP}")"
    
    # Check if database exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ransomeye; then
        echo "  ⚠️  Database 'ransomeye' already exists"
        read -p "  Drop and recreate? [y/N]: " drop_db
        if [[ "$drop_db" == "y" || "$drop_db" == "Y" ]]; then
            sudo -u postgres dropdb ransomeye 2>/dev/null || true
        else
            echo "  ⚠️  Database restore skipped (exists)"
            echo "  ✅ Database restore skipped"
        fi
    fi
    
    if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ransomeye; then
        # Extract DB credentials from environment if available
        if [[ -f /opt/ransomeye/config/environment ]]; then
            source /opt/ransomeye/config/environment
            if [[ -n "${RANSOMEYE_DB_USER:-}" ]]; then
                sudo -u postgres createuser "${RANSOMEYE_DB_USER}" 2>/dev/null || true
                sudo -u postgres createdb -O "${RANSOMEYE_DB_USER}" ransomeye 2>/dev/null || true
            fi
        fi
        
        if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ransomeye; then
            echo "  Restoring database..."
            sudo -u postgres psql ransomeye < "${DB_DUMP}" || {
                echo "  ❌ Database restore failed"
                exit 1
            }
            echo "  ✅ Database restored"
        else
            echo "  ⚠️  Cannot create database (manual restore required)"
        fi
    fi
else
    echo "  ⚠️  Database dump not found in backup"
fi

echo

# D.4.7 — Set ownership and permissions
echo "[PERMISSIONS] Setting ownership..."

if [[ -d /opt/ransomeye ]]; then
    sudo chown -R ransomeye:ransomeye /opt/ransomeye || true
    echo "  ✅ /opt/ransomeye ownership set"
fi

if [[ -d /opt/ransomeye-agent ]]; then
    sudo chown -R ransomeye-agent:ransomeye-agent /opt/ransomeye-agent || true
    echo "  ✅ /opt/ransomeye-agent ownership set"
fi

echo

# D.4.8 — Reload systemd
echo "[SYSTEMD] Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "  ✅ Systemd reloaded"
echo

# D.4.9 — Verify restore integrity
echo "[VERIFY] Verifying restore integrity..."

RESTORE_OK=true

if [[ ! -d /opt/ransomeye ]]; then
    echo "  ❌ /opt/ransomeye missing"
    RESTORE_OK=false
fi

if [[ ! -f /etc/systemd/system/ransomeye-core.target ]]; then
    echo "  ❌ Systemd units missing"
    RESTORE_OK=false
fi

if [[ "$RESTORE_OK" == "true" ]]; then
    echo "  ✅ Restore integrity verified"
else
    echo "  ❌ Restore integrity check failed"
    exit 1
fi

echo
echo "=== RESTORE COMPLETE ==="
echo
echo "Next steps:"
echo "  1. sudo systemctl daemon-reload"
echo "  2. sudo systemctl start ransomeye-core.target"
echo "  3. Verify services are active"
echo
