#!/bin/bash
set -e
INSTALL_ROOT="/opt/ransomeye"

create_service() {
  local name=$1
  local deps=$2
  local binds=$3
  
  cat > "${name}.service" << EOF
[Unit]
Description=RansomEye $(echo ${name} | tr '-' ' ' | sed 's/\b\(.\)/\u\1/g')
Documentation=https://ransomeye.v1.0/
${deps}
${binds}

[Service]
Type=notify
User=ransomeye
Group=ransomeye
WorkingDirectory=${INSTALL_ROOT}
EnvironmentFile=-${INSTALL_ROOT}/config/environment
ExecStart=${INSTALL_ROOT}/bin/ransomeye-${name}
Restart=on-failure
RestartSec=10
WatchdogSec=30
StartLimitIntervalSec=300
StartLimitBurst=3
LimitNOFILE=65536
LimitNPROC=4096
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_ROOT}/logs ${INSTALL_ROOT}/runtime
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ransomeye-${name}

[Install]
WantedBy=ransomeye.target
EOF
}

create_service "secure-bus" "Requires=postgresql.service\nAfter=postgresql.service" "BindsTo=postgresql.service"
create_service "ingest" "Requires=secure-bus.service postgresql.service\nAfter=secure-bus.service postgresql.service" "BindsTo=secure-bus.service"
create_service "core-runtime" "Requires=ingest.service postgresql.service\nAfter=ingest.service postgresql.service" "BindsTo=ingest.service"
create_service "correlation-engine" "Requires=core-runtime.service postgresql.service\nAfter=core-runtime.service postgresql.service" "BindsTo=core-runtime.service"
create_service "policy-engine" "Requires=correlation-engine.service\nAfter=correlation-engine.service" "BindsTo=correlation-engine.service"
create_service "ai-core" "Requires=correlation-engine.service\nAfter=correlation-engine.service" "BindsTo=correlation-engine.service"
create_service "llm-soc" "Requires=ai-core.service\nAfter=ai-core.service" "BindsTo=ai-core.service"
create_service "ui" "Requires=postgresql.service\nAfter=postgresql.service" "BindsTo=postgresql.service"

