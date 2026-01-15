#!/bin/bash
#
# RansomEye v1.0 DPI Probe Installer
# AUTHORITATIVE: Production-grade installer for Core-supervised DPI Probe
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
    python3 "$TRANSACTION_PY" init --state-file "$INSTALL_STATE_FILE" --component "dpi-probe"
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

# Validate root privileges (CRITICAL for DPI Probe - requires root for installation)
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Installer must be run as root (required for user creation, capability management, and build)"
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
    echo "RansomEye v${RANSOMEYE_VERSION} DPI Probe Installer"
    echo "=================================================="
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
    SRC_ROOT="$(cd "${INSTALLER_DIR}/../../dpi/probe" && pwd)"
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
        "${INSTALL_ROOT}/config"
        "${INSTALL_ROOT}/config/component-keys"
        "${INSTALL_ROOT}/config/keys"
        "${INSTALL_ROOT}/lib"
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
    echo "Creating system user: ransomeye-dpi..."
    
    if id "ransomeye-dpi" &>/dev/null; then
        echo -e "${YELLOW}✓${NC} User 'ransomeye-dpi' already exists"
    else
        useradd --system --no-create-home --shell /bin/false ransomeye-dpi || error_exit "Failed to create user 'ransomeye-dpi'"
        record_step "create_user" "remove_user" --meta "username=ransomeye-dpi" --rollback-meta "username=ransomeye-dpi"
        echo -e "${GREEN}✓${NC} Created user: ransomeye-dpi"
    fi
    
    RANSOMEYE_DPI_UID=$(id -u ransomeye-dpi)
    RANSOMEYE_DPI_GID=$(id -g ransomeye-dpi)
    echo -e "${GREEN}✓${NC} UID: ${RANSOMEYE_DPI_UID}, GID: ${RANSOMEYE_DPI_GID}"
}

# Install DPI Probe script
install_dpi_probe_script() {
    echo ""
    echo "Installing DPI Probe script..."
    
    # Check if source script exists
    if [[ ! -f "${SRC_ROOT}/main.py" ]]; then
        error_exit "DPI Probe source script not found: ${SRC_ROOT}/main.py"
    fi
    
    # Copy script
    cp "${SRC_ROOT}/main.py" "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" || \
        error_exit "Failed to copy DPI Probe script"
    
    chmod +x "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" || error_exit "Failed to make script executable"
    chown ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" || \
        error_exit "Failed to set ownership on script"
    record_step "install_probe" "remove_path" --meta "path=${INSTALL_ROOT}/bin/ransomeye-dpi-probe" --rollback-meta "path=${INSTALL_ROOT}/bin/ransomeye-dpi-probe"
    
    echo -e "${GREEN}✓${NC} Installed: ${INSTALL_ROOT}/bin/ransomeye-dpi-probe"
}

# Build AF_PACKET fastpath library
build_fastpath_library() {
    echo ""
    echo "Building AF_PACKET fastpath library..."

    if ! command -v gcc &> /dev/null; then
        error_exit "gcc is required to build AF_PACKET fastpath (install build-essential)"
    fi

    local fastpath_src="${INSTALLER_DIR}/../../dpi-advanced/fastpath/af_packet_capture.c"
    local output_lib="${INSTALL_ROOT}/lib/libransomeye_dpi_af_packet.so"

    if [[ ! -f "$fastpath_src" ]]; then
        error_exit "AF_PACKET fastpath source not found: ${fastpath_src}"
    fi

    gcc -shared -fPIC -O2 -o "$output_lib" "$fastpath_src" || \
        error_exit "Failed to build AF_PACKET fastpath library"
    chmod 755 "$output_lib" || error_exit "Failed to set permissions on fastpath library"
    chown ransomeye-dpi:ransomeye-dpi "$output_lib" || \
        error_exit "Failed to set ownership on fastpath library"

    record_step "build_fastpath" "remove_path" --meta "path=${output_lib}" --rollback-meta "path=${output_lib}"
    echo -e "${GREEN}✓${NC} Built: ${output_lib}"
}

