@echo off
REM Double-click this file to launch the uploader GUI picker and run uploader.ps1
SET scriptDir=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%scriptDir%uploader-launcher.ps1"
pause
