# Windows Agent Deep ETW Telemetry - Architecture Design

**AUTHORITATIVE:** Design document for Phase 6 - Windows Agent Deep ETW Telemetry

## Overview

This document defines the architecture for implementing deep, deterministic ETW (Event Tracing for Windows) telemetry collection in the Windows Agent to achieve parity with Linux Agent eBPF-based observability.

## Core Principles

### Read-Only Telemetry
- **ETW READ-ONLY**: No blocking, no hooking, no interception
- **Observation Only**: Collect events, never modify system behavior
- **No Enforcement**: This phase adds detection only, no enforcement logic

### User-Mode Only
- **No Kernel Drivers**: User-mode ETW consumption only
- **No Kernel Hooks**: No kernel-level interception
- **Standard APIs**: Use Windows ETW consumer APIs only

### Performance Constraints
- **<5% CPU Impact**: Maximum 5% CPU overhead during active collection
- **Fail-Open Telemetry**: Agent must not crash if ETW fails
- **Graceful Degradation**: Continue operation if providers unavailable

### Deterministic & Auditable
- **Deterministic Schemas**: Same ETW event → same normalized event
- **Signed Telemetry**: All events cryptographically signed
- **Offline Capable**: Events buffered locally, no online dependency

## Architecture Design

### Module Structure

```
agents/windows/
├── agent/
│   ├── etw/
│   │   ├── __init__.py
│   │   ├── providers.py              # ETW provider definitions and configuration
│   │   ├── session_manager.py        # ETW session lifecycle management
│   │   ├── event_parser.py            # ETW event parsing and normalization
│   │   ├── schema_mapper.py          # Map ETW events to normalized schemas
│   │   ├── health_monitor.py         # ETW session health and telemetry loss detection
│   │   └── buffer_manager.py         # Local event buffering (offline capable)
│   ├── telemetry/
│   │   ├── __init__.py
│   │   ├── event_envelope.py         # Event envelope construction
│   │   ├── signer.py                 # Event signing (ed25519)
│   │   └── sender.py                 # Event transmission to Core (offline buffering)
│   └── agent_main.py                 # Main agent entry point (integrates ETW + command gate)
└── command_gate.ps1                  # Existing command gate (unchanged)
```

### Data Flow

```
ETW Providers (Windows Kernel)
    ↓
ETW Session (User-Mode Consumer)
    ↓
Event Parser (ETW → Normalized Schema)
    ↓
Schema Mapper (Normalized → Event Envelope)
    ↓
Event Signer (Cryptographic Signature)
    ↓
Buffer Manager (Local Offline Buffer)
    ↓
Event Sender (Transmit to Core when available)
```

## ETW Provider List with Rationale

### 1. Process & Thread Activity

**Providers:**
- `Microsoft-Windows-Kernel-Process` (GUID: 22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716)
- `Microsoft-Windows-Kernel-Thread` (GUID: 3D6FA8D1-FE05-11D0-9DDA-00C04FD7BA7C)

**Rationale:**
- **Process Creation/Termination**: Essential for process lineage tracking
- **Parent-Child Relationships**: Required for killchain reconstruction
- **Command Line Capture**: Critical for detection (ransomware indicators)
- **Image Path & Hash**: Required for executable tracking
- **Thread Injection Indicators**: Detects process hollowing, DLL injection

**Events Collected:**
- `ProcessStart` (Opcode 1): Process creation with PID, parent PID, image path, command line
- `ProcessStop` (Opcode 2): Process termination with exit code
- `ThreadStart` (Opcode 1): Thread creation with thread ID, process ID
- `ThreadStop` (Opcode 2): Thread termination
- `ImageLoad` (from Kernel-Process): DLL/executable load with image path and hash

**Normalized Mapping:**
- ETW `ProcessStart` → `process_activity` table (activity_type: PROCESS_START)
- ETW `ProcessStop` → `process_activity` table (activity_type: PROCESS_EXIT)
- ETW `ImageLoad` (suspicious patterns) → `process_activity` table (activity_type: PROCESS_INJECT)

### 2. Filesystem Activity

**Providers:**
- `Microsoft-Windows-Kernel-File` (GUID: ED54C3B-6C5F-4F3B-8B8E-8B8E8B8E8B8E)

**Rationale:**
- **File Create/Write/Delete**: Essential for ransomware detection (mass file encryption)
- **File Entropy Change**: Pre/post write size heuristic for encryption detection
- **Executable Write Detection**: Detects malware dropping executables
- **File Rename Patterns**: Detects ransomware file extension changes

**Events Collected:**
- `FileCreate` (Opcode 64): File creation with path, process ID
- `FileWrite` (Opcode 67): File write with path, size, process ID
- `FileDelete` (Opcode 65): File deletion with path, process ID
- `FileRename` (Opcode 66): File rename with old/new paths, process ID
- `FileRead` (Opcode 68): File read with path, process ID (for executable detection)

**Normalized Mapping:**
- ETW `FileCreate` → `file_activity` table (activity_type: FILE_CREATE)
- ETW `FileWrite` → `file_activity` table (activity_type: FILE_MODIFY)
- ETW `FileDelete` → `file_activity` table (activity_type: FILE_DELETE)
- ETW `FileRead` (executable patterns) → `file_activity` table (activity_type: FILE_READ)
- File entropy change (heuristic) → `file_activity` table (activity_type: FILE_ENCRYPT)

### 3. Registry Activity

**Providers:**
- `Microsoft-Windows-Kernel-Registry` (GUID: 70EB4F03-C1DE-4F73-A051-33D13D5873B8)

**Rationale:**
- **Autorun & Persistence**: Detects persistence mechanisms (Run keys, services, scheduled tasks)
- **Service Registration**: Detects malicious service installation
- **Driver Registration**: Detects rootkit installation
- **Registry Modification**: Detects configuration changes (security policy bypass)

**Events Collected:**
- `RegCreateKey` (Opcode 9): Registry key creation with key path, process ID
- `RegSetValue` (Opcode 10): Registry value modification with key path, value name, process ID
- `RegDeleteKey` (Opcode 12): Registry key deletion with key path, process ID
- `RegDeleteValue` (Opcode 13): Registry value deletion with key path, value name, process ID

**Normalized Mapping:**
- ETW `RegCreateKey` / `RegSetValue` (persistence locations) → `persistence` table
  - Run keys → persistence_type: REGISTRY_RUN_KEY
  - Service keys → persistence_type: SERVICE
  - Scheduled task keys → persistence_type: SCHEDULED_TASK

### 4. Network Intent (Host-Side)

**Providers:**
- `Microsoft-Windows-Kernel-Network` (GUID: 7DD42A49-5389-4FBF-9CA3-4A4E4A4E4A4E)
- `Microsoft-Windows-TCPIP` (GUID: 2F07E2EE-15DB-40F1-90EF-9F7E9F7E9F7E)

**Rationale:**
- **Socket Creation**: Detects network connection intent (before DPI sees it)
- **Bind/Connect Intent**: Process-to-socket correlation for killchain
- **DNS Query Intent**: Host-side DNS queries (correlates with DPI DNS responses)
- **Connection Attempts**: Failed connection attempts (firewall blocks, unreachable hosts)

**Events Collected:**
- `TcpConnect` (from TCPIP): TCP connection attempt with source IP, dest IP, port, process ID
- `TcpDisconnect` (from TCPIP): TCP disconnection with connection info, process ID
- `UdpSend` (from TCPIP): UDP send with source IP, dest IP, port, process ID
- `DnsQuery` (from Kernel-Network): DNS query with domain, process ID (best-effort)

**Normalized Mapping:**
- ETW `TcpConnect` / `UdpSend` → `network_intent` table (activity_type: CONNECTION_ATTEMPT)
- ETW `TcpListen` → `network_intent` table (activity_type: LISTEN)
- ETW `DnsQuery` → `network_intent` table (activity_type: DNS_QUERY)