# Generate telemetry signing keys
generate_telemetry_keys() {
    echo ""
    echo "Generating DPI telemetry signing keys..."

    local key_dir="${INSTALL_ROOT}/config/component-keys"
    local private_key="${key_dir}/dpi.key"
    local key_id

    KEY_DIR="$key_dir" PRIVATE_KEY="$private_key" key_id=$(python3 - << 'EOF' || exit 1
import hashlib
import os
from pathlib import Path
from nacl.signing import SigningKey

key_dir = Path(os.environ["KEY_DIR"])
key_dir.mkdir(parents=True, exist_ok=True)
private_key_path = Path(os.environ["PRIVATE_KEY"])

if private_key_path.exists():
    signing_key = SigningKey(private_key_path.read_bytes())
else:
    signing_key = SigningKey.generate()
    private_key_path.write_bytes(signing_key.encode())

public_key = signing_key.verify_key.encode()
key_id = hashlib.sha256(public_key).hexdigest()
public_key_path = key_dir / f"{key_id}.pub"
public_key_path.write_bytes(public_key)
print(key_id)
EOF
)
    if [[ -z "$key_id" ]]; then
        error_exit "Failed to generate telemetry signing keys (PyNaCl required)"
    fi

    chmod 600 "$private_key" || error_exit "Failed to set permissions on private key"
    chown ransomeye-dpi:ransomeye-dpi "$private_key" || \
        error_exit "Failed to set ownership on private key"
    record_step "create_telemetry_key" "remove_path" --meta "path=${private_key}" --rollback-meta "path=${private_key}"
    record_step "create_telemetry_pubkey" "remove_path" --meta "path=${key_dir}/${key_id}.pub" --rollback-meta "path=${key_dir}/${key_id}.pub"
}

# Set Linux capabilities (CRITICAL for DPI Probe - network packet capture requires privileges)
set_capabilities() {
    echo ""
    echo "Setting Linux capabilities for DPI Probe..."
    
    # Check if setcap is available
    if ! command -v setcap &> /dev/null; then
        error_exit "setcap command not found. Please install libcap2-bin: sudo apt-get install libcap2-bin"
    fi
    
    # Set CAP_NET_RAW and CAP_NET_ADMIN for packet capture (not full root)
    # CAP_NET_RAW: Required for raw socket creation (packet capture)
    # CAP_NET_ADMIN: Required for network interface configuration
    setcap cap_net_raw,cap_net_admin+ep "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" 2>/dev/null || \
        error_exit "Failed to set capabilities on DPI Probe script. Ensure file is not on a filesystem without capability support (e.g., NFS, tmpfs)."
    
    # Verify capabilities were set
    if getcap "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" | grep -q "cap_net_raw,cap_net_admin"; then
        echo -e "${GREEN}✓${NC} Capabilities set: CAP_NET_RAW, CAP_NET_ADMIN"
    else
        error_exit "Failed to verify capabilities on DPI Probe script"
    fi
    
    record_step "set_capabilities" "remove_capabilities" \
        --meta "path=${INSTALL_ROOT}/bin/ransomeye-dpi-probe" \
        --rollback-meta "path=${INSTALL_ROOT}/bin/ransomeye-dpi-probe"
    
    echo -e "${GREEN}✓${NC} DPI Probe script configured with required capabilities (not full root)"
}

