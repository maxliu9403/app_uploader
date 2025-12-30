@echo off
chcp 65001 >nul
title Proxy Manager - 代理配置管理工具

color 0A
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║     Proxy Manager - 代理配置管理工具                ║
echo ║     一键启动 Web 管理界面                            ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [❌] 错误: 未检测到 Python
    echo.
    echo 请先安装 Python 3.7 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

color 0B
echo [✓] Python 环境检查通过
python --version
echo.

REM 检查依赖包
echo [1/3] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    color 0E
    echo [⚠] 依赖包未安装，正在安装...
    echo.
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [⚠] 使用默认源重试...
        pip install -r requirements.txt
    )
    if errorlevel 1 (
        color 0C
        echo [❌] 依赖包安装失败，请手动执行: pip install -r requirements.txt
        pause
        exit /b 1
    )
    color 0A
    echo [✓] 依赖包安装完成
) else (
    color 0A
    echo [✓] 依赖包已安装
)
echo.

REM 检查配置文件
if not exist "config.yaml" (
    color 0E
    echo [⚠] 警告: config.yaml 不存在，将自动创建
    echo.
)

REM 启动服务
color 0B
echo [2/3] 启动 Web 服务...
echo.
color 0F
echo ════════════════════════════════════════════════════════
echo    🌐 服务地址: http://localhost:5000
echo    📁 配置文件: %CD%\config.yaml
echo    ⏹  停止服务: 按 Ctrl+C
echo ════════════════════════════════════════════════════════
echo.
color 0A
echo [3/3] 正在启动，浏览器将自动打开...
echo.

REM 延迟后自动打开浏览器
timeout /t 2 /nobreak >nul
start "" "http://localhost:5000" >nul 2>&1

REM 启动 Flask 服务（已重构为 app.py）
color 0F
python app.py

REM 如果服务意外退出
if errorlevel 1 (
    color 0C
    echo.
    echo [❌] 服务启动失败，请检查错误信息
    pause
)

