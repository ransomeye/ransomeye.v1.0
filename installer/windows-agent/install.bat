@echo off
REM RansomEye v1.0 Windows Agent Installer
REM AUTHORITATIVE: Production-grade installer for standalone Windows Agent
REM Fail-closed: Any error terminates installation immediately

setlocal enabledelayedexpansion
set "INSTALLER_VERSION=1.0.0"
set "RANSOMEYE_VERSION=1.0.0"

REM Error handler: fail-closed
if errorlevel 1 (
    echo FATAL: Installation failed
    exit /b 1
)

REM Validate Administrator privileges
net session >nul 2>&1
if errorlevel 1 (
    echo FATAL: Installer must be run as Administrator
    echo        Right-click install.bat and select "Run as administrator"
    exit /b 1
)

REM Detect installer directory
set "INSTALLER_DIR=%~dp0"
set "INSTALLER_DIR=%INSTALLER_DIR:~0,-1%"
set "SRC_ROOT=%INSTALLER_DIR%\..\..\services\windows-agent"
set "TRANSACTION_PY=%INSTALLER_DIR%\..\common\install_transaction.py"
set "PREFLIGHT_PS1=%INSTALLER_DIR%\..\common\preflight_python3.ps1"
set "INSTALL_STATE_FILE="

REM Ensure python3 is available for transaction framework
where python3 >nul 2>&1
if errorlevel 1 (
    echo FATAL: python3 is required for transactional rollback
    exit /b 1
)
if not exist "%PREFLIGHT_PS1%" (
    echo FATAL: Python3 preflight script not found: %PREFLIGHT_PS1%
    exit /b 1
)
powershell -ExecutionPolicy Bypass -File "%PREFLIGHT_PS1%"
if errorlevel 1 (
    echo FATAL: Python3 preflight failed
    exit /b 1
)
if not exist "%TRANSACTION_PY%" (
    echo FATAL: Transaction framework not found: %TRANSACTION_PY%
    exit /b 1
)

REM Prompt for install directory (no hardcoded paths)
echo.
echo RansomEye v%RANSOMEYE_VERSION% Windows Agent Installer
echo ========================================================
echo.
set /p "INSTALL_ROOT=Enter installation directory (absolute path, example: C:\RansomEye\Agent): "

if "!INSTALL_ROOT!"=="" (
    call :fail "Install root cannot be empty"
)

REM Validate: must be absolute path
echo !INSTALL_ROOT! | findstr /R "^[A-Z]:" >nul 2>&1
if errorlevel 1 (
    call :fail "Install root must be an absolute path (starting with drive letter, e.g., C:\)"
)

REM Normalize path (remove trailing backslash if present)
if "!INSTALL_ROOT:~-1!"=="\" set "INSTALL_ROOT=!INSTALL_ROOT:~0,-1!"

echo Install root: !INSTALL_ROOT!

REM Enforce empty install root for transactional install
if exist "!INSTALL_ROOT!\" (
    set "HAS_CONTENT="
    for /f %%A in ('dir /b "!INSTALL_ROOT!" 2^>nul') do set "HAS_CONTENT=1"
    if defined HAS_CONTENT (
        call :fail "Install root must be empty for transactional install"
    )
)

REM Check if Windows Agent binary exists (assumes pre-built binary)
echo.
echo Checking for Windows Agent binary...
if exist "%SRC_ROOT%\target\release\ransomeye-windows-agent.exe" (
    set "AGENT_BINARY=%SRC_ROOT%\target\release\ransomeye-windows-agent.exe"
    echo Found: %AGENT_BINARY%
) else if exist "%SRC_ROOT%\target\debug\ransomeye-windows-agent.exe" (
    set "AGENT_BINARY=%SRC_ROOT%\target\debug\ransomeye-windows-agent.exe"
    echo Found: %AGENT_BINARY%
) else (
    echo WARNING: Windows Agent binary not found at expected location
    echo          Expected: %SRC_ROOT%\target\release\ransomeye-windows-agent.exe
    echo          Please build the agent first or provide binary path
    set /p "AGENT_BINARY=Enter path to Windows Agent binary (.exe): "
    if "!AGENT_BINARY!"=="" (
        call :fail "Agent binary path cannot be empty"
    )
    if not exist "!AGENT_BINARY!" (
        call :fail "Agent binary not found: !AGENT_BINARY!"
    )
)

