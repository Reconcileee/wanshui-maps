@echo off
chcp 65001 >nul
REM Minecraft 在线地图 - 启动脚本
REM 启动 FastAPI 后端并打开浏览器

cd /d "%~dp0"

echo ========================================
echo   Minecraft 在线地图
echo ========================================
echo.
echo 正在启动服务...

REM 启动后端 (后台运行)
start "Minecraft Map Server" cmd /k "uvicorn backend.main:app --port 8000"

REM 等待服务就绪
echo 等待服务启动...
timeout /t 3 /nobreak >nul

REM 打开浏览器
echo 正在打开浏览器...
start "" http://127.0.0.1:8000

echo.
echo ========================================
echo  服务已启动: http://127.0.0.1:8000
echo  关闭窗口或按 Ctrl+C 停止服务
echo ========================================
pause
