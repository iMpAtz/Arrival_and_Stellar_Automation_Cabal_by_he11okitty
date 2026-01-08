# Heil automation logic
# Advanced click automation with OCR detection for inventory management

import time
import threading
from tkinter import messagebox

class HeilAutomation:
    def __init__(self, game_connector, ocr_engine, status_callback=None):
        """Initialize Heil automation"""
        self.game_connector = game_connector
        self.ocr_engine = ocr_engine
        self.status_callback = status_callback

        # Automation state
        self.running = False
        self.last_inventory_check_time = 0  # Track when inventory management was last run

        # Configuration - 5 click positions
        self.click_coords_1 = None  # Position 1 - Main action
        self.click_coords_2 = None  # Position 2 - Inventory management
        self.click_coords_3 = None  # Position 3 - Inventory management
        self.click_coords_4 = None  # Position 4 - Inventory management
        self.click_coords_5 = None  # Position 5 - Inventory management
        self.ocr_area_count = None   # OCR area for item count (X / Y)
        self.ocr_area_message = None # OCR area for inventory message
        self.delay_ms = 1000         # Default delay in milliseconds
        self.inventory_check_cooldown = 30  # Cooldown in seconds (1 minute)

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def set_click_position_1(self, coords):
        """Set click position 1 (main action)"""
        self.click_coords_1 = coords

    def set_click_position_2(self, coords):
        """Set click position 2 (inventory management)"""
        self.click_coords_2 = coords

    def set_click_position_3(self, coords):
        """Set click position 3 (inventory management)"""
        self.click_coords_3 = coords

    def set_click_position_4(self, coords):
        """Set click position 4 (inventory management)"""
        self.click_coords_4 = coords

    def set_click_position_5(self, coords):
        """Set click position 5 (inventory management)"""
        self.click_coords_5 = coords

    def set_ocr_area_count(self, area):
        """Set the OCR area for item count detection (X / Y format)"""
        self.ocr_area_count = area

    def set_ocr_area_message(self, area):
        """Set the OCR area for inventory message detection"""
        self.ocr_area_message = area

    def set_delay(self, delay_ms):
        """Set the delay in milliseconds"""
        self.delay_ms = delay_ms
        print(f"[Automation] Delay updated to: {self.delay_ms} ms ({self.delay_ms / 1000.0} seconds)")

    def start(self):
        """Start the Heil automation"""
        # Check if all required positions are set
        if not self.click_coords_1:
            messagebox.showwarning("Missing click position", "Please set click position 1 first!")
            return False

        if not self.click_coords_2 or not self.click_coords_3 or not self.click_coords_4 or not self.click_coords_5:
            messagebox.showwarning("Missing click positions", "Please set all click positions (2, 3, 4, 5) for inventory management!")
            return False

        if not self.ocr_area_count:
            messagebox.showwarning("Missing OCR area", "Please define OCR area for item count detection!")
            return False

        if not self.ocr_area_message:
            messagebox.showwarning("Missing OCR area", "Please define OCR area for inventory message detection!")
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

    def _detect_inventory_message(self):
        """Detect inventory full message using OCR"""
        try:
            # Capture screenshot of OCR area for message detection
            screenshot = self.game_connector.capture_area_bitblt(self.ocr_area_message)
            if screenshot is None:
                return False

            # Extract text using OCR
            raw_text = self.ocr_engine.extract_text(screenshot)
            text_lower = raw_text.lower()

            # Check for inventory message
            if "need more than 16 space" in text_lower or "inventory" in text_lower:
                print(f"Inventory message detected: {repr(raw_text)}")
                return True

            return False
        except Exception as e:
            print(f"OCR detection error: {e}")
            return False

    def _check_stop_condition(self):
        """Stop when detected number from OCR is <= 12"""
        try:
        # Capture screenshot of OCR area
            screenshot = self.game_connector.capture_area_bitblt(self.ocr_area_count)
            if screenshot is None:
                return False

            # Extract numbers using OCR
            raw_text = self.ocr_engine.extract_numbers(screenshot)
            print(f"OCR numbers read: {repr(raw_text)}")

            import re
            numbers = re.findall(r'\d+', raw_text)

            if not numbers:
                return False

        # Use first detected number group
            value = int(numbers[0])
            print(f"OCR value detected: {value}")

        # Stop condition
            if value <= 12 or value == 274:
                self.update_status(f"⚠️ Stop condition met: {value} <= 12")
                return True

            return False
        except Exception as e:
            print(f"Stop condition check error: {e}")
            return False

    def _inventory_management_loop(self):
        """Execute inventory management by clicking positions 2, 3, 4, 5"""
        self.update_status("🎒 Inventory full detected! Starting inventory management...")
        
        # Fixed 1 second delay for inventory positions (2-5)
        delay_sec = 1.0

        # Click position 2
        if not self.running:
            return
        self.update_status("Clicking position 2...")
        self.game_connector.click_at_position(self.click_coords_2)
        self._interruptible_sleep(delay_sec)

        # Click position 3
        if not self.running:
            return
        self.update_status("Clicking position 3...")
        self.game_connector.click_at_position(self.click_coords_3)
        self._interruptible_sleep(delay_sec)

        # Click position 4
        if not self.running:
            return
        self.update_status("Clicking position 4...")
        self.game_connector.click_at_position(self.click_coords_4)
        self._interruptible_sleep(delay_sec)

        # Click position 5
        if not self.running:
            return
        self.update_status("Clicking position 5...")
        self.game_connector.click_at_position(self.click_coords_5)
        self._interruptible_sleep(delay_sec)

        self.update_status("✅ Inventory management complete, resuming main loop...")

    def _interruptible_sleep(self, duration):
        """Sleep that can be interrupted by stopping automation"""
        # Break sleep into small chunks to allow quick response to stop
        # Use smaller chunk size for very short delays
        chunk = min(0.05, duration / 2)  # 50ms chunks or half duration, whichever is smaller
        elapsed = 0
        
        while elapsed < duration and self.running:
            remaining = duration - elapsed
            sleep_time = min(chunk, remaining)
            time.sleep(sleep_time)
            elapsed += sleep_time

    def _automation_loop(self):
        """Main automation loop - click position 1, check for inventory message, handle if needed"""
        self.update_status("⏱️ Heil automation started")
        
        click_count = 0
        inventory_management_count = 0
        delay_sec = self.delay_ms / 1000.0
        ocr_check_interval = 50  # Check OCR every 50 clicks
        
        print(f"Position 1 delay set to: {delay_sec} seconds ({self.delay_ms} ms)")
        print(f"OCR checks will run every {ocr_check_interval} clicks")

        while self.running:
            loop_start = time.time()
            click_count += 1

            # Click at position 1 (main action)
            if not self.game_connector.click_at_position(self.click_coords_1):
                pass  # Silent fail, don't spam status
            
            # Wait for the specified delay (using interruptible sleep)
            self._interruptible_sleep(delay_sec)

            # Check OCR only every N clicks to improve performance
            should_check_ocr = (click_count % ocr_check_interval == 0)
            
            if should_check_ocr:
                self.update_status(f"🔍 Running OCR check at click #{click_count}")
                ocr_start = time.time()
                
                # Check for stop condition (number comparison)
                if self._check_stop_condition():
                    self.update_status("🛑 Stopping automation - Stop condition met!")
                    self.stop()
                    messagebox.showinfo("Automation Stopped", "Stop condition met: Left number is less than right number.")
                    break
                
                # Check for inventory full message (with cooldown)
                current_time = time.time()
                time_since_last_check = current_time - self.last_inventory_check_time
                
                if time_since_last_check >= self.inventory_check_cooldown:
                    if self._detect_inventory_message():
                        inventory_management_count += 1
                        self._inventory_management_loop()
                        # Update last check time after inventory management completes
                        self.last_inventory_check_time = time.time()
                
                ocr_time = time.time() - ocr_start
                print(f"[OCR Check #{click_count}] Took: {ocr_time:.4f}s")
            
            loop_time = time.time() - loop_start
            if should_check_ocr:
                print(f"[Loop #{click_count}] Total time: {loop_time:.4f}s (with OCR)\n")
            elif click_count % 10 == 0:  # Print every 10 clicks for monitoring
                print(f"[Loop #{click_count}] Fast loop time: {loop_time:.4f}s")

        self.update_status(f"Heil automation stopped - Clicks: {click_count}, Inventory management: {inventory_management_count}")

    def stop(self):
        """Stop the Heil automation"""
        self.running = False
        self.update_status("Heil automation stopped")

    def emergency_stop(self):
        """Emergency stop the automation"""
        if self.running:
            self.stop()
            self.update_status("🚨 EMERGENCY STOP - Heil automation stopped!")