# Prompt for Core endpoint (optional, no assumption Core exists)
prompt_core_endpoint() {
    echo ""
    echo "Core endpoint configuration:"
    echo "  The DPI Probe is supervised by Core and transmits events to Ingest."
    echo "  DPI will fail fast if Core/Ingest is unavailable."
    echo ""
    echo -n "Core Ingest URL [http://localhost:8000/events]: "
    
    read -r ingest_url
    ingest_url="${ingest_url:-http://localhost:8000/events}"
    
    # Basic URL validation
    if [[ ! "$ingest_url" =~ ^https?:// ]]; then
        error_exit "Ingest URL must start with http:// or https://"
    fi
    
    RANSOMEYE_INGEST_URL="$ingest_url"
    echo -e "${GREEN}✓${NC} Core Ingest URL: ${RANSOMEYE_INGEST_URL}"
    echo -e "${YELLOW}NOTE:${NC} DPI Probe will fail gracefully if Core is unreachable (no crash-loop)"
}

# Prompt for network interface (configurable)
prompt_network_interface() {
    echo ""
    echo "Network interface configuration:"
    echo "  The DPI Probe can capture packets from a specific network interface."
    echo "  Leave empty to use default or auto-detect."
    echo ""
    
    # List available network interfaces
    if command -v ip &> /dev/null; then
        echo "Available network interfaces:"
        ip -br link show | awk '{print "  - " $1}' || true
    fi
    echo ""
    
    echo -n "Network interface [empty for auto-detect]: "
    read -r network_interface
    
    RANSOMEYE_DPI_INTERFACE="${network_interface:-}"
    if [[ -z "$RANSOMEYE_DPI_INTERFACE" ]]; then
        echo -e "${GREEN}✓${NC} Network interface: auto-detect"
    else
        echo -e "${GREEN}✓${NC} Network interface: ${RANSOMEYE_DPI_INTERFACE}"
    fi
}

# Generate environment file
generate_environment_file() {
    echo ""
    echo "Generating environment file..."
    
    # Generate component instance ID
    if command -v uuidgen &> /dev/null; then
        COMPONENT_INSTANCE_ID=$(uuidgen)
    else
        # Fallback: generate UUID-like string
        COMPONENT_INSTANCE_ID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())")
    fi
    
    cat > "${INSTALL_ROOT}/config/environment" << EOF
# RansomEye v${RANSOMEYE_VERSION} DPI Probe Environment
# Generated by installer on $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# DO NOT EDIT MANUALLY - Regenerate using installer

# Installation paths (absolute, no trailing slashes)
RANSOMEYE_INSTALL_ROOT="${INSTALL_ROOT}"
RANSOMEYE_BIN_DIR="${INSTALL_ROOT}/bin"
RANSOMEYE_CONFIG_DIR="${INSTALL_ROOT}/config"
RANSOMEYE_LOG_DIR="${INSTALL_ROOT}/logs"
RANSOMEYE_RUN_DIR="${INSTALL_ROOT}/runtime"

# Runtime identity
RANSOMEYE_USER="ransomeye-dpi"
RANSOMEYE_GROUP="ransomeye-dpi"
RANSOMEYE_UID="${RANSOMEYE_DPI_UID}"
RANSOMEYE_GID="${RANSOMEYE_DPI_GID}"

# Probe identity
RANSOMEYE_COMPONENT_INSTANCE_ID="${COMPONENT_INSTANCE_ID}"
RANSOMEYE_VERSION="${RANSOMEYE_VERSION}"

# Core endpoint (configurable, no assumption Core is installed)
RANSOMEYE_INGEST_URL="${RANSOMEYE_INGEST_URL}"

# DPI Probe configuration
RANSOMEYE_DPI_CAPTURE_BACKEND="af_packet_c"
RANSOMEYE_DPI_INTERFACE="${RANSOMEYE_DPI_INTERFACE}"
RANSOMEYE_DPI_FASTPATH_LIB="${INSTALL_ROOT}/lib/libransomeye_dpi_af_packet.so"
RANSOMEYE_DPI_FLOW_TIMEOUT="300"
RANSOMEYE_DPI_HEARTBEAT_SECONDS="5"
RANSOMEYE_DPI_PRIVACY_MODE="FORENSIC"
RANSOMEYE_DPI_IP_REDACTION="none"
RANSOMEYE_DPI_PORT_REDACTION="none"

# Component key directory (telemetry signing keys)
RANSOMEYE_COMPONENT_KEY_DIR="${INSTALL_ROOT}/config/component-keys"

# Service key directory (used for service auth tokens)
RANSOMEYE_SERVICE_KEY_DIR="${INSTALL_ROOT}/config/keys"

# Database credentials (if probe needs direct DB access in future)
RANSOMEYE_DB_USER="gagan"
RANSOMEYE_DB_PASSWORD="gagan"
EOF

    chmod 600 "${INSTALL_ROOT}/config/environment" || error_exit "Failed to set permissions on environment file"
    chown ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/config/environment" || \
        error_exit "Failed to set ownership on environment file"
    record_step "create_environment" "remove_path" --meta "path=${INSTALL_ROOT}/config/environment" --rollback-meta "path=${INSTALL_ROOT}/config/environment"
    echo -e "${GREEN}✓${NC} Created: ${INSTALL_ROOT}/config/environment"
}

# Set ownership and permissions
set_permissions() {
    echo ""
    echo "Setting ownership and permissions..."
    
    # Logs and runtime must be writable by probe user
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/logs" || \
        error_exit "Failed to set ownership on logs/"
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/runtime" || \
        error_exit "Failed to set ownership on runtime/"
    chmod 755 "${INSTALL_ROOT}/logs" || error_exit "Failed to set permissions on logs/"
    chmod 755 "${INSTALL_ROOT}/runtime" || error_exit "Failed to set permissions on runtime/"
    
    # Config, bin, and lib owned by probe user but readable only
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/config" || \
        error_exit "Failed to set ownership on config/"
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/bin" || \
        error_exit "Failed to set ownership on bin/"
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/lib" || \
        error_exit "Failed to set ownership on lib/"
    
    echo -e "${GREEN}✓${NC} Permissions set correctly"
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
    "config": "${INSTALL_ROOT}/config",
    "lib": "${INSTALL_ROOT}/lib",
    "logs": "${INSTALL_ROOT}/logs",
    "runtime": "${INSTALL_ROOT}/runtime"
  },
  "runtime_identity": {
    "user": "ransomeye-dpi",
    "group": "ransomeye-dpi",
    "uid": ${RANSOMEYE_DPI_UID},
    "gid": ${RANSOMEYE_DPI_GID}
  },
  "component_instance_id": "${COMPONENT_INSTANCE_ID}",
  "core_endpoint": "${RANSOMEYE_INGEST_URL}",
  "network_interface": "${RANSOMEYE_DPI_INTERFACE}",
  "capabilities": ["CAP_NET_RAW", "CAP_NET_ADMIN"],
  "component_key_dir": "${INSTALL_ROOT}/config/component-keys",
  "fastpath_library": "${INSTALL_ROOT}/lib/libransomeye_dpi_af_packet.so"
}
EOF

    chmod 644 "$manifest_file" || error_exit "Failed to set permissions on manifest"
    chown ransomeye-dpi:ransomeye-dpi "$manifest_file" || \
        error_exit "Failed to set ownership on manifest"
    record_step "create_manifest" "remove_path" --meta "path=${manifest_file}" --rollback-meta "path=${manifest_file}"
    echo -e "${GREEN}✓${NC} Created: $manifest_file"
}

