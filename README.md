# NoCap

Hide any window from screen capture software like OBS, Discord, or screenshots. Works on Windows 10/11.

## What it does

NoCap prevents windows from appearing in:
- OBS recordings/streams
- Discord screen sharing
- Screenshots
- Any screen capture software

It can also hide windows from the taskbar.

## How it works

Windows has an API called `SetWindowDisplayAffinity` that blocks screen capture. The catch is it only works when called from inside the target process. 

NoCap uses DLL injection to call this API from within the target window's process. The injected DLL (`payload.dll`) enumerates all windows belonging to that process and applies the capture blocking flag.

## Requirements

- Windows 10/11
- Python 3.7+
- Visual Studio (to compile the DLL)
- Administrator privileges (for DLL injection)

## Building

### 1. Compile the DLL

You need Visual Studio with C++ tools installed.

Open "x64 Native Tools Command Prompt for VS" and run:

```cmd
cd nocap
cl /LD /O2 payload.c /link /OUT:payload.dll user32.lib kernel32.lib
```

This creates `payload.dll` which gets injected into target processes.

**Note:** The `build_dll.bat` script uses a hardcoded Visual Studio path and won't work on your system.

### 2. Install Python dependencies

```cmd
pip install -r requirements.txt
```

## Usage

Run as Administrator:

```cmd
python nocap.py
```

### Features

- **Hide/Show Windows**: Select any window and hide it from capture or taskbar
- **Auto-Hide List**: Add window patterns that get automatically hidden when they appear
- **Background Monitor**: Runs in background and auto-hides windows matching your list
- **Search**: Filter windows by name
- **Arrow key navigation**: Navigate menus with arrow keys

### Controls

- `↑/↓`: Navigate
- `ENTER`: Select
- `S`: Search windows
- `C`: Clear search
- `A`: Add pattern (in auto-hide list)
- `Q`: Back/Quit

## Files

- `nocap.py` - Main program with TUI
- `injector.py` - DLL injection logic
- `payload.c` - Source code for the injected DLL
- `payload.dll` - Compiled DLL (you need to build this)
- `requirements.txt` - Python dependencies

## Technical Details

The injection process:
1. Get target window's process ID
2. Open the process with `OpenProcess`
3. Allocate memory in target process with `VirtualAllocEx`
4. Write DLL path to allocated memory with `WriteProcessMemory`
5. Create remote thread that calls `LoadLibraryW` with `CreateRemoteThread`
6. DLL loads and calls `SetWindowDisplayAffinity` on all windows in that process

## Limitations

- Requires Administrator privileges
- Only works on Windows 10 v2004+ and Windows 11
- Some protected processes (like Task Manager) cannot be injected
- Anti-cheat software may flag DLL injection
- Dont use it on any games pls..if u do im not responsible for any bans

## License

MIT
