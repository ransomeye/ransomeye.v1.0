<# 
RansomEye Installer Python3 Preflight Check
AUTHORITATIVE: Enforce python3 availability and minimum version
#>

$minMajor = 3
$minMinor = 9

try {
    $versionOutput = & python3 --version 2>&1
} catch {
    Write-Error "FATAL: python3 is required (>=${minMajor}.${minMinor}) but was not found in PATH."
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL: python3 is required (>=${minMajor}.${minMinor}) but was not found in PATH."
    exit 1
}

if ($versionOutput -match 'Python\s+(\d+)\.(\d+)\.(\d+)') {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    $patch = [int]$Matches[3]
} else {
    Write-Error "FATAL: Unable to parse python3 version from output: $versionOutput"
    exit 1
}

if ($major -lt $minMajor -or ($major -eq $minMajor -and $minor -lt $minMinor)) {
    Write-Error "FATAL: python3 >= ${minMajor}.${minMinor} required, found ${major}.${minor}.${patch}."
    exit 1
}

Write-Host "✓ python3 ${major}.${minor}.${patch} detected (>=${minMajor}.${minMinor})"
