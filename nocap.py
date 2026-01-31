import ctypes
from ctypes import wintypes
import json
import os
import threading
import time
from pathlib import Path
import curses
import injector

WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32
GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = wintypes.LONG
SetWindowLongW = user32.SetWindowLongW
SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
SetWindowLongW.restype = wintypes.LONG
SetWindowDisplayAffinity = user32.SetWindowDisplayAffinity
SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
SetWindowDisplayAffinity.restype = wintypes.BOOL
EnumWindows = user32.EnumWindows
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowThreadProcessId = user32.GetWindowThreadProcessId

CONFIG_FILE = Path.home() / ".nocap_config.json"


class WindowInfo:
    def __init__(self, hwnd, title, pid):
        self.hwnd = hwnd
        self.title = title
        self.pid = pid
        self.is_capture_hidden = False
        self.is_taskbar_hidden = False


class NoCapConfig:
    def __init__(self):
        self.hidden_windows = []
        self.load()
    
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.hidden_windows = data.get('hidden_windows', [])
            except:
                pass
    
    def save(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'hidden_windows': self.hidden_windows
            }, f, indent=2)
    
    def add_hidden_window(self, title):
        if title not in self.hidden_windows:
            self.hidden_windows.append(title)
            self.save()
    
    def remove_hidden_window(self, title):
        if title in self.hidden_windows:
            self.hidden_windows.remove(title)
            self.save()


class BackgroundMonitor:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.thread = None
        self.hidden_hwnds = {}
        self.last_inject_time = 0
        self.next_inject_in = 0
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def add_window(self, hwnd, title):
        self.hidden_hwnds[hwnd] = title
    
    def remove_window(self, hwnd):
        if hwnd in self.hidden_hwnds:
            del self.hidden_hwnds[hwnd]
    
    def _monitor_loop(self):
        while self.running:
            try:
                if self.hidden_hwnds:
                    self.last_inject_time = time.time()
                    for hwnd in list(self.hidden_hwnds.keys()):
                        try:
                            hide_from_capture(hwnd)
                        except:
                            pass
            except:
                pass
            
            for i in range(50):
                if not self.running:
                    break
                self.next_inject_in = 5 - (i * 0.1)
                time.sleep(0.1)


def hide_from_capture(hwnd):
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    if not os.path.exists("payload.dll"):
        return False
    
    return injector.inject_hide_capture(pid.value)


def show_in_capture(hwnd):
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    if not os.path.exists("payload.dll"):
        return False
    
    return injector.inject_show_capture(pid.value)


def hide_from_taskbar(hwnd):
    style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    if style == 0:
        return False
    new_style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
    return SetWindowLongW(hwnd, GWL_EXSTYLE, new_style) != 0


def show_in_taskbar(hwnd):
    style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    if style == 0:
        return False
    new_style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
    return SetWindowLongW(hwnd, GWL_EXSTYLE, new_style) != 0


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
    if not title or title in ["Program Manager", "Settings", "Microsoft Text Input Application"]:
        return True
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    _windows_list.append(WindowInfo(hwnd, title, pid.value))
    return True


def get_all_windows():
    global _windows_list
    _windows_list = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    callback = callback_type(enum_windows_callback)
    EnumWindows(callback, 0)
    return _windows_list


def check_window_status(window):
    style = GetWindowLongW(window.hwnd, GWL_EXSTYLE)
    if style != 0:
        has_toolwindow = (style & WS_EX_TOOLWINDOW) != 0
        has_appwindow = (style & WS_EX_APPWINDOW) != 0
        window.is_taskbar_hidden = has_toolwindow and not has_appwindow
    return window


class NoCapApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.config = NoCapConfig()
        self.monitor = BackgroundMonitor(self.config)
        self.search_query = ""
        self.filtered_windows = []
        self.selected_index = 0
        self.message = ""
        self.message_time = 0
        
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
        
        self.monitor.start()
        self.refresh_windows()
        self.restore_hidden_windows()
    
    def toggle_self_hide(self):
        if not self.console_hwnd:
            self.show_message("Console window not found")
            return
        
        if self.self_hidden:
            if show_in_capture(self.console_hwnd):
                self.monitor.remove_window(self.console_hwnd)
                self.self_hidden = False
                self.show_message("NoCap unhidden")
            else:
                self.show_message("Failed to unhide")
        else:
            if hide_from_capture(self.console_hwnd):
                self.monitor.add_window(self.console_hwnd, "NoCap Console")
                self.self_hidden = True
                self.show_message("NoCap hidden")
            else:
                self.show_message("Failed to hide")
    
    def refresh_windows(self):
        windows = get_all_windows()
        for window in windows:
            check_window_status(window)
        
        if self.search_query:
            self.filtered_windows = [w for w in windows if self.search_query.lower() in w.title.lower()]
        else:
            self.filtered_windows = []
        
        if self.selected_index >= len(self.filtered_windows):
            self.selected_index = max(0, len(self.filtered_windows) - 1)
    
    def draw(self):
        try:
            self.stdscr.erase()
            height, width = self.stdscr.getmaxyx()
            
            if height < 10 or width < 80:
                self.stdscr.addstr(0, 0, "Terminal too small. Resize to at least 80x10")
                self.stdscr.refresh()
                return
            
            split_x = width // 2
            
            title = "NOCAP - made by kirsh"
            title_x = max(0, (width - len(title)) // 2)
            if title_x + len(title) < width:
                self.stdscr.addstr(0, title_x, title, curses.color_pair(1))
            
            for y in range(2, height - 2):
                if split_x < width:
                    try:
                        self.stdscr.addstr(y, split_x, "|", curses.color_pair(1))
                    except:
                        pass
            
            self.stdscr.addstr(2, 2, "SEARCH WINDOWS", curses.color_pair(1) | curses.A_BOLD)
            search_text = f"Query: {self.search_query}_"
            if len(search_text) < split_x - 4:
                self.stdscr.addstr(3, 2, search_text, curses.color_pair(1))
            
            if not self.search_query:
                hint_text = "Type to search for windows..."
                if len(hint_text) < split_x - 4:
                    self.stdscr.addstr(5, 2, hint_text, curses.color_pair(1))
            
            start_y = 5
            max_items = height - 8
            
            for i, window in enumerate(self.filtered_windows[:max_items]):
                y = start_y + i
                if y >= height - 3:
                    break
                
                max_title_len = split_x - 7
                title = window.title[:max_title_len] if len(window.title) > max_title_len else window.title
                status = " [T]" if window.is_taskbar_hidden else ""
                display_text = f"> {title}{status}" if i == self.selected_index else f"  {title}{status}"
                
                if len(display_text) > split_x - 3:
                    display_text = display_text[:split_x - 3]
                
                if i == self.selected_index:
                    self.stdscr.attron(curses.color_pair(5))
                    self.stdscr.addstr(y, 2, display_text[:split_x - 3].ljust(split_x - 3))
                    self.stdscr.attroff(curses.color_pair(5))
                else:
                    self.stdscr.addstr(y, 2, display_text[:split_x - 3])
            
            if split_x + 2 < width:
                monitor_count = len(self.monitor.hidden_hwnds)
                header = f"HIDDEN WINDOWS (Monitoring: {monitor_count})"
                self.stdscr.addstr(2, split_x + 2, header, curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(3, split_x + 2, f"Count: {len(self.config.hidden_windows)}", curses.color_pair(1))
            
            for i, hidden in enumerate(self.config.hidden_windows[:max_items]):
                y = start_y + i
                if y >= height - 3:
                    break
                available_width = width - split_x - 4
                if available_width > 3:
                    title = hidden[:available_width - 2]
                    display = f"• {title}"
                    try:
                        self.stdscr.addstr(y, split_x + 2, display[:available_width], curses.color_pair(2))
                    except:
                        pass
            
            monitor_status = "RUNNING" if self.monitor.running else "STOPPED"
            monitor_color = 2 if self.monitor.running else 3
            
            help_text = "ENTER:Hide  ESC:Unhide  Q:Quit"
            if len(help_text) < width:
                self.stdscr.addstr(height - 2, 0, help_text, curses.color_pair(1))
            
            status_text = "Monitoring: "
            status_color = 1
            
            self.stdscr.addstr(height - 1, 0, status_text, curses.color_pair(status_color))
            
            monitor_count = f"{len(self.monitor.hidden_hwnds)} window(s)"
            if len(status_text) + len(monitor_count) < width // 2:
                self.stdscr.addstr(height - 1, len(status_text), monitor_count, curses.color_pair(2))
            
            if len(self.monitor.hidden_hwnds) > 0 and self.monitor.next_inject_in > 0:
                inject_info = f" | Inject: {self.monitor.next_inject_in:.1f}s"
                if len(status_text) + len(inject_info) < width // 2:
                    self.stdscr.addstr(height - 1, len(status_text), inject_info, curses.color_pair(4))
            
            if self.message and time.time() - self.message_time < 2:
                msg_color = 2 if "success" in self.message.lower() or "hidden" in self.message.lower() else 3
                msg_x = width - len(self.message) - 2
                if msg_x > len(status_text) + 2 and len(self.message) < width - len(status_text) - 4:
                    self.stdscr.addstr(height - 1, msg_x, self.message, curses.color_pair(msg_color))
            
            self.stdscr.refresh()
        except curses.error:
            pass
    
    def show_message(self, msg):
        self.message = msg
        self.message_time = time.time()
    
    def restore_hidden_windows(self):
        if not self.config.hidden_windows:
            return
        
        all_windows = get_all_windows()
        restored_count = 0
        
        for hidden_title in self.config.hidden_windows:
            for window in all_windows:
                if window.title == hidden_title:
                    same_process_windows = [w for w in all_windows if w.pid == window.pid]
                    for w in same_process_windows:
                        if hide_from_capture(w.hwnd):
                            self.monitor.add_window(w.hwnd, w.title)
                            restored_count += 1
                    break
        
        if restored_count > 0:
            self.show_message(f"Restored {restored_count} window(s)")
    
    def run(self):
        self.stdscr.timeout(100)
        
        while True:
            self.draw()
            
            try:
                key = self.stdscr.getch()
            except:
                continue
            
            if key == -1:
                continue
            elif key == ord('q') or key == ord('Q'):
                break
            elif key == curses.KEY_UP:
                self.selected_index = max(0, self.selected_index - 1)
            elif key == curses.KEY_DOWN:
                self.selected_index = min(len(self.filtered_windows) - 1, self.selected_index + 1)
            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                self.search_query = self.search_query[:-1]
                self.refresh_windows()
            elif key == 10 or key == 13:  # ENTER - Hide
                if self.filtered_windows and self.selected_index < len(self.filtered_windows):
                    window = self.filtered_windows[self.selected_index]
                    
                    # Find all windows with the same PID
                    all_windows = get_all_windows()
                    same_process_windows = [w for w in all_windows if w.pid == window.pid]
                    
                    success_count = 0
                    for w in same_process_windows:
                        if hide_from_capture(w.hwnd):
                            self.monitor.add_window(w.hwnd, w.title)
                            success_count += 1
                    
                    if success_count > 0:
                        self.config.add_hidden_window(window.title)
                        self.show_message(f"Hidden {success_count} window(s)")
                    else:
                        self.show_message("Failed")
            elif key == 27:  # ESC - Unhide
                if self.filtered_windows and self.selected_index < len(self.filtered_windows):
                    window = self.filtered_windows[self.selected_index]
                    
                    # Find all windows with the same PID
                    all_windows = get_all_windows()
                    same_process_windows = [w for w in all_windows if w.pid == window.pid]
                    
                    success_count = 0
                    for w in same_process_windows:
                        if show_in_capture(w.hwnd):
                            self.monitor.remove_window(w.hwnd)
                            success_count += 1
                    
                    if success_count > 0:
                        self.config.remove_hidden_window(window.title)
                        self.show_message(f"Unhidden {success_count} window(s)")
                    else:
                        self.show_message("Failed")
            elif 32 <= key <= 126:
                self.search_query += chr(key)
                self.refresh_windows()
        
        if self.monitor.running:
            self.monitor.stop()


def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    stdscr.clear()
    stdscr.refresh()
    app = NoCapApp(stdscr)
    app.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
