@echo off
REM V6.0 项目初始化：在【项目根】（本 workflow 的父目录）下建空目录骨架并复制模板
REM 双击运行。无参数。已存在的目录与文件不会被覆盖。

setlocal
set "WF_ROOT=%~dp0"
for %%I in ("%WF_ROOT%..") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo  V6.0 Init Project
echo  Project root: %PROJECT_ROOT%
echo ========================================
echo.

REM 建目录骨架
for %%D in (Shadow src tests plan reviews docs) do (
    if not exist "%PROJECT_ROOT%\%%D" (
        mkdir "%PROJECT_ROOT%\%%D"
        echo [MK] %PROJECT_ROOT%\%%D
    ) else (
        echo [SKIP] %PROJECT_ROOT%\%%D already exists
    )
)

REM 复制 PLAN 模板
for %%F in (PLAN_INDEX.md PLAN_BACKLOG.md PLAN_DONE.md) do (
    if not exist "%PROJECT_ROOT%\plan\%%F" (
        copy /Y "%WF_ROOT%templates\%%F" "%PROJECT_ROOT%\plan\%%F" >nul
        echo [CP] %PROJECT_ROOT%\plan\%%F
    ) else (
        echo [SKIP] %PROJECT_ROOT%\plan\%%F already exists
    )
)

REM 复制 docs 三件套模板
for %%F in (PRD.md TECH_DESIGN.md EXECUTION_PLAN.md) do (
    if not exist "%PROJECT_ROOT%\docs\%%F" (
        copy /Y "%WF_ROOT%templates\%%F" "%PROJECT_ROOT%\docs\%%F" >nul
        echo [CP] %PROJECT_ROOT%\docs\%%F
    ) else (
        echo [SKIP] %PROJECT_ROOT%\docs\%%F already exists
    )
)

REM 初始化 Git 仓库（用于环节 PASS 时自动 commit）
if not exist "%PROJECT_ROOT%\.git" (
    pushd "%PROJECT_ROOT%"
    git init >nul 2>&1
    if errorlevel 1 (
        echo [WARN] git init failed; auto-commit will be skipped during workflow
    ) else (
        REM 写 .gitignore（避免把 Shadow/ 信号文件污染历史）
        if not exist ".gitignore" (
            > ".gitignore" echo Shadow/TRIGGER_*.md
            >> ".gitignore" echo Shadow/TRIGGER_*.tmp
            >> ".gitignore" echo Shadow/*.handling
            >> ".gitignore" echo Shadow/_webhook_fallback.log
            >> ".gitignore" echo Shadow/_git_fallback.log
            >> ".gitignore" echo _archive/
            echo [MK] %PROJECT_ROOT%\.gitignore
        )
        git add . >nul 2>&1
        git -c user.name="workflow_bootstrap" -c user.email="bootstrap@local" commit -m "[INIT] project skeleton baseline" >nul 2>&1
        if errorlevel 1 (
            echo [WARN] baseline commit failed; you may need to configure git user.name and user.email
        ) else (
            echo [OK] git repo initialized with baseline commit
        )
    )
    popd
) else (
    echo [SKIP] %PROJECT_ROOT%\.git already exists
)

echo.
echo [OK] Init complete.
echo Next steps:
echo   1) Fill in %PROJECT_ROOT%\docs\PRD.md
echo   2) Fill in %PROJECT_ROOT%\docs\TECH_DESIGN.md
echo   3) Fill in %PROJECT_ROOT%\docs\EXECUTION_PLAN.md (this drives the workflow)
echo   4) Edit %PROJECT_ROOT%\plan\PLAN_BACKLOG.md to seed your tasks
echo   5) Start the three AI clients ^(planner / executor / auditor^)
echo   6) Configure and start the bus (Workbuddy) per bus_setup\BUS_SETUP_GUIDE.md
echo   7) Run bootstrap.bat to drop the first signal
echo.

endlocal