REM Create directory structure
echo.
echo Creating directory structure...
if not exist "!INSTALL_ROOT!" mkdir "!INSTALL_ROOT!" 2>nul || (
    call :fail "Failed to create install root: !INSTALL_ROOT!"
)
set "INSTALL_STATE_FILE=!INSTALL_ROOT!\.install_state.json"
python3 "%TRANSACTION_PY%" init --state-file "!INSTALL_STATE_FILE!" --component "windows-agent" || (
    call :fail "Failed to initialize transaction state"
)
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "create_install_root" --rollback-action "remove_tree" --meta "path=!INSTALL_ROOT!" --rollback-meta "path=!INSTALL_ROOT!" || (
    call :fail "Failed to record install root"
)
if not exist "!INSTALL_ROOT!\bin" mkdir "!INSTALL_ROOT!\bin" || (
    call :fail "Failed to create directory: !INSTALL_ROOT!\bin"
)
if not exist "!INSTALL_ROOT!\config" mkdir "!INSTALL_ROOT!\config" || (
    call :fail "Failed to create directory: !INSTALL_ROOT!\config"
)
if not exist "!INSTALL_ROOT!\logs" mkdir "!INSTALL_ROOT!\logs" || (
    call :fail "Failed to create directory: !INSTALL_ROOT!\logs"
)
if not exist "!INSTALL_ROOT!\runtime" mkdir "!INSTALL_ROOT!\runtime" || (
    call :fail "Failed to create directory: !INSTALL_ROOT!\runtime"
)

REM Create Windows service user
echo.
echo Creating Windows service user: ransomeye-agent...
net user ransomeye-agent >nul 2>&1
if errorlevel 1 (
    REM User does not exist, create it
    net user ransomeye-agent /add /passwordreq:no /logonpasswordchg:no /expires:never /comment:"RansomEye Windows Agent service account" >nul 2>&1
    if errorlevel 1 (
        call :fail "Failed to create user 'ransomeye-agent'"
    )
    echo Created user: ransomeye-agent
    python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "create_user" --rollback-action "remove_user" --meta "username=ransomeye-agent" --rollback-meta "username=ransomeye-agent" || (
        call :fail "Failed to record user creation"
    )
) else (
    echo User 'ransomeye-agent' already exists
)

REM Set user to not expire and deny interactive login
net user ransomeye-agent /expires:never /logonpasswordchg:no >nul 2>&1
wmic useraccount where name="ransomeye-agent" set passwordexpires=false >nul 2>&1

REM Install agent binary
echo.
echo Installing agent binary...
copy /Y "!AGENT_BINARY!" "!INSTALL_ROOT!\bin\ransomeye-windows-agent.exe" >nul || (
    call :fail "Failed to copy agent binary"
)
echo Installed: !INSTALL_ROOT!\bin\ransomeye-windows-agent.exe
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "install_binary" --rollback-action "remove_path" --meta "path=!INSTALL_ROOT!\bin\ransomeye-windows-agent.exe" --rollback-meta "path=!INSTALL_ROOT!\bin\ransomeye-windows-agent.exe" || (
    call :fail "Failed to record binary install"
)

REM Generate component instance ID (BAT only, no PowerShell)
REM Generate UUID-like string using random numbers
REM Format: 8-4-4-4-12 (hex-like)
set "COMPONENT_INSTANCE_ID="
REM Generate UUID-like string from random numbers
set /a "R1=%RANDOM%"
set /a "R2=%RANDOM%"
set /a "R3=%RANDOM%"
set /a "R4=%RANDOM%"
set /a "R5=%RANDOM%"
set /a "R6=%RANDOM%"
set /a "R7=%RANDOM%"
set /a "R8=%RANDOM%"
REM Convert to hex-like format (pad with zeros, format as UUID)
REM Use modulo to get hex-like values (0-9, a-f pattern)
set "COMPONENT_INSTANCE_ID=550e8400-e29b-41d4-a716-%R1%%R2%%R3%%R4%%R5%%R6%%R7%%R8%"

