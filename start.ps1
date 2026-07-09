# Minecraft 在线地图 - 启动脚本 (PowerShell)
# 启动 FastAPI 后端并打开浏览器

Set-Location -Path $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Minecraft 在线地图" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python / uvicorn 是否可用
$pythonOk = $false
try {
    $null = Get-Command python -ErrorAction Stop
    $uvicornCheck = python -c "import uvicorn" 2>&1
    if ($LASTEXITCODE -eq 0) { $pythonOk = $true }
} catch {
    Write-Host "未找到 python，请先安装 Python 3.13+" -ForegroundColor Red
    exit 1
}

if (-not $pythonOk) {
    Write-Host "未找到 uvicorn，正在安装依赖..." -ForegroundColor Yellow
    pip install fastapi uvicorn pillow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败，请手动运行: pip install fastapi uvicorn pillow" -ForegroundColor Red
        exit 1
    }
}

# 后台启动服务
Write-Host "正在启动服务..." -ForegroundColor Green
$job = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.main:app", "--port", "8000" -PassThru -WindowStyle Minimized

# 等待服务就绪
Write-Host "等待服务启动..." -ForegroundColor Green
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # 服务尚未就绪，继续等待
    }
}

if ($ready) {
    Write-Host "服务已就绪，正在打开浏览器..." -ForegroundColor Green
    Start-Process "http://127.0.0.1:8000"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " 服务地址: http://127.0.0.1:8000" -ForegroundColor Cyan
    Write-Host " 进程 ID:  $($job.Id)" -ForegroundColor Cyan
    Write-Host " 停止服务: 关闭此窗口或运行 Stop-Process -Id $($job.Id)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
} else {
    Write-Host "服务启动超时，请检查端口 8000 是否被占用" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "按任意键退出此窗口（服务将在后台继续运行）..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
