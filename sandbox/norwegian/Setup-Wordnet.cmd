@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Wordnet.ps1"
if errorlevel 1 pause

