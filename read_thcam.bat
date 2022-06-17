chcp 65001
cd /d %~dp0
cls

python3 read_thcam.py %1

@echo off
if %errorlevel% neq 0 (pause)
exit
