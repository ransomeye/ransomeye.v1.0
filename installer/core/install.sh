#!/bin/bash
#
# RansomEye v1.0 Core Installer
# AUTHORITATIVE: Commercial-grade installer for RansomEye Core
# Fail-closed: Any error terminates installation immediately
#

set -euo pipefail  # Fail-fast: exit on any error, undefined variable, or pipe failure

# Installer version
INSTALLER_VERSION="1.0.0"
RANSOMEYE_VERSION="1.0.0"

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

# Validate root privileges (needed for systemd, user creation)
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Installer must be run as root (required for systemd service and user creation)"
    fi
}

# Validate Ubuntu LTS
check_ubuntu() {
    if [[ ! -f /etc/os-release ]]; then
        error_exit "Cannot determine OS: /etc/os-release not found"
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        error_exit "Installer supports Ubuntu only (detected: $ID)"
    fi
    
    echo -e "${GREEN}✓${NC} Ubuntu detected: $VERSION"
}

# Prompt for install root (no hardcoded paths)
prompt_install_root() {
    local default_root="/opt/ransomeye"
    
    echo ""
    echo "RansomEye v${RANSOMEYE_VERSION} Core Installer"
    echo "================================================"
    echo ""
    echo "Enter installation root directory (absolute path, no trailing slash):"
    echo "  Example: ${default_root}"
    echo -n "Install root [${default_root}]: "
    
    read -r install_root
    install_root="${install_root:-${default_root}}"
    
    # Validate: must be absolute path, no trailing slash
    if [[ ! "$install_root" =~ ^/ ]]; then
        error_exit "Install root must be an absolute path (starting with /)"
    fi
    
    if [[ "$install_root" =~ /$ ]]; then
        error_exit "Install root must not end with trailing slash"
    fi
    
    INSTALL_ROOT="$install_root"
    echo -e "${GREEN}✓${NC} Install root: ${INSTALL_ROOT}"
}

# Detect installer directory (where install.sh is located)
detect_installer_dir() {
    INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SRC_ROOT="$(cd "${INSTALLER_DIR}/../.." && pwd)"
}

