@echo off
chcp 65001 > nul
title 앱 파일 재생성
cd /d "%~dp0"

if not exist "python\python.exe" (
    echo [오류] python 폴더가 없습니다. setup.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

if not exist "regen.py" (
    echo [오류] regen.py가 없습니다.
    pause
    exit /b 1
)

"python\python.exe" "regen.py"
echo.
pause