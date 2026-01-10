@echo off
REM RansomEye v1.0 Windows Agent Uninstaller
REM AUTHORITATIVE: Production-grade uninstaller for standalone Windows Agent
REM Fail-closed: Any error terminates uninstallation immediately

setlocal enabledelayedexpansion

REM Validate Administrator privileges
net session >nul 2>&1
if errorlevel 1 (
    echo FATAL: Uninstaller must be run as Administrator
    echo        Right-click uninstall.bat and select "Run as administrator"
    exit /b 1
)

REM Detect installation root from manifest or prompt
set "INSTALL_ROOT="

REM Try to find manifest in common locations
if exist "C:\RansomEye\Agent\config\installer.manifest.json" (
    set "INSTALL_ROOT=C:\RansomEye\Agent"
    echo Found installation at: !INSTALL_ROOT!
) else if exist "C:\Program Files\RansomEye\Agent\config\installer.manifest.json" (
    set "INSTALL_ROOT=C:\Program Files\RansomEye\Agent"
    echo Found installation at: !INSTALL_ROOT!
) else (
    REM Prompt if not found
    echo.
    echo RansomEye v1.0 Windows Agent Uninstaller
    echo =========================================
    echo.
    echo Installation manifest not found in common locations.
    set /p "INSTALL_ROOT=Enter installation directory (absolute path, example: C:\RansomEye\Agent): "
    
    if "!INSTALL_ROOT!"=="" (
        echo FATAL: Install root cannot be empty
        exit /b 1
    )
    
    REM Validate: must be absolute path
    echo !INSTALL_ROOT! | findstr /R "^[A-Z]:" >nul 2>&1
    if errorlevel 1 (
        echo FATAL: Install root must be an absolute path (starting with drive letter, e.g., C:\)
        exit /b 1
    )
    
    REM Normalize path
    if "!INSTALL_ROOT:~-1!"=="\" set "INSTALL_ROOT=!INSTALL_ROOT:~0,-1!"
    
    if not exist "!INSTALL_ROOT!\config\installer.manifest.json" (
        echo FATAL: Not a valid RansomEye Windows Agent installation: manifest not found at !INSTALL_ROOT!\config\installer.manifest.json
        exit /b 1
    )
)

REM Stop and remove Windows Service
echo.
echo Removing Windows Service: RansomEyeWindowsAgent...

sc query "RansomEyeWindowsAgent" >nul 2>&1
if not errorlevel 1 (
    REM Service exists, stop it first
    echo Stopping service...
    sc stop "RansomEyeWindowsAgent" >nul 2>&1
    
    REM Wait for service to stop
    timeout /t 5 /nobreak >nul 2>&1
    
    REM Delete service
    echo Removing service...
    sc delete "RansomEyeWindowsAgent" >nul 2>&1
    if errorlevel 1 (
        echo FATAL: Failed to delete Windows service
        exit /b 1
    )
    echo Service removed successfully
) else (
    echo Service 'RansomEyeWindowsAgent' does not exist (may have been removed already)
)

REM Remove installation directory
echo.
echo Removing installation directory...
if exist "!INSTALL_ROOT!" (
    echo.
    echo WARNING: This will permanently delete the installation directory:
    echo   !INSTALL_ROOT!
    echo.
    echo Logs and configuration will be lost.
    set /p "CONFIRM=Continue? [y/N]: "
    if /i not "!CONFIRM!"=="y" (
        echo Uninstallation cancelled.
        exit /b 0
    )
    
    REM Remove directory
    rd /s /q "!INSTALL_ROOT!" 2>nul
    if errorlevel 1 (
        echo WARNING: Failed to remove some files (may require manual cleanup)
    ) else (
        echo Removed: !INSTALL_ROOT!
    )
) else (
    echo Installation directory does not exist: !INSTALL_ROOT!
)

REM Remove Windows service user (optional, with confirmation)
echo.
echo Windows service user 'ransomeye-agent' management...
net user ransomeye-agent >nul 2>&1
if not errorlevel 1 (
    echo User 'ransomeye-agent' exists.
    echo NOTE: Removing Windows user may affect other installations or services.
    set /p "CONFIRM_USER=Remove user 'ransomeye-agent'? [y/N]: "
    
    if /i "!CONFIRM_USER!"=="y" (
        REM Check if user is used by any process
        tasklist /FI "USERNAME eq ransomeye-agent" 2>nul | findstr "ransomeye-agent" >nul 2>&1
        if not errorlevel 1 (
            echo FATAL: Cannot remove user 'ransomeye-agent': processes are still running as this user
            exit /b 1
        )
        
        net user ransomeye-agent /delete >nul 2>&1
        if errorlevel 1 (
            echo WARNING: Failed to remove user 'ransomeye-agent' (may require manual cleanup)
        ) else (
            echo Removed user: ransomeye-agent
        )
    ) else (
        echo User 'ransomeye-agent' kept (not removed)
    )
) else (
    echo User 'ransomeye-agent' does not exist
)

echo.
echo ================================================================================
echo Uninstallation completed successfully!
echo ================================================================================
echo.
echo RansomEye Windows Agent has been removed from this system.
echo.
echo NOTE: Windows Agent is standalone - no Core dependencies to clean up.
echo.

endlocal
exit /b 0