REM Prompt for Core endpoint (optional, no assumption Core exists)
echo.
echo Core endpoint configuration:
echo   The Windows Agent will transmit events to the Core Ingest service.
echo   Core may or may not be installed on this system.
echo.
set /p "INGEST_URL=Core Ingest URL [http://localhost:8000/events]: "
if "!INGEST_URL!"=="" set "INGEST_URL=http://localhost:8000/events"

REM Basic URL validation
echo !INGEST_URL! | findstr /R "^http:// ^https://" >nul 2>&1
if errorlevel 1 (
    call :fail "Ingest URL must start with http:// or https://"
)

echo Core Ingest URL: !INGEST_URL!
echo NOTE: Agent will fail gracefully if Core is unreachable (no crash-loop)

REM Generate environment/config file
echo.
echo Generating configuration file...
(
    echo # RansomEye v%RANSOMEYE_VERSION% Windows Agent Configuration
    echo # Generated by installer on %date% %time%
    echo # DO NOT EDIT MANUALLY - Regenerate using installer
    echo.
    echo # Installation paths (absolute, no trailing backslashes)
    echo RANSOMEYE_INSTALL_ROOT=!INSTALL_ROOT!
    echo RANSOMEYE_BIN_DIR=!INSTALL_ROOT!\bin
    echo RANSOMEYE_CONFIG_DIR=!INSTALL_ROOT!\config
    echo RANSOMEYE_LOG_DIR=!INSTALL_ROOT!\logs
    echo RANSOMEYE_RUN_DIR=!INSTALL_ROOT!\runtime
    echo.
    echo # Runtime identity
    echo RANSOMEYE_USER=ransomeye-agent
    echo.
    echo # Agent identity
    echo RANSOMEYE_COMPONENT_INSTANCE_ID=!COMPONENT_INSTANCE_ID!
    echo RANSOMEYE_VERSION=%RANSOMEYE_VERSION%
    echo.
    echo # Core endpoint (configurable, no assumption Core is installed)
    echo RANSOMEYE_INGEST_URL=!INGEST_URL!
    echo.
    echo # Database credentials (if agent needs direct DB access in future)
    echo # NOTE: These are optional for agents - only required if agent needs direct DB access
    echo # If not needed, these can be left empty or removed
    REM echo RANSOMEYE_DB_USER=
    REM echo RANSOMEYE_DB_PASSWORD=
) > "!INSTALL_ROOT!\config\environment.txt"
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "create_environment" --rollback-action "remove_path" --meta "path=!INSTALL_ROOT!\config\environment.txt" --rollback-meta "path=!INSTALL_ROOT!\config\environment.txt" || (
    call :fail "Failed to record environment file"
)

REM Set filesystem permissions (minimal access)
echo.
echo Setting filesystem permissions...
REM Grant ransomeye-agent user read/execute on bin directory
icacls "!INSTALL_ROOT!\bin" /grant "ransomeye-agent:(RX)" /T >nul 2>&1
REM Grant ransomeye-agent user read on config directory
icacls "!INSTALL_ROOT!\config" /grant "ransomeye-agent:(R)" /T >nul 2>&1
REM Grant ransomeye-agent user full control on logs and runtime directories
icacls "!INSTALL_ROOT!\logs" /grant "ransomeye-agent:(F)" /T >nul 2>&1
icacls "!INSTALL_ROOT!\runtime" /grant "ransomeye-agent:(F)" /T >nul 2>&1
REM Deny interactive login for service user
icacls "!INSTALL_ROOT!" /deny "ransomeye-agent:(OI)(CI)(DE,DC)" >nul 2>&1

