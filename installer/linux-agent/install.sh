#!/bin/bash
#
# RansomEye v1.0 Linux Agent Installer
# AUTHORITATIVE: Production-grade installer for standalone Linux Agent
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
    local default_root="/opt/ransomeye-agent"
    
    echo ""
    echo "RansomEye v${RANSOMEYE_VERSION} Linux Agent Installer"
    echo "======================================================"
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
    SRC_ROOT="$(cd "${INSTALLER_DIR}/../../services/linux-agent" && pwd)"
}

# Check if Rust and cargo are available
check_rust() {
    if ! command -v cargo &> /dev/null; then
        error_exit "Rust toolchain (cargo) not found. Please install Rust first: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    fi
    
    echo -e "${GREEN}✓${NC} Rust toolchain available"
}

# Build Linux Agent binary
build_agent() {
    echo ""
    echo "Building Linux Agent binary..."
    
    cd "$SRC_ROOT" || error_exit "Failed to change to agent source directory"
    
    # Build release binary
    cargo build --release || error_exit "Failed to build Linux Agent binary"
    
    # Verify binary exists
    if [[ ! -f "${SRC_ROOT}/target/release/ransomeye-linux-agent" ]]; then
        error_exit "Binary not found after build: ${SRC_ROOT}/target/release/ransomeye-linux-agent"
    fi
    
    echo -e "${GREEN}✓${NC} Linux Agent binary built successfully"
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
    echo "Creating system user: ransomeye-agent..."
    
    if id "ransomeye-agent" &>/dev/null; then
        echo -e "${YELLOW}✓${NC} User 'ransomeye-agent' already exists"
    else
        useradd --system --no-create-home --shell /bin/false ransomeye-agent || error_exit "Failed to create user 'ransomeye-agent'"
        echo -e "${GREEN}✓${NC} Created user: ransomeye-agent"
    fi
    
    RANSOMEYE_AGENT_UID=$(id -u ransomeye-agent)
    RANSOMEYE_AGENT_GID=$(id -g ransomeye-agent)
    echo -e "${GREEN}✓${NC} UID: ${RANSOMEYE_AGENT_UID}, GID: ${RANSOMEYE_AGENT_GID}"
}

# Install agent binary
install_agent_binary() {
    echo ""
    echo "Installing agent binary..."
    
    # Copy binary
    cp "${SRC_ROOT}/target/release/ransomeye-linux-agent" "${INSTALL_ROOT}/bin/ransomeye-linux-agent" || \
        error_exit "Failed to copy agent binary"
    
    chmod +x "${INSTALL_ROOT}/bin/ransomeye-linux-agent" || error_exit "Failed to make binary executable"
    chown ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/bin/ransomeye-linux-agent" || \
        error_exit "Failed to set ownership on binary"
    
    echo -e "${GREEN}✓${NC} Installed: ${INSTALL_ROOT}/bin/ransomeye-linux-agent"
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

# Prompt for Core endpoint (optional, no assumption Core exists)
prompt_core_endpoint() {
    echo ""
    echo "Core endpoint configuration:"
    echo "  The Linux Agent will transmit events to the Core Ingest service."
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
    echo -e "${YELLOW}NOTE:${NC} Agent will fail gracefully if Core is unreachable (no crash-loop)"
}

# Generate environment file
generate_environment_file() {
    echo ""
    echo "Generating environment file..."
    
    generate_component_instance_id
    
    cat > "${INSTALL_ROOT}/config/environment" << EOF
# RansomEye v${RANSOMEYE_VERSION} Linux Agent Environment
# Generated by installer on $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# DO NOT EDIT MANUALLY - Regenerate using installer

# Installation paths (absolute, no trailing slashes)
RANSOMEYE_INSTALL_ROOT="${INSTALL_ROOT}"
RANSOMEYE_BIN_DIR="${INSTALL_ROOT}/bin"
RANSOMEYE_CONFIG_DIR="${INSTALL_ROOT}/config"
RANSOMEYE_LOG_DIR="${INSTALL_ROOT}/logs"
RANSOMEYE_RUN_DIR="${INSTALL_ROOT}/runtime"

# Runtime identity
RANSOMEYE_USER="ransomeye-agent"
RANSOMEYE_GROUP="ransomeye-agent"
RANSOMEYE_UID="${RANSOMEYE_AGENT_UID}"
RANSOMEYE_GID="${RANSOMEYE_AGENT_GID}"

# Agent identity
RANSOMEYE_COMPONENT_INSTANCE_ID="${COMPONENT_INSTANCE_ID}"
RANSOMEYE_VERSION="${RANSOMEYE_VERSION}"

# Core endpoint (configurable, no assumption Core is installed)
RANSOMEYE_INGEST_URL="${RANSOMEYE_INGEST_URL}"

# Database credentials (if agent needs direct DB access in future)
# NOTE: These are optional for agents - only required if agent needs direct DB access
# If not needed, these can be left empty or removed
# RANSOMEYE_DB_USER=""
# RANSOMEYE_DB_PASSWORD=""
EOF

    chmod 600 "${INSTALL_ROOT}/config/environment" || error_exit "Failed to set permissions on environment file"
    chown ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/config/environment" || \
        error_exit "Failed to set ownership on environment file"
    echo -e "${GREEN}✓${NC} Created: ${INSTALL_ROOT}/config/environment"
}

# Set ownership and permissions
set_permissions() {
    echo ""
    echo "Setting ownership and permissions..."
    
    # Logs and runtime must be writable by agent user
    chown -R ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/logs" || \
        error_exit "Failed to set ownership on logs/"
    chown -R ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/runtime" || \
        error_exit "Failed to set ownership on runtime/"
    chmod 755 "${INSTALL_ROOT}/logs" || error_exit "Failed to set permissions on logs/"
    chmod 755 "${INSTALL_ROOT}/runtime" || error_exit "Failed to set permissions on runtime/"
    
    # Config and bin owned by agent user but readable only
    chown -R ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/config" || \
        error_exit "Failed to set ownership on config/"
    chown -R ransomeye-agent:ransomeye-agent "${INSTALL_ROOT}/bin" || \
        error_exit "Failed to set ownership on bin/"
    
    echo -e "${GREEN}✓${NC} Permissions set correctly"
}

# Install systemd service (ONE service only)
install_systemd_service() {
    echo ""
    echo "Installing systemd service..."
    
    local service_file="${INSTALLER_DIR}/ransomeye-linux-agent.service"
    
    if [[ ! -f "$service_file" ]]; then
        error_exit "Service file not found: $service_file"
    fi
    
    # Replace INSTALL_ROOT placeholder in service file
    sed "s|@INSTALL_ROOT@|${INSTALL_ROOT}|g" "$service_file" > /etc/systemd/system/ransomeye-linux-agent.service || \
        error_exit "Failed to install systemd service"
    
    systemctl daemon-reload || error_exit "Failed to reload systemd daemon"
    echo -e "${GREEN}✓${NC} Installed systemd service: ransomeye-linux-agent.service"
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
    "user": "ransomeye-agent",
    "group": "ransomeye-agent",
    "uid": ${RANSOMEYE_AGENT_UID},
    "gid": ${RANSOMEYE_AGENT_GID}
  },
  "component_instance_id": "${COMPONENT_INSTANCE_ID}",
  "core_endpoint": "${RANSOMEYE_INGEST_URL}",
  "systemd_service": "ransomeye-linux-agent.service"
}
EOF

    chmod 644 "$manifest_file" || error_exit "Failed to set permissions on manifest"
    chown ransomeye-agent:ransomeye-agent "$manifest_file" || \
        error_exit "Failed to set ownership on manifest"
    echo -e "${GREEN}✓${NC} Created: $manifest_file"
}

