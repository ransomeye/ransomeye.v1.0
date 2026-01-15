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

# Transaction framework
TRANSACTION_PY=""
INSTALL_STATE_FILE=""

init_transaction() {
    TRANSACTION_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")/../common" && pwd)/install_transaction.py"
    if [[ ! -f "$TRANSACTION_PY" ]]; then
        error_exit "Transaction framework not found: $TRANSACTION_PY"
    fi
    INSTALL_STATE_FILE="${INSTALL_ROOT}/.install_state.json"
    python3 "$TRANSACTION_PY" init --state-file "$INSTALL_STATE_FILE" --component "core"
}

record_step() {
    local action="$1"
    local rollback_action="$2"
    shift 2
    python3 "$TRANSACTION_PY" record --state-file "$INSTALL_STATE_FILE" \
        --action "$action" --rollback-action "$rollback_action" "$@"
}

run_rollback() {
    trap - ERR
    if [[ -n "${INSTALL_STATE_FILE}" && -f "${INSTALL_STATE_FILE}" ]]; then
        python3 "$TRANSACTION_PY" rollback --state-file "$INSTALL_STATE_FILE" || true
    fi
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

# Enforce empty install root for transactional install
ensure_clean_install_root() {
    if [[ -d "${INSTALL_ROOT}" ]] && [[ "$(ls -A "${INSTALL_ROOT}")" ]]; then
        error_exit "Install root must be empty for transactional install: ${INSTALL_ROOT}"
    fi
}

# Detect installer directory (where install.sh is located)
detect_installer_dir() {
    INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SRC_ROOT="$(cd "${INSTALLER_DIR}/../.." && pwd)"
}

# Preflight: enforce python3 availability and minimum version
preflight_python3() {
    local preflight_script="${INSTALLER_DIR}/../common/preflight_python3.sh"
    if [[ ! -f "$preflight_script" ]]; then
        error_exit "Python3 preflight script not found: $preflight_script"
    fi
    if ! bash "$preflight_script"; then
        error_exit "Python3 preflight failed"
    fi
}

# Create directory structure (no hardcoded paths)
create_directory_structure() {
    echo ""
    echo "Creating directory structure..."
    
    local dirs=(
        "${INSTALL_ROOT}"
        "${INSTALL_ROOT}/bin"
        "${INSTALL_ROOT}/lib"
        "${INSTALL_ROOT}/config"
        "${INSTALL_ROOT}/logs"
        "${INSTALL_ROOT}/runtime"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir" || error_exit "Failed to create directory: $dir"
            if [[ "$dir" == "${INSTALL_ROOT}" ]]; then
                init_transaction
                record_step "create_install_root" "remove_tree" --meta "path=${INSTALL_ROOT}" --rollback-meta "path=${INSTALL_ROOT}"
            else
                record_step "create_directory" "remove_tree" --meta "path=${dir}" --rollback-meta "path=${dir}"
            fi
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
        record_step "create_user" "remove_user" --meta "username=ransomeye" --rollback-meta "username=ransomeye"
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
    
    # Copy DPI probe (supervised by Core)
    if [[ -d "${SRC_ROOT}/dpi" ]]; then
        cp -r "${SRC_ROOT}/dpi" "${INSTALL_ROOT}/lib/" || error_exit "Failed to copy DPI probe"
        echo -e "${GREEN}✓${NC} Installed: dpi/"
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
# Core is the only process started by installer

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

# Run Core main entry point (foreground process - systemd tracks this)
exec python3 "${INSTALL_ROOT}/lib/core/main.py" "$@"
WRAPPER_EOF

    chmod +x "${INSTALL_ROOT}/bin/ransomeye-core" || error_exit "Failed to make wrapper executable"
    chown ransomeye:ransomeye "${INSTALL_ROOT}/bin/ransomeye-core" || error_exit "Failed to set ownership on wrapper"
    record_step "create_wrapper" "remove_path" --meta "path=${INSTALL_ROOT}/bin/ransomeye-core" --rollback-meta "path=${INSTALL_ROOT}/bin/ransomeye-core"
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
RANSOMEYE_CORE_STATUS_PATH="${INSTALL_ROOT}/runtime/core_status.json"

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
RANSOMEYE_SCHEMA_MIGRATIONS_DIR="${INSTALL_ROOT}/config/schemas/migrations"

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
    record_step "create_environment" "remove_path" --meta "path=${INSTALL_ROOT}/config/environment" --rollback-meta "path=${INSTALL_ROOT}/config/environment"
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

# Check PostgreSQL availability
check_postgresql() {
    echo ""
    echo "Checking PostgreSQL availability..."
    
    if ! command -v psql &> /dev/null; then
        error_exit "PostgreSQL client (psql) not found. Please install PostgreSQL first."
    fi
    
    # Test connection with credentials (user: gagan, password: gagan)
    export PGPASSWORD="gagan"
    if psql -h localhost -U gagan -d ransomeye -c "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL connection successful"
    else
        error_exit "Cannot connect to PostgreSQL (host: localhost, user: gagan, database: ransomeye). Ensure PostgreSQL is running and database exists."
    fi
    unset PGPASSWORD
}

# Run database migrations (fail-closed, idempotent)
run_database_migrations() {
    echo ""
    echo "Applying database migrations..."
    
    local migrations_dir="${INSTALL_ROOT}/config/schemas/migrations"
    if [[ ! -d "$migrations_dir" ]]; then
        error_exit "Migrations directory not found: $migrations_dir"
    fi
    
    preflight_python3
    
    if ! PYTHONPATH="${INSTALL_ROOT}/lib" \
        RANSOMEYE_DB_HOST="${RANSOMEYE_DB_HOST}" \
        RANSOMEYE_DB_PORT="${RANSOMEYE_DB_PORT}" \
        RANSOMEYE_DB_NAME="${RANSOMEYE_DB_NAME}" \
        RANSOMEYE_DB_USER="${RANSOMEYE_DB_USER}" \
        RANSOMEYE_DB_PASSWORD="${RANSOMEYE_DB_PASSWORD}" \
        RANSOMEYE_SCHEMA_MIGRATIONS_DIR="${migrations_dir}" \
        python3 -m common.db.migration_runner upgrade --migrations-dir "${migrations_dir}"; then
        error_exit "Database migrations failed. Installation aborted (fail-closed)."
    fi
    
    record_step "apply_migrations" "rollback_migrations" \
        --meta "migrations_dir=${migrations_dir}" \
        --meta "pythonpath=${INSTALL_ROOT}/lib" \
        --meta "db_host=${RANSOMEYE_DB_HOST}" \
        --meta "db_port=${RANSOMEYE_DB_PORT}" \
        --meta "db_name=${RANSOMEYE_DB_NAME}" \
        --meta "db_user=${RANSOMEYE_DB_USER}" \
        --meta "db_password=${RANSOMEYE_DB_PASSWORD}" \
        --rollback-meta "migrations_dir=${migrations_dir}" \
        --rollback-meta "pythonpath=${INSTALL_ROOT}/lib" \
        --rollback-meta "db_host=${RANSOMEYE_DB_HOST}" \
        --rollback-meta "db_port=${RANSOMEYE_DB_PORT}" \
        --rollback-meta "db_name=${RANSOMEYE_DB_NAME}" \
        --rollback-meta "db_user=${RANSOMEYE_DB_USER}" \
        --rollback-meta "db_password=${RANSOMEYE_DB_PASSWORD}"
    
    echo -e "${GREEN}✓${NC} Database migrations applied successfully"
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
    record_step "install_systemd_service" "remove_systemd_service" \
        --meta "service=ransomeye-core.service" \
        --meta "service_file=/etc/systemd/system/ransomeye-core.service" \
        --rollback-meta "service=ransomeye-core.service" \
        --rollback-meta "service_file=/etc/systemd/system/ransomeye-core.service"
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
    record_step "create_manifest" "remove_path" --meta "path=${manifest_file}" --rollback-meta "path=${manifest_file}"
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
    local status_file="${INSTALL_ROOT}/runtime/core_status.json"
    local core_ready=false
    
    echo "Waiting for Core to reach RUNNING state (max ${max_wait}s)..."
    
    while [[ $waited -lt $max_wait ]]; do
        if systemctl is-active --quiet ransomeye-core; then
            if [[ -f "$status_file" ]]; then
                if python3 -c "import json; s=json.load(open('$status_file')); print(s.get('state',''))" 2>/dev/null | grep -q "RUNNING"; then
                    core_ready=true
                    break
                fi
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
    
    if [[ "$core_ready" != "true" ]]; then
        error_exit "Core did not reach RUNNING state during validation"
    fi
    
    # Validate status schema and enforce authoritative state
    local status_check
    status_check=$(PYTHONPATH="${INSTALL_ROOT}/lib" python3 -c "import json; from core.status_schema import validate_status; s=json.load(open('$status_file')); ok,err=validate_status(s); print('OK' if ok else err)" 2>/dev/null || echo "INVALID")
    if [[ "$status_check" != "OK" ]]; then
        error_exit "Core status file invalid: ${status_check}"
    fi
    
    local global_state
    global_state=$(PYTHONPATH="${INSTALL_ROOT}/lib" python3 -c "import json; s=json.load(open('$status_file')); print(s.get('global_state',''))" 2>/dev/null || echo "")
    if [[ "$global_state" != "RUNNING" ]]; then
        local reason
        reason=$(PYTHONPATH="${INSTALL_ROOT}/lib" python3 -c "import json; s=json.load(open('$status_file')); print(s.get('failure_reason_code'), s.get('failure_reason'))" 2>/dev/null || echo "")
        error_exit "Core did not reach RUNNING state: ${global_state} ${reason}"
    fi
    
    # Validate component states from status file (fail-closed)
    local component_check
    component_check=$(PYTHONPATH="${INSTALL_ROOT}/lib" python3 -c "import json; s=json.load(open('$status_file')); print([k for k,v in s.get('components',{}).items() if v.get('state')!='RUNNING' and k!='ui-backend'])" 2>/dev/null || echo "[]")
    if [[ "$component_check" != "[]" ]]; then
        error_exit "Critical components not RUNNING: ${component_check}"
    fi
    
    echo -e "${GREEN}✓${NC} Core started successfully (RUNNING, all components supervised)"
}

# Main installation flow
main() {
    trap 'run_rollback' ERR
    check_root
    check_ubuntu
    detect_installer_dir
    preflight_python3
    prompt_install_root
    ensure_clean_install_root
    create_directory_structure
    create_system_user
    install_python_files
    create_core_wrapper
    generate_environment_file
    set_permissions
    check_postgresql
    run_database_migrations
    install_systemd_service
    create_manifest
    validate_installation
    
    rm -f "${INSTALL_STATE_FILE}" 2>/dev/null || true
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
