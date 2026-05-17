@echo off
REM V6.0 工作流清场脚本：清空【项目根】下的 Shadow/、归档当前 reviews 与 plan 状态
REM 双击运行。会要求二次确认，避免误清。
REM 项目根 = 本 workflow 文件夹的父目录

setlocal
set "WF_ROOT=%~dp0"
for %%I in ("%WF_ROOT%..") do set "PROJECT_ROOT=%%~fI"

REM ─── 路径硬约定自检：本目录名必须为 workflow_template ───
for %%I in ("%WF_ROOT%.") do set "WF_NAME=%%~nxI"
if /I not "%WF_NAME%"=="workflow_template" (
    echo [FAIL] workflow folder must be named "workflow_template" but got "%WF_NAME%".
    echo        prompts and instructions reference this name verbatim. Rename it back.
    exit /b 2
)

set "SHADOW=%PROJECT_ROOT%\Shadow"
set "REVIEWS=%PROJECT_ROOT%\reviews"
set "PLAN=%PROJECT_ROOT%\plan"
set "ARCHIVE_ROOT=%PROJECT_ROOT%\_archive"

echo.
echo ========================================
echo  V6.0 Bootstrap Reset
echo  Project root: %PROJECT_ROOT%
echo ========================================
echo.
echo The following actions will be taken:
echo   1) Move all TRIGGER_*.md from Shadow/ into archive
echo   2) Move all REVIEW_REPORT_v*.{md,json} from reviews/ into archive
echo   3) Move PLAN_*.md from plan/ into archive
echo.
set /p CONFIRM=Proceed? Type YES to continue: 

if /I not "%CONFIRM%"=="YES" (
    echo Aborted.
    exit /b 0
)

REM 用时间戳建归档目录
for /f "tokens=2 delims==" %%I in ('"wmic os get localdatetime /value"') do set "DT=%%I"
set "TS=%DT:~0,8%_%DT:~8,6%"
set "ARCHIVE=%ARCHIVE_ROOT%\%TS%"
mkdir "%ARCHIVE%" 2>nul
mkdir "%ARCHIVE%\Shadow" 2>nul
mkdir "%ARCHIVE%\reviews" 2>nul
mkdir "%ARCHIVE%\plan" 2>nul

REM 防止误清未提交改动：先尝试 git stash
if exist "%PROJECT_ROOT%\.git" (
    pushd "%PROJECT_ROOT%"
    git stash push -u -m "bootstrap_reset_%TS%" 2>nul
    if errorlevel 1 (
        echo [INFO] no changes to stash or git unavailable
    ) else (
        echo [OK] uncommitted changes stashed: bootstrap_reset_%TS%
    )
    popd
)

REM 清 Shadow
if exist "%SHADOW%" (
    pushd "%SHADOW%"
    for %%F in (TRIGGER_*.md TRIGGER_*.tmp *.handling _webhook_fallback.log) do (
        if exist "%%F" move /Y "%%F" "%ARCHIVE%\Shadow\" >nul
    )
    popd
)

REM 清 reviews
if exist "%REVIEWS%" (
    pushd "%REVIEWS%"
    for %%F in (REVIEW_REPORT_v*.md REVIEW_REPORT_v*.json) do (
        if exist "%%F" move /Y "%%F" "%ARCHIVE%\reviews\" >nul
    )
    popd
)

REM 清 plan
if exist "%PLAN%" (
    pushd "%PLAN%"
    for %%F in (PLAN_INDEX.md PLAN_BACKLOG.md PLAN_DONE.md) do (
        if exist "%%F" move /Y "%%F" "%ARCHIVE%\plan\" >nul
    )
    popd
)

echo.
echo [OK] Reset complete. Archive: %ARCHIVE%
echo Now you can edit PLAN_INDEX.md / PLAN_BACKLOG.md and run bootstrap.bat
echo.

endlocal
