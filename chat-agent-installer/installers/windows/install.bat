@echo off
echo Starting Chat-Agent Windows Installer...
echo.
echo This installer requires Administrator privileges.
echo.
pause

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0install.ps1'"

pause
