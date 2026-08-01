# CABAL Automation Tool — v6.0.5

> **Developed by Hello Kitty Gang** (Based on original source by aquazz / Revolwer)  
> *USE AT YOUR OWN RISK! Provided for educational and automation utility purposes.*

A comprehensive, multi-tab Python automation tool for CABAL Online. The application integrates high-performance screen capture (GDI BitBlt), optical character recognition (Tesseract OCR), template-based computer vision (OpenCV), and background input automation wrapped inside a modern dark-themed CustomTkinter GUI.

---

## 📚 Technical Stack & Libraries Overview

Below is the complete summary of all libraries and modules used in this project, explaining their technical role and internal logic.

| Library / Module | Category | Primary Function | Technical Logic & How It Works |
| :--- | :--- | :--- | :--- |
| **`customtkinter`** | GUI Framework | Modern Dark UI Interface | Extends Tkinter widgets with rounded corners, custom themes, and dark-mode styling (`CTkTabview`, `CTkButton`, `CTkFrame`, `CTkEntry`). Manages event loops and async UI state updates without UI freeze. |
| **`tkinter` / `ttk`** | Base GUI Toolkit | Native Canvas & Windows | Provides core Tkinter foundation (`StringVar`, `DoubleVar`), root window event loop (`Tk`), dialog boxes, and transparent fullscreen selection canvas overlay for defining screen capture areas (`area_selector.py`). |
| **`pytesseract`** | Optical Character Recognition | Text & Digit Extraction | Python wrapper for the embedded Tesseract OCR engine (`Tesseract/tesseract.exe`). Converts preprocessed images into string data or numbers using specialized Page Segmentation Modes (`--psm 7 --oem 1`). |
| **`cv2` (OpenCV)** | Computer Vision | Template Matching | Uses `cv2.matchTemplate()` with normalized cross-correlation (`cv2.TM_CCOEFF_NORMED`) to search for sub-image patterns (pet icons, UI buttons) inside full game screenshots. |
| **`numpy`** | Array Processing | Image Matrix Operations | High-performance N-dimensional array processing required by OpenCV for template matching, thresholding, and array slicing of screenshot pixels. |
| **`win32gui` / `win32con` / `win32ui`** (`pywin32`) | Windows API Bindings | Screen Capture & Window Control | Direct bindings to Windows GDI (`gdi32.dll`) and User32 (`user32.dll`). Captures game framebuffers via **GDI BitBlt** (`BitBlt`, `CreateDCFromHandle`) directly from GPU buffer without needing window focus. Sends raw background mouse/keyboard messages via `PostMessage`. |
| **`pywinauto`** | Windows Automation | Game Window Attachment | Connects to `D3D Window` process class instances, validates window visibility/state, and converts screen coordinates to client window relative coordinates (`game_connector.py`). |
| **`PIL` / `Pillow`** | Image Processing | Contrast, Grayscale & Crop | Converts raw GDI bitmap byte arrays (`BGRX`) to RGB PIL Images. Performs image preprocessing prior to OCR (grayscale conversion, `ImageEnhance.Contrast(2.0)`, `ImageFilter.SHARPEN`), and handles UI image rendering (`CTkImage`). |
| **`keyboard` & `mouse`** | Low-Level Input Hooks | Global Hotkeys & Mouse Capture | Hooks system-level Windows input events (`keyboard.add_hotkey("F5")`) for global start/stop/emergency hotkeys, and tracks mouse coordinates for click target selection. |
| **`threading` & `queue`** | Concurrency | Asynchronous Automation Loops | Executes long-running automation tasks in background daemon threads (`threading.Thread`). Uses `threading.Event` for clean thread cancellation, `threading.RLock` for state synchronization, and a watchdog thread in `BotCore`. |
| **`PyInstaller`** | Executable Packaging | Single `.exe` Distribution | Bundles Python runtime, standard libraries, compiled C-extensions (`cv2`, `PIL`), binaries (`Tesseract/tesseract.exe`), and assets (`logo.ico`, `logo.png`) into a standalone Windows binary (`main_updated.spec`). |

---

## 🏗️ System Architecture & Logic Flow

```mermaid
flowchart TD
    UI["CustomTkinter Main Window (GUI Thread)"] -->|User Action / Hotkey| BC["BotCore (Runtime Controller)"]
    BC -->|Launch Worker| Worker["Automation Worker (Stellar / Arrival / Pet / ImageClicker)"]
    
    subgraph Engine ["Core Engine Layer"]
        Worker -->|Request Screenshot| GC["GameConnector (Win32 GDI BitBlt)"]
        GC -->|Get Window DC & BitBlt| Game["CABAL Game Window (D3D Window)"]
        GC -->|Raw BGRX Buffer| PIL["Pillow Image Processing"]
        
        PIL -->|Enhanced Grayscale Image| OCR["OCREngine (PyTesseract)"]
        PIL -->|Pixel Array| CV["OpenCV (Template Matching)"]
        
        OCR -->|Extracted Text / Numbers| Worker
        CV -->|Target Coordinates (X, Y)| Worker
    end
    
    Worker -->|Send Background Click / Press| GC
    Worker -->|Status Logs| UI
```

