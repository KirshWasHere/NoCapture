# NoCap

Hide any window from screen capture software like OBS, Discord, or screenshots. Works on Windows 10/11.

## WARNING

**Use common sense and don't try to hide any games.** If anticheat detects you injected some random DLL and bans you, I am not responsible. Use common sense.

## What it does

NoCap prevents windows from appearing in:
- OBS recordings/streams
- Discord screen sharing
- Screenshots
- Any screen capture software

## How it works

Windows has an API called `SetWindowDisplayAffinity` that blocks screen capture. The catch is it only works when called from inside the target process. 

NoCap uses DLL injection to call this API from within the target window's process. The injected DLL (`payload.dll`) enumerates all windows belonging to that process and applies the capture blocking flag.

## Requirements

- Windows 10/11 (v2004+)
- Python 3.7+
- Visual Studio with C++ tools (to compile the DLL)
- Administrator privileges (for DLL injection)

## Setup

### 1. Compile the DLL

You need Visual Studio with C++ tools installed.

Run `build_dll.bat` or manually compile:

```cmd
cl /LD /O2 payload.c /link /OUT:payload.dll user32.lib kernel32.lib
```

This creates `payload.dll` which gets injected into target processes.

**Note:** Edit `build_dll.bat` if your Visual Studio path is different.

### 2. Install Python dependencies

```cmd
pip install -r requirements.txt
```

## Usage

### Interactive Mode (TUI)

Run as Administrator:

```cmd
python nocap.py
```

**Features:**
- Split-panel interface: Search windows on left, hidden windows on right
- Type to search for windows by name
- Press `ENTER` to hide selected window (hides all windows from same process)
- Press `ESC` to unhide selected window
- Press `Q` to quit
- Hidden windows are saved to config and restored on restart
- Background monitor re-injects DLL every 5 seconds to maintain hidden state

### Background Service Mode

For persistent monitoring without keeping the TUI open:

**Start service:**
```cmd
start_service.bat
```

**Stop service:**
```cmd
stop_service.bat
```

The service runs in the background and keeps re-injecting hidden windows every 5 seconds. It reads from the same config file as the TUI, so any windows you hide in the TUI will be monitored by the service.

## Files

- `nocap.py` - Main TUI application
- `nocap_service.py` - Background service (no GUI)
- `injector.py` - DLL injection logic
- `payload.c` - Source code for the injected DLL
- `build_dll.bat` - Compiles the DLL
- `start_service.bat` - Starts background service
- `stop_service.bat` - Stops background service
- `requirements.txt` - Python dependencies
- `~/.nocap_config.json` - Config file (auto-created)

## Technical Details

**Injection process:**
1. Get target window's process ID
2. Open the process with `OpenProcess`
3. Allocate memory in target process with `VirtualAllocEx`
4. Write DLL path to allocated memory with `WriteProcessMemory`
5. Create remote thread that calls `LoadLibraryW` with `CreateRemoteThread`
6. DLL loads and calls `SetWindowDisplayAffinity` on all windows in that process

**Process grouping:**
When you hide a window, NoCap automatically hides ALL windows belonging to the same process. This ensures apps like Discord (which have multiple windows) are completely hidden.

**Persistence:**
Hidden windows are saved to `~/.nocap_config.json` and automatically restored when you restart NoCap.

## Limitations

- Requires Administrator privileges
- Only works on Windows 10 v2004+ and Windows 11
- Some protected processes (like Task Manager) cannot be injected
- Anti-cheat software may flag DLL injection
- Don't use on games - you may get banned

## License

MIT
