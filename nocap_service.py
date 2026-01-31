import ctypes
from ctypes import wintypes
import json
import time
from pathlib import Path
import injector

WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = wintypes.LONG
EnumWindows = user32.EnumWindows
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetConsoleWindow = kernel32.GetConsoleWindow
ShowWindow = user32.ShowWindow

CONFIG_FILE = Path.home() / ".nocap_config.json"
SW_HIDE = 0


def hide_console():
    hwnd = GetConsoleWindow()
    if hwnd:
        ShowWindow(hwnd, SW_HIDE)


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                return data.get('hidden_windows', [])
        except:
            pass
    return []


_windows_list = []

def enum_windows_callback(hwnd, lParam):
    if not IsWindowVisible(hwnd):
        return True
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return True
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    title = buffer.value
    if not title:
        return True
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    _windows_list.append((hwnd, title, pid.value))
    return True


def get_all_windows():
    global _windows_list
    _windows_list = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    callback = callback_type(enum_windows_callback)
    EnumWindows(callback, 0)
    return _windows_list


def hide_from_capture(hwnd):
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return injector.inject_hide_capture(pid.value)


def main():
    hide_console()
    print("NoCap Service Started")
    
    hidden_titles = load_config()
    if not hidden_titles:
        print("No hidden windows in config")
        return
    
    print(f"Monitoring {len(hidden_titles)} window(s)")
    
    while True:
        try:
            all_windows = get_all_windows()
            
            for hidden_title in hidden_titles:
                for hwnd, title, pid in all_windows:
                    if title == hidden_title:
                        same_process_windows = [(h, t, p) for h, t, p in all_windows if p == pid]
                        for h, t, p in same_process_windows:
                            try:
                                hide_from_capture(h)
                            except:
                                pass
                        break
            
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except:
            time.sleep(5)


if __name__ == "__main__":
    main()
