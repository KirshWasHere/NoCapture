import ctypes
from ctypes import wintypes
import os
import shutil

kernel32 = ctypes.windll.kernel32

PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
INFINITE = 0xFFFFFFFF

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

VirtualAllocEx = kernel32.VirtualAllocEx
VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
VirtualAllocEx.restype = wintypes.LPVOID

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

CreateRemoteThread = kernel32.CreateRemoteThread
CreateRemoteThread.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, wintypes.LPDWORD]
CreateRemoteThread.restype = wintypes.HANDLE

GetProcAddress = kernel32.GetProcAddress
GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
GetProcAddress.restype = wintypes.LPVOID

GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
GetModuleHandleW.restype = wintypes.HMODULE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

WaitForSingleObject = kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
WaitForSingleObject.restype = wintypes.DWORD


def inject_dll(pid, dll_path):
    hProcess = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        return False
    
    try:
        kernel32_handle = GetModuleHandleW("kernel32.dll")
        load_library_addr = GetProcAddress(kernel32_handle, b"LoadLibraryW")
        
        if not load_library_addr:
            return False
        
        dll_path_wide = dll_path.encode('utf-16le') + b'\x00\x00'
        dll_path_size = len(dll_path_wide)
        
        remote_memory = VirtualAllocEx(hProcess, None, dll_path_size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not remote_memory:
            return False
        
        bytes_written = ctypes.c_size_t(0)
        if not WriteProcessMemory(hProcess, remote_memory, dll_path_wide, dll_path_size, ctypes.byref(bytes_written)):
            return False
        
        thread_id = wintypes.DWORD(0)
        hThread = CreateRemoteThread(hProcess, None, 0, load_library_addr, remote_memory, 0, ctypes.byref(thread_id))
        
        if not hThread:
            return False
        
        WaitForSingleObject(hThread, INFINITE)
        CloseHandle(hThread)
        
        return True
        
    finally:
        CloseHandle(hProcess)


def inject_hide_capture(pid):
    import tempfile
    import uuid
    
    temp_name = f"payload_hide_{uuid.uuid4().hex[:8]}.dll"
    dll_path = os.path.join(tempfile.gettempdir(), temp_name)
    
    if os.path.exists("payload.dll"):
        try:
            shutil.copy("payload.dll", dll_path)
            result = inject_dll(pid, dll_path)
            return result
        except:
            return False
    return False


def inject_show_capture(pid):
    import tempfile
    import uuid
    
    temp_name = f"payload_show_{uuid.uuid4().hex[:8]}.dll"
    dll_path = os.path.join(tempfile.gettempdir(), temp_name)
    
    if os.path.exists("payload.dll"):
        try:
            shutil.copy("payload.dll", dll_path)
            result = inject_dll(pid, dll_path)
            return result
        except:
            return False
    return False