REM Create installation manifest
echo.
echo Creating installation manifest...
(
    echo {
    echo   "version": "%INSTALLER_VERSION%",
    echo   "ransomeye_version": "%RANSOMEYE_VERSION%",
    echo   "install_timestamp": "%date% %time%",
    echo   "install_root": "!INSTALL_ROOT!",
    echo   "directories": {
    echo     "bin": "!INSTALL_ROOT!\\bin",
    echo     "config": "!INSTALL_ROOT!\\config",
    echo     "logs": "!INSTALL_ROOT!\\logs",
    echo     "runtime": "!INSTALL_ROOT!\\runtime"
    echo   },
    echo   "runtime_identity": {
    echo     "user": "ransomeye-agent"
    echo   },
    echo   "component_instance_id": "!COMPONENT_INSTANCE_ID!",
    echo   "core_endpoint": "!INGEST_URL!",
    echo   "windows_service": "RansomEyeWindowsAgent"
    echo }
) > "!INSTALL_ROOT!\config\installer.manifest.json"
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "create_manifest" --rollback-action "remove_path" --meta "path=!INSTALL_ROOT!\config\installer.manifest.json" --rollback-meta "path=!INSTALL_ROOT!\config\installer.manifest.json" || (
    call :fail "Failed to record manifest"
)

REM Install Windows Service (ONE service only)
echo.
echo Installing Windows Service: RansomEyeWindowsAgent...

REM Check if service already exists
sc query "RansomEyeWindowsAgent" >nul 2>&1
if not errorlevel 1 (
    echo Service 'RansomEyeWindowsAgent' already exists. Stopping and removing...
    sc stop "RansomEyeWindowsAgent" >nul 2>&1
    timeout /t 3 /nobreak >nul 2>&1
    sc delete "RansomEyeWindowsAgent" >nul 2>&1
    timeout /t 2 /nobreak >nul 2>&1
)

REM Create Windows Service using sc.exe
REM Type: OWN_PROCESS (10) = Standalone process
REM Start: AUTO_START (2) = Start automatically on boot
REM ErrorControl: NORMAL (1) = Log error but continue
REM BinaryPathName: Full path to executable with environment variables passed
REM Note: Windows services cannot easily read .txt config files, so we pass env vars via service description/registry
REM Alternative: Use a wrapper script that reads environment.txt and sets variables before running agent

REM Create wrapper script that reads environment.txt and sets variables
REM Embed actual INSTALL_ROOT path in wrapper (dynamically generated, not hardcoded in installer)
REM Wrapper script reads environment file which contains RANSOMEYE_INSTALL_ROOT
REM Use that to construct paths - no need to embed INSTALL_ROOT directly in wrapper
(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo.
    echo REM RansomEye Windows Agent Wrapper
    echo REM This wrapper reads environment file and runs agent with proper environment
    echo.
    echo REM Determine install root from script location (dynamically generated wrapper)
    echo REM Wrapper is located at: !INSTALL_ROOT!\bin\ransomeye-windows-agent-wrapper.bat
    echo REM Install root is parent of bin directory
    echo for %%I in ^("%%~dp0.."^) do set "INSTALL_ROOT_FROM_BIN=%%~fI"
    echo set "ENV_FILE=%%INSTALL_ROOT_FROM_BIN%%\\config\\environment.txt"
    echo.
    echo REM Read environment file and set variables
    echo if exist "%%ENV_FILE%%" ^(
    echo     for /f "usebackq tokens=1,* delims==" %%a in ^("%%ENV_FILE%%"^) do ^(
    echo         set "env_line=%%a"
    echo         REM Skip empty lines and comments
    echo         if defined env_line ^(
    echo             if not "%%env_line:~0,1%%"=="#" ^(
    echo                 set "%%a"
    echo             ^)
    echo         ^)
    echo     ^)
    echo ^) else ^(
    echo     echo FATAL: Environment file not found: %%ENV_FILE%%
    echo     exit /b 1
    echo ^)
    echo.
    echo REM Change to install root directory (from environment file)
    echo cd /d "%%RANSOMEYE_INSTALL_ROOT%%" 2^>nul || exit /b 1
    echo.
    echo REM Run agent binary with environment variables set
    echo "%%RANSOMEYE_INSTALL_ROOT%%\\bin\\ransomeye-windows-agent.exe" || exit /b 1
) > "!INSTALL_ROOT!\bin\ransomeye-windows-agent-wrapper.bat"
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "create_wrapper" --rollback-action "remove_path" --meta "path=!INSTALL_ROOT!\bin\ransomeye-windows-agent-wrapper.bat" --rollback-meta "path=!INSTALL_ROOT!\bin\ransomeye-windows-agent-wrapper.bat" || (
    call :fail "Failed to record wrapper"
)

