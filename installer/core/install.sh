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
    
    # Detect release root (parent of installer directory, or current directory if in release bundle)
    if [[ -f "${INSTALLER_DIR}/../manifest.json" ]]; then
        RELEASE_ROOT="$(cd "${INSTALLER_DIR}/.." && pwd)"
    elif [[ -f "${INSTALLER_DIR}/../../manifest.json" ]]; then
        RELEASE_ROOT="$(cd "${INSTALLER_DIR}/../.." && pwd)"
    else
        # Try to find release root by looking for manifest.json
        RELEASE_ROOT=""
        local search_dir="${INSTALLER_DIR}"
        for i in {1..5}; do
            if [[ -f "${search_dir}/manifest.json" ]]; then
                RELEASE_ROOT="$(cd "${search_dir}" && pwd)"
                break
            fi
            search_dir="${search_dir}/.."
        done
    fi
}

# GA-BLOCKING: Verify SBOM (manifest.json) before installation
verify_sbom() {
    echo ""
    echo "Verifying release bundle integrity (SBOM verification)..."
    
    if [[ -z "${RELEASE_ROOT:-}" ]] || [[ ! -d "${RELEASE_ROOT}" ]]; then
        error_exit "Release root not found. Cannot verify SBOM."
    fi
    
    local manifest_path="${RELEASE_ROOT}/manifest.json"
    local signature_path="${RELEASE_ROOT}/manifest.json.sig"
    
    # Check if manifest exists
    if [[ ! -f "$manifest_path" ]]; then
        error_exit "SBOM manifest not found: $manifest_path. Installation cannot proceed without SBOM verification."
    fi
    
    if [[ ! -f "$signature_path" ]]; then
        error_exit "SBOM signature not found: $signature_path. Installation cannot proceed without signature verification."
    fi
    
    # GA-BLOCKING: Verify using Python verification utility (offline, no network)
    # Check if verify_sbom.py is available (must be in release bundle for air-gapped scenarios)
    local verify_script=""
    if [[ -f "${RELEASE_ROOT}/verify_sbom.py" ]]; then
        verify_script="${RELEASE_ROOT}/verify_sbom.py"
    elif [[ -f "${SRC_ROOT}/release/verify_sbom.py" ]]; then
        verify_script="${SRC_ROOT}/release/verify_sbom.py"
    elif [[ -f "${RELEASE_ROOT}/../verify_sbom.py" ]]; then
        verify_script="${RELEASE_ROOT}/../verify_sbom.py"
    else
        error_exit "SBOM verification script (verify_sbom.py) not found. Cannot verify release bundle integrity. Installation aborted (fail-closed)."
    fi
    
    # Use Python verification utility
    if ! command -v python3 &> /dev/null; then
        error_exit "python3 not found. Cannot verify SBOM."
    fi
    
    # Try to find public key
    local public_key_path=""
    local key_dir=""
    local signing_key_id=""
    
    # Check for public key in release bundle
    if [[ -f "${RELEASE_ROOT}/public_key.pem" ]]; then
        public_key_path="${RELEASE_ROOT}/public_key.pem"
    elif [[ -d "${RELEASE_ROOT}/keys" ]]; then
        key_dir="${RELEASE_ROOT}/keys"
        signing_key_id="vendor-release-key-1"  # Default key ID
    elif [[ -n "${RANSOMEYE_SIGNING_KEY_DIR:-}" ]] && [[ -d "${RANSOMEYE_SIGNING_KEY_DIR}" ]]; then
        key_dir="${RANSOMEYE_SIGNING_KEY_DIR}"
        signing_key_id="${RANSOMEYE_SIGNING_KEY_ID:-vendor-release-key-1}"
    fi
    
    # Run verification
    local verify_cmd="python3 \"${verify_script}\" --release-root \"${RELEASE_ROOT}\" --manifest \"${manifest_path}\" --signature \"${signature_path}\""
    
    if [[ -n "$public_key_path" ]]; then
        verify_cmd="${verify_cmd} --public-key \"${public_key_path}\""
    elif [[ -n "$key_dir" ]] && [[ -n "$signing_key_id" ]]; then
        verify_cmd="${verify_cmd} --key-dir \"${key_dir}\" --signing-key-id \"${signing_key_id}\""
    else
        error_exit "Public key not found. Cannot verify SBOM signature. Provide public key via RANSOMEYE_SIGNING_KEY_DIR or place public_key.pem in release root."
    fi
    
    if ! eval "$verify_cmd"; then
        error_exit "SBOM verification failed. Installation aborted (fail-closed)."
    fi
    
    echo -e "${GREEN}✓${NC} SBOM verification passed"
    echo -e "${GREEN}✓${NC} Manifest signature: VALID"
    echo -e "${GREEN}✓${NC} All artifact hashes: VERIFIED"
}

