# Stellar System tab — CustomTkinter rewrite
# All business logic preserved; only UI widgets changed.

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import mouse
import json
from data.stellar_data import get_stellar_options
from automation.stellar_automation import StellarAutomation
import os
from datetime import datetime
import sys

_A = {
    "primary": "#1f6aa5", "success": "#2fa572", "danger": "#d9534f",
    "warning": "#e8a317", "info": "#17a2b8", "purple": "#7c3aed",
    "surface2": "#333333", "muted": "#888888",
}


def _section_header(parent, title, color=None):
    color = color or _A["primary"]
    header = ctk.CTkFrame(parent, fg_color=color, corner_radius=0, height=32)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(
        header, text=title,
        font=ctk.CTkFont("Segoe UI", 11, "bold"),
        text_color="#ffffff", anchor="w",
    ).pack(side=tk.LEFT, padx=12, pady=4)


class StellarTab:
    def __init__(self, parent_frame, main_window):
        """Initialize the Stellar System tab."""
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = StellarAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core,
        )
        self.automation.set_target_found_callback(self.on_target_found)

        self.area = None
        self.imprint_button_coords = None
        self.match_mode_var = tk.StringVar(value="single")
        self.or_rows = []

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "stellar_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # Intro card
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        intro_inner = ctk.CTkFrame(intro, fg_color="transparent")
        intro_inner.pack(fill=tk.X, padx=12, pady=8)
        ctk.CTkLabel(intro_inner, text="⭐", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(intro_inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="STELLAR SYSTEM — Option Reroll", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="1) Set Imprint  •  2) Define Area  •  3) Configure  •  4) Start", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        # ── Imprint Coordinates ──
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Button Coordinates")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        row = ctk.CTkFrame(coord_body, fg_color="transparent")
        row.pack(fill=tk.X)
        ctk.CTkLabel(row, text="Imprint:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=80, anchor="w").pack(side=tk.LEFT)
        self.imprint_coord_var = tk.StringVar(value="Not set")
        ctk.CTkLabel(row, textvariable=self.imprint_coord_var, font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)
        ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=60, height=28, corner_radius=6, command=self.set_imprint_button).pack(side=tk.RIGHT)

        # ── Option Configuration ──
        option_card = ctk.CTkFrame(scroll, corner_radius=8)
        option_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(option_card, "⚙️  Option Configuration", _A["success"])
        option_body = ctk.CTkFrame(option_card, fg_color="transparent")
        option_body.pack(fill=tk.X, padx=12, pady=8)

        # Match mode (radio buttons)
        mode_row = ctk.CTkFrame(option_body, fg_color="transparent")
        mode_row.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(mode_row, text="Match mode:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        ctk.CTkRadioButton(mode_row, text="Single", variable=self.match_mode_var, value="single", font=ctk.CTkFont("Segoe UI", 11), command=self.update_match_mode).pack(side=tk.LEFT, padx=(6, 12))
        ctk.CTkRadioButton(mode_row, text="OR", variable=self.match_mode_var, value="or", font=ctk.CTkFont("Segoe UI", 11), command=self.update_match_mode).pack(side=tk.LEFT)

        # Single option
        self.single_option_frame = ctk.CTkFrame(option_body, fg_color="transparent")
        self.single_option_frame.pack(fill=tk.X, pady=(0, 6))
        ctk.CTkLabel(self.single_option_frame, text="Option:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.combo_option_name = ttk.Combobox(self.single_option_frame, values=get_stellar_options(), state="readonly", width=22, font=("Segoe UI", 10))
        self.combo_option_name.pack(side=tk.LEFT, padx=(6, 0))

        # OR options container (hidden by default)
        self.or_options_frame = ctk.CTkFrame(option_body, fg_color="transparent")
        # Don't pack yet — update_match_mode will handle visibility

        or_header = ctk.CTkFrame(self.or_options_frame, fg_color="transparent")
        or_header.pack(fill=tk.X)
        ctk.CTkLabel(or_header, text="OR stat constraints:", font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        ctk.CTkButton(or_header, text="+ Add stat", font=ctk.CTkFont("Segoe UI", 11), fg_color=_A["primary"], hover_color="#1a5a8e", width=90, height=26, corner_radius=6, command=self.add_or_constraint_row).pack(side=tk.RIGHT)

        self.or_rows_container = ctk.CTkFrame(self.or_options_frame, fg_color="transparent")
        self.or_rows_container.pack(fill=tk.X, pady=(4, 0))

        # Min value
        self.single_min_frame = ctk.CTkFrame(option_body, fg_color="transparent")
        self.single_min_frame.pack(fill=tk.X)
        ctk.CTkLabel(self.single_min_frame, text="Min value:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.entry_option_min_value = ctk.CTkEntry(self.single_min_frame, width=90, height=28, font=ctk.CTkFont("Segoe UI", 11), placeholder_text="optional")
        self.entry_option_min_value.pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(self.single_min_frame, text="(optional)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # ── Visual Effect ──
        effect_card = ctk.CTkFrame(scroll, corner_radius=8)
        effect_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(effect_card, "✨  Visual Effect", _A["warning"])
        effect_body = ctk.CTkFrame(effect_card, fg_color="transparent")
        effect_body.pack(fill=tk.X, padx=12, pady=8)

        delay_row = ctk.CTkFrame(effect_body, fg_color="transparent")
        delay_row.pack(fill=tk.X)
        ctk.CTkLabel(delay_row, text="Clear delay:", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=100, anchor="w").pack(side=tk.LEFT)
        self.entry_effect_delay = ctk.CTkEntry(delay_row, width=80, height=28, font=ctk.CTkFont("Segoe UI", 11))
        self.entry_effect_delay.pack(side=tk.LEFT, padx=(6, 8))
        self.entry_effect_delay.insert(0, "1000")
        ctk.CTkLabel(delay_row, text="ms (wait for effects)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # ── Define OCR Area ──
        area_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        area_frame.pack(fill=tk.X, pady=(0, 8))
        self.btn_define_area = ctk.CTkButton(area_frame, text="📐  Define OCR Area", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["purple"], hover_color="#6b2fc7", height=36, corner_radius=8, command=self.define_area)
        self.btn_define_area.pack(expand=True)

        # ── Controls ──
        ctrl = ctk.CTkFrame(scroll, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(4, 8))
        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack()

        self.btn_start = ctk.CTkButton(btn_row, text="▶  START", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["success"], hover_color="#258a5e", width=120, height=38, corner_radius=8, state="disabled", command=self.start_automation)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ctk.CTkButton(btn_row, text="⏹  STOP", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["danger"], hover_color="#c9302c", width=120, height=38, corner_radius=8, state="disabled", command=self.stop_automation)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_save_config = ctk.CTkButton(btn_row, text="💾  Save Config", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=130, height=38, corner_radius=8, command=self.save_config)
        self.btn_save_config.pack(side=tk.LEFT)

    # ══════════════════════════════════════════════════════════
    # ALL BUSINESS LOGIC BELOW — COMPLETELY UNCHANGED
    # ══════════════════════════════════════════════════════════

    def set_imprint_button(self):
        self.main_window.bot_core.start()
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return
        messagebox.showinfo("Instruction", "Click on the 'Imprint' button in the game window.\nThe coordinates will be captured automatically.")
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                pos = self.main_window.bot_core.wait_for_mouse_click(mouse, button='left')
                if not pos:
                    return
                x, y = pos
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                if success:
                    self.imprint_button_coords = (rel_x, rel_y)
                    self.automation.set_imprint_button(self.imprint_button_coords)
                    self.imprint_coord_var.set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"Imprint button set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        self.main_window.bot_core.register_thread("stellar-capture-imprint", capture_click, daemon=True)

    def define_area(self):
        self.main_window.bot_core.start()

        def area_callback(area):
            self.area = area
            self.automation.set_area(area)
            self._check_enable_start()
            self.main_window.update_status(f"Area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        if self.imprint_button_coords and self.area:
            self.btn_start.configure(state="normal")

    def save_config(self):
        or_rows_data = []
        for row in self.or_rows:
            or_rows_data.append({"option": row['combo'].get().strip(), "min_value": row['entry'].get().strip()})

        config_data = {
            "imprint_button_coords": list(self.imprint_button_coords) if self.imprint_button_coords else None,
            "area": list(self.area) if self.area else None,
            "match_mode": self.match_mode_var.get(),
            "single_option_name": self.combo_option_name.get().strip(),
            "single_option_min": self.entry_option_min_value.get().strip(),
            "or_rows": or_rows_data,
            "effect_delay_ms": self.entry_effect_delay.get().strip(),
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Stellar System config saved successfully!")
            messagebox.showinfo("Config Saved", "Stellar System configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Stellar System config: {e}")

    def load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("imprint_button_coords"):
                self.imprint_button_coords = tuple(data["imprint_button_coords"])
                self.automation.set_imprint_button(self.imprint_button_coords)
                self.imprint_coord_var.set(f"({self.imprint_button_coords[0]}, {self.imprint_button_coords[1]})")
            if data.get("area"):
                self.area = tuple(data["area"])
                self.automation.set_area(self.area)
            if data.get("match_mode"):
                self.match_mode_var.set(data["match_mode"])
                self.update_match_mode()
            if data.get("single_option_name"):
                self.combo_option_name.set(data["single_option_name"])
            if data.get("single_option_min") is not None:
                self.entry_option_min_value.delete(0, tk.END)
                self.entry_option_min_value.insert(0, str(data["single_option_min"]))
            if data.get("or_rows") and isinstance(data["or_rows"], list):
                for row in list(self.or_rows):
                    self.remove_or_constraint_row(row['frame'])
                for item in data["or_rows"]:
                    self.add_or_constraint_row(item.get("option", ""), str(item.get("min_value", "")))
            if data.get("effect_delay_ms"):
                self.entry_effect_delay.delete(0, tk.END)
                self.entry_effect_delay.insert(0, str(data["effect_delay_ms"]))
            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Stellar System config: {e}")

    def add_or_constraint_row(self, option_name="", min_value=""):
        row_frame = ctk.CTkFrame(self.or_rows_container, fg_color="transparent")
        row_frame.pack(fill=tk.X, pady=(0, 4))

        option_var = tk.StringVar(value=option_name)
        option_combo = ttk.Combobox(row_frame, textvariable=option_var, values=get_stellar_options(), state="readonly", width=22, font=("Segoe UI", 10))
        option_combo.pack(side=tk.LEFT, padx=(0, 6))

        ctk.CTkLabel(row_frame, text="Min:", font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        min_entry = ctk.CTkEntry(row_frame, width=70, height=26, font=ctk.CTkFont("Segoe UI", 11))
        min_entry.insert(0, min_value)
        min_entry.pack(side=tk.LEFT, padx=(0, 6))

        remove_btn = ctk.CTkButton(row_frame, text="✕", width=28, height=26, corner_radius=6, fg_color=_A["danger"], hover_color="#c9302c", font=ctk.CTkFont("Segoe UI", 11), command=lambda: self.remove_or_constraint_row(row_frame))
        remove_btn.pack(side=tk.LEFT)

        self.or_rows.append({'frame': row_frame, 'combo': option_combo, 'entry': min_entry})

    def remove_or_constraint_row(self, row_frame):
        for row in self.or_rows:
            if row['frame'] is row_frame:
                row_frame.destroy()
                self.or_rows.remove(row)
                break

    def get_selected_option_constraints(self):
        if self.match_mode_var.get() == "or":
            constraints = []
            for row in self.or_rows:
                name = row['combo'].get().strip()
                min_value = row['entry'].get().strip()
                if name:
                    constraints.append({'name': name, 'min_value': min_value})
            return constraints
        option_name = self.combo_option_name.get().strip()
        option_min_value = self.entry_option_min_value.get().strip()
        return [{'name': option_name, 'min_value': option_min_value}] if option_name else []

    def get_selected_option_names(self):
        return [c['name'] for c in self.get_selected_option_constraints()]

    def format_selected_constraints(self):
        constraints = self.get_selected_option_constraints()
        return ", ".join(f"{c['name']} ({c['min_value']})" if c['min_value'] else c['name'] for c in constraints)

    def update_match_mode(self):
        if self.match_mode_var.get() == "or":
            self.single_option_frame.pack_forget()
            self.single_min_frame.pack_forget()
            self.or_options_frame.pack(fill=tk.X, pady=(0, 4))
            if not self.or_rows:
                self.add_or_constraint_row()
            self.combo_option_name.config(state=tk.DISABLED)
            self.entry_option_min_value.configure(state="disabled")
        else:
            self.or_options_frame.pack_forget()
            self.single_option_frame.pack(fill=tk.X, pady=(0, 6))
            self.single_min_frame.pack(fill=tk.X)
            self.combo_option_name.config(state="readonly")
            self.entry_option_min_value.configure(state="normal")

    def start_automation(self):
        if not self.main_window.set_running_tool("Stellar System", automation=self.automation):
            return
        effect_delay = self.entry_effect_delay.get().strip()
        constraints = self.get_selected_option_constraints()
        if not constraints:
            if self.match_mode_var.get() == "single":
                messagebox.showwarning("Missing Option", "Please select an option name.")
            else:
                messagebox.showwarning("Missing Options", "Please add one or more OR stat constraints.")
            self.main_window.clear_running_tool()
            return
        try:
            effect_delay_ms = int(effect_delay) if effect_delay else 1000
            if effect_delay_ms < 0:
                effect_delay_ms = 1000
        except ValueError:
            effect_delay_ms = 1000
        self.automation.set_effect_delay(effect_delay_ms)
        if self.automation.start(constraints):
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Stellar automation started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Stellar automation stopped")
        self.generate_summary("stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()

    def on_target_found(self):
        self.generate_summary("target_found")

    def generate_summary(self, reason):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stellar_summary_{timestamp}.txt"
            summaries_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            filepath = os.path.join(summaries_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("STELLAR SYSTEM AUTOMATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Option(s): {self.format_selected_constraints()}\n")
                f.write(f"Effect Delay: {self.entry_effect_delay.get()}ms\n")
                f.write(f"Wrong Read Counter: {self.automation.wrong_read_counter}\n")
                total_attempts = sum(self.automation.stat_counter.values()) + self.automation.wrong_read_counter
                if total_attempts > 0:
                    success_rate = ((total_attempts - self.automation.wrong_read_counter) / total_attempts) * 100
                    error_rate = (self.automation.wrong_read_counter / total_attempts) * 100
                    f.write("\nOVERALL PERCENTAGES:\n")
                    f.write(f"Success Rate: {success_rate:.1f}%\n")
                    f.write(f"Error Rate: {error_rate:.1f}%\n")
                if self.automation.stat_counter:
                    f.write("\nDETECTED VALUES STATISTICS:\n")
                    target_value = None
                    if self.entry_option_min_value.get().isdigit():
                        target_value = int(self.entry_option_min_value.get())
                    for value_str, count in sorted(self.automation.stat_counter.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True):
                        percentage = (count / total_attempts) * 100 if total_attempts > 0 else 0
                        status = ""
                        if target_value is not None and value_str.isdigit():
                            value_int = int(value_str)
                            if value_int >= target_value:
                                status = " ✓ TARGET MET"
                            else:
                                status = " ✗ BELOW TARGET"
                        f.write(f"  Value {value_str}: {count} times ({percentage:.1f}%){status}\n")
                if self.automation.unmapped_ocr_counter:
                    f.write("\nOTHER DETECTED OPTIONS:\n")
                    for text_key, count in sorted(self.automation.unmapped_ocr_counter.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_attempts) * 100 if total_attempts > 0 else 0
                        f.write(f"  '{text_key}': {count} times ({percentage:.1f}%)\n")
                f.write("\nAutomation completed.\n")
            self.main_window.update_status(f"Summary saved to: {filename}")
        except Exception as e:
            self.main_window.update_status(f"Failed to save summary: {str(e)}")