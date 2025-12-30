# Proxy Manager 启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Proxy Manager - 代理配置管理工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Green
    Write-Host $pythonVersion
} catch {
    Write-Host "[错误] 未检测到 Python，请先安装 Python 3.7+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按 Enter 键退出"
    exit 1
}

Write-Host ""
Write-Host "[2/3] 检查依赖包..." -ForegroundColor Green

try {
    python -c "import flask" 2>&1 | Out-Null
    Write-Host "依赖包已安装" -ForegroundColor Green
} catch {
    Write-Host "正在安装依赖包..." -ForegroundColor Yellow
    try {
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    } catch {
        Write-Host "使用默认源安装..." -ForegroundColor Yellow
        pip install -r requirements.txt
    }
}

Write-Host ""
Write-Host "[3/3] 启动服务..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  服务地址: http://localhost:5000" -ForegroundColor Cyan
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 延迟 2 秒后自动打开浏览器
Start-Sleep -Seconds 2
Start-Process "http://localhost:5000"

# 启动 Flask 服务（已重构为 app.py）
python app.py

