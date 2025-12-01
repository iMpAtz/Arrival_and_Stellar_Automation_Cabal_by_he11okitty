# Main entry point for the Unified Game Automation Tool
# This will be the main file that starts the tabbed interface

from ui.main_window import MainWindow

def main():
    """Main entry point for the unified game automation tool"""
    print("Starting Unified Game Automation Tool...")

    # Create and run the main window
    app = MainWindow()
    app.run()

if __name__ == "__main__":
    main()