# Validate installation (no service start; Core supervises runtime)
validate_installation() {
    echo ""
    echo "Validating DPI Probe installation..."
    
    # Verify capabilities are set correctly
    if getcap "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" | grep -q "cap_net_raw,cap_net_admin"; then
        echo -e "${GREEN}✓${NC} Capabilities verified: CAP_NET_RAW, CAP_NET_ADMIN"
    else
        error_exit "Capabilities not verified on DPI Probe binary"
    fi

    # Verify fastpath library exists
    if [[ -f "${INSTALL_ROOT}/lib/libransomeye_dpi_af_packet.so" ]]; then
        echo -e "${GREEN}✓${NC} Fastpath library present"
    else
        error_exit "Fastpath library missing: ${INSTALL_ROOT}/lib/libransomeye_dpi_af_packet.so"
    fi
    
    echo -e "${GREEN}✓${NC} Installation validation complete"
}

# Main installation flow
main() {
    trap 'run_rollback' ERR
    check_root
    check_ubuntu
    detect_installer_dir
    prompt_install_root
    ensure_clean_install_root
    preflight_python3
    create_directory_structure
    create_system_user
    install_dpi_probe_script
    build_fastpath_library
    set_capabilities
    generate_telemetry_keys
    prompt_core_endpoint
    prompt_network_interface
    generate_environment_file
    set_permissions
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
    echo "Capabilities: CAP_NET_RAW, CAP_NET_ADMIN (scoped privileges, not full root)"
    echo ""
    echo "Logs location: ${INSTALL_ROOT}/logs/"
    echo ""
    echo "NOTE: DPI Probe is supervised by Core only (no standalone mode)."
    echo ""
}

# Run main installation
main "$@"