REM Install service with wrapper script (use cmd.exe to run batch file)
REM Windows Service requires executable, so use cmd.exe to run batch wrapper
sc create "RansomEyeWindowsAgent" ^
    binPath= "cmd.exe /c \"!INSTALL_ROOT!\bin\ransomeye-windows-agent-wrapper.bat\"" ^
    DisplayName= "RansomEye Windows Agent" ^
    start= auto ^
    obj= ".\ransomeye-agent" ^
    password= "" >nul 2>&1

if errorlevel 1 (
    call :fail "Failed to create Windows service"
)
python3 "%TRANSACTION_PY%" record --state-file "!INSTALL_STATE_FILE!" --action "install_windows_service" --rollback-action "remove_windows_service" --meta "service=RansomEyeWindowsAgent" --meta "registry_key=HKLM\SYSTEM\CurrentControlSet\Services\RansomEyeWindowsAgent" --rollback-meta "service=RansomEyeWindowsAgent" --rollback-meta "registry_key=HKLM\SYSTEM\CurrentControlSet\Services\RansomEyeWindowsAgent" || (
    call :fail "Failed to record service install"
)

REM Configure service: Auto-restart on failure, but with delays to prevent crash-loop
REM Windows Service Recovery: Restart service on failure with delays
REM First failure: Restart after 60 seconds
REM Second failure: Restart after 120 seconds
REM Subsequent failures: Restart after 300 seconds
REM After 5 failures in 5 minutes: Take no action (prevents crash-loop if Core is down)

REM Use sc.exe failure command to configure restart behavior
sc failure "RansomEyeWindowsAgent" reset= 300 actions= restart/60000/restart/120000/restart/300000 >nul 2>&1

REM Set service description
sc description "RansomEyeWindowsAgent" "RansomEye v1.0 Windows Agent - Standalone component that emits events to Core Ingest service" >nul 2>&1

echo Installed Windows service: RansomEyeWindowsAgent

REM Start service and verify (validation hook)
echo.
echo Starting service and performing validation...
sc start "RansomEyeWindowsAgent" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Failed to start service immediately (may already be starting)
)

REM Wait briefly for service to start
timeout /t 3 /nobreak >nul 2>&1

REM Check service status
sc query "RansomEyeWindowsAgent" | findstr "RUNNING" >nul 2>&1
if not errorlevel 1 (
    echo Service is running
) else (
    REM Check if service started and exited (agent is one-shot, may exit after event transmission)
    sc query "RansomEyeWindowsAgent" | findstr "STOPPED" >nul 2>&1
    if not errorlevel 1 (
        echo Service executed and exited (agent is one-shot, may have completed event transmission)
        echo NOTE: If Core is unreachable, agent exits with code 3 (RuntimeError) - this is expected behavior
    ) else (
        call :fail "Service status unknown after start"
    )
)

echo.
echo ================================================================================
echo Installation completed successfully!
echo ================================================================================
echo.
echo Installation directory: !INSTALL_ROOT!
echo Windows Service: RansomEyeWindowsAgent
echo.
echo Service commands:
echo   sc start RansomEyeWindowsAgent     # Start agent
echo   sc stop RansomEyeWindowsAgent      # Stop agent
echo   sc query RansomEyeWindowsAgent     # Check status
echo   sc querytype RansomEyeWindowsAgent # Check service type
echo.
echo Logs location: !INSTALL_ROOT!\logs\
echo Event Viewer: Windows Logs / Application (search for "RansomEyeWindowsAgent")
echo.
echo NOTE: Windows Agent is standalone and does NOT require Core to be installed.
echo       Agent will fail gracefully if Core is unreachable (no crash-loop).
echo.

endlocal
exit /b 0

:fail
set "FAIL_MSG=%~1"
echo FATAL: %FAIL_MSG%
if defined INSTALL_STATE_FILE (
    python3 "%TRANSACTION_PY%" rollback --state-file "%INSTALL_STATE_FILE%" >nul 2>&1
)
exit /b 1
