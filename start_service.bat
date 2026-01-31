@echo off
start /B pythonw nocap_service.py
echo NoCap service started in background
timeout /t 2 >nul
