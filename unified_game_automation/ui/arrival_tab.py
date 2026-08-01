# Arrival Skill tab — CustomTkinter rewrite
# All business logic preserved; only UI widgets changed.

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import mouse
import re
import json
from data.arrival_data import get_offensive_skills, get_defensive_skills, get_stat_variations
from automation.arrival_automation import ArrivalAutomation
import os
from datetime import datetime
import sys

# Accent colors (shared with main_window)
_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "info": "#17a2b8", "surface2": "#333333",
    "muted": "#888888",
}


def _section_header(parent, title, color=None):
    """Reusable section header inside a card."""
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(
        header, text=title,
        font=ctk.CTkFont("Segoe UI", 11, "bold"),
        text_color="#ffffff", anchor="w",
    ).pack(side=tk.LEFT, padx=12, pady=4)
    return header


class ArrivalTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Arrival Skill tab."""
        self.parent_frame = parent_frame
        self.main_window = main_window

        # Automation components
        self.automation = ArrivalAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core,
        )
        self.automation.set_target_found_callback(self.on_target_found)

        # UI state
        self.area = None
        self.apply_button_coords = None
        self.change_button_coords = None

        # Create UI
        self.create_ui()
        self.load_config()

    # ──────────────────────────────────────────────────────────
    # Config path (unchanged business logic)
    # ──────────────────────────────────────────────────────────
    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "arrival_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    # ──────────────────────────────────────────────────────────
    # UI CREATION
    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        """Build the Arrival Skill tab UI with CustomTkinter."""

        # Scrollable container so content never overflows
        scroll = ctk.CTkScrollableFrame(
            self.parent_frame, fg_color="transparent",
        )
        scroll.pack(fill=tk.BOTH, expand=True)

        # ── Intro card ──
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        intro_inner = ctk.CTkFrame(intro, fg_color="transparent")
        intro_inner.pack(fill=tk.X, padx=12, pady=8)

        ctk.CTkLabel(
            intro_inner, text="⚔️",
            font=ctk.CTkFont("Segoe UI", 16),
        ).pack(side=tk.LEFT, padx=(0, 8))

        text_fr = ctk.CTkFrame(intro_inner, fg_color="transparent")
        text_fr.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ctk.CTkLabel(
            text_fr, text="ARRIVAL SKILL — OCR Stat Reroll",
            font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w",
        ).pack(fill=tk.X)
        ctk.CTkLabel(
            text_fr,
            text="1) Set Buttons  •  2) Define Area  •  3) Select Stats  •  4) Start",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=_A["muted"], anchor="w",
        ).pack(fill=tk.X)

        # ── Button Coordinates ──
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Button Coordinates")

        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        # Apply button row
        self.apply_coord_var = tk.StringVar(value="Not set")
        self._coord_row(
            coord_body, "Apply:", self.apply_coord_var,
            self.set_apply_button,
        )
        # Change button row
        self.change_coord_var = tk.StringVar(value="Not set")
        self._coord_row(
            coord_body, "Change:", self.change_coord_var,
            self.set_change_button,
        )

        # ── Define OCR Area ──
        area_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        area_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_define_area = ctk.CTkButton(
            area_frame,
            text="📐  Define OCR Area",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["warning"], hover_color="#cc8c0e",
            height=36, corner_radius=8,
            command=self.define_area,
        )
        self.btn_define_area.pack(expand=True)

        # ── Desired Stats ──
        stats_card = ctk.CTkFrame(scroll, corner_radius=8)
        stats_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(stats_card, "⚙️  Desired Stats", _A["success"])

        stats_body = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_body.pack(fill=tk.X, padx=12, pady=8)

        offensive_skills = [""] + get_offensive_skills()
        defensive_skills = [""] + get_defensive_skills()

        # Offensive 1
        self.off_stat = tk.StringVar()
        self.off_var = tk.StringVar()
        self.off_stat_dropdown, self.off_var_dropdown = self._stat_row(
            stats_body, "Offensive:", offensive_skills, self.off_stat,
            self.off_var, self.update_off_variations,
        )
        # Offensive 2
        self.off_stat2 = tk.StringVar()
        self.off_var2 = tk.StringVar()
        self.off_stat2_dropdown, self.off_var2_dropdown = self._stat_row(
            stats_body, "Offensive 2:", offensive_skills, self.off_stat2,
            self.off_var2, self.update_off2_variations,
        )
        # Offensive 3
        self.off_stat3 = tk.StringVar()
        self.off_var3 = tk.StringVar()
        self.off_stat3_dropdown, self.off_var3_dropdown = self._stat_row(
            stats_body, "Offensive 3:", offensive_skills, self.off_stat3,
            self.off_var3, self.update_off3_variations,
        )
        # Defensive 1
        self.def_stat = tk.StringVar()
        self.def_var = tk.StringVar()
        self.def_stat_dropdown, self.def_var_dropdown = self._stat_row(
            stats_body, "Defensive:", defensive_skills, self.def_stat,
            self.def_var, self.update_def_variations,
        )
        # Defensive 2
        self.def_stat2 = tk.StringVar()
        self.def_var2 = tk.StringVar()
        self.def_stat2_dropdown, self.def_var2_dropdown = self._stat_row(
            stats_body, "Defensive 2:", defensive_skills, self.def_stat2,
            self.def_var2, self.update_def2_variations,
        )

        # Delay
        delay_row = ctk.CTkFrame(stats_body, fg_color="transparent")
        delay_row.pack(fill=tk.X, pady=(4, 0))

        ctk.CTkLabel(
            delay_row, text="Delay (ms):",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            width=100, anchor="w",
        ).pack(side=tk.LEFT)

        self.delay_var = tk.StringVar(value="1000")
        self.delay_entry = ctk.CTkEntry(
            delay_row, textvariable=self.delay_var,
            width=90, height=28, font=ctk.CTkFont("Segoe UI", 11),
            placeholder_text="1000",
        )
        self.delay_entry.pack(side=tk.LEFT, padx=(6, 8))

        ctk.CTkLabel(
            delay_row, text="(between actions)",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=_A["muted"],
        ).pack(side=tk.LEFT)

        # ── Control buttons ──
        ctrl = ctk.CTkFrame(scroll, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(4, 8))

        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack()

        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  START",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["success"], hover_color="#258a5e",
            width=120, height=38, corner_radius=8,
            state="disabled", command=self.start_automation,
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_row, text="⏹  STOP",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["danger"], hover_color="#c9302c",
            width=120, height=38, corner_radius=8,
            state="disabled", command=self.stop_automation,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_save_config = ctk.CTkButton(
            btn_row, text="💾  Save Config",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=_A["primary"], hover_color="#1a5a8e",
            width=130, height=38, corner_radius=8,
            command=self.save_config,
        )
        self.btn_save_config.pack(side=tk.LEFT)

    # ──────────────────────────────────────────────────────────
    # UI HELPER — Coordinate row
    # ──────────────────────────────────────────────────────────
    def _coord_row(self, parent, label_text, coord_var, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 6))

        ctk.CTkLabel(
            row, text=label_text,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            width=80, anchor="w",
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            row, textvariable=coord_var,
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=_A["primary"], anchor="w",
        ).pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)

        ctk.CTkButton(
            row, text="Set",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=_A["primary"], hover_color="#1a5a8e",
            width=60, height=28, corner_radius=6,
            command=command,
        ).pack(side=tk.RIGHT)

    # ──────────────────────────────────────────────────────────
    # UI HELPER — Stat dropdown row
    # ──────────────────────────────────────────────────────────
    def _stat_row(self, parent, label, options, stat_var, var_var, change_cb):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 6))

        ctk.CTkLabel(
            row, text=label,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            width=100, anchor="w",
        ).pack(side=tk.LEFT)

        # Use ttk.Combobox because CTkComboBox doesn't support readonly+var binding well
        stat_cb = ttk.Combobox(
            row, textvariable=stat_var,
            values=options, state="readonly",
            width=18, font=("Segoe UI", 10),
        )
        stat_cb.pack(side=tk.LEFT, padx=(6, 8))
        stat_cb.bind("<<ComboboxSelected>>", change_cb)

        ctk.CTkLabel(
            row, text="Min:",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 4))

        var_cb = ttk.Combobox(
            row, textvariable=var_var,
            state="readonly", width=8,
            font=("Segoe UI", 10),
        )
        var_cb.pack(side=tk.LEFT)

        return stat_cb, var_cb

    # ══════════════════════════════════════════════════════════
    # ALL BUSINESS LOGIC BELOW — COMPLETELY UNCHANGED
    # ══════════════════════════════════════════════════════════

    def set_apply_button(self):
        """Set the apply button coordinates."""
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the 'Apply' button in the game window.\n"
            "The coordinates will be captured automatically."
        )

        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.apply_button_coords = (rel_x, rel_y)
                    self.automation.set_apply_button(self.apply_button_coords)
                    self.apply_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Apply button set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def set_change_button(self):
        """Set the change button coordinates."""
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return

        messagebox.showinfo(
            "Instruction",
            "Click on the 'Change' button in the game window.\n"
            "The coordinates will be captured automatically."
        )

        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)

                if success:
                    self.change_button_coords = (rel_x, rel_y)
                    self.automation.set_change_button(self.change_button_coords)
                    self.change_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Change button set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def define_area(self):
        """Define the OCR area using the shared area selector."""
        def area_callback(area):
            self.area = area
            self.automation.set_area(area)
            self._check_enable_start()
            self.main_window.update_status(f"OCR area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        """Enable start button if apply, change, and area are configured."""
        if self.apply_button_coords and self.change_button_coords and self.area:
            self.btn_start.configure(state="normal")

    def save_config(self):
        """Save configuration to JSON file."""
        config_data = {
            "apply_button_coords": list(self.apply_button_coords) if self.apply_button_coords else None,
            "change_button_coords": list(self.change_button_coords) if self.change_button_coords else None,
            "area": list(self.area) if self.area else None,
            "off_stat": self.off_stat.get(),
            "off_var": self.off_var.get(),
            "off_stat2": self.off_stat2.get(),
            "off_var2": self.off_var2.get(),
            "off_stat3": self.off_stat3.get(),
            "off_var3": self.off_var3.get(),
            "def_stat": self.def_stat.get(),
            "def_var": self.def_var.get(),
            "def_stat2": self.def_stat2.get(),
            "def_var2": self.def_var2.get(),
            "delay_ms": self.delay_var.get(),
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Arrival Skill config saved successfully!")
            messagebox.showinfo("Config Saved", "Arrival Skill configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Arrival Skill config: {e}")

    def load_config(self):
        """Load configuration from JSON file."""
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("apply_button_coords"):
                self.apply_button_coords = tuple(data["apply_button_coords"])
                self.automation.set_apply_button(self.apply_button_coords)
                self.apply_coord_var.set(f"({self.apply_button_coords[0]}, {self.apply_button_coords[1]})")

            if data.get("change_button_coords"):
                self.change_button_coords = tuple(data["change_button_coords"])
                self.automation.set_change_button(self.change_button_coords)
                self.change_coord_var.set(f"({self.change_button_coords[0]}, {self.change_button_coords[1]})")

            if data.get("area"):
                self.area = tuple(data["area"])
                self.automation.set_area(self.area)

            if data.get("off_stat"):
                self.off_stat.set(data["off_stat"])
                self.update_off_variations()
                if data.get("off_var"):
                    self.off_var.set(data["off_var"])

            if data.get("off_stat2"):
                self.off_stat2.set(data["off_stat2"])
                self.update_off2_variations()
                if data.get("off_var2"):
                    self.off_var2.set(data["off_var2"])

            if data.get("off_stat3"):
                self.off_stat3.set(data["off_stat3"])
                self.update_off3_variations()
                if data.get("off_var3"):
                    self.off_var3.set(data["off_var3"])

            if data.get("def_stat"):
                self.def_stat.set(data["def_stat"])
                self.update_def_variations()
                if data.get("def_var"):
                    self.def_var.set(data["def_var"])

            if data.get("def_stat2"):
                self.def_stat2.set(data["def_stat2"])
                self.update_def2_variations()
                if data.get("def_var2"):
                    self.def_var2.set(data["def_var2"])

            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))

            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Arrival Skill config: {e}")

    def update_off_variations(self, event=None):
        selected_stat = self.off_stat.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var_dropdown['values'] = variations
            if variations:
                self.off_var.set(variations[0])
        else:
            self.off_var_dropdown['values'] = []
            self.off_var.set("")

    def update_off2_variations(self, event=None):
        selected_stat = self.off_stat2.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var2_dropdown['values'] = variations
            if variations:
                self.off_var2.set(variations[0])
        else:
            self.off_var2_dropdown['values'] = []
            self.off_var2.set("")

    def update_off3_variations(self, event=None):
        selected_stat = self.off_stat3.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.off_var3_dropdown['values'] = variations
            if variations:
                self.off_var3.set(variations[0])
        else:
            self.off_var3_dropdown['values'] = []
            self.off_var3.set("")

    def update_def_variations(self, event=None):
        selected_stat = self.def_stat.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.def_var_dropdown['values'] = variations
            if variations:
                self.def_var.set(variations[0])
        else:
            self.def_var_dropdown['values'] = []
            self.def_var.set("")

    def update_def2_variations(self, event=None):
        selected_stat = self.def_stat2.get()
        if selected_stat:
            variations = get_stat_variations(selected_stat)
            self.def_var2_dropdown['values'] = variations
            if variations:
                self.def_var2.set(variations[0])
        else:
            self.def_var2_dropdown['values'] = []
            self.def_var2.set("")

    def start_automation(self):
        """Start the arrival skill automation."""
        if not self.main_window.set_running_tool("Arrival Skill"):
            return

        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError("Delay must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return

        if not self.off_stat.get() and not self.off_stat2.get() and not self.off_stat3.get() and not self.def_stat.get() and not self.def_stat2.get():
            messagebox.showerror("Error", "Please specify at least one stat to look for.")
            self.main_window.clear_running_tool()
            return

        desired_stats = {'offensive': [], 'defensive': []}

        # Offensive stat 1
        stat_name = self.off_stat.get()
        if stat_name:
            variation = self.off_var.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} with minimum value {variation}")

        # Offensive stat 2
        stat_name = self.off_stat2.get()
        if stat_name:
            variation = self.off_var2.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 2) with minimum value {variation}")

        # Offensive stat 3
        stat_name = self.off_stat3.get()
        if stat_name:
            variation = self.off_var3.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                off_val = int(value_match.group(1))
                desired_stats['offensive'].append((stat_name, off_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 3) with minimum value {variation}")

        # Defensive stat 1
        stat_name = self.def_stat.get()
        if stat_name:
            variation = self.def_var.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                def_val = int(value_match.group(1))
                desired_stats['defensive'].append((stat_name, def_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} with minimum value {variation}")

        # Defensive stat 2
        stat_name = self.def_stat2.get()
        if stat_name:
            variation = self.def_var2.get()
            if not variation:
                messagebox.showerror("Error", f"Please select a minimum value for {stat_name}.")
                self.main_window.clear_running_tool()
                return
            value_match = re.search(r'(\d+)', variation)
            if value_match:
                def_val = int(value_match.group(1))
                desired_stats['defensive'].append((stat_name, def_val, variation))
                self.main_window.update_status(f"Looking for {stat_name} (option 2) with minimum value {variation}")

        self.automation.set_delay(delay_ms)

        if self.automation.start(desired_stats):
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Arrival skill automation started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        """Stop the arrival skill automation."""
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Arrival skill automation stopped")
        self.generate_summary("stopped")

    def emergency_stop(self):
        """Emergency stop the automation."""
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()

    def on_target_found(self):
        """Called when target stat is found."""
        self.generate_summary("target_found")

    def generate_summary(self, reason):
        """Generate and save summary to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arrival_summary_{timestamp}.txt"
            summaries_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            filepath = os.path.join(summaries_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("ARRIVAL SKILL AUTOMATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reason: {reason}\n")

                offensive_stats = []
                defensive_stats = []
                if self.off_stat.get():
                    offensive_stats.append(f"{self.off_stat.get()} (Min: {self.off_var.get()})")
                if self.off_stat2.get():
                    offensive_stats.append(f"{self.off_stat2.get()} (Min: {self.off_var2.get()})")
                if self.off_stat3.get():
                    offensive_stats.append(f"{self.off_stat3.get()} (Min: {self.off_var3.get()})")
                if self.def_stat.get():
                    defensive_stats.append(f"{self.def_stat.get()} (Min: {self.def_var.get()})")
                if self.def_stat2.get():
                    defensive_stats.append(f"{self.def_stat2.get()} (Min: {self.def_var2.get()})")

                f.write(f"Desired Offensive Stats: {', '.join(offensive_stats) if offensive_stats else 'None'}\n")
                f.write(f"Desired Defensive Stats: {', '.join(defensive_stats) if defensive_stats else 'None'}\n")
                f.write(f"Delay: {self.delay_var.get()}ms\n")

                total_rolls = sum(self.automation.stat_counter.values())
                if total_rolls > 0:
                    f.write("\nSTATISTICS ENCOUNTERED:\n")
                    for stat_key, count in sorted(self.automation.stat_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_rolls) * 100
                        f.write(f"  {stat_key}: {count} times ({percentage:.1f}%)\n")

                if self.automation.unmapped_ocr_counter:
                    f.write("\nUNMAPPED OCR DETECTIONS:\n")
                    for unmapped_key, count in sorted(self.automation.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_rolls) * 100 if total_rolls > 0 else 0
                        f.write(f"  {unmapped_key}: {count} times ({percentage:.1f}%)\n")

                f.write("\nAutomation completed.\n")

            self.main_window.update_status(f"Summary saved to: {filename}")
        except Exception as e:
            self.main_window.update_status(f"Failed to save summary: {str(e)}")
