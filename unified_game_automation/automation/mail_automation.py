# Auto Mail Receive automation logic
# Simple 2-position click automation with configurable delay

import time
import threading
from tkinter import messagebox

class MailAutomation:
    def __init__(self, game_connector, status_callback=None):
        """Initialize Mail automation"""
        self.game_connector = game_connector
        self.status_callback = status_callback

        # Automation state
        self.running = False

        # Configuration - 2 click positions
        self.click_coords_1 = None  # Position 1
        self.click_coords_2 = None  # Position 2
        self.delay_ms = 500          # Default delay in milliseconds

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def set_click_position_1(self, coords):
        """Set click position 1"""
        self.click_coords_1 = coords

    def set_click_position_2(self, coords):
        """Set click position 2"""
        self.click_coords_2 = coords

    def set_delay(self, delay_ms):
        """Set the delay in milliseconds"""
        self.delay_ms = delay_ms
        print(f"[Mail Automation] Delay updated to: {self.delay_ms} ms ({self.delay_ms / 1000.0} seconds)")

    def start(self):
        """Start the Mail automation"""
        # Check if all required positions are set
        if not self.click_coords_1:
            messagebox.showwarning("Missing click position", "Please set click position 1 first!")
            return False

        if not self.click_coords_2:
            messagebox.showwarning("Missing click position", "Please set click position 2!")
            return False

        # Connect to game if not already connected
        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return False

        self.update_status(f"Starting Auto Mail Receive - delay: {self.delay_ms}ms")

        self.running = True

        # Start automation in thread
        threading.Thread(target=self._automation_loop, daemon=True).start()
        return True

    def _automation_loop(self):
        """Main automation loop - alternately click position 1 and position 2"""
        self.update_status("📧 Auto Mail Receive started")
        
        click_count = 0
        delay_sec = self.delay_ms / 1000.0
        
        print(f"Mail automation delay set to: {delay_sec} seconds ({self.delay_ms} ms)")

        while self.running:
            click_count += 1

            # Click position 1
            if self.game_connector.click_at_position(self.click_coords_1):
                self.update_status(f"📬 Click #{click_count}: Position 1")
            else:
                self.update_status(f"⚠️ Position 1 click failed - retrying...")

            # Wait
            time.sleep(delay_sec)
            
            if not self.running:
                break

            # Click position 2
            if self.game_connector.click_at_position(self.click_coords_2):
                self.update_status(f"📭 Click #{click_count}: Position 2")
            else:
                self.update_status(f"⚠️ Position 2 click failed - retrying...")

            # Wait
            time.sleep(delay_sec)

        self.update_status(f"Auto Mail Receive stopped - Total cycles: {click_count}")

    def stop(self):
        """Stop the Mail automation"""
        self.running = False
        self.update_status("Auto Mail Receive stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Auto Mail Receive stopped!")