### 5. Memory & Injection Signals (Best-Effort)

**Providers:**
- `Microsoft-Windows-Kernel-Memory` (GUID: D1D93EF7-E1F2-4F45-9933-535793579357)
- `Microsoft-Windows-Threat-Intelligence` (GUID: F4E1897C-BEC5-4A12-9D9F-9D9F9D9F9D9F) - If accessible

**Rationale:**
- **Remote Thread Creation**: Detects process injection (CreateRemoteThread)
- **Process Hollowing Indicators**: Detects process hollowing (unusual memory patterns)
- **RWX Memory Allocation**: Detects suspicious memory permissions (executable writable memory)
- **Memory Protection Changes**: Detects memory protection modification (PAGE_EXECUTE_READWRITE)

**Events Collected:**
- `VirtualAlloc` (from Kernel-Memory): Memory allocation with address, size, protection flags, process ID
- `VirtualProtect` (from Kernel-Memory): Memory protection change with address, old protection, new protection, process ID
- `CreateRemoteThread` (from Kernel-Thread): Remote thread creation with source process, target process, thread ID

**Normalized Mapping:**
- ETW `CreateRemoteThread` → `process_activity` table (activity_type: PROCESS_INJECT)
- ETW `VirtualAlloc` (RWX flags) → `process_activity` table (activity_type: PROCESS_MODIFY)
- ETW `VirtualProtect` (to RWX) → `process_activity` table (activity_type: PROCESS_MODIFY)

**Note**: Memory events are best-effort due to:
- Limited provider availability (some require kernel access)
- High event volume (requires filtering)
- Performance impact (memory events are frequent)

## Normalized Event Schema Examples

### Example 1: Process Start Event

**ETW Event:**
```
Provider: Microsoft-Windows-Kernel-Process
Event ID: 1 (ProcessStart)
Timestamp: 2025-01-12T12:00:00.123456Z
PID: 1234
Parent PID: 567
Image Path: C:\Windows\System32\cmd.exe
Command Line: cmd.exe /c "powershell.exe -EncodedCommand ..."
User: DOMAIN\user
```

**Normalized Event Envelope:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "machine_id": "host-001",
  "component": "windows_agent",
  "component_instance_id": "windows-agent-001",
  "observed_at": "2025-01-12T12:00:00.123456Z",
  "ingested_at": "2025-01-12T12:00:01.000000Z",
  "sequence": 42,
  "payload": {
    "activity_type": "PROCESS_START",
    "process_pid": 1234,
    "parent_pid": 567,
    "process_name": "cmd.exe",
    "process_path": "C:\\Windows\\System32\\cmd.exe",
    "command_line": "cmd.exe /c \"powershell.exe -EncodedCommand ...\"",
    "user_name": "DOMAIN\\user",
    "user_id": 1001,
    "image_hash": "a1b2c3d4e5f6...",
    "etw_provider_id": "22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716",
    "etw_event_id": 1,
    "etw_keywords": 0x10
  },
  "identity": {
    "hostname": "WIN-HOST-001",
    "boot_id": "boot-20250112-001",
    "agent_version": "1.0.0"
  },
  "integrity": {
    "hash_sha256": "abc123...",
    "prev_hash_sha256": "def456..."
  }
}
```

### Example 2: File Write Event (with Entropy Change)

**ETW Event:**
```
Provider: Microsoft-Windows-Kernel-File
Event ID: 67 (FileWrite)
Timestamp: 2025-01-12T12:00:05.789012Z
PID: 1234
File Path: C:\Users\user\Documents\file.txt
File Size Before: 1024
File Size After: 2048
IO Flags: 0x00000001
```

**Normalized Event Envelope:**
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440001",
  "machine_id": "host-001",
  "component": "windows_agent",
  "component_instance_id": "windows-agent-001",
  "observed_at": "2025-01-12T12:00:05.789012Z",
  "ingested_at": "2025-01-12T12:00:06.000000Z",
  "sequence": 43,
  "payload": {
    "activity_type": "FILE_MODIFY",
    "file_path": "C:\\Users\\user\\Documents\\file.txt",
    "file_size_before": 1024,
    "file_size_after": 2048,
    "entropy_change_indicator": true,
    "process_pid": 1234,
    "process_name": "cmd.exe",
    "etw_provider_id": "ED54C3B-6C5F-4F3B-8B8E-8B8E8B8E8B8E",
    "etw_event_id": 67
  },
  "identity": {
    "hostname": "WIN-HOST-001",
    "boot_id": "boot-20250112-001",
    "agent_version": "1.0.0"
  },
  "integrity": {
    "hash_sha256": "ghi789...",
    "prev_hash_sha256": "abc123..."
  }
}
```