### 1. Game Attachment & BitBlt Screen Capture (`game_connector.py`)
- **Connection**: `GameConnector` searches for active Windows handles matching class name `"D3D Window"` (CABAL Online client).
- **Framebuffer Capture**: Instead of using desktop print-screen, it requests a Device Context handle (`win32gui.GetWindowDC`) and executes GDI `BitBlt` (`windll.gdi32.BitBlt`). This reads pixels directly from the window's GPU memory buffer, allowing accurate screenshot capture even if other windows overlap.
- **Coordinate Conversion**: Converts screen coordinates to client-relative coordinates (`GetClientRect`, `ClientToScreen`) for precise click placement.

### 2. Image Preprocessing & OCR Extraction (`ocr_engine.py`)
- **Preprocessing Pipeline**: Converts the cropped screenshot area to grayscale (`L` mode), applies contrast enhancement (`ImageEnhance.Contrast(2.0)`), and sharpens pixel boundaries (`ImageFilter.SHARPEN`).
- **Tesseract Parsing**:
  - For text (Skill names, "Penetration"): Runs standard `image_to_string`.
  - For digits (Skill force "+15", item counts `X / Y`): Uses custom config `--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789/ ` to eliminate non-digit misreadings.
- **Regex Parsing**: Extracts option names and numerical values from raw text output.

### 3. OpenCV Computer Vision (`image_clicker_automation.py`, `pet_automation.py`)
- **Template Matching**: Loads reference images (`logo.png`, pet icons, UI buttons) as NumPy arrays.
- **Scan Cycle**: Performs `cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)` across specified screen regions. When match confidence exceeds the user-configured threshold (e.g. `0.80`), it computes the bounding box center `(X, Y)` and executes click actions.

### 4. Background Threading & Watchdog (`bot_core.py`)
- **Concurrency**: All automation loops execute in background worker threads to keep the CustomTkinter GUI responsive at 60 FPS.
- **Watchdog Timer**: `BotCore` runs a watchdog monitoring thread checking loop heartbeats every second. If an automation loop hangs for >8 seconds, `BotCore` triggers safety cleanup and alerts the user.
- **Emergency Stop**: Pressing emergency key shortcuts or clicking "Stop" sets `stop_event`, cleanly interrupting waiting sleep cycles (`BotCore.sleep(seconds, step=0.05)`).

---

## 🛠️ Main Automation Modules

1. **Stellar Imprint OCR Tab**: Automatically rerolls Stellar stats until requested stat phrase (e.g., "Penetration") and force value (e.g., "+15") are detected by OCR.
2. **Arrival Skill OCR Tab**: Automatically trains Arrival skills, reading skill levels and names via OCR to stop upon reaching target configuration.
3. **Heil Automation Tab**: Automated click sequence runner for Heil activities with customizable delays and click position presets.
4. **Mail Automation Tab**: Automatic mail collecting/sending bot with configurable item slot offsets.
5. **Pet Automation Tab**: Detects pet untrain icons via OpenCV template matching and performs automated pet skill resets.
6. **Image Clicker Tab**: Independent continuous multi-image detection bot. Scans specified screen zones for target template images and clicks upon visual match with customizable cooldowns.

---

## 🚀 How to Build & Run

### Running from Source
1. **Prerequisites**: Python 3.10+ installed on Windows.
2. **Run as Administrator**: Right-click PowerShell/CMD and select **Run as Administrator** (required for Windows API window attachment).
3. **Start Application**:
   ```powershell
   python unified_game_automation/main.py
   ```

### Building Standalone Executable (.exe)
To compile the complete application into a single standalone `.exe` using PyInstaller:
```powershell
pyinstaller .\main_updated.spec
```
The compiled output will be generated inside the `dist/` directory as `HelloK1TTY_Automation_V6.0.5.exe`.

---

## 📋 General Instructions & Best Practices

1. **Run as Administrator**: Windows security restricts sending low-level window events to DirectX games unless the automation tool runs with Administrator privileges.
2. **In-Game Font Setting**: If using custom game fonts, set in-game font to **Tahoma** (*Esc -> Options -> Preferences -> Font*) for optimal Tesseract OCR accuracy.
3. **Main Display Usage**: Keep the game window on your primary monitor to avoid multi-monitor DPI scaling coordinate offsets.
4. **Log Files**: Application logs are automatically saved to `C:\Users\<YOUR_USER>\stellarlink_logs` for tracking OCR readings and troubleshooting.

---

## 👤 Credits & Disclaimers

- **Original Source Code**: Discord (`aquazz`), In-game (`Revolwer`).
- **Enhanced & Maintained By**: **Hello Kitty Gang (PlayCabal Guild)**.
- **Disclaimer**: *This tool is provided for educational and private convenience purposes. Users assume full responsibility for using automation tools in compliance with game service terms.*
