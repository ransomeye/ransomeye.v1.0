#!/bin/bash
#
# RansomEye v1.0 Core Uninstaller
# AUTHORITATIVE: Commercial-grade uninstaller for RansomEye Core
# Fail-closed: Any error terminates uninstallation immediately
#

set -euo pipefail  # Fail-fast: exit on any error, undefined variable, or pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handler: fail-closed
error_exit() {
    echo -e "${RED}FATAL: ${1}${NC}" >&2
    exit 1
}

# Validate root privileges
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Uninstaller must be run as root (required for systemd service and file removal)"
    fi
}

# Detect installation root from manifest or prompt
detect_install_root() {
    # Try to find manifest in common locations
    local manifest_paths=(
        "/opt/ransomeye/config/installer.manifest.json"
        "/usr/local/ransomeye/config/installer.manifest.json"
    )
    
    INSTALL_ROOT=""
    
    for manifest_path in "${manifest_paths[@]}"; do
        if [[ -f "$manifest_path" ]]; then
            # Extract install_root from manifest (simple JSON parsing)
            INSTALL_ROOT=$(grep -o '"install_root"[[:space:]]*:[[:space:]]*"[^"]*"' "$manifest_path" | cut -d'"' -f4 || true)
            if [[ -n "$INSTALL_ROOT" ]]; then
                echo -e "${GREEN}✓${NC} Found installation at: ${INSTALL_ROOT}"
                return
            fi
        fi
    done
    
    # Prompt if not found
    echo ""
    echo "RansomEye v1.0 Core Uninstaller"
    echo "================================="
    echo ""
    echo "Installation manifest not found in common locations."
    echo "Enter installation root directory (absolute path, no trailing slash):"
    echo "  Example: /opt/ransomeye"
    echo -n "Install root: "
    
    read -r INSTALL_ROOT
    
    if [[ -z "$INSTALL_ROOT" ]]; then
        error_exit "Install root cannot be empty"
    fi
    
    # Validate: must be absolute path
    if [[ ! "$INSTALL_ROOT" =~ ^/ ]]; then
        error_exit "Install root must be an absolute path (starting with /)"
    fi
    
    if [[ ! -d "$INSTALL_ROOT" ]]; then
        error_exit "Installation directory does not exist: $INSTALL_ROOT"
    fi
    
    # Verify it's a RansomEye installation
    if [[ ! -f "${INSTALL_ROOT}/config/installer.manifest.json" ]]; then
        error_exit "Not a valid RansomEye installation: manifest not found at ${INSTALL_ROOT}/config/installer.manifest.json"
    fi
}

# Stop and remove systemd service
remove_systemd_service() {
    echo ""
    echo "Removing systemd service..."
    
    if systemctl list-unit-files --type=service | grep -q "^ransomeye-core.service"; then
        # Stop service if running
        if systemctl is-active --quiet ransomeye-core; then
            echo "Stopping ransomeye-core service..."
            systemctl stop ransomeye-core || error_exit "Failed to stop ransomeye-core service"
            echo -e "${GREEN}✓${NC} Service stopped"
        fi
        
        # Disable service
        systemctl disable ransomeye-core || error_exit "Failed to disable ransomeye-core service"
        echo -e "${GREEN}✓${NC} Service disabled"
        
        # Remove service file
        if [[ -f /etc/systemd/system/ransomeye-core.service ]]; then
            rm -f /etc/systemd/system/ransomeye-core.service || error_exit "Failed to remove systemd service file"
            echo -e "${GREEN}✓${NC} Service file removed"
        fi
        
        # Reload systemd
        systemctl daemon-reload || error_exit "Failed to reload systemd daemon"
        echo -e "${GREEN}✓${NC} Systemd daemon reloaded"
    else
        echo -e "${YELLOW}✓${NC} Service not found (may have been removed already)"
    fi
}

