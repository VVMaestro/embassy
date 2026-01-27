@echo off
REM ========================================================
REM Chrome Process Cleanup Script for Windows
REM ========================================================
REM This batch file aggressively cleans up Chrome, Chromium,
REM and ChromeDriver processes that might be left running
REM after bot execution.
REM ========================================================

echo.
echo ========================================================
echo Chrome Process Cleanup Script for Windows
echo ========================================================
echo Started at: %date% %time%
echo.

REM Function to print section headers
:print_section
echo.
echo === %~1 ===
echo.
goto :eof

REM Function to kill processes by image name
:kill_by_name
setlocal
set IMAGE_NAME=%~1
set SIGNAL=%~2
if "%SIGNAL%"=="" set SIGNAL=/F

call :print_section "Killing %IMAGE_NAME% processes"

echo Using taskkill for %IMAGE_NAME%...
taskkill %SIGNAL% /IM "%IMAGE_NAME%" /T >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ taskkill successful for %IMAGE_NAME%
) else (
    echo   No %IMAGE_NAME% processes found
)

endlocal
goto :eof

REM Function to kill processes by PID
:kill_by_pid
setlocal
set TARGET_PID=%~1

echo Killing PID %TARGET_PID%...
taskkill /F /PID %TARGET_PID% >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Killed PID %TARGET_PID%
) else (
    echo   ✗ Failed to kill PID %TARGET_PID%
)

endlocal
goto :eof

REM Function to kill processes by port
:kill_by_port
setlocal
set TARGET_PORT=%~1

call :print_section "Killing processes on port %TARGET_PORT%"

echo Finding processes using port %TARGET_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%TARGET_PORT%"') do (
    if not "%%a"=="0" (
        call :kill_by_pid %%a
    )
)

endlocal
goto :eof

REM Function to list Chrome-related processes
:list_chrome_processes
call :print_section "Listing Chrome-related processes"

echo Chrome processes:
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul
if %errorlevel% neq 0 echo   None found

echo.
echo Chromium processes:
tasklist /FI "IMAGENAME eq chromium.exe" 2>nul
if %errorlevel% neq 0 echo   None found

echo.
echo ChromeDriver processes:
tasklist /FI "IMAGENAME eq chromedriver.exe" 2>nul
if %errorlevel% neq 0 echo   None found

echo.
echo Processes with "chrome" in command line:
wmic process where "commandline like '%%chrome%%'" get processid,commandline /format:list 2>nul | findstr "ProcessId="
if %errorlevel% neq 0 echo   None found

echo.
echo Processes with "chromedriver" in command line:
wmic process where "commandline like '%%chromedriver%%'" get processid,commandline /format:list 2>nul | findstr "ProcessId="
if %errorlevel% neq 0 echo   None found

goto :eof

REM Function to clean up Chrome data directories
:clean_chrome_data
call :print_section "Cleaning Chrome data directories"

echo Warning: Chrome data directory cleanup requires care
echo Skipping automatic data directory cleanup for safety
echo.
echo You can manually clean:
echo   - %%LOCALAPPDATA%%\Google\Chrome\User Data
echo   - %%LOCALAPPDATA%%\Chromium\User Data
echo   - Temp directories with chrome_cleanup_ prefix

goto :eof

REM Main cleanup sequence
echo Starting aggressive Chrome cleanup...
echo Platform: Windows
echo.

REM List processes before cleanup
call :list_chrome_processes

REM Kill processes by name
call :kill_by_name "chrome.exe"
call :kill_by_name "chromium.exe"
call :kill_by_name "chromedriver.exe"
call :kill_by_name "chrome.dll"
call :kill_by_name "chromedriver.dll"

REM Kill processes on common Chrome ports
call :kill_by_port 9222  REM Chrome DevTools
call :kill_by_port 9515  REM ChromeDriver default

REM Additional aggressive cleanup
call :print_section "Additional aggressive cleanup"

echo Killing any process with --user-data-dir in command line...
for /f "tokens=2 delims=," %%a in ('wmic process where "commandline like '%%--user-data-dir=%%'" get processid /format:csv 2^>nul ^| findstr /v "Node,ProcessId"') do (
    call :kill_by_pid %%a
)

echo.
echo Killing any process with --remote-debugging-port in command line...
for /f "tokens=2 delims=," %%a in ('wmic process where "commandline like '%%--remote-debugging-port=%%'" get processid /format:csv 2^>nul ^| findstr /v "Node,ProcessId"') do (
    call :kill_by_pid %%a
)

echo.
echo Killing any process with --headless in command line...
for /f "tokens=2 delims=," %%a in ('wmic process where "commandline like '%%--headless%%'" get processid /format:csv 2^>nul ^| findstr /v "Node,ProcessId"') do (
    call :kill_by_pid %%a
)

REM Clean up Chrome data (with caution)
call :clean_chrome_data

REM Wait for processes to die
call :print_section "Finalizing cleanup"
echo Waiting 3 seconds for processes to terminate...
timeout /t 3 /nobreak >nul

REM List processes after cleanup
call :list_chrome_processes

REM Final summary
call :print_section "Cleanup Summary"
echo Cleanup completed at: %date% %time%
echo.
echo If Chrome processes are still running, you may need to:
echo 1. Run this script as Administrator
echo 2. Check for services named Chrome or Chromium
echo 3. Reboot your system if problems persist
echo.
echo For the embassy bot, ensure you're using:
echo   ChromeUltraAggressiveCleanup
echo in your Python code for automatic cleanup.
echo.
echo ========================================================
pause
exit /b 0
