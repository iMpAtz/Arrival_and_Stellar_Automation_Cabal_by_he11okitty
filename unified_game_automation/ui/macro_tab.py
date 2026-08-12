# Macro tab — CustomTkinter UI for 6 Mouse Click Positions with Left / Right / Middle Click Selection

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import mouse
import json
import os
import sys
from automation.macro_automation import MacroAutomation

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "purple": "#7c3aed", "muted": "#888888",
    "surface2": "#333333",
}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(
        header, text=title,
        font=ctk.CTkFont("Segoe UI", 11, "bold"),
        text_color="#ffffff", anchor="w"
    ).pack(side=tk.LEFT, padx=12, pady=4)
    return header


class MacroTab:
    """UI tab for setting 6 mouse click coordinates with Left, Right, or Middle click selection."""

    def __init__(self, parent_frame, main_window):
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = MacroAutomation(
            game_connector=main_window.game_connector,
            ocr_engine=main_window.ocr_engine,
            status_callback=main_window.update_status,
            bot_core=main_window.bot_core,
        )

        # 6 Coordinate data storage & UI variables
        self.click_coords = [None] * 6
        self.click_coords_enabled = [tk.BooleanVar(value=True) for _ in range(6)]
        self.click_coord_vars = [tk.StringVar(value="Not set") for _ in range(6)]
        self.click_coords_type = [tk.StringVar(value="Left Click") for _ in range(6)]

        # Delay variables
        self.coord_delay_var = tk.StringVar(value="500")
        self.loop_delay_var = tk.StringVar(value="1000")

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "macro_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # ── Intro Card ──
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        intro_inner = ctk.CTkFrame(intro, fg_color="transparent")
        intro_inner.pack(fill=tk.X, padx=12, pady=8)

        ctk.CTkLabel(intro_inner, text="🕹️", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(intro_inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ctk.CTkLabel(
            tf, text="MACRO — Continuous 6 Position Click Automation",
            font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w"
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            tf, text="1) Set 6 Click Positions  •  2) Choose Click Type (Left / Right / Middle)  •  3) Set Delays  •  4) Start Loop",
            font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w"
        ).pack(fill=tk.X)

        # ── 6 Click Positions Card ──
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Mouse Positions (6 Positions)")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        for idx in range(6):
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 6))

            ctk.CTkCheckBox(
                row, text="", variable=self.click_coords_enabled[idx],
                width=24, height=24
            ).pack(side=tk.LEFT, padx=(0, 6))

            ctk.CTkLabel(
                row, text=f"Position {idx + 1}:",
                font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w"
            ).pack(side=tk.LEFT)

            ctk.CTkLabel(
                row, textvariable=self.click_coord_vars[idx],
                font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w"
            ).pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)

            ctk.CTkOptionMenu(
                row, values=["Left Click", "Right Click", "Middle Click"],
                variable=self.click_coords_type[idx],
                width=120, height=28,
                font=ctk.CTkFont("Segoe UI", 10, "bold"),
                fg_color=_A["surface2"], button_color=_A["primary"],
                dropdown_fg_color="#333333",
            ).pack(side=tk.RIGHT, padx=(0, 6))

            ctk.CTkButton(
                row, text="Set",
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                fg_color=_A["primary"], hover_color="#1a5a8e",
                width=65, height=28, corner_radius=6,
                command=lambda pos_idx=idx: self.set_click_position(pos_idx),
            ).pack(side=tk.RIGHT)

        # ── Delays & Timing Card ──
        delay_card = ctk.CTkFrame(scroll, corner_radius=8)
        delay_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(delay_card, "⏱️  Delays & Timing Settings", _A["warning"])
        delay_body = ctk.CTkFrame(delay_card, fg_color="transparent")
        delay_body.pack(fill=tk.X, padx=12, pady=8)

        # Row 1: Position Click Delay
        d_row1 = ctk.CTkFrame(delay_body, fg_color="transparent")
        d_row1.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(d_row1, text="Position Click Delay (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=180, anchor="w").pack(side=tk.LEFT)
        ctk.CTkEntry(d_row1, textvariable=self.coord_delay_var, width=90, height=28).pack(side=tk.LEFT, padx=(6, 8))

        # Row 2: Full Loop Delay
        d_row2 = ctk.CTkFrame(delay_body, fg_color="transparent")
        d_row2.pack(fill=tk.X, pady=(0, 2))
        ctk.CTkLabel(d_row2, text="End-of-Loop Delay (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=180, anchor="w").pack(side=tk.LEFT)
        ctk.CTkEntry(d_row2, textvariable=self.loop_delay_var, width=90, height=28).pack(side=tk.LEFT, padx=(6, 8))

        # ── Control Buttons Bar ──
        ctrl = ctk.CTkFrame(scroll, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(4, 8))
        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack()

        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  START",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["success"], hover_color="#258a5e",
            width=120, height=38, corner_radius=8,
            command=self.start_automation,
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_row, text="⏹  STOP",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["danger"], hover_color="#c9302c",
            width=120, height=38, corner_radius=8,
            command=self.stop_automation,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_save_config = ctk.CTkButton(
            btn_row, text="💾  Save Config",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["primary"], hover_color="#1a5a8e",
            width=120, height=38, corner_radius=8,
            command=self.save_config,
        )
        self.btn_save_config.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            btn_row, text="🗑️  Clear",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["surface2"], hover_color="#444444",
            width=90, height=38, corner_radius=8,
            command=self.clear_coords,
        )
        self.btn_clear.pack(side=tk.LEFT)

    # ──────────────────────────────────────────────────────────
    # Coordinate Pickers
    # ──────────────────────────────────────────────────────────
    def set_click_position(self, index):
        """Capture click position for index 0 to 5."""
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            f"Click on Position {index + 1} target in the game window.\n"
            "The coordinates will be captured automatically."
        )

        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                if success:
                    self.click_coords[index] = (rel_x, rel_y)
                    self.automation.set_coord(index, (rel_x, rel_y))
                    self.click_coord_vars[index].set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Position {index + 1} set at ({rel_x}, {rel_y})")
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def clear_coords(self):
        """Reset all coordinates."""
        for idx in range(6):
            self.click_coords[idx] = None
            self.automation.set_coord(idx, None)
            self.click_coord_vars[idx].set("Not set")

        self.main_window.update_status("Macro coordinates cleared.")

    # ──────────────────────────────────────────────────────────
    # Automation Start / Stop
    # ──────────────────────────────────────────────────────────
    def start_automation(self):
        """Pass configuration to MacroAutomation and start loop."""
        # Update 6 click coords config
        for idx in range(6):
            self.automation.set_coord(idx, self.click_coords[idx])
            self.automation.set_coord_enabled(idx, self.click_coords_enabled[idx].get())
            self.automation.set_coord_click_type(idx, self.click_coords_type[idx].get())

        # Update delays
        try:
            c_delay = int(self.coord_delay_var.get())
            l_delay = int(self.loop_delay_var.get())
            self.automation.set_delays(c_delay, l_delay)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for delays.")
            return

        self.automation.start()

    def stop_automation(self):
        """Stop Macro automation loop."""
        self.automation.stop()

    # ──────────────────────────────────────────────────────────
    # Config Save / Load
    # ──────────────────────────────────────────────────────────
    def save_config(self):
        """Save Macro configuration to JSON file."""
        config_data = {
            "click_coords": [list(c) if c else None for c in self.click_coords],
            "click_coords_enabled": [var.get() for var in self.click_coords_enabled],
            "click_coords_type": [var.get() for var in self.click_coords_type],
            "coord_delay_ms": self.coord_delay_var.get(),
            "loop_delay_ms": self.loop_delay_var.get(),
        }
        try:
            path = self._get_config_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Macro config saved successfully!")
            messagebox.showinfo("Config Saved", "Macro configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Macro config: {e}")

    def load_config(self):
        """Load Macro configuration from JSON file."""
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("click_coords"):
                for idx, c in enumerate(data["click_coords"]):
                    if idx < 6 and c:
                        coord_tuple = tuple(c)
                        self.click_coords[idx] = coord_tuple
                        self.automation.set_coord(idx, coord_tuple)
                        self.click_coord_vars[idx].set(f"({coord_tuple[0]}, {coord_tuple[1]})")

            if data.get("click_coords_enabled"):
                for idx, en in enumerate(data["click_coords_enabled"]):
                    if idx < 6:
                        self.click_coords_enabled[idx].set(bool(en))
                        self.automation.set_coord_enabled(idx, bool(en))

            if data.get("click_coords_type"):
                for idx, ct in enumerate(data["click_coords_type"]):
                    if idx < 6:
                        self.click_coords_type[idx].set(str(ct))
                        self.automation.set_coord_click_type(idx, str(ct))

            if data.get("coord_delay_ms"):
                self.coord_delay_var.set(str(data["coord_delay_ms"]))
            if data.get("loop_delay_ms"):
                self.loop_delay_var.set(str(data["loop_delay_ms"]))

        except Exception as e:
            print(f"Failed to load Macro config: {e}")
