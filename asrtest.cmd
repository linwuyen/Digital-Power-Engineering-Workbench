@echo off
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py "%~dp0tools\auto_run.py" %*
) else (
  python "%~dp0tools\auto_run.py" %*
)
exit /b %ERRORLEVEL%
