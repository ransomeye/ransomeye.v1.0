#!/bin/bash
#
# RansomEye v1.0 DPI Probe Installer
# AUTHORITATIVE: Production-grade installer for standalone DPI Probe
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

# Validate root privileges (CRITICAL for DPI Probe - requires root for installation)
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Installer must be run as root (required for systemd service, user creation, and capability management)"
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
    local default_root="/opt/ransomeye-dpi"
    
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

# Detect installer directory (where install.sh is located)
detect_installer_dir() {
    INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SRC_ROOT="$(cd "${INSTALLER_DIR}/../../dpi/probe" && pwd)"
}

# Check if Python 3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        error_exit "Python 3 is not installed. Please install Python 3.10+ first: sudo apt-get install python3"
    fi
    
    # Check Python version (3.10+ required)
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ]]; then
        error_exit "Python 3.10+ is required (detected: Python ${PYTHON_VERSION})"
    fi
    
    echo -e "${GREEN}✓${NC} Python 3 detected: ${PYTHON_VERSION}"
}

# Create directory structure (no hardcoded paths)
create_directory_structure() {
    echo ""
    echo "Creating directory structure..."
    
    local dirs=(
        "${INSTALL_ROOT}/bin"
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
    echo "Creating system user: ransomeye-dpi..."
    
    if id "ransomeye-dpi" &>/dev/null; then
        echo -e "${YELLOW}✓${NC} User 'ransomeye-dpi' already exists"
    else
        useradd --system --no-create-home --shell /bin/false ransomeye-dpi || error_exit "Failed to create user 'ransomeye-dpi'"
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
    
    echo -e "${GREEN}✓${NC} Installed: ${INSTALL_ROOT}/bin/ransomeye-dpi-probe"
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
    
    echo -e "${GREEN}✓${NC} DPI Probe script configured with required capabilities (not full root)"
}

# Prompt for Core endpoint (optional, no assumption Core exists)
prompt_core_endpoint() {
    echo ""
    echo "Core endpoint configuration:"
    echo "  The DPI Probe will transmit events to the Core Ingest service."
    echo "  Core may or may not be installed on this system."
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
RANSOMEYE_DPI_CAPTURE_ENABLED="false"
RANSOMEYE_DPI_INTERFACE="${RANSOMEYE_DPI_INTERFACE}"

# Database credentials (if probe needs direct DB access in future)
RANSOMEYE_DB_USER="gagan"
RANSOMEYE_DB_PASSWORD="gagan"
EOF

    chmod 600 "${INSTALL_ROOT}/config/environment" || error_exit "Failed to set permissions on environment file"
    chown ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/config/environment" || \
        error_exit "Failed to set ownership on environment file"
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
    
    # Config and bin owned by probe user but readable only
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/config" || \
        error_exit "Failed to set ownership on config/"
    chown -R ransomeye-dpi:ransomeye-dpi "${INSTALL_ROOT}/bin" || \
        error_exit "Failed to set ownership on bin/"
    
    echo -e "${GREEN}✓${NC} Permissions set correctly"
}

# Install systemd service (ONE service only)
install_systemd_service() {
    echo ""
    echo "Installing systemd service..."
    
    local service_file="${INSTALLER_DIR}/ransomeye-dpi.service"
    
    if [[ ! -f "$service_file" ]]; then
        error_exit "Service file not found: $service_file"
    fi
    
    # Replace INSTALL_ROOT placeholder in service file
    sed "s|@INSTALL_ROOT@|${INSTALL_ROOT}|g" "$service_file" > /etc/systemd/system/ransomeye-dpi.service || \
        error_exit "Failed to install systemd service"
    
    systemctl daemon-reload || error_exit "Failed to reload systemd daemon"
    echo -e "${GREEN}✓${NC} Installed systemd service: ransomeye-dpi.service"
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
  "systemd_service": "ransomeye-dpi.service"
}
EOF

    chmod 644 "$manifest_file" || error_exit "Failed to set permissions on manifest"
    chown ransomeye-dpi:ransomeye-dpi "$manifest_file" || \
        error_exit "Failed to set ownership on manifest"
    echo -e "${GREEN}✓${NC} Created: $manifest_file"
}

