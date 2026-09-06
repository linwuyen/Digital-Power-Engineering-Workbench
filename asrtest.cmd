@echo off
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PY=py"
) else (
  set "PY=python"
)
if /I "%~1"=="bind" (
  shift
  %PY% "%~dp0tools\hardware_bind.py" %*
) else (
  %PY% "%~dp0tools\auto_run_ext.py" %*
)
exit /b %ERRORLEVEL%
