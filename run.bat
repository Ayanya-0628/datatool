@echo off
echo 正在启动数据分析软件...
cd /d "%~dp0"
start http://127.0.0.1:7860
python app.py
pause