# Main entry point for the Unified Game Automation Tool
# This will be the main file that starts the tabbed interface

from ui.main_window import MainWindow

def main():
    """Main entry point for the unified game automation tool"""
    print("Starting Unified Game Automation Tool...")

    # Enable Windows DPI Awareness to prevent coordinate shifting in PyInstaller executables
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # Create and run the main window
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
