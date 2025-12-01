# Heil automation logic
# Simple click automation without OCR

import time
import threading
from tkinter import messagebox

class HeilAutomation:
    def __init__(self, game_connector, status_callback=None):
        """Initialize Heil automation"""
        self.game_connector = game_connector
        self.status_callback = status_callback

        # Automation state
        self.running = False

        # Configuration
        self.click_coords = None
        self.delay_ms = 1000  # Default delay in milliseconds

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def set_click_position(self, coords):
        """Set the click position coordinates"""
        self.click_coords = coords

    def set_delay(self, delay_ms):
        """Set the delay in milliseconds"""
        self.delay_ms = delay_ms

    def start(self):
        """Start the Heil automation"""
        if not self.click_coords:
            messagebox.showwarning("Missing click position", "Please set the click position first!")
            return False

        # Connect to game if not already connected
        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return False

        self.update_status(f"Starting Heil automation - delay: {self.delay_ms}ms")

        self.running = True

        # Start automation in thread
        threading.Thread(target=self._automation_loop, daemon=True).start()
        return True

    def _automation_loop(self):
        """Main automation loop - continuously click at the set position with delay"""
        self.update_status("⏱️ Heil automation started")
        
        click_count = 0
        delay_sec = self.delay_ms / 1000.0

        while self.running:
            click_count += 1

            # Click at the set position
            if not self.game_connector.click_at_position(self.click_coords):
                self.update_status("Click failed - retrying...")
            else:
                self.update_status(f"Click #{click_count} - waiting {self.delay_ms}ms")

            # Wait for the specified delay
            time.sleep(delay_sec)

        self.update_status(f"Heil automation stopped - Total clicks: {click_count}")

    def stop(self):
        """Stop the Heil automation"""
        self.running = False
        self.update_status("Heil automation stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Heil automation stopped!")
