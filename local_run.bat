@echo off
setlocal
chcp 65001 >nul

rem 切换到脚本所在目录
cd /d "%~dp0"

set PORT=8001

rem 杀掉占用指定端口的旧进程
echo [INFO] Checking port %PORT%...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo 检测到端口 %PORT% 已被占用^(PID %%p^)，正在关闭旧进程...
    taskkill /F /PID %%p >nul 2>&1
)

echo 启动房价数据可视化服务器...
start "HousePrice Server" cmd /c python web_server.py --host localhost --port %PORT%

rem 等待服务启动
ping 127.0.0.1 -n 3 >nul

echo 服务已启动：http://localhost:%PORT%
start "" http://localhost:%PORT%

endlocal