# Remove installation directory
remove_installation() {
    echo ""
    echo "Removing installation directory..."
    
    if [[ -d "$INSTALL_ROOT" ]]; then
        # Confirmation prompt
        echo ""
        echo "WARNING: This will permanently delete the installation directory:"
        echo "  ${INSTALL_ROOT}"
        echo ""
        echo "Logs and configuration will be lost."
        echo -n "Continue? [y/N]: "
        read -r confirm
        
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "Uninstallation cancelled."
            exit 0
        fi
        
        # Remove directory
        rm -rf "$INSTALL_ROOT" || error_exit "Failed to remove installation directory: $INSTALL_ROOT"
        echo -e "${GREEN}✓${NC} Removed: $INSTALL_ROOT"
    else
        echo -e "${YELLOW}✓${NC} Installation directory does not exist: $INSTALL_ROOT"
    fi
}

# Optional rollback of database schema (non-destructive to other databases)
rollback_database_schema() {
    echo ""
    echo "Database schema rollback (optional)..."
    
    local env_file="${INSTALL_ROOT}/config/environment"
    if [[ ! -f "$env_file" ]]; then
        echo -e "${YELLOW}✓${NC} Environment file not found; skipping schema rollback"
        return
    fi
    
    echo "This will rollback RansomEye schema migrations to base (schema objects removed)."
    echo -n "Rollback database schema? [y/N]: "
    read -r confirm_db
    if [[ "$confirm_db" != "y" && "$confirm_db" != "Y" ]]; then
        echo -e "${YELLOW}✓${NC} Database schema rollback skipped"
        return
    fi
    
    set -a
    source "$env_file"
    set +a
    
    local migrations_dir="${RANSOMEYE_SCHEMA_MIGRATIONS_DIR:-${INSTALL_ROOT}/config/schemas/migrations}"
    if [[ ! -d "$migrations_dir" ]]; then
        error_exit "Migrations directory not found: $migrations_dir"
    fi
    
    if ! PYTHONPATH="${INSTALL_ROOT}/lib" \
        RANSOMEYE_DB_HOST="${RANSOMEYE_DB_HOST}" \
        RANSOMEYE_DB_PORT="${RANSOMEYE_DB_PORT}" \
        RANSOMEYE_DB_NAME="${RANSOMEYE_DB_NAME}" \
        RANSOMEYE_DB_USER="${RANSOMEYE_DB_USER}" \
        RANSOMEYE_DB_PASSWORD="${RANSOMEYE_DB_PASSWORD}" \
        RANSOMEYE_SCHEMA_MIGRATIONS_DIR="${migrations_dir}" \
        python3 -m common.db.migration_runner downgrade --migrations-dir "${migrations_dir}" --target-version "0"; then
        error_exit "Database schema rollback failed"
    fi
    
    echo -e "${GREEN}✓${NC} Database schema rollback completed"
}
# Remove system user (optional, with confirmation)
remove_system_user() {
    echo ""
    echo "System user 'ransomeye' management..."
    
    if id "ransomeye" &>/dev/null; then
        echo "User 'ransomeye' exists."
        echo "NOTE: Removing system user may affect other installations or services."
        echo -n "Remove user 'ransomeye'? [y/N]: "
        read -r confirm_user
        
        if [[ "$confirm_user" == "y" || "$confirm_user" == "Y" ]]; then
            # Check if user is used by any other process
            if pgrep -u ransomeye > /dev/null 2>&1; then
                error_exit "Cannot remove user 'ransomeye': processes are still running as this user"
            fi
            
            userdel ransomeye || error_exit "Failed to remove user 'ransomeye'"
            echo -e "${GREEN}✓${NC} Removed user: ransomeye"
        else
            echo -e "${YELLOW}✓${NC} User 'ransomeye' kept (not removed)"
        fi
    else
        echo -e "${YELLOW}✓${NC} User 'ransomeye' does not exist"
    fi
}

# Main uninstallation flow
main() {
    check_root
    detect_install_root
    remove_systemd_service
    rollback_database_schema
    remove_installation
    remove_system_user
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Uninstallation completed successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo "RansomEye Core has been removed from this system."
    echo ""
    echo "NOTE: PostgreSQL database and roles were NOT removed."
    echo "      Schema rollback can be executed via the migration runner if needed."
    echo ""
}

# Run main uninstallation
main "$@"