### Example 3: Registry Persistence Event

**ETW Event:**
```
Provider: Microsoft-Windows-Kernel-Registry
Event ID: 10 (RegSetValue)
Timestamp: 2025-01-12T12:00:10.345678Z
PID: 1234
Key Path: HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
Value Name: MaliciousService
Value Data: C:\temp\malware.exe
```

**Normalized Event Envelope:**
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440002",
  "machine_id": "host-001",
  "component": "windows_agent",
  "component_instance_id": "windows-agent-001",
  "observed_at": "2025-01-12T12:00:10.345678Z",
  "ingested_at": "2025-01-12T12:00:11.000000Z",
  "sequence": 44,
  "payload": {
    "persistence_type": "REGISTRY_RUN_KEY",
    "registry_key": "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
    "registry_value": "MaliciousService",
    "registry_data": "C:\\temp\\malware.exe",
    "process_pid": 1234,
    "process_name": "cmd.exe",
    "etw_provider_id": "70EB4F03-C1DE-4F73-A051-33D13D5873B8",
    "etw_event_id": 10
  },
  "identity": {
    "hostname": "WIN-HOST-001",
    "boot_id": "boot-20250112-001",
    "agent_version": "1.0.0"
  },
  "integrity": {
    "hash_sha256": "jkl012...",
    "prev_hash_sha256": "ghi789..."
  }
}
```

### Example 4: Network Intent Event

**ETW Event:**
```
Provider: Microsoft-Windows-TCPIP
Event ID: 11 (TcpConnect)
Timestamp: 2025-01-12T12:00:15.901234Z
PID: 1234
Source IP: 192.168.1.100
Source Port: 49152
Dest IP: 10.0.0.50
Dest Port: 443
Protocol: TCP
```

**Normalized Event Envelope:**
```json
{
  "event_id": "880e8400-e29b-41d4-a716-446655440003",
  "machine_id": "host-001",
  "component": "windows_agent",
  "component_instance_id": "windows-agent-001",
  "observed_at": "2025-01-12T12:00:15.901234Z",
  "ingested_at": "2025-01-12T12:00:16.000000Z",
  "sequence": 45,
  "payload": {
    "activity_type": "CONNECTION_ATTEMPT",
    "source_ip": "192.168.1.100",
    "source_port": 49152,
    "dest_ip": "10.0.0.50",
    "dest_port": 443,
    "protocol": "TCP",
    "process_pid": 1234,
    "process_name": "powershell.exe",
    "etw_provider_id": "2F07E2EE-15DB-40F1-90EF-9F7E9F7E9F7E",
    "etw_event_id": 11
  },
  "identity": {
    "hostname": "WIN-HOST-001",
    "boot_id": "boot-20250112-001",
    "agent_version": "1.0.0"
  },
  "integrity": {
    "hash_sha256": "mno345...",
    "prev_hash_sha256": "jkl012..."
  }
}
```

## Performance Mitigation Strategy

### 1. Event Filtering (Pre-Collection)

**Strategy:**
- **Keyword Filtering**: Use ETW keywords to filter events at provider level
- **Level Filtering**: Collect only WARNING/ERROR level events where appropriate
- **Process Filtering**: Filter out known-safe processes (whitelist approach)
- **Path Filtering**: Filter out known-safe paths (Windows system directories)

**Implementation:**
```python
# providers.py
PROVIDER_FILTERS = {
    'Microsoft-Windows-Kernel-Process': {
        'keywords': 0x10,  # Process events only (not thread events)
        'level': 4,  # WARNING level and above
        'process_whitelist': ['svchost.exe', 'explorer.exe']  # Exclude from collection
    },
    'Microsoft-Windows-Kernel-File': {
        'keywords': 0x80,  # File I/O events
        'path_exclusions': [
            r'C:\\Windows\\System32\\',
            r'C:\\Windows\\SysWOW64\\',
            r'C:\\Program Files\\'
        ]
    }
}
```

### 2. Event Sampling (During Collection)

**Strategy:**
- **Rate Limiting**: Limit events per second per provider
- **Sampling**: Sample high-volume events (e.g., file I/O) at configurable rate
- **Priority Queuing**: High-priority events (process creation, registry persistence) always collected

**Implementation:**
```python
# session_manager.py
SAMPLING_RATES = {
    'Microsoft-Windows-Kernel-File': 0.1,  # 10% sampling for file events
    'Microsoft-Windows-Kernel-Process': 1.0,  # 100% for process events (critical)
    'Microsoft-Windows-Kernel-Registry': 1.0,  # 100% for registry events (critical)
    'Microsoft-Windows-TCPIP': 0.5  # 50% sampling for network events
}
```

### 3. Buffering & Batching

**Strategy:**
- **Local Buffer**: Buffer events locally before transmission
- **Batch Transmission**: Transmit events in batches (100-1000 events per batch)
- **Backpressure Handling**: Drop oldest events if buffer full (fail-open)
- **Offline Capability**: Buffer persists to disk for offline operation

**Implementation:**
```python
# buffer_manager.py
BUFFER_CONFIG = {
    'max_memory_events': 10000,  # Max events in memory buffer
    'max_disk_events': 100000,  # Max events in disk buffer
    'batch_size': 500,  # Events per transmission batch
    'flush_interval_seconds': 5  # Flush buffer every 5 seconds
}
```

### 4. CPU Affinity & Threading

**Strategy:**
- **Dedicated Thread**: ETW collection on dedicated thread (not main agent thread)
- **CPU Affinity**: Pin ETW thread to specific CPU core (reduce context switching)
- **Priority**: Lower thread priority (below normal) to reduce impact
- **Yield**: Yield CPU frequently to prevent starvation

**Implementation:**
```python
# session_manager.py
ETW_THREAD_CONFIG = {
    'cpu_affinity': None,  # Use all CPUs (or specify core)
    'thread_priority': 'BELOW_NORMAL',  # Lower priority
    'yield_interval_events': 100  # Yield after 100 events processed
}
```

### 5. Provider Session Management

**Strategy:**
- **Session Reuse**: Reuse ETW sessions (don't create/destroy frequently)
- **Lazy Provider Start**: Start providers on-demand (not all at once)
- **Provider Health Monitoring**: Monitor provider health, restart if needed
- **Graceful Degradation**: Continue if some providers fail

**Implementation:**
```python
# session_manager.py
SESSION_CONFIG = {
    'session_name': 'RansomEye-Windows-Agent',
    'buffer_size_mb': 64,  # ETW buffer size
    'min_buffers': 2,  # Minimum buffers
    'max_buffers': 64,  # Maximum buffers
    'flush_timer_seconds': 1  # Flush timer
}
```

### 6. Event Parsing Optimization

**Strategy:**
- **Lazy Parsing**: Parse only required fields (not all ETW event data)
- **Field Caching**: Cache frequently accessed fields (process names, paths)
- **Binary Parsing**: Use binary ETW event structures (not XML)
- **Early Filtering**: Filter events before full parsing

**Implementation:**
```python
# event_parser.py
PARSING_CONFIG = {
    'parse_only_required_fields': True,  # Skip optional fields
    'cache_process_names': True,  # Cache process name lookups
    'cache_path_normalization': True,  # Cache path normalization
    'early_filter_enabled': True  # Filter before parsing
}
```

## Validation Requirements

### Event Volume Benchmarks

**Target Metrics:**
- **Idle System**: <100 events/second (baseline)
- **Active System**: <1000 events/second (normal workload)
- **Heavy Workload**: <5000 events/second (peak, with sampling)

**Measurement Method:**
```python
# health_monitor.py
def measure_event_volume():
    """Measure events per second per provider."""
    # Count events over 60-second window
    # Report: provider_id, events_per_second, cpu_percent