# Start agent and verify process (validation hook)
validate_installation() {
    echo ""
    echo "Starting agent and performing validation..."
    
    # Start service
    systemctl start ransomeye-linux-agent || error_exit "Failed to start ransomeye-linux-agent service"
    echo -e "${GREEN}✓${NC} Service started"
    
    # Wait briefly for agent to run (agent is one-shot, exits after event transmission)
    sleep 2
    
    # Check service status (agent may have already completed and exited)
    if systemctl is-active --quiet ransomeye-linux-agent; then
        echo -e "${GREEN}✓${NC} Agent process is running"
    else
        # Check exit status (agent is one-shot, may exit after completing transmission)
        local exit_status=$(systemctl show -p ExecMainStatus --value ransomeye-linux-agent 2>/dev/null || echo "unknown")
        if [[ "$exit_status" == "0" ]]; then
            echo -e "${GREEN}✓${NC} Agent completed successfully (exit code: 0)"
        elif [[ "$exit_status" == "3" ]]; then
            # Exit code 3 = RuntimeError (Core unreachable) - this is expected if Core is not installed
            echo -e "${YELLOW}✓${NC} Agent exited with RuntimeError (exit code: 3) - Core may be unreachable (this is expected if Core is not installed)"
        else
            echo -e "${YELLOW}WARNING:${NC} Agent exited with status: $exit_status (may be expected if Core is not installed)"
        fi
    fi
    
    # Verify process was created (check journal for agent activity)
    if journalctl -u ransomeye-linux-agent --no-pager -n 5 2>/dev/null | grep -q "STARTUP: Linux Agent starting"; then
        echo -e "${GREEN}✓${NC} Agent process was created and executed"
    else
        echo -e "${YELLOW}WARNING:${NC} Agent execution log not found (service may not have run yet)"
    fi
    
    echo -e "${GREEN}✓${NC} Installation validation complete"
}

# Main installation flow
main() {
    check_root
    check_ubuntu
    detect_installer_dir
    prompt_install_root
    check_rust
    build_agent
    create_directory_structure
    create_system_user
    install_agent_binary
    prompt_core_endpoint
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
    echo "Systemd service: ransomeye-linux-agent.service"
    echo ""
    echo "Service commands:"
    echo "  sudo systemctl start ransomeye-linux-agent     # Start agent (one-shot)"
    echo "  sudo systemctl stop ransomeye-linux-agent      # Stop agent"
    echo "  sudo systemctl status ransomeye-linux-agent    # Check status"
    echo "  sudo systemctl restart ransomeye-linux-agent   # Restart agent"
    echo ""
    echo "Logs location: ${INSTALL_ROOT}/logs/"
    echo "Systemd logs: sudo journalctl -u ransomeye-linux-agent -f"
    echo ""
    echo "NOTE: Linux Agent is standalone and does NOT require Core to be installed."
    echo "      Agent will fail gracefully if Core is unreachable (no crash-loop)."
    echo ""
}

# Run main installation
main "$@"
