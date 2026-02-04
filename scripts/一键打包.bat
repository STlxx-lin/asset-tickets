@echo off
setlocal

echo [INFO] Searching for official Python installation...

REM Try to find Python in common locations
set "PYTHON_EXE="

REM Check AppData location for Python 3.12
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :FOUND
)

REM Check AppData location for Python 3.11
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :FOUND
)

REM Check Program Files for Python 3.12
if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    goto :FOUND
)

REM Check Program Files for Python 3.11
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :FOUND
)

:NOT_FOUND
echo [ERROR] Could not find a suitable Python installation (non-Store version).
echo Please ensure Python 3.11 or 3.12 is installed from python.org.
pause
exit /b 1

:FOUND
echo [INFO] Found Python at: "%PYTHON_EXE%"
echo [INFO] Starting build process...

"%PYTHON_EXE%" build_nuitka.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Build completed successfully!
) else (
    echo.
    echo [ERROR] Build failed with error code %ERRORLEVEL%.
)

pause
