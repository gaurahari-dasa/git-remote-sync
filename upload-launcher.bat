@echo off
REM Double-click this file to launch the uploader script
SET scriptDir=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%scriptDir%uploader.ps1"
pause
