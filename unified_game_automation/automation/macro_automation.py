# Macro Automation logic
# Loops through 6 configurable mouse coordinate positions (Left, Right, or Middle Click)

import time
from tkinter import messagebox
from core.base_automation import BaseAutomation


class MacroAutomation(BaseAutomation):
    """Automation engine that loops through 6 mouse coordinate positions."""

    def __init__(self, game_connector, ocr_engine=None, status_callback=None, bot_core=None):
        super().__init__(
            game_connector=game_connector,
            ocr_engine=ocr_engine,
            bot_core=bot_core,
            name="Macro",
        )

        # 6 Mouse Position sets
        self.coords = [None] * 6
        self.coords_enabled = [True] * 6
        self.coords_click_type = ["Left Click"] * 6

        # Timing (in milliseconds)
        self.coord_delay_ms = 500
        self.loop_delay_ms = 1000

        # Click stats
        self.total_loops = 0
        self.total_clicks = 0

    def set_coord(self, index, coords):
        if 0 <= index < 6:
            self.coords[index] = coords

    def set_coord_enabled(self, index, enabled):
        if 0 <= index < 6:
            self.coords_enabled[index] = bool(enabled)

    def set_coord_click_type(self, index, click_type):
        if 0 <= index < 6:
            if click_type in ("Right Click", "Middle Click"):
                self.coords_click_type[index] = click_type
            else:
                self.coords_click_type[index] = "Left Click"

    def set_delays(self, coord_delay_ms=500, loop_delay_ms=1000):
        self.coord_delay_ms = max(50, int(coord_delay_ms))
        self.loop_delay_ms = max(50, int(loop_delay_ms))

    def start(self):
        """Start the Macro automation loop."""
        has_coords = any(c and e for c, e in zip(self.coords, self.coords_enabled))

        if not has_coords:
            messagebox.showwarning(
                "No Positions Configured",
                "Please set at least one enabled Mouse Position coordinate before starting!"
            )
            return False

        if not self.game_connector.is_connected():
            if not self.game_connector.connect_to_game():
                messagebox.showerror(
                    "Connection Error",
                    "Could not connect to the game window. Make sure the game is running."
                )
                return False

        if self.running:
            return False

        if not super().start():
            return False

        self.total_loops = 0
        self.total_clicks = 0
        self.update_status("Starting Macro automation loop...")

        if self.core:
            self.core.start_watchdog(timeout_sec=15.0, check_interval_sec=1.0)
            self.core.register_thread("macro-automation-loop", self._automation_loop, daemon=True)

        return True

    def _automation_loop(self):
        """Main loop: Position 1 → Position 2 → Position 3 → Position 4 → Position 5 → Position 6."""
        while self.running and not self.stop_event.is_set():
            if self.core:
                self.core.heartbeat("macro-loop")

            loop_performed = False

            # Iterate through Positions 1 to 6
            for idx in range(6):
                if not self.running or self.stop_event.is_set():
                    break

                coords = self.coords[idx]
                enabled = self.coords_enabled[idx]
                click_type = self.coords_click_type[idx]

                if coords and enabled:
                    if not self.game_connector.is_connected() and not self.game_connector.connect_to_game():
                        self.update_status("Game disconnected")
                        break

                    ok = False
                    if click_type == "Right Click":
                        ok = self.game_connector.right_click_at_position(coords)
                        if ok:
                            self.update_status(f"Right Click Position {idx + 1} at ({coords[0]}, {coords[1]})")
                    elif click_type == "Middle Click":
                        ok = self.game_connector.middle_click_at_position(coords)
                        if ok:
                            self.update_status(f"Middle Click Position {idx + 1} at ({coords[0]}, {coords[1]})")
                    else:
                        ok = self.protected_click(coords, label=f"Left Click Position {idx + 1}")

                    if ok:
                        self.total_clicks += 1
                        loop_performed = True

                    if not self.safe_sleep_ms(self.coord_delay_ms):
                        break

            if loop_performed:
                self.total_loops += 1

            # End of round delay
            if not self.safe_sleep_ms(self.loop_delay_ms):
                break

        self.running = False
        self.update_status(f"Macro stopped — Loops: {self.total_loops}, Total Clicks: {self.total_clicks}")