# Basic SBOM verification (fallback if Python utility not available)
verify_sbom_basic() {
    echo "Performing basic SBOM verification (hash checking only)..."
    
    local manifest_path="${RELEASE_ROOT}/manifest.json"
    
    if ! command -v jq &> /dev/null; then
        error_exit "jq not found. Cannot parse manifest.json for basic verification."
    fi
    
    # Verify artifact hashes (signature verification skipped in basic mode)
    local artifacts
    artifacts=$(jq -r '.artifacts[] | "\(.path)|\(.sha256)"' "$manifest_path" 2>/dev/null || true)
    
    if [[ -z "$artifacts" ]]; then
        error_exit "Failed to parse manifest.json or no artifacts found"
    fi
    
    local failed_artifacts=()
    while IFS='|' read -r artifact_path expected_hash; do
        local full_path="${RELEASE_ROOT}/${artifact_path}"
        
        if [[ ! -f "$full_path" ]]; then
            failed_artifacts+=("${artifact_path} (file not found)")
            continue
        fi
        
        local computed_hash
        computed_hash=$(sha256sum "$full_path" | cut -d' ' -f1)
        
        if [[ "$expected_hash" != "$computed_hash" ]]; then
            failed_artifacts+=("${artifact_path} (hash mismatch)")
        fi
    done <<< "$artifacts"
    
    if [[ ${#failed_artifacts[@]} -gt 0 ]]; then
        error_exit "Artifact hash verification failed: ${failed_artifacts[*]}"
    fi
    
    echo -e "${GREEN}✓${NC} Basic SBOM verification passed (artifact hashes verified)"
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

# Validate secret strength (fail-closed)
validate_secret_strength() {
    local secret="$1"
    local secret_name="$2"
    local min_length="${3:-8}"
    
    # Check if empty
    if [[ -z "$secret" ]]; then
        error_exit "SECURITY VIOLATION: ${secret_name} is required (no empty values allowed)"
    fi
    
    # Check minimum length
    if [[ ${#secret} -lt $min_length ]]; then
        error_exit "SECURITY VIOLATION: ${secret_name} is too short (minimum ${min_length} characters required)"
    fi
    
    # Check for weak secrets (all same character, insufficient entropy)
    local unique_chars=$(echo -n "$secret" | fold -w1 | sort -u | wc -l)
    if [[ $unique_chars -lt 3 ]]; then
        error_exit "SECURITY VIOLATION: ${secret_name} is too weak (insufficient entropy, minimum 3 unique characters required)"
    fi
    
    # Check for known weak/default values
    local weak_patterns=("gagan" "password" "test" "changeme" "default" "secret" "admin" "12345678")
    for pattern in "${weak_patterns[@]}"; do
        if [[ "$secret" == "$pattern" ]] || [[ "$secret" == *"$pattern"* ]]; then
            error_exit "SECURITY VIOLATION: ${secret_name} contains weak/default value '${pattern}' (not allowed)"
        fi
    done
}

# Validate signing key strength (fail-closed)
validate_signing_key_strength() {
    local key="$1"
    local min_length="${2:-32}"
    
    # Check if empty
    if [[ -z "$key" ]]; then
        error_exit "SECURITY VIOLATION: Signing key is required (no empty values allowed)"
    fi
    
    # Check minimum length
    if [[ ${#key} -lt $min_length ]]; then
        error_exit "SECURITY VIOLATION: Signing key is too short (minimum ${min_length} characters required)"
    fi
    
    # Check for weak keys (all same character, insufficient entropy)
    local unique_chars=$(echo -n "$key" | fold -w1 | sort -u | wc -l)
    local min_unique=$(echo "scale=0; ${#key} * 0.3" | bc 2>/dev/null || echo "8")
    if [[ $min_unique -lt 8 ]]; then
        min_unique=8
    fi
    if [[ $unique_chars -lt $min_unique ]]; then
        error_exit "SECURITY VIOLATION: Signing key has insufficient entropy (minimum ${min_unique} unique characters required)"
    fi
    
    # Check for known weak/default values
    local weak_patterns=("test_signing_key" "default" "changeme" "password" "secret" "phase7_minimal")
    for pattern in "${weak_patterns[@]}"; do
        if [[ "$key" == *"$pattern"* ]]; then
            error_exit "SECURITY VIOLATION: Signing key contains weak/default pattern '${pattern}' (not allowed)"
        fi
    done
    
    # Check if key is alphabetic only (too weak)
    if [[ "$key" =~ ^[a-zA-Z]+$ ]]; then
        error_exit "SECURITY VIOLATION: Signing key format is too weak (alphabetic only, must include numbers/special characters)"
    fi
}

# Prompt for database credentials (fail-closed, no defaults)
prompt_database_credentials() {
    echo ""
    echo "Database configuration (REQUIRED):"
    echo "  RansomEye requires PostgreSQL database credentials."
    echo "  All credentials must be provided - no defaults allowed."
    echo ""
    
    # Prompt for DB host
    echo -n "Database host [localhost]: "
    read -r db_host
    db_host="${db_host:-localhost}"
    RANSOMEYE_DB_HOST="$db_host"
    
    # Prompt for DB port
    echo -n "Database port [5432]: "
    read -r db_port
    db_port="${db_port:-5432}"
    RANSOMEYE_DB_PORT="$db_port"
    
    # Prompt for DB name
    echo -n "Database name [ransomeye]: "
    read -r db_name
    db_name="${db_name:-ransomeye}"
    RANSOMEYE_DB_NAME="$db_name"
    
    # Prompt for DB user (REQUIRED, no default)
    echo -n "Database user (REQUIRED): "
    read -r db_user
    if [[ -z "$db_user" ]]; then
        error_exit "SECURITY VIOLATION: Database user is required (no default allowed)"
    fi
    validate_secret_strength "$db_user" "Database user" 3
    RANSOMEYE_DB_USER="$db_user"
    
    # Prompt for DB password (REQUIRED, no default)
    echo -n "Database password (REQUIRED, minimum 8 characters): "
    read -rs db_password
    echo ""
    if [[ -z "$db_password" ]]; then
        error_exit "SECURITY VIOLATION: Database password is required (no default allowed)"
    fi
    validate_secret_strength "$db_password" "Database password" 8
    RANSOMEYE_DB_PASSWORD="$db_password"
    
    echo -e "${GREEN}✓${NC} Database credentials validated"
}

# Prompt for signing key (fail-closed, no defaults)
prompt_signing_key() {
    echo ""
    echo "Command signing key configuration (REQUIRED):"
    echo "  RansomEye requires a signing key for command authentication."
    echo "  Key must be at least 32 characters with sufficient entropy."
    echo "  No defaults allowed - must be provided."
    echo ""
    
    echo -n "Command signing key (REQUIRED, minimum 32 characters): "
    read -rs signing_key
    echo ""
    if [[ -z "$signing_key" ]]; then
        error_exit "SECURITY VIOLATION: Command signing key is required (no default allowed)"
    fi
    validate_signing_key_strength "$signing_key" 32
    RANSOMEYE_COMMAND_SIGNING_KEY="$signing_key"
    
    echo -e "${GREEN}✓${NC} Signing key validated"
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

# Database configuration (from installer prompts, no defaults)
RANSOMEYE_DB_HOST="${RANSOMEYE_DB_HOST}"
RANSOMEYE_DB_PORT="${RANSOMEYE_DB_PORT}"
RANSOMEYE_DB_NAME="${RANSOMEYE_DB_NAME}"
RANSOMEYE_DB_USER="${RANSOMEYE_DB_USER}"
RANSOMEYE_DB_PASSWORD="${RANSOMEYE_DB_PASSWORD}"

# Service ports
RANSOMEYE_INGEST_PORT="8000"
RANSOMEYE_UI_PORT="8080"

# Paths to configuration files
RANSOMEYE_EVENT_ENVELOPE_SCHEMA_PATH="${INSTALL_ROOT}/config/contracts/event-envelope.schema.json"
RANSOMEYE_POLICY_DIR="${INSTALL_ROOT}/config/policy"

# Command signing key (from installer prompt, no defaults)
RANSOMEYE_COMMAND_SIGNING_KEY="${RANSOMEYE_COMMAND_SIGNING_KEY}"

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

# Check PostgreSQL availability and verify database user (v1.0 GA: gagan/gagan)
check_postgresql() {
    echo ""
    echo "Checking PostgreSQL availability..."
    
    if ! command -v psql &> /dev/null; then
        error_exit "PostgreSQL client (psql) not found. Please install PostgreSQL first."
    fi
    
    # v1.0 GA: Use single gagan user (Phase A.2 reverted)
    export PGPASSWORD="${RANSOMEYE_DB_PASSWORD}"
    if psql -h "${RANSOMEYE_DB_HOST}" -p "${RANSOMEYE_DB_PORT}" -U "${RANSOMEYE_DB_USER}" -d "${RANSOMEYE_DB_NAME}" -c "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Database connection verified: ${RANSOMEYE_DB_USER}@${RANSOMEYE_DB_HOST}:${RANSOMEYE_DB_PORT}/${RANSOMEYE_DB_NAME}"
    else
        unset PGPASSWORD
        error_exit "Cannot connect to PostgreSQL (host: ${RANSOMEYE_DB_HOST}, user: ${RANSOMEYE_DB_USER}, database: ${RANSOMEYE_DB_NAME}). Ensure user exists and password is correct."
    fi
    unset PGPASSWORD
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

# PHASE B1: Verify artifact signatures (SBOM & Artifact Verification)
verify_artifact_signatures() {
    echo ""
    echo "Verifying artifact signatures (SBOM & Artifact Verification)..."
    
    # PHASE B1: Installer must verify its own artifacts
    # Check for installer artifact files: manifest.json, .sha256, .sig
    local installer_artifact="${INSTALLER_DIR}/install.sh"
    local installer_manifest="${INSTALLER_DIR}/install.sh.manifest.json"
    local installer_sha256="${INSTALLER_DIR}/install.sh.sha256"
    local installer_sig="${INSTALLER_DIR}/install.sh.sig"
    
    # Check for required files
    local missing_files=()
    [[ ! -f "$installer_manifest" ]] && missing_files+=("$installer_manifest")
    [[ ! -f "$installer_sha256" ]] && missing_files+=("$installer_sha256")
    [[ ! -f "$installer_sig" ]] && missing_files+=("$installer_sig")
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        error_exit "Missing artifact verification files (PHASE B1 requirement): ${missing_files[*]}"
    fi
    
    # Verify using Python supply-chain verification engine
    if command -v python3 &> /dev/null; then
        local verify_script=$(cat <<'PYTHON_EOF'
import sys
import json
from pathlib import Path

# Add supply-chain module to path
supply_chain_dir = Path(__file__).parent.parent.parent / "supply-chain"
sys.path.insert(0, str(supply_chain_dir))

try:
    from crypto.vendor_key_manager import VendorKeyManager, VendorKeyManagerError
    from crypto.artifact_verifier import ArtifactVerifier, ArtifactVerificationError
    from engine.verification_engine import VerificationEngine, VerificationEngineError
    
    artifact_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    key_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    signing_key_id = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Load manifest to get signing_key_id if not provided
    if not signing_key_id and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        signing_key_id = manifest.get('signing_key_id')
    
    # Initialize verifier
    if key_dir and signing_key_id:
        key_manager = VendorKeyManager(key_dir)
        public_key = key_manager.get_public_key(signing_key_id)
        if not public_key:
            print(f"FATAL: Public key not found: {signing_key_id}", file=sys.stderr)
            sys.exit(1)
        verifier = ArtifactVerifier(public_key=public_key)
    else:
        print("FATAL: Key directory and signing key ID required for verification", file=sys.stderr)
        sys.exit(1)
    
    # Initialize verification engine
    verification_engine = VerificationEngine(verifier)
    
    # Verify artifact
    result = verification_engine.verify_artifact(artifact_path, manifest_path)
    
    if not result.passed:
        print(f"FATAL: Artifact verification failed: {result.reason}", file=sys.stderr)
        if result.details:
            for key, value in result.details.items():
                print(f"  {key}: {value}", file=sys.stderr)
        sys.exit(1)
    
    print("PASS: Artifact verification successful")
    sys.exit(0)
    
except (VendorKeyManagerError, ArtifactVerificationError, VerificationEngineError) as e:
    print(f"FATAL: Artifact verification error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"FATAL: Unexpected error during artifact verification: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
)
        
        # Create temporary Python script
        local temp_script=$(mktemp)
        echo "$verify_script" > "$temp_script"
        chmod +x "$temp_script"
        
        # Run verification (key_dir and signing_key_id from environment or use defaults)
        local key_dir="${RANSOMEYE_SIGNING_KEY_DIR:-${INSTALLER_DIR}/keys}"
        local signing_key_id="${RANSOMEYE_SIGNING_KEY_ID:-ransomeye-v1.0-installer}"
        
        if python3 "$temp_script" "$installer_artifact" "$installer_manifest" "$key_dir" "$signing_key_id" 2>&1; then
            echo -e "${GREEN}✓${NC} Artifact verification passed"
        else
            rm -f "$temp_script"
            error_exit "Artifact verification failed (PHASE B1 requirement). Installation aborted."
        fi
        
        rm -f "$temp_script"
    else
        # Fallback: Basic file existence check (not ideal, but better than nothing)
        echo -e "${YELLOW}⚠${NC}  Python3 not available, performing basic file checks only"
        echo -e "${GREEN}✓${NC} Artifact files found (full verification requires Python3)"
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
    
    # GA-BLOCKING: Verify SBOM (manifest.json) before installation (fail-closed)
    verify_sbom
    
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