```

### CPU / Memory Impact Measurements

**Target Metrics:**
- **CPU Impact**: <5% CPU per core (average)
- **Memory Impact**: <100MB resident memory
- **Peak CPU**: <10% CPU (temporary spikes acceptable)

**Measurement Method:**
```python
# health_monitor.py
def measure_resource_impact():
    """Measure CPU and memory impact."""
    # Use psutil or WMI to measure:
    # - CPU percent (per core and total)
    # - Resident memory (RSS)
    # - Peak memory usage
```

### Provider Failure Handling

**Failure Scenarios:**
1. Provider not available (Windows version mismatch)
2. Provider access denied (insufficient privileges)
3. Provider session failure (ETW session crash)
4. Provider event loss (buffer overflow)

**Handling Strategy:**
```python
# health_monitor.py
def handle_provider_failure(provider_id, error):
    """Handle provider failure gracefully."""
    # 1. Log failure to audit log
    # 2. Mark provider as unavailable
    # 3. Continue operation with other providers
    # 4. Retry provider start after delay (exponential backoff)
    # 5. Emit health event to Core
```

### Session Restart Resilience

**Restart Scenarios:**
1. ETW session crash (unexpected termination)
2. Agent restart (service restart)
3. System reboot (persistent session)

**Resilience Strategy:**
```python
# session_manager.py
def restart_session():
    """Restart ETW session after failure."""
    # 1. Stop existing session (if any)
    # 2. Clear buffers
    # 3. Recreate session
    # 4. Restart all providers
    # 5. Resume event collection
    # 6. Emit session_restarted event