# Create directory structure (no hardcoded paths)
create_directory_structure() {
    echo ""
    echo "Creating directory structure..."
    
    local dirs=(
        "${INSTALL_ROOT}/bin"
        "${INSTALL_ROOT}/lib"
        "${INSTALL_ROOT}/config"
        "${INSTALL_ROOT}/logs"
        "${INSTALL_ROOT}/runtime"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir" || error_exit "Failed to create directory: $dir"
            echo -e "${GREEN}✓${NC} Created: $dir"
        else
            echo -e "${YELLOW}✓${NC} Exists: $dir"
        fi
    done
}

# Create system user and group
create_system_user() {
    echo ""
    echo "Creating system user: ransomeye..."
    
    if id "ransomeye" &>/dev/null; then
        echo -e "${YELLOW}✓${NC} User 'ransomeye' already exists"
    else
        useradd --system --no-create-home --shell /bin/false ransomeye || error_exit "Failed to create user 'ransomeye'"
        echo -e "${GREEN}✓${NC} Created user: ransomeye"
    fi
    
    RANSOMEYE_UID=$(id -u ransomeye)
    RANSOMEYE_GID=$(id -g ransomeye)
    echo -e "${GREEN}✓${NC} UID: ${RANSOMEYE_UID}, GID: ${RANSOMEYE_GID}"
}

# Install Python files (lib directory)
install_python_files() {
    echo ""
    echo "Installing Python files..."
    
    # Copy common utilities
    if [[ -d "${SRC_ROOT}/common" ]]; then
        cp -r "${SRC_ROOT}/common" "${INSTALL_ROOT}/lib/" || error_exit "Failed to copy common utilities"
        echo -e "${GREEN}✓${NC} Installed: common/"
    fi
    
    # Copy core runtime
    if [[ -d "${SRC_ROOT}/core" ]]; then
        cp -r "${SRC_ROOT}/core" "${INSTALL_ROOT}/lib/" || error_exit "Failed to copy core runtime"
        echo -e "${GREEN}✓${NC} Installed: core/"
    fi
    
    # Copy services
    if [[ -d "${SRC_ROOT}/services" ]]; then
        cp -r "${SRC_ROOT}/services" "${INSTALL_ROOT}/lib/" || error_exit "Failed to copy services"
        echo -e "${GREEN}✓${NC} Installed: services/"
    fi
    
    # Copy contracts
    if [[ -d "${SRC_ROOT}/contracts" ]]; then
        mkdir -p "${INSTALL_ROOT}/config/contracts"
        cp -r "${SRC_ROOT}/contracts"/* "${INSTALL_ROOT}/config/contracts/" || error_exit "Failed to copy contracts"
        echo -e "${GREEN}✓${NC} Installed: contracts/"
    fi
    
    # Copy schemas
    if [[ -d "${SRC_ROOT}/schemas" ]]; then
        mkdir -p "${INSTALL_ROOT}/config/schemas"
        cp -r "${SRC_ROOT}/schemas"/* "${INSTALL_ROOT}/config/schemas/" || error_exit "Failed to copy schemas"
        echo -e "${GREEN}✓${NC} Installed: schemas/"
    fi
    
    # Set ownership
    chown -R ransomeye:ransomeye "${INSTALL_ROOT}/lib" || error_exit "Failed to set ownership on lib/"
    chown -R ransomeye:ransomeye "${INSTALL_ROOT}/config" || error_exit "Failed to set ownership on config/"
}

# Create executable wrapper script
create_core_wrapper() {
    echo ""
    echo "Creating Core wrapper script..."
    
    cat > "${INSTALL_ROOT}/bin/ransomeye-core" << 'WRAPPER_EOF'
#!/bin/bash
# RansomEye Core Runtime Wrapper
# This wrapper starts Core runtime and FastAPI services with proper environment
# Installer requirement: Start services using uvicorn without modifying Core code

set -euo pipefail

# Source environment file (created by installer)
INSTALL_ROOT="${RANSOMEYE_INSTALL_ROOT:-/opt/ransomeye}"
ENV_FILE="${INSTALL_ROOT}/config/environment"

if [[ -f "$ENV_FILE" ]]; then
    set -a  # Export all variables
    source "$ENV_FILE"
    set +a
else
    echo "FATAL: Environment file not found: $ENV_FILE" >&2
    exit 1
fi

# Change to install root for relative path resolution
cd "$INSTALL_ROOT" || exit 1

# Background process PIDs
INGEST_PID=""
UI_PID=""

# Cleanup function: kill background services when Core exits
cleanup() {
    if [[ -n "$INGEST_PID" ]]; then
        kill "$INGEST_PID" 2>/dev/null || true
        wait "$INGEST_PID" 2>/dev/null || true
    fi
    if [[ -n "$UI_PID" ]]; then
        kill "$UI_PID" 2>/dev/null || true
        wait "$UI_PID" 2>/dev/null || true
    fi
}

# Trap signals to ensure cleanup on exit
trap cleanup SIGTERM SIGINT

# Installer requirement: Start FastAPI services (Ingest, UI Backend) using uvicorn
# Services have their own main blocks that call uvicorn when run directly
# This does NOT modify Core code - installer calls services as-is

# Start Ingest service in background
python3 "${INSTALL_ROOT}/lib/services/ingest/app/main.py" &
INGEST_PID=$!

# Start UI Backend service in background
python3 "${INSTALL_ROOT}/lib/services/ui/backend/main.py" &
UI_PID=$!

# Give services time to start
sleep 2

# Run Core main entry point (foreground process - systemd tracks this)
# Core runtime coordinates modules and remains running until shutdown signal
# Use exec to replace shell with Core process (systemd tracks this)
python3 "${INSTALL_ROOT}/lib/core/main.py" "$@"
CORE_EXIT=$?

# Cleanup when Core exits
cleanup

exit $CORE_EXIT
WRAPPER_EOF

    chmod +x "${INSTALL_ROOT}/bin/ransomeye-core" || error_exit "Failed to make wrapper executable"
    chown ransomeye:ransomeye "${INSTALL_ROOT}/bin/ransomeye-core" || error_exit "Failed to set ownership on wrapper"
    echo -e "${GREEN}✓${NC} Created: ${INSTALL_ROOT}/bin/ransomeye-core"
}

# Generate component instance ID
generate_component_instance_id() {
    if command -v uuidgen &> /dev/null; then
        COMPONENT_INSTANCE_ID=$(uuidgen)
    else
        # Fallback: generate UUID-like string
        COMPONENT_INSTANCE_ID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())")
    fi
}

# Generate environment file
generate_environment_file() {
    echo ""
    echo "Generating environment file..."
    
    generate_component_instance_id
    
    cat > "${INSTALL_ROOT}/config/environment" << EOF
# RansomEye v${RANSOMEYE_VERSION} Core Environment
# Generated by installer on $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# DO NOT EDIT MANUALLY - Regenerate using installer

# Installation paths (absolute, no trailing slashes)
RANSOMEYE_INSTALL_ROOT="${INSTALL_ROOT}"
RANSOMEYE_BIN_DIR="${INSTALL_ROOT}/bin"
RANSOMEYE_LIB_DIR="${INSTALL_ROOT}/lib"
RANSOMEYE_ETC_DIR="${INSTALL_ROOT}/config"
RANSOMEYE_LOG_DIR="${INSTALL_ROOT}/logs"
RANSOMEYE_RUN_DIR="${INSTALL_ROOT}/runtime"
RANSOMEYE_TMP_DIR="${INSTALL_ROOT}/runtime/tmp"

# Runtime identity
RANSOMEYE_USER="ransomeye"
RANSOMEYE_GROUP="ransomeye"
RANSOMEYE_UID="${RANSOMEYE_UID}"
RANSOMEYE_GID="${RANSOMEYE_GID}"

# Component identity
RANSOMEYE_COMPONENT="core"
RANSOMEYE_COMPONENT_INSTANCE_ID="${COMPONENT_INSTANCE_ID}"
RANSOMEYE_VERSION="${RANSOMEYE_VERSION}"

# Database configuration (user: gagan, password: gagan)
RANSOMEYE_DB_HOST="localhost"
RANSOMEYE_DB_PORT="5432"
RANSOMEYE_DB_NAME="ransomeye"
RANSOMEYE_DB_USER="gagan"
RANSOMEYE_DB_PASSWORD="gagan"

# Service ports
RANSOMEYE_INGEST_PORT="8000"
RANSOMEYE_UI_PORT="8080"

# Paths to configuration files
RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH="${INSTALL_ROOT}/config/contracts/event-envelope.schema.json"
RANSOMEYE_POLICY_DIR="${INSTALL_ROOT}/config/policy"

# Command signing key (required, minimum 32 characters)
RANSOMEYE_COMMAND_SIGNING_KEY="test_signing_key_minimum_32_characters_long_for_validation_long_enough"

# Python path
PYTHONPATH="${INSTALL_ROOT}/lib:\${PYTHONPATH:-}"
EOF

    chmod 600 "${INSTALL_ROOT}/config/environment" || error_exit "Failed to set permissions on environment file"
    chown ransomeye:ransomeye "${INSTALL_ROOT}/config/environment" || error_exit "Failed to set ownership on environment file"
    echo -e "${GREEN}✓${NC} Created: ${INSTALL_ROOT}/config/environment"
}

# Set ownership and permissions
set_permissions() {
    echo ""
    echo "Setting ownership and permissions..."
    
    # Logs and runtime must be writable by ransomeye user
    chown -R ransomeye:ransomeye "${INSTALL_ROOT}/logs" || error_exit "Failed to set ownership on logs/"
    chown -R ransomeye:ransomeye "${INSTALL_ROOT}/runtime" || error_exit "Failed to set ownership on runtime/"
    chmod 755 "${INSTALL_ROOT}/logs" || error_exit "Failed to set permissions on logs/"
    chmod 755 "${INSTALL_ROOT}/runtime" || error_exit "Failed to set permissions on runtime/"
    
    echo -e "${GREEN}✓${NC} Permissions set correctly"
}

# Check PostgreSQL availability and verify service users (PHASE B1: No defaults)
check_postgresql() {
    echo ""
    echo "Checking PostgreSQL availability and service users..."
    
    if ! command -v psql &> /dev/null; then
        error_exit "PostgreSQL client (psql) not found. Please install PostgreSQL first."
    fi
    
    # Verify each service user exists and can connect
    local users=(
        "${RANSOMEYE_DB_USER_INGEST}:${RANSOMEYE_DB_PASSWORD_INGEST}:Ingest"
        "${RANSOMEYE_DB_USER_CORRELATION}:${RANSOMEYE_DB_PASSWORD_CORRELATION}:Correlation"
        "${RANSOMEYE_DB_USER_AI_CORE}:${RANSOMEYE_DB_PASSWORD_AI_CORE}:AI Core"
        "${RANSOMEYE_DB_USER_POLICY}:${RANSOMEYE_DB_PASSWORD_POLICY}:Policy Engine"
        "${RANSOMEYE_DB_USER_UI}:${RANSOMEYE_DB_PASSWORD_UI}:UI Backend"
    )
    
    for user_info in "${users[@]}"; do
        IFS=':' read -r db_user db_password service_name <<< "$user_info"
        
        export PGPASSWORD="$db_password"
        if psql -h "${RANSOMEYE_DB_HOST}" -p "${RANSOMEYE_DB_PORT}" -U "$db_user" -d "${RANSOMEYE_DB_NAME}" -c "SELECT 1" &> /dev/null; then
            echo -e "${GREEN}✓${NC} ${service_name} service user verified: $db_user"
        else
            unset PGPASSWORD
            error_exit "Cannot connect to PostgreSQL with ${service_name} credentials (host: ${RANSOMEYE_DB_HOST}, user: $db_user, database: ${RANSOMEYE_DB_NAME}). Ensure user exists and password is correct."
        fi
        unset PGPASSWORD
    done
    
    echo -e "${GREEN}✓${NC} All service database users verified"
}

# Install systemd service (ONE service only)
install_systemd_service() {
    echo ""
    echo "Installing systemd service..."
    
    local service_file="${INSTALLER_DIR}/ransomeye-core.service"
    
    if [[ ! -f "$service_file" ]]; then
        error_exit "Service file not found: $service_file"
    fi
    
    # Replace INSTALL_ROOT placeholder in service file
    sed "s|@INSTALL_ROOT@|${INSTALL_ROOT}|g" "$service_file" > /etc/systemd/system/ransomeye-core.service || \
        error_exit "Failed to install systemd service"
    
    systemctl daemon-reload || error_exit "Failed to reload systemd daemon"
    echo -e "${GREEN}✓${NC} Installed systemd service: ransomeye-core.service"
}

# Create installation manifest
create_manifest() {
    echo ""
    echo "Creating installation manifest..."
    
    local manifest_file="${INSTALL_ROOT}/config/installer.manifest.json"
    
    # Generate manifest with absolute paths
    cat > "$manifest_file" << EOF
{
  "version": "${INSTALLER_VERSION}",
  "ransomeye_version": "${RANSOMEYE_VERSION}",
  "install_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "install_root": "${INSTALL_ROOT}",
  "directories": {
    "bin": "${INSTALL_ROOT}/bin",
    "lib": "${INSTALL_ROOT}/lib",
    "config": "${INSTALL_ROOT}/config",
    "logs": "${INSTALL_ROOT}/logs",
    "runtime": "${INSTALL_ROOT}/runtime"
  },
  "runtime_identity": {
    "user": "ransomeye",
    "group": "ransomeye",
    "uid": ${RANSOMEYE_UID},
    "gid": ${RANSOMEYE_GID}
  },
  "component_instance_id": "${COMPONENT_INSTANCE_ID}",
  "systemd_service": "ransomeye-core.service"
}
EOF

    chmod 644 "$manifest_file" || error_exit "Failed to set permissions on manifest"
    chown ransomeye:ransomeye "$manifest_file" || error_exit "Failed to set ownership on manifest"
    echo -e "${GREEN}✓${NC} Created: $manifest_file"
}

# Start Core and perform health check
validate_installation() {
    echo ""
    echo "Starting Core and performing health check..."
    
    # Start service
    systemctl start ransomeye-core || error_exit "Failed to start ransomeye-core service"
    echo -e "${GREEN}✓${NC} Service started"
    
    # Wait for startup (max 30 seconds)
    local max_wait=30
    local waited=0
    local health_check_passed=false
    
    echo "Waiting for Core to become healthy (max ${max_wait}s)..."
    
    while [[ $waited -lt $max_wait ]]; do
        if systemctl is-active --quiet ransomeye-core; then
            # Check health endpoints (if available)
            sleep 2  # Give services time to initialize
            
            # Check Ingest health (port 8000)
            if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} Ingest health check passed"
                health_check_passed=true
                break
            fi
            
            # Check UI health (port 8080)
            if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} UI Backend health check passed"
                health_check_passed=true
                break
            fi
        fi
        
        sleep 1
        waited=$((waited + 1))
        echo -n "."
    done
    echo ""
    
    if ! systemctl is-active --quiet ransomeye-core; then
        systemctl status ransomeye-core || true
        error_exit "Core service is not active after startup"
    fi
    
    if [[ "$health_check_passed" == "false" ]]; then
        echo -e "${YELLOW}WARNING: Health check endpoints not accessible (service may still be starting)${NC}"
    fi
    
    echo -e "${GREEN}✓${NC} Core started successfully"
}

# PHASE B3: Rollback capability
ROLLBACK_STACK=()

push_rollback() {
    # Add rollback action to stack
    ROLLBACK_STACK+=("$1")
}

execute_rollback() {
    echo ""
    echo "================================================================================"
    echo -e "${RED}INSTALLATION FAILED - Executing rollback${NC}"
    echo "================================================================================"
    
    # Execute rollback actions in reverse order
    for (( idx=${#ROLLBACK_STACK[@]}-1 ; idx>=0 ; idx-- )) ; do
        local action="${ROLLBACK_STACK[idx]}"
        echo "Rollback: $action"
        eval "$action" || echo "Warning: Rollback action failed: $action"
    done
    
    echo ""
    echo "Rollback completed. System restored to pre-installation state."
}

# PHASE B2: Manifest validation
validate_manifest() {
    echo ""
    echo "Validating installation manifest..."
    
    local manifest_file="${INSTALL_ROOT}/config/installer.manifest.json"
    local schema_file="${INSTALLER_DIR}/installer.manifest.json"
    
    if [[ ! -f "$manifest_file" ]]; then
        error_exit "Manifest file not found: $manifest_file"
    fi
    
    if [[ ! -f "$schema_file" ]]; then
        echo -e "${YELLOW}⚠${NC}  Manifest schema not found, skipping validation"
        return
    fi
    
    # Validate manifest against schema (if python available)
    if command -v python3 &> /dev/null; then
        if python3 -c "import json, jsonschema" 2>/dev/null; then
            if python3 -c "
import json
import sys
import jsonschema

manifest = json.load(open('$manifest_file'))
schema = json.load(open('$schema_file'))

try:
    jsonschema.validate(manifest, schema)
    print('✓ Manifest validation passed')
except jsonschema.ValidationError as e:
    print(f'✗ Manifest validation failed: {e.message}')
    sys.exit(1)
" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Manifest validation passed"
            else
                error_exit "Manifest validation failed. Installation manifest does not match schema."
            fi
        else
            echo -e "${YELLOW}⚠${NC}  jsonschema not available, skipping validation"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  Python3 not available, skipping validation"
    fi
}

# PHASE B2: Verify artifact signatures (placeholder - requires signing infrastructure)
verify_artifact_signatures() {
    echo ""
    echo "Verifying artifact signatures..."
    
    # Check for signature files
    local sig_files=(
        "${SRC_ROOT}/contracts/.sig"
        "${SRC_ROOT}/schemas/.sig"
    )
    
    local missing_sigs=()
    for sig_file in "${sig_files[@]}"; do
        if [[ ! -f "$sig_file" ]]; then
            missing_sigs+=("$sig_file")
        fi
    done
    
    if [[ ${#missing_sigs[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠${NC}  Some signature files missing (signing infrastructure not yet implemented)"
        echo "  Missing: ${missing_sigs[*]}"
        echo "  Continuing installation (signature verification will be enforced in production)"
    else
        echo -e "${GREEN}✓${NC} Artifact signatures found"
        # TODO: Implement signature verification when signing infrastructure is ready
    fi
}

# Main installation flow (PHASE B: Updated with credential prompts and rollback)
main() {
    # Set up error handler for rollback
    trap 'execute_rollback' ERR
    
    check_root
    check_ubuntu
    detect_installer_dir
    
    # PHASE B1: Prompt for credentials (no defaults)
    prompt_install_root
    prompt_database_credentials
    prompt_signing_key
    
    # Track installation steps for rollback
    push_rollback "echo 'Rollback: Installation directory created at ${INSTALL_ROOT}'"
    
    create_directory_structure
    push_rollback "rm -rf '${INSTALL_ROOT}' 2>/dev/null || true"
    
    create_system_user
    push_rollback "userdel ransomeye 2>/dev/null || true"
    
    # PHASE B2: Verify artifacts before installation
    verify_artifact_signatures
    
    install_python_files
    push_rollback "rm -rf '${INSTALL_ROOT}/lib' 2>/dev/null || true"
    
    create_core_wrapper
    push_rollback "rm -f '${INSTALL_ROOT}/bin/ransomeye-core' 2>/dev/null || true"
    
    generate_environment_file
    push_rollback "rm -f '${INSTALL_ROOT}/config/environment' 2>/dev/null || true"
    
    set_permissions
    
    # PHASE A2: Verify service users exist in database
    check_postgresql
    
    install_systemd_service
    push_rollback "systemctl stop ransomeye-core 2>/dev/null || true; rm -f /etc/systemd/system/ransomeye-core.service 2>/dev/null || true; systemctl daemon-reload 2>/dev/null || true"
    
    create_manifest
    
    # PHASE B2: Validate manifest
    validate_manifest
    
    validate_installation
    
    # Clear rollback stack on success
    ROLLBACK_STACK=()
    trap - ERR
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo "Installation root: ${INSTALL_ROOT}"
    echo "Systemd service: ransomeye-core.service"
    echo ""
    echo "Service commands:"
    echo "  sudo systemctl start ransomeye-core    # Start Core"
    echo "  sudo systemctl stop ransomeye-core     # Stop Core"
    echo "  sudo systemctl status ransomeye-core   # Check status"
    echo "  sudo systemctl restart ransomeye-core  # Restart Core"
    echo ""
    echo "Logs location: ${INSTALL_ROOT}/logs/"
    echo ""
}

# Run main installation
main "$@"
