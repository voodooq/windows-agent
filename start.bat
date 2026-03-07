@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 切换到当前 bat 所在目录
cd /d "%~dp0"

REM 定义 Anaconda 路径和环境名称
set "CONDA_PATH=D:\anaconda3"
set "ENV_NAME=windows_agent"
set "DONE_MARKER=.initialized"

echo [Windows Agent] 正在检查启动状态...

REM 如果标记文件存在，直接激活并启动
if exist "%DONE_MARKER%" (
    echo [信息] 检测到已初始化，正在快速启动...
    call "%CONDA_PATH%\Scripts\activate.bat" %ENV_NAME%
    goto START_APP
)

REM 检查 Conda 是否存在
if not exist "%CONDA_PATH%\Scripts\conda.exe" (
    echo [错误] 未在 %CONDA_PATH% 找到 Anaconda，请确保路径正确。
    pause
    exit /b 1
)

REM 检查环境是否已存在
call "%CONDA_PATH%\Scripts\activate.bat" base
call conda env list | findstr /C:"%ENV_NAME%" > nul

if errorlevel 1 (
    echo [信息] 正在创建 Python 3.11 环境: %ENV_NAME%...
    call conda create -n %ENV_NAME% python=3.11 -y
    if errorlevel 1 (
        echo [错误] 环境创建失败。
        pause
        exit /b 1
    )
)

REM 激活环境
echo [信息] 正在激活环境: %ENV_NAME%...
call "%CONDA_PATH%\Scripts\activate.bat" %ENV_NAME%

REM 安装/更新依赖
if exist "requirements.txt" (
    echo [信息] 正在安装依赖资源...
    pip install -r requirements.txt -i https://pypi.tsinghua.edu.cn/simple
    if errorlevel 0 (
        echo. > "%DONE_MARKER%"
    )
) else (
    echo. > "%DONE_MARKER%"
)

:START_APP
echo.
echo [Windows Agent] 正在启动 UI...
echo.

python app\ui_main.py --config configs/default.yaml

if errorlevel 1 (
    echo.
    echo [错误] 启动失败，请检查控制台输出。
    echo.
    pause
)

endlocal
