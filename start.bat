@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   培英 AI 行政平台 - 启动服务
echo ============================================
echo.

set "PROJECT_ROOT=%~dp0"

REM 检查依赖是否已安装
if not exist "%PROJECT_ROOT%apps\api\venv\Scripts\python.exe" (
    echo [提示] 未检测到 Python 虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)
if not exist "%PROJECT_ROOT%apps\web\node_modules" (
    echo [提示] 未检测到 Node.js 依赖，请先运行 setup.bat
    pause
    exit /b 1
)

echo 正在启动后端服务 (端口 8000) ...
start "Backend API" powershell.exe -NoExit -Command "cd '%PROJECT_ROOT%apps\api'; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo 正在启动前端服务 (端口 3000) ...
start "Frontend Web" powershell.exe -NoExit -Command "cd '%PROJECT_ROOT%apps\web'; npm run dev"

echo.
echo ============================================
echo   服务已启动！
echo.
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo ============================================
echo.
echo 关闭服务：直接关闭弹出的两个 PowerShell 窗口即可
echo.
pause
