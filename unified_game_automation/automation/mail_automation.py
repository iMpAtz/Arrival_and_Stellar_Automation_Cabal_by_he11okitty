# Auto Mail Receive automation logic
# Simple 2-position click automation with configurable delay

from tkinter import messagebox
from core.base_automation import BaseAutomation


class MailAutomation(BaseAutomation):
    def __init__(self, game_connector, status_callback=None, bot_core=None):
        """Initialize Mail automation"""
        super().__init__(game_connector=game_connector, ocr_engine=None, bot_core=bot_core, name="Mail")

        # Automation state
        # Configuration - 2 click positions
        self.click_coords_1 = None  # Position 1
        self.click_coords_2 = None  # Position 2
        self.delay_ms = 500          # Default delay in milliseconds

    def update_status(self, message):
        if self.core:
            self.core.update_status(f"[Mail] {message}")

    def set_click_position_1(self, coords):
        """Set click position 1"""
        self.click_coords_1 = coords

    def set_click_position_2(self, coords):
        """Set click position 2"""
        self.click_coords_2 = coords

    def set_delay(self, delay_ms):
        """Set the delay in milliseconds"""
        self.delay_ms = delay_ms

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

        if self.running:
            return False
        if not super().start():
            return False
        if self.core:
            self.core.start_watchdog(timeout_sec=8.0, check_interval_sec=1.0)
            self.core.register_thread("mail-automation-loop", self._automation_loop, daemon=True)
        return True

    def _automation_loop(self):
        """Main automation loop - alternately click position 1 and position 2"""
        self.update_status("📧 Auto Mail Receive started")
        
        click_count = 0
        delay_sec = self.delay_ms / 1000.0

        while self.running:
            if self.stop_event.is_set():
                break
            if self.core:
                self.core.heartbeat("mail-main-loop")
            click_count += 1

            # Click position 1
            if self.protected_click(self.click_coords_1, label=f"Position 1 #{click_count}"):
                self.update_status(f"📬 Click #{click_count}: Position 1")
            else:
                self.update_status(f"⚠️ Position 1 click failed - retrying...")

            # Wait
            if not self.safe_sleep_ms(self.delay_ms):
                break
            
            if not self.running:
                break

            # Click position 2
            if self.protected_click(self.click_coords_2, label=f"Position 2 #{click_count}"):
                self.update_status(f"📭 Click #{click_count}: Position 2")
            else:
                self.update_status(f"⚠️ Position 2 click failed - retrying...")

            # Wait
            if not self.safe_sleep_ms(self.delay_ms):
                break

        self.update_status(f"Auto Mail Receive stopped - Total cycles: {click_count}")
        self.running = False

    def stop(self):
        """Stop the Mail automation"""
        self.running = False
        if self.core:
            self.core.stop()
        self.update_status("Auto Mail Receive stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Auto Mail Receive stopped!")
