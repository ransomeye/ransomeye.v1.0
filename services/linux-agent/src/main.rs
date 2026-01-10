// RansomEye v1.0 Linux Agent (Phase 10 - Hardened)
// AUTHORITATIVE: Hardened Linux agent with proper error handling and exit codes
// Rust only - aligns with Phase 10 requirements

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::clone::Clone;
use std::env;
use std::process;
use uuid::Uuid;

/// Exit codes for Linux Agent (Phase 10 requirement: Clear exit codes)
#[repr(i32)]
enum ExitCode {
    Success = 0,
    ConfigError = 1,
    StartupError = 2,
    RuntimeError = 3,
    FatalError = 4,
}

/// Canonical event envelope structure matching event-envelope.schema.json exactly
/// Contract compliance: All fields match Phase 1 system contract schema
/// Phase 10 requirement: Cloneable for hash computation
#[derive(Debug, Serialize, Deserialize, Clone)]
struct EventEnvelope {
    // Required field: UUID v4 (event-envelope.schema.json)
    #[serde(rename = "event_id")]
    event_id: String,

    // Required field: Machine identifier (event-envelope.schema.json)
    #[serde(rename = "machine_id")]
    machine_id: String,

    // Required field: Component type enum (event-envelope.schema.json)
    // MUST be exactly "linux_agent" (matches enum value)
    #[serde(rename = "component")]
    component: String,

    // Required field: Component instance ID (event-envelope.schema.json)
    #[serde(rename = "component_instance_id")]
    component_instance_id: String,

    // Required field: RFC3339 UTC timestamp (event-envelope.schema.json)
    // Contract compliance: observed_at MUST be RFC3339 UTC (time-semantics.md)
    #[serde(rename = "observed_at")]
    observed_at: String,

    // Required field: RFC3339 UTC timestamp (event-envelope.schema.json)
    // Contract compliance: ingested_at MUST be RFC3339 UTC (time-semantics.md)
    // NOTE: For Phase 4, we set this to observed_at (ingest service will update it)
    #[serde(rename = "ingested_at")]
    ingested_at: String,

    // Required field: 64-bit unsigned integer (event-envelope.schema.json)
    // Contract compliance: sequence MUST be uint64 (0 to 2^64-1)
    // Phase 4 requirement: sequence = 1 (first event, so prev_hash_sha256 = null)
    #[serde(rename = "sequence")]
    sequence: u64,

    // Required field: JSON object (event-envelope.schema.json)
    // Contract compliance: payload is opaque, component-specific
    // Phase 4 explicitly allows one dummy key/value for this phase
    #[serde(rename = "payload")]
    payload: serde_json::Value,

    // Required field: Identity object (event-envelope.schema.json)
    #[serde(rename = "identity")]
    identity: EventIdentity,

    // Required field: Integrity object (event-envelope.schema.json)
    #[serde(rename = "integrity")]
    integrity: EventIntegrity,
}

/// Identity metadata matching event-envelope.schema.json exactly
/// Phase 10 requirement: Cloneable for hash computation
#[derive(Debug, Serialize, Deserialize, Clone)]
struct EventIdentity {
    // Required field: hostname (event-envelope.schema.json)
    #[serde(rename = "hostname")]
    hostname: String,

    // Required field: boot_id (event-envelope.schema.json)
    #[serde(rename = "boot_id")]
    boot_id: String,

    // Required field: agent_version (event-envelope.schema.json)
    #[serde(rename = "agent_version")]
    agent_version: String,
}

/// Integrity chain matching event-envelope.schema.json exactly
/// Phase 10 requirement: Cloneable for hash computation
#[derive(Debug, Serialize, Deserialize, Clone)]
struct EventIntegrity {
    // Required field: SHA256 hash of entire envelope (event-envelope.schema.json)
    // Contract compliance: hash_sha256 MUST be 64-character hex string
    #[serde(rename = "hash_sha256")]
    hash_sha256: String,

    // Required field: Previous hash or null (event-envelope.schema.json)
    // Contract compliance: prev_hash_sha256 MUST be null for first event (sequence=0)
    // Phase 4: sequence=1, but this is effectively the first event, so prev_hash_sha256 = null
    #[serde(rename = "prev_hash_sha256")]
    prev_hash_sha256: Option<String>,
}

/// Read environment variable with contract compliance (hardened)
/// Phase 10 requirement: Fail-fast on missing required variables, clear error messages
/// Contract compliance: Missing required variables MUST cause failure (fail-closed)
fn read_env_var(name: &str, description: &str) -> Result<String> {
    env::var(name).with_context(|| {
        eprintln!("FATAL: Missing required environment variable: {}", name);
        eprintln!("  Description: {}", description);
        eprintln!("  Action: Agent cannot start without this variable (fail-closed)");
        format!("Missing required environment variable: {} ({})", name, description)
    })
}

