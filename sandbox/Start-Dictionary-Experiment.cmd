@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0norwegian\Launch-Dictionary-Experiment.ps1"
if errorlevel 1 pause
