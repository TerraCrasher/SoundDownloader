@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title Sound Downloader
cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [오류] python 폴더가 없습니다.
    pause
    exit /b 1
)

"python\python.exe" "app\main.py" %*
if errorlevel 1 pause
