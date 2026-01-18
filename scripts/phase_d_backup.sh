#!/usr/bin/env bash
set -euo pipefail

# PHASE D.1 — AUTHORITATIVE BACKUP
# Backs up ONLY production components, no development artifacts

BACKUP_ROOT="/tmp/ransomeye_phase_d_backup_$(date +%Y%m%d_%H%M%S)"
BACKUP_MANIFEST="${BACKUP_ROOT}/BACKUP_MANIFEST.txt"

echo "=== PHASE D.1 — CREATING AUTHORITATIVE BACKUP ==="
echo "Backup location: ${BACKUP_ROOT}"
echo

mkdir -p "${BACKUP_ROOT}"

# Backup manifest header
cat > "${BACKUP_MANIFEST}" <<EOF
RANSOMEYE PHASE D BACKUP
Created: $(date -Iseconds)
Hostname: $(hostname)
User: $(whoami)

SCOPE: Production components only
- Core installation
- Agent installation
- Systemd units
- Configuration
- Database
EXCLUDED: CI, docs, tests, temp artifacts
================================================================================

EOF

# Function to backup with verification
backup_component() {
    local name="$1"
    local source="$2"
    local dest="${BACKUP_ROOT}/${name}"
    
    echo "[BACKUP] ${name}: ${source}"
    
    if [[ -d "$source" ]]; then
        mkdir -p "$(dirname "$dest")"
        cp -a "$source" "$dest"
        echo "✅ ${name}: $(du -sh "$dest" | cut -f1)" >> "${BACKUP_MANIFEST}"
    elif [[ -f "$source" ]]; then
        mkdir -p "$(dirname "$dest")"
        cp -a "$source" "$dest"
        echo "✅ ${name}: $(ls -lh "$dest" | awk '{print $5}')" >> "${BACKUP_MANIFEST}"
    else
        echo "⚠️  ${name}: NOT FOUND (${source})" >> "${BACKUP_MANIFEST}"
        echo "   WARNING: ${source} not found (may not be installed)"
    fi
}

# D.1.1 — Core installation
if [[ -d /opt/ransomeye ]]; then
    echo "Backing up: /opt/ransomeye/"
    mkdir -p "${BACKUP_ROOT}/opt"
    cp -a /opt/ransomeye "${BACKUP_ROOT}/opt/"
    echo "✅ /opt/ransomeye: $(du -sh "${BACKUP_ROOT}/opt/ransomeye" | cut -f1)" >> "${BACKUP_MANIFEST}"
else
    echo "⚠️  /opt/ransomeye: NOT FOUND" >> "${BACKUP_MANIFEST}"
fi

# D.1.2 — Agent installation
if [[ -d /opt/ransomeye-agent ]]; then
    echo "Backing up: /opt/ransomeye-agent/"
    mkdir -p "${BACKUP_ROOT}/opt"
    cp -a /opt/ransomeye-agent "${BACKUP_ROOT}/opt/"
    echo "✅ /opt/ransomeye-agent: $(du -sh "${BACKUP_ROOT}/opt/ransomeye-agent" | cut -f1)" >> "${BACKUP_MANIFEST}"
else
    echo "⚠️  /opt/ransomeye-agent: NOT FOUND" >> "${BACKUP_MANIFEST}"
fi

# D.1.3 — Systemd units
echo "Backing up: systemd units"
mkdir -p "${BACKUP_ROOT}/etc/systemd/system"

for unit in /etc/systemd/system/ransomeye*; do
    if [[ -e "$unit" ]]; then
        cp -a "$unit" "${BACKUP_ROOT}/etc/systemd/system/"
        echo "✅ $(basename "$unit")" >> "${BACKUP_MANIFEST}"
    fi
done

# D.1.4 — Configuration (if separate from /opt)
if [[ -d /etc/ransomeye ]]; then
    echo "Backing up: /etc/ransomeye/"
    mkdir -p "${BACKUP_ROOT}/etc"
    cp -a /etc/ransomeye "${BACKUP_ROOT}/etc/"
    echo "✅ /etc/ransomeye: $(du -sh "${BACKUP_ROOT}/etc/ransomeye" | cut -f1)" >> "${BACKUP_MANIFEST}"
fi

# D.1.5 — PostgreSQL database
echo "Backing up: PostgreSQL database"
mkdir -p "${BACKUP_ROOT}/database"

DB_BACKUP="${BACKUP_ROOT}/database/ransomeye_$(date +%Y%m%d_%H%M%S).sql"

if command -v sudo &> /dev/null && id -u postgres &> /dev/null; then
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ransomeye; then
        sudo -u postgres pg_dump ransomeye > "${DB_BACKUP}"
        echo "✅ PostgreSQL dump: $(du -sh "${DB_BACKUP}" | cut -f1)" >> "${BACKUP_MANIFEST}"
        
        # Also backup schema only for reference
        sudo -u postgres pg_dump --schema-only ransomeye > "${BACKUP_ROOT}/database/schema_only.sql"
        echo "✅ Schema dump: $(du -sh "${BACKUP_ROOT}/database/schema_only.sql" | cut -f1)" >> "${BACKUP_MANIFEST}"
    else
        echo "⚠️  PostgreSQL: database 'ransomeye' not found" >> "${BACKUP_MANIFEST}"
    fi
else
    echo "⚠️  PostgreSQL: cannot access (sudo or postgres user unavailable)" >> "${BACKUP_MANIFEST}"
fi

# D.1.6 — System state snapshot
echo "Capturing: system state"
mkdir -p "${BACKUP_ROOT}/system_state"

# Service status
systemctl list-units 'ransomeye*' --all --no-pager > "${BACKUP_ROOT}/system_state/services.txt" 2>&1 || true

# Process list
ps aux | grep -E '(ransomeye|correlation|ingest|policy|ai-core)' | grep -v grep > "${BACKUP_ROOT}/system_state/processes.txt" || true

# Users and groups
getent passwd ransomeye > "${BACKUP_ROOT}/system_state/users.txt" 2>&1 || echo "No ransomeye user" > "${BACKUP_ROOT}/system_state/users.txt"
getent group ransomeye > "${BACKUP_ROOT}/system_state/groups.txt" 2>&1 || echo "No ransomeye group" > "${BACKUP_ROOT}/system_state/groups.txt"

echo "✅ System state snapshot" >> "${BACKUP_MANIFEST}"

# D.1.7 — Create compressed archive
echo
echo "Creating compressed archive..."
ARCHIVE_NAME="ransomeye_phase_d_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
ARCHIVE_PATH="/tmp/${ARCHIVE_NAME}"

tar -czf "${ARCHIVE_PATH}" -C "$(dirname "${BACKUP_ROOT}")" "$(basename "${BACKUP_ROOT}")"

echo
echo "=== BACKUP COMPLETE ==="
echo "Archive: ${ARCHIVE_PATH}"
echo "Size: $(du -sh "${ARCHIVE_PATH}" | cut -f1)"
echo "SHA256: $(sha256sum "${ARCHIVE_PATH}" | cut -d' ' -f1)"
echo
echo "Manifest:"
cat "${BACKUP_MANIFEST}"
echo
echo "Archive can be extracted with:"
echo "  tar -xzf ${ARCHIVE_PATH} -C /tmp/"
echo