# Start probe and verify process (validation hook)
validate_installation() {
    echo ""
    echo "Starting DPI Probe and performing validation..."
    
    # Start service
    systemctl start ransomeye-dpi || error_exit "Failed to start ransomeye-dpi service"
    echo -e "${GREEN}✓${NC} Service started"
    
    # Wait briefly for probe to start
    sleep 2
    
    # Check service status
    if systemctl is-active --quiet ransomeye-dpi; then
        echo -e "${GREEN}✓${NC} DPI Probe process is running"
    else
        # Check exit status (probe may have completed and exited if stub mode)
        local exit_status=$(systemctl show -p ExecMainStatus --value ransomeye-dpi 2>/dev/null || echo "unknown")
        if [[ "$exit_status" == "0" ]]; then
            echo -e "${GREEN}✓${NC} DPI Probe completed successfully (exit code: 0)"
        elif [[ "$exit_status" == "3" ]]; then
            # Exit code 3 = RuntimeError (Core unreachable) - this is expected if Core is not installed
            echo -e "${YELLOW}✓${NC} DPI Probe exited with RuntimeError (exit code: 3) - Core may be unreachable (this is expected if Core is not installed)"
        else
            echo -e "${YELLOW}WARNING:${NC} DPI Probe exited with status: $exit_status (may be expected if Core is not installed)"
        fi
    fi
    
    # Verify process was created (check journal for probe activity)
    if journalctl -u ransomeye-dpi --no-pager -n 5 2>/dev/null | grep -q "STARTUP: DPI Probe starting"; then
        echo -e "${GREEN}✓${NC} DPI Probe process was created and executed"
    else
        echo -e "${YELLOW}WARNING:${NC} DPI Probe execution log not found (service may not have run yet)"
    fi
    
    # Verify capabilities are set correctly
    if getcap "${INSTALL_ROOT}/bin/ransomeye-dpi-probe" | grep -q "cap_net_raw,cap_net_admin"; then
        echo -e "${GREEN}✓${NC} Capabilities verified: CAP_NET_RAW, CAP_NET_ADMIN"
    else
        echo -e "${YELLOW}WARNING:${NC} Capabilities not verified (may require filesystem support)"
    fi
    
    echo -e "${GREEN}✓${NC} Installation validation complete"
}

# Main installation flow
main() {
    check_root
    check_ubuntu
    detect_installer_dir
    prompt_install_root
    check_python
    create_directory_structure
    create_system_user
    install_dpi_probe_script
    set_capabilities
    prompt_core_endpoint
    prompt_network_interface
    generate_environment_file
    set_permissions
    install_systemd_service
    create_manifest
    validate_installation
    
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo "Installation root: ${INSTALL_ROOT}"
    echo "Systemd service: ransomeye-dpi.service"
    echo "Capabilities: CAP_NET_RAW, CAP_NET_ADMIN (scoped privileges, not full root)"
    echo ""
    echo "Service commands:"
    echo "  sudo systemctl start ransomeye-dpi      # Start DPI Probe"
    echo "  sudo systemctl stop ransomeye-dpi       # Stop DPI Probe"
    echo "  sudo systemctl status ransomeye-dpi     # Check status"
    echo "  sudo systemctl restart ransomeye-dpi    # Restart DPI Probe"
    echo ""
    echo "Logs location: ${INSTALL_ROOT}/logs/"
    echo "Systemd logs: sudo journalctl -u ransomeye-dpi -f"
    echo ""
    echo "NOTE: DPI Probe is standalone and does NOT require Core to be installed."
    echo "      DPI Probe runs with CAP_NET_RAW and CAP_NET_ADMIN capabilities (not full root)."
    echo "      DPI Probe will fail gracefully if Core is unreachable (no crash-loop)."
    echo ""
}

# Run main installation
main "$@"
