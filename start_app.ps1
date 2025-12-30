# Proxy Manager 启动脚本 (PowerShell)
# 用于快速启动重构后的应用

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "🚀 启动 Proxy Manager (重构版本)" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 切换到项目目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Host "📂 工作目录: $scriptPath" -ForegroundColor Yellow
Write-Host ""

# 设置环境变量
$env:PYTHONIOENCODING = 'utf-8'
Write-Host "🔧 环境变量: PYTHONIOENCODING=utf-8" -ForegroundColor Yellow
Write-Host ""

# 检查依赖
if (Test-Path "requirements.txt") {
    Write-Host "📦 检查依赖包..." -ForegroundColor Yellow
    pip list | Select-String "pyyaml|flask|flask-cors" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  警告: 某些依赖包可能未安装" -ForegroundColor Yellow
        Write-Host "    请运行: pip install -r requirements.txt" -ForegroundColor Yellow
        Write-Host ""
    }
}

# 启动应用
Write-Host "🚀 启动应用..." -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

python app.py

# 捕获退出信号
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "👋 应用已停止" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Cyan

