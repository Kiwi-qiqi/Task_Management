@echo off
chcp 65001 >nul
echo ========================================
echo Task管理系统 - 启动脚本
echo ========================================
echo.

cd /d C:\Users\M0199528\Documents\Task_Management

echo [1/3] 切换到项目目录...
echo Current directory: %CD%
echo.

echo [2/3] 激活虚拟环境...
powershell -ExecutionPolicy Bypass -Command "& '.\venv\Scripts\Activate.ps1'"
call .\venv\Scripts\activate.bat
echo.

echo [3/3] 启动Task服务...
echo.
python task_app.py

echo.
echo ========================================
echo 程序已退出N
pause
