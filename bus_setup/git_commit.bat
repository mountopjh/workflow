@echo off
REM V6.0 工作流：审计员判 PASS 后由大总管调用本脚本自动 commit
REM
REM 流程：
REM   1. 读 <项目根>/reviews/ 下编号最大的 .meta.json
REM   2. 提取 task_id / version / reason_short
REM   3. git add . && git commit -m "[TASK-XXX][V<n>][PASS] <reason_short>"
REM   4. 检查 PLAN_INDEX.md 是否标注"待打 tag" → 若是则打 tag 并清掉标记

setlocal enabledelayedexpansion
set "WF_ROOT=%~dp0..\"
for %%I in ("%WF_ROOT%..") do set "PROJECT_ROOT=%%~fI"
set "REVIEWS=%PROJECT_ROOT%\reviews"
set "PLAN_INDEX=%PROJECT_ROOT%\plan\PLAN_INDEX.md"

if not exist "%PROJECT_ROOT%\.git" (
    echo [SKIP] No git repo at %PROJECT_ROOT%; skipping auto-commit
    exit /b 0
)

REM 找最新 meta.json
set "LATEST_META="
for /f "delims=" %%F in ('dir /b /o:n "%REVIEWS%\REVIEW_REPORT_v*.meta.json" 2^>nul') do (
    set "LATEST_META=%%F"
)

if "%LATEST_META%"=="" (
    echo [SKIP] No meta.json found in %REVIEWS%
    exit /b 0
)

set "META_PATH=%REVIEWS%\%LATEST_META%"

REM 解析 task_id / version / status / reason_short （简单字符串提取，假设字段每行一条）
set "TASK_ID="
set "VER="
set "STATUS="
set "REASON="
for /f "usebackq tokens=1,* delims=:" %%A in ("%META_PATH%") do (
    set "K=%%A"
    set "V=%%B"
    REM 去引号、逗号、首尾空格
    set "K=!K: =!"
    set "K=!K:"=!"
    set "V=!V:"=!"
    set "V=!V:,=!"
    if /I "!K!"=="task_id" set "TASK_ID=!V: =!"
    if /I "!K!"=="version" set "VER=!V: =!"
    if /I "!K!"=="status" set "STATUS=!V: =!"
    if /I "!K!"=="reason_short" set "REASON=!V!"
)

if /I not "%STATUS%"=="PASS" (
    echo [SKIP] Latest meta is %STATUS%; commit only on PASS
    exit /b 0
)

set "MSG=[%TASK_ID%][V%VER%][PASS]%REASON%"

pushd "%PROJECT_ROOT%"
git add .
if errorlevel 1 (
    echo [WARN] git add failed
    popd
    exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
    git commit -m "%MSG%"
    if errorlevel 1 (
        echo [WARN] git commit failed
        popd
        exit /b 1
    )
    echo [OK] Committed: %MSG%
) else (
    echo [SKIP] No staged changes to commit
)

REM ── 打 tag 检查 ──
REM 在 PLAN_INDEX.md 中查找 "待打 phase-N-done" 标记
if exist "%PLAN_INDEX%" (
    for /f "usebackq tokens=*" %%L in (`findstr /R /C:"待打 phase-[0-9]*-done" "%PLAN_INDEX%"`) do (
        for /f "tokens=2 delims= " %%T in ("%%L") do (
            set "TAG=%%T"
            REM 去掉可能的尾号
        )
    )
    REM 用 PowerShell 提取更稳
    for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "$m=[regex]::Match((Get-Content -LiteralPath '%PLAN_INDEX%' -Raw),'phase-\d+-done'); if($m.Success){$m.Value}"`) do set "TAG=%%T"

    if defined TAG (
        if not "!TAG!"=="" (
            git tag !TAG! 2>nul
            if errorlevel 1 (
                echo [WARN] tag !TAG! may already exist; skipping
            ) else (
                echo [OK] Tagged: !TAG!
            )
        )
    )
)

popd
endlocal
exit /b 0
