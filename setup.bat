@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   培英 AI 行政平台 - 环境初始化脚本
echo ============================================
echo.

REM 使用脚本所在目录作为项目根目录
set "PROJECT_ROOT=%~dp0"
set "API_DIR=%PROJECT_ROOT%apps\api"
set "WEB_DIR=%PROJECT_ROOT%apps\web"

REM ==================== 检查 Python ====================
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Python，请先安装 Python 3.10 或更高版本。
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [OK] 检测到 Python %PYTHON_VERSION%

REM ==================== 检查 Node.js ====================
echo.
echo [2/5] 检查 Node.js 环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Node.js，请先安装 Node.js 20 或更高版本。
    echo 下载地址: https://nodejs.org/
    echo 安装时请务必勾选 "Add to PATH"
    echo.
    pause
    exit /b 1
)
for /f "delims=v tokens=*" %%a in ('node --version 2^>^&1') do set NODE_VERSION=%%a
echo [OK] 检测到 Node.js %NODE_VERSION%

REM ==================== 创建 Python 虚拟环境 ====================
echo.
echo [3/5] 安装 Python 依赖...
cd /d "%API_DIR%"

if exist "venv" (
    echo 检测到已有 venv 目录，正在删除旧环境...
    rmdir /s /q "venv"
)

echo 正在创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
)

echo 正在安装依赖包（约需 2-5 分钟）...
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [错误] Python 依赖安装失败。
    pause
    exit /b 1
)
echo [OK] Python 依赖安装完成

REM ==================== 安装 Node.js 依赖 ====================
echo.
echo [4/5] 安装 Node.js 依赖...
cd /d "%WEB_DIR%"

if exist "node_modules" (
    echo 检测到已有 node_modules 目录，正在删除旧依赖...
    rmdir /s /q "node_modules"
)

echo 正在安装 npm 依赖（约需 1-3 分钟）...
call npm install
if errorlevel 1 (
    echo [错误] Node.js 依赖安装失败。
    pause
    exit /b 1
)
echo [OK] Node.js 依赖安装完成

REM ==================== 配置环境变量 ====================
echo.
echo [5/5] 配置环境变量...
cd /d "%PROJECT_ROOT%"

if exist ".env" (
    echo 检测到已有 .env 文件，跳过创建。
    echo 如需修改配置，请直接编辑 %PROJECT_ROOT%.env
) else (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] 已从 .env.example 创建 .env 文件。
        echo.
        echo ============================================
        echo [重要提示] .env 文件已创建，请用记事本打开并填入真实密钥：
        echo   %PROJECT_ROOT%.env
        echo.
        echo 必须填写的项：
        echo   - XFYUN_APPID / XFYUN_API_SECRET / XFYUN_API_KEY  （讯飞 OCR）
        echo   - LLM_API_KEY  （AI 分类，如 DeepSeek API Key）
        echo   - SECRET_KEY  （建议改为随机字符串）
        echo ============================================
    ) else (
        echo [警告] 未找到 .env.example 文件，无法自动创建 .env
    )
)

REM ==================== 完成 ====================
echo.
echo ============================================
echo   环境初始化完成！
echo ============================================
echo.
echo 启动方式：
echo   1. 先编辑 .env 填入真实 API 密钥（如未配置）
echo   2. 双击 start.bat 启动前后端服务
echo.
echo 访问地址：
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo ============================================
echo.
pause