```

### Telemetry Loss Detection

**Detection Methods:**
1. **Sequence Gaps**: Detect missing sequence numbers
2. **Timestamp Gaps**: Detect large time gaps between events
3. **Provider Health**: Monitor provider buffer overflow events
4. **Event Count Discrepancy**: Compare expected vs actual event counts

**Implementation:**
```python
# health_monitor.py
def detect_telemetry_loss():
    """Detect telemetry loss."""
    # 1. Check sequence numbers for gaps
    # 2. Check timestamps for large gaps
    # 3. Monitor ETW buffer overflow events
    # 4. Emit telemetry_loss event if detected
```

## Explicit List of What is NOT Implemented

### 1. Kernel-Mode ETW Collection
- **Status**: NOT IMPLEMENTED
- **Rationale**: User-mode only (no kernel drivers)
- **Impact**: Some advanced memory events may not be available

### 2. Real-Time Event Blocking
- **Status**: NOT IMPLEMENTED
- **Rationale**: Read-only telemetry (no enforcement)
- **Impact**: Events are collected but not blocked

### 3. User-Mode API Hooking
- **Status**: NOT IMPLEMENTED
- **Rationale**: Explicitly forbidden (no hooking)
- **Impact**: Cannot intercept API calls (ETW provides kernel-level events)

### 4. Signature-Based Detection
- **Status**: NOT IMPLEMENTED
- **Rationale**: Explicitly forbidden (no signature matching)
- **Impact**: No hash-based malware detection (events only)

### 5. ML Inference on Endpoint
- **Status**: NOT IMPLEMENTED
- **Rationale**: Explicitly forbidden (no ML inference)
- **Impact**: No local anomaly detection (events sent to Core for analysis)

### 6. WMI Polling
- **Status**: NOT IMPLEMENTED
- **Rationale**: Explicitly forbidden (no polling loops)
- **Impact**: Real-time ETW events only (no periodic WMI queries)

### 7. DLL Injection Detection (Advanced)
- **Status**: PARTIAL
- **Rationale**: Best-effort via ImageLoad events
- **Impact**: Some injection techniques may not be detected

### 8. Process Hollowing Detection (Advanced)
- **Status**: PARTIAL
- **Rationale**: Best-effort via memory events (if available)
- **Impact**: Some hollowing techniques may not be detected

### 9. Encrypted Traffic Analysis
- **Status**: NOT IMPLEMENTED
- **Rationale**: Host-side only (no decryption)
- **Impact**: Only connection intent captured (not payload)

### 10. Registry Hive Analysis
- **Status**: NOT IMPLEMENTED
- **Rationale**: Event-based only (no hive parsing)
- **Impact**: Only registry modifications captured (not full hive state)

## Implementation Dependencies

### Required Python Packages
- `pythonnet` or `pywin32` - Windows API access
- `pywintrace` or custom ETW wrapper - ETW consumer API
- `protobuf` - Event envelope serialization
- `cryptography` - Event signing (ed25519)

### Windows Requirements
- **Windows 7+**: ETW support (all modern Windows versions)
- **Administrator Privileges**: Required for some ETW providers (kernel providers)
- **.NET Framework**: May be required for some ETW libraries

### Performance Requirements
- **CPU**: Multi-core recommended (ETW on dedicated core)
- **Memory**: 100MB+ available for event buffering
- **Disk**: 1GB+ available for offline event buffer

## Security Considerations

### Privilege Requirements
- **Standard User**: Can collect user-mode ETW events
- **Administrator**: Required for kernel-mode ETW providers
- **No Kernel Access**: User-mode only (no kernel drivers)

### Event Signing
- **All Events Signed**: ed25519 signature on every event
- **Signing Key**: Stored securely (encrypted at rest)
- **Key Rotation**: Support for key rotation (future enhancement)

### Data Privacy
- **PII Redaction**: Command lines and file paths may contain PII (redaction in Core)
- **Local Buffering**: Events buffered locally (encrypted at rest)
- **Transmission**: Events transmitted over encrypted channel (TLS)

## Integration Points

### 1. Event Envelope Contract
- **Schema**: Uses canonical event-envelope.schema.json
- **Protobuf**: Uses event-envelope.proto for serialization
- **Integrity**: Hash chain maintained (prev_hash_sha256)

### 2. Normalized Schema
- **Tables**: Maps to process_activity, file_activity, persistence, network_intent tables
- **Foreign Keys**: All events reference raw_events table
- **Timestamps**: All events use RFC3339 UTC timestamps

### 3. Core Integration
- **Ingest Service**: Events sent to Core ingest service
- **Offline Buffering**: Events buffered locally if Core unavailable
- **Retry Logic**: Automatic retry on transmission failure

## Failure Semantics

### Provider Unavailable
- **Behavior**: Log warning, continue with other providers
- **Impact**: Reduced telemetry coverage
- **Recovery**: Retry provider start after delay

### ETW Session Failure
- **Behavior**: Restart session, resume collection
- **Impact**: Temporary event loss during restart
- **Recovery**: Automatic session restart

### Buffer Overflow
- **Behavior**: Drop oldest events (fail-open)
- **Impact**: Event loss (logged)
- **Recovery**: Increase buffer size or reduce event volume

### Core Unavailable
- **Behavior**: Buffer events locally, retry transmission
- **Impact**: Events delayed until Core available
- **Recovery**: Automatic retry with exponential backoff

---

**AUTHORITATIVE**: This design document is the single authoritative source for Windows Agent Deep ETW Telemetry architecture.

**STATUS**: Design complete, ready for implementation approval.
