# RansomEye v1.0 Windows Agent - Command Acceptance Gate
# AUTHORITATIVE: Single command intake gate with strict validation (NO ASSUMPTIONS)
# PowerShell 5.1+ only

param(
    [Parameter(Mandatory=$true)]
    [hashtable]$Command,
    
    [Parameter(Mandatory=$true)]
    [string]$TREPublicKeyPath,
    
    [Parameter(Mandatory=$true)]
    [string]$TREKeyId,
    
    [Parameter(Mandatory=$true)]
    [string]$AgentId,
    
    [Parameter(Mandatory=$true)]
    [string]$AuditLogPath
)

# Import required modules
Add-Type -AssemblyName System.Security.Cryptography

# Command acceptance gate pipeline
function Receive-Command {
    param([hashtable]$Command)
    
    $CommandId = $Command.command_id
    
    try {
        # Step 1: Schema validation
        Test-CommandSchema -Command $Command
        
        # Step 2: Timestamp + nonce freshness check
        Test-CommandFreshness -Command $Command
        
        # Step 3: ed25519 signature verification
        Test-CommandSignature -Command $Command -PublicKeyPath $TREPublicKeyPath
        
        # Step 4: Issuer trust verification (TRE public key)
        Test-CommandIssuer -Command $Command -ExpectedKeyId $TREKeyId
        
        # Step 5: RBAC + role assertion validation (embedded)
        Test-CommandRBAC -Command $Command
        
        # Step 6: HAF approval presence (if required)
        Test-CommandHAFApproval -Command $Command
        
        # Step 7: Idempotency check (command_id)
        Test-CommandIdempotency -CommandId $CommandId
        
        # Step 8: Rate limiting
        Test-CommandRateLimit
        
        # PHASE 4: Step 9: Policy authority validation
        Test-CommandPolicyAuthority -Command $Command
        
        # All checks passed
        Write-AuditLog -EventType "command_received" -CommandId $CommandId -Outcome "SUCCESS"
        
        return $Command
        
    } catch {
        Write-AuditLog -EventType "command_rejected" -CommandId $CommandId -Outcome "REJECTED" -Reason $_.Exception.Message
        throw
    }
}

function Test-CommandSchema {
    param([hashtable]$Command)
    
    $RequiredFields = @(
        'command_id', 'action_type', 'target', 'incident_id',
        'tre_mode', 'issued_by_user_id', 'issued_by_role',
        'issued_at', 'expires_at', 'rollback_token', 'signature'
    )
    
    foreach ($Field in $RequiredFields) {
        if (-not $Command.ContainsKey($Field)) {
            throw "Missing required field: $Field"
        }
    }
    
    # Validate action_type enum
    $ValidActionTypes = @(
        'BLOCK_PROCESS', 'BLOCK_NETWORK_CONNECTION', 'TEMPORARY_FIREWALL_RULE',
        'QUARANTINE_FILE', 'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
        'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
    )
    if ($ValidActionTypes -notcontains $Command.action_type) {
        throw "Invalid action_type: $($Command.action_type)"
    }
    
    # Validate tre_mode enum
    $ValidModes = @('DRY_RUN', 'GUARDED_EXEC', 'FULL_ENFORCE')
    if ($ValidModes -notcontains $Command.tre_mode) {
        throw "Invalid tre_mode: $($Command.tre_mode)"
    }
    
    # Validate issued_by_role enum
    $ValidRoles = @('SUPER_ADMIN', 'SECURITY_ANALYST', 'POLICY_MANAGER', 'IT_ADMIN', 'AUDITOR')
    if ($ValidRoles -notcontains $Command.issued_by_role) {
        throw "Invalid issued_by_role: $($Command.issued_by_role)"
    }
}

function Test-CommandFreshness {
    param([hashtable]$Command)
    
    $IssuedAt = [DateTime]::Parse($Command.issued_at)
    $ExpiresAt = [DateTime]::Parse($Command.expires_at)
    $Now = [DateTime]::UtcNow
    
    if ($ExpiresAt -lt $Now) {
        throw "Command expired: expires_at=$ExpiresAt, now=$Now"
    }
    
    $Skew = [Math]::Abs(($IssuedAt - $Now).TotalSeconds)
    if ($Skew -gt 60) {
        throw "Clock skew too large: $Skew seconds (max 60 seconds)"
    }
}

