@echo off
wmic process where "commandline like '%%nocap_service.py%%'" delete >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
echo NoCap service stopped
timeout /t 2 >nul