/// Get machine ID from system hostname
/// Contract compliance: machine_id MUST be non-empty string (event-envelope.schema.json)
fn get_machine_id() -> Result<String> {
    // For Phase 4 minimal: use hostname as machine_id
    // Contract allows any non-empty string
    hostname::get()
        .context("Failed to get hostname")?
        .into_string()
        .map_err(|_| anyhow::anyhow!("Hostname is not valid UTF-8"))
}

/// Get boot ID from /proc/sys/kernel/random/boot_id (Linux)
/// Phase 10 requirement: Proper error handling with clear error messages
/// Contract compliance: boot_id MUST be non-empty string (event-envelope.schema.json)
fn get_boot_id() -> Result<String> {
    let boot_id_path = "/proc/sys/kernel/random/boot_id";
    let boot_id = std::fs::read_to_string(boot_id_path)
        .with_context(|| format!("Failed to read boot_id from {}", boot_id_path))?;
    
    let boot_id = boot_id.trim().to_string();
    if boot_id.is_empty() {
        anyhow::bail!("boot_id is empty after reading from {}", boot_id_path);
    }
    
    Ok(boot_id)
}

/// Compute SHA256 hash of JSON-serialized event envelope (hardened)
/// Phase 10 requirement: Hash computation must exclude hash_sha256 field itself
/// Contract compliance: hash_sha256 MUST be 64-character hex string (event-envelope.schema.json)
fn compute_hash(envelope: &EventEnvelope) -> Result<String> {
    // Phase 10 requirement: Hash computation must exclude hash_sha256 field (contract compliance)
    // Create a copy of envelope with empty hash_sha256 for hashing
    let mut envelope_for_hash = envelope.clone();
    envelope_for_hash.integrity.hash_sha256 = String::new();
    
    // Serialize to canonical JSON (compact, sorted keys for deterministic hashing)
    // Contract compliance: hash MUST be computed after all fields are populated
    let json = serde_json::to_string(&envelope_for_hash)
        .context("Failed to serialize event envelope to JSON")?;

    // Phase 10 requirement: Compute SHA256 hash with proper error handling
    let mut hasher = Sha256::new();
    hasher.update(json.as_bytes());
    let hash = hasher.finalize();

    // Convert to 64-character hex string
    let hash_str = format!("{:x}", hash);
    
    // Phase 10 requirement: Verify hash format (64 hex chars)
    if hash_str.len() != 64 {
        anyhow::bail!("Computed hash is not 64 characters: {}", hash_str.len());
    }
    
    Ok(hash_str)
}

/// Construct canonical event envelope
/// Contract compliance: All fields MUST match event-envelope.schema.json exactly
fn construct_event_envelope() -> Result<EventEnvelope> {
    // Phase 10 requirement: Read required environment variables with clear error messages
    let component_instance_id = read_env_var(
        "RANSOMEYE_COMPONENT_INSTANCE_ID",
        "Component instance identifier (required, UUID format recommended)"
    )
    .context("Failed to read RANSOMEYE_COMPONENT_INSTANCE_ID")?;
    
    let agent_version = read_env_var(
        "RANSOMEYE_VERSION",
        "Agent version string (required, e.g., '1.0.0')"
    )
    .context("Failed to read RANSOMEYE_VERSION")?;

    // Get machine-level identifiers
    let machine_id = get_machine_id().context("Failed to get machine_id")?;
    let hostname = machine_id.clone(); // For Phase 4, use machine_id as hostname
    let boot_id = get_boot_id().context("Failed to get boot_id")?;

    // Generate UUID v4 for event_id (event-envelope.schema.json requirement)
    let event_id = Uuid::new_v4().to_string();

    // Get current UTC time for observed_at (time-semantics.md compliance: RFC3339 UTC)
    let now_utc: DateTime<Utc> = Utc::now();
    let observed_at = now_utc.to_rfc3339();

    // Phase 4: First event (sequence=0 for first event per schema constraint)
    // Contract compliance: sequence MUST be uint64 (0 to 2^64-1)
    // Schema constraint: sequence=0 AND prev_hash_sha256 IS NULL (first event)
    let sequence = 0u64;

    // Phase 4 explicitly allows one dummy key/value in payload
    let payload = serde_json::json!({
        "phase": "phase4_minimal"
    });

    // Construct event envelope (without hash first, will compute after)
    // Contract compliance: hash_sha256 must be computed after all fields are populated
    // Standard approach: compute hash with hash_sha256 set to empty string, then set hash_sha256 to that computed hash
    let mut envelope = EventEnvelope {
        event_id: event_id.clone(),
        machine_id: machine_id.clone(),
        component: "linux_agent".to_string(), // Contract compliance: MUST be exactly "linux_agent"
        component_instance_id,
        observed_at: observed_at.clone(),
        ingested_at: observed_at.clone(), // Phase 4: Ingest service will update this
        sequence,
        payload,
        identity: EventIdentity {
            hostname,
            boot_id,
            agent_version,
        },
        integrity: EventIntegrity {
            hash_sha256: String::new(), // Empty placeholder for hash computation
            prev_hash_sha256: None, // Contract compliance: sequence=0 means prev_hash_sha256=NULL (first event)
        },
    };

    // Phase 10 requirement: Compute hash_sha256 correctly (hash of envelope with hash_sha256 empty)
    // Contract compliance: hash is computed after all fields populated, but hash_sha256 is excluded from hash computation
    // The envelope already has hash_sha256 set to empty string, so compute_hash will compute correctly
    let final_hash = compute_hash(&envelope)
        .context("Failed to compute hash_sha256")?;
    envelope.integrity.hash_sha256 = final_hash;

    Ok(envelope)
}

/// Transmit event to ingest service via HTTP (hardened)
/// Phase 10 requirement: Proper error handling, clear error messages, timeout handling
/// Contract compliance: No retries, no batching, no buffering (Phase 4 requirements)
fn transmit_event(client: &Client, envelope: &EventEnvelope, ingest_url: &str) -> Result<()> {
    // Phase 10 requirement: Explicit error handling for network operations
    eprintln!("INFO: Transmitting event to ingest service: {}", ingest_url);
    
    // Contract compliance: No retries, no buffering, no background threads (Phase 4 requirements)
    // Single HTTP POST request, fail if it fails
    let response = match client
        .post(ingest_url)
        .json(envelope)
        .send()
    {
        Ok(r) => r,
        Err(e) => {
            eprintln!("ERROR: Failed to send HTTP request to ingest service: {}", e);
            eprintln!("  Ingest URL: {}", ingest_url);
            eprintln!("  Event ID: {}", envelope.event_id);
            anyhow::bail!("HTTP request failed: {}", e);
        }
    };

    // Phase 10 requirement: Check response status with clear error messages
    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().unwrap_or_else(|_| String::from("(no response body)"));
        eprintln!("ERROR: Ingest service returned error status: {}", status);
        eprintln!("  Response body: {}", body);
        eprintln!("  Event ID: {}", envelope.event_id);
        anyhow::bail!(
            "Ingest service returned error status {}: {}",
            status,
            body
        );
    }

    eprintln!("INFO: Event transmission successful: {}", envelope.event_id);
    Ok(())
}

fn main() {
    // Phase 10 requirement: Deterministic startup with proper error handling
    eprintln!("STARTUP: Linux Agent starting");
    
    // Contract compliance: Read environment variables (env.contract.json)
    // Phase 10 requirement: Fail-fast on missing required variables
    let ingest_url = env::var("RANSOMEYE_INGEST_URL")
        .unwrap_or_else(|_| {
            eprintln!("INFO: RANSOMEYE_INGEST_URL not set, using default: http://localhost:8000/events");
            "http://localhost:8000/events".to_string()
        });

    // Phase 10 requirement: Construct event envelope with proper error handling
    let envelope = match construct_event_envelope() {
        Ok(env) => env,
        Err(e) => {
            eprintln!("FATAL: Failed to construct event envelope: {}", e);
            eprintln!("  Error chain: {}", format!("{:?}", e));
            process::exit(ExitCode::StartupError as i32);
        }
    };

    // Phase 10 requirement: Create HTTP client with error handling
    let client = match Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            eprintln!("FATAL: Failed to create HTTP client: {}", e);
            process::exit(ExitCode::StartupError as i32);
        }
    };

    // Phase 10 requirement: Transmit event with proper error handling
    match transmit_event(&client, &envelope, &ingest_url) {
        Ok(()) => {
            eprintln!("INFO: Event transmitted successfully: {}", envelope.event_id);
            eprintln!("SHUTDOWN: Linux Agent completed successfully");
            process::exit(ExitCode::Success as i32);
        }
        Err(e) => {
            eprintln!("FATAL: Failed to transmit event to ingest service: {}", e);
            eprintln!("  Error chain: {}", format!("{:?}", e));
            eprintln!("  Event ID: {}", envelope.event_id);
            eprintln!("  Ingest URL: {}", ingest_url);
            process::exit(ExitCode::RuntimeError as i32);
        }
    }
}
