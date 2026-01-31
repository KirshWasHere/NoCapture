#include <windows.h>
#include <string.h>

#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#define WDA_NONE 0x00000000

typedef struct {
    DWORD pid;
    BOOL hide;
} EnumData;

BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lParam) {
    EnumData* data = (EnumData*)lParam;
    DWORD windowPid;
    GetWindowThreadProcessId(hwnd, &windowPid);
    
    if (windowPid == data->pid && IsWindowVisible(hwnd)) {
        if (data->hide) {
            SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
        } else {
            SetWindowDisplayAffinity(hwnd, WDA_NONE);
        }
    }
    return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinstDLL);
        
        char dllPath[MAX_PATH];
        GetModuleFileNameA(hinstDLL, dllPath, MAX_PATH);
        
        EnumData data;
        data.pid = GetCurrentProcessId();
        data.hide = (strstr(dllPath, "hide") != NULL);
        
        EnumWindows(EnumWindowsProc, (LPARAM)&data);
    }
    return TRUE;
}
