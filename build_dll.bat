@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cl /LD /O2 payload.c /link /OUT:payload.dll user32.lib kernel32.lib
del payload.obj payload.exp payload.lib 2>nul
echo DLL built: payload.dll
