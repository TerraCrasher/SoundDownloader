@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title Sound Downloader - 최초 설치
cd /d "%~dp0"

if not exist "setup.py" (
    echo [오류] setup.py 가 없습니다.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM Python 선택 우선순위:
REM   1) python\python.exe  (이미 임베디드가 들어있는 경우 = zip 배포 사용자)
REM   2) py -3              (시스템에 Python Launcher 가 있는 경우)
REM   3) python             (시스템 PATH 의 python)
REM ----------------------------------------------------------------------

set PYRUN=
if exist "python\python.exe" (
    set "PYRUN=python\python.exe"
    goto :run
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYRUN=py -3"
    echo [정보] 임베디드 Python 이 없어 시스템 Python 으로 부트스트랩합니다.
    goto :run
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PYRUN=python"
    echo [정보] 임베디드 Python 이 없어 시스템 python 으로 부트스트랩합니다.
    goto :run
)

echo.
echo [오류] 사용할 Python 을 찾을 수 없습니다.
echo.
echo 다음 중 하나가 필요합니다:
echo   - python\python.exe   (zip 배포물에 포함된 임베디드 Python)
echo   - 시스템에 설치된 Python 3 (https://www.python.org/downloads/)
echo.
echo 시스템 Python 을 한 번만 설치하면 setup.bat 이 자동으로 임베디드 Python 까지 받아옵니다.
pause
exit /b 1

:run
%PYRUN% setup.py %*
if errorlevel 1 (
    pause
    exit /b 1
)

pause