function Test-CommandSignature {
    param([hashtable]$Command, [string]$PublicKeyPath)
    
    # PHASE 4: Real ed25519 signature verification (replaces placeholder)
    # Use Python helper script for ed25519 verification
    
    # Extract signature
    $Signature = $Command.signature
    if (-not $Signature) {
        throw "Missing signature field"
    }
    
    # Create command payload copy without signature fields (for verification)
    $CommandCopy = $Command.Clone()
    $CommandCopy.Remove('signature')
    $CommandCopy.Remove('signing_key_id')
    $CommandCopy.Remove('signing_algorithm')
    $CommandCopy.Remove('signed_at')
    
    # Serialize command payload to JSON
    $CommandPayloadJson = $CommandCopy | ConvertTo-Json -Compress -Depth 10
    
    # Find Python verifier script (in same directory as this script)
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $VerifierScript = Join-Path $ScriptDir "verify_signature.py"
    
    if (-not (Test-Path $VerifierScript)) {
        throw "PHASE 4: Signature verifier script not found: $VerifierScript"
    }
    
    # Call Python verifier script
    $PythonArgs = @(
        $VerifierScript,
        "--command-payload", $CommandPayloadJson,
        "--signature", $Signature,
        "--public-key-path", $PublicKeyPath
    )
    
    try {
        $Result = & python $PythonArgs 2>&1
        $ExitCode = $LASTEXITCODE
        
        if ($ExitCode -ne 0) {
            throw "PHASE 4: Signature verification failed: $Result"
        }
        
        if ($Result -ne "SUCCESS") {
            throw "PHASE 4: Signature verification failed: $Result"
        }
    } catch {
        throw "PHASE 4: Signature verification error: $_"
    }
}

function Test-CommandIssuer {
    param([hashtable]$Command, [string]$ExpectedKeyId)
    
    $SigningKeyId = $Command.signing_key_id
    if ($SigningKeyId -ne $ExpectedKeyId) {
        throw "Signing key ID mismatch: expected $ExpectedKeyId, got $SigningKeyId"
    }
}

function Test-CommandRBAC {
    param([hashtable]$Command)
    
    $Role = $Command.issued_by_role
    $UserId = $Command.issued_by_user_id
    
    if (-not $Role) {
        throw "Missing issued_by_role"
    }
    
    if (-not $UserId) {
        throw "Missing issued_by_user_id"
    }
    
    $ValidRoles = @('SUPER_ADMIN', 'SECURITY_ANALYST', 'POLICY_MANAGER', 'IT_ADMIN', 'AUDITOR')
    if ($ValidRoles -notcontains $Role) {
        throw "Invalid role: $Role"
    }
}

function Test-CommandHAFApproval {
    param([hashtable]$Command)
    
    $ActionType = $Command.action_type
    $TREMode = $Command.tre_mode
    
    $DestructiveActions = @(
        'ISOLATE_HOST', 'LOCK_USER', 'DISABLE_SERVICE',
        'MASS_PROCESS_KILL', 'NETWORK_SEGMENT_ISOLATION'
    )
    
    if ($DestructiveActions -contains $ActionType -and $TREMode -eq 'FULL_ENFORCE') {
        if (-not $Command.approval_id) {
            throw "HAF approval required for DESTRUCTIVE action $ActionType in FULL_ENFORCE mode"
        }
    }
}

function Test-CommandIdempotency {
    param([string]$CommandId)
    
    # Nonce cache for replay protection
    $NonceCachePath = "$env:TEMP\ransomeye_nonce_cache.json"
    $NonceCache = @()
    
    if (Test-Path $NonceCachePath) {
        $NonceCache = Get-Content $NonceCachePath | ConvertFrom-Json
    }
    
    if ($NonceCache -contains $CommandId) {
        throw "Command ID already seen: $CommandId (replay attack)"
    }
    
    $NonceCache += $CommandId
    
    # Keep only last 1000 entries
    if ($NonceCache.Count -gt 1000) {
        $NonceCache = $NonceCache[-1000..-1]
    }
    
    $NonceCache | ConvertTo-Json | Set-Content $NonceCachePath
}

function Test-CommandRateLimit {
    # Rate limiting: 100 commands per minute max
    $RateLimitPath = "$env:TEMP\ransomeye_rate_limit.json"
    $RateLimitData = @{
        timestamps = @()
    }
    
    if (Test-Path $RateLimitPath) {
        $RateLimitData = Get-Content $RateLimitPath | ConvertFrom-Json
    }
    
    $Now = [DateTime]::UtcNow
    $OneMinuteAgo = $Now.AddMinutes(-1)
    
    # Remove old timestamps
    $RateLimitData.timestamps = $RateLimitData.timestamps | Where-Object { [DateTime]::Parse($_) -gt $OneMinuteAgo }
    
    if ($RateLimitData.timestamps.Count -ge 100) {
        throw "Rate limit exceeded: $($RateLimitData.timestamps.Count) commands in last minute"
    }
    
    $RateLimitData.timestamps += $Now.ToString("o")
    $RateLimitData | ConvertTo-Json | Set-Content $RateLimitPath
}

function Write-AuditLog {
    param(
        [string]$EventType,
        [string]$CommandId,
        [string]$Outcome,
        [string]$Reason = $null
    )
    
    $Event = @{
        event_type = $EventType
        agent_id = $AgentId
        command_id = $CommandId
        outcome = $Outcome
        timestamp = [DateTime]::UtcNow.ToString("o")
        reason = $Reason
    }
    
    $EventJson = $Event | ConvertTo-Json -Compress
    Add-Content -Path $AuditLogPath -Value $EventJson
}

# Main execution
try {
    $ValidatedCommand = Receive-Command -Command $Command
    return $ValidatedCommand
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
