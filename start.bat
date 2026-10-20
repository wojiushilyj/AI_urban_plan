@echo off
chcp 65001 >nul
echo ========================================================
echo  国土 AI 竞赛｜多场景智慧选址系统 (原版专业三栏工作台)
echo  技术栈: Vue3 + MapLibre GL + Element Plus + FastAPI
echo ========================================================
echo.
echo 正在启动本地服务...
start http://127.0.0.1:8000/
"C:\Users\Reload\.workbuddy\binaries\python\envs\default\Scripts\python.exe" -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
