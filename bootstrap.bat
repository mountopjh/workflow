@echo off
REM V6.0 工作流冷启动：在【项目根】（即本 workflow 的父目录）下原子产生首封 PHASE_1 信号
REM 双击运行。无参数。

setlocal
set "WF_ROOT=%~dp0"
REM 项目根 = workflow 文件夹的父目录
for %%I in ("%WF_ROOT%..") do set "PROJECT_ROOT=%%~fI"

REM ─── 路径硬约定自检：本目录名必须为 workflow_template ───
for %%I in ("%WF_ROOT%.") do set "WF_NAME=%%~nxI"
if /I not "%WF_NAME%"=="workflow_template" (
    echo [FAIL] workflow folder must be named "workflow_template" but got "%WF_NAME%".
    echo        prompts and instructions reference this name verbatim. Rename it back.
    exit /b 2
)

set "SHADOW=%PROJECT_ROOT%\Shadow"
set "TMP=%SHADOW%\TRIGGER_PHASE_1_PLAN.tmp"
set "FINAL=%SHADOW%\TRIGGER_PHASE_1_PLAN.md"

if not exist "%SHADOW%" mkdir "%SHADOW%"

REM 取系统时间精确到秒（YYYY-MM-DD HH:MM:SS）
for /f "tokens=2 delims==" %%I in ('"wmic os get localdatetime /value"') do set "DT=%%I"
set "TS=%DT:~0,4%-%DT:~4,2%-%DT:~6,2% %DT:~8,2%:%DT:~10,2%:%DT:~12,2%"

REM 写临时文件（哑文本占位）
> "%TMP%" echo bootstrap %TS%

REM 原子改名为正式信号
ren "%TMP%" "TRIGGER_PHASE_1_PLAN.md"

if exist "%FINAL%" (
    echo [OK] Bootstrap signal placed: %FINAL%
) else (
    echo [FAIL] Could not place signal at %FINAL%
    exit /b 1
)

endlocal
