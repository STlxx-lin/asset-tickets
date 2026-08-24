@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ===================================================
echo           素材工单管理系统 - 一键打包发布
echo ===================================================
echo [INFO] 正在检测 Python 环境...

set "PYTHON_EXE="

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :FOUND
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :FOUND
)

if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    goto :FOUND
)

if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :FOUND
)

:NOT_FOUND
echo [ERROR] 未找到官方 Python 3.11 或 3.12 安装。
pause
exit /b 1

:FOUND
echo [INFO] 已找到 Python: "%PYTHON_EXE%"
echo.
echo 请选择需要打包的版本类型：
echo [1] 绿色免安装版 (推荐：0.5秒极速秒开，生成文件夹与.zip)
echo [2] 单文件便携版 (生成单个独立 .exe 文件)
echo [3] 双版本同时构建 (生成单文件 exe + 绿色免安装 zip)
echo.

set /p CHOICE="请输入选项 [1-3] (直接回车默认选择 3): "

if "%CHOICE%"=="1" (
    set "BUILD_MODE=standalone"
) else if "%CHOICE%"=="2" (
    set "BUILD_MODE=onefile"
) else (
    set "BUILD_MODE=both"
)

echo.
echo [INFO] 正在启动打包 (模式: %BUILD_MODE%)...
"%PYTHON_EXE%" scripts\build_nuitka.py --mode=%BUILD_MODE%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo [SUCCESS] 打包成功！产物已存放在 dist 目录中。
    echo ===================================================
) else (
    echo.
    echo [ERROR] 打包失败，错误代码 %ERRORLEVEL%。
)

pause
