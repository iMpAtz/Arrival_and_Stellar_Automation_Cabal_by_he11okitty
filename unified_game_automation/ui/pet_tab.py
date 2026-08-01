# Pet Untrain tab — CustomTkinter rewrite
# All business logic preserved; only UI widgets changed.

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import mouse
import json
import os
import sys
from data.pet_data import get_pet_untrain_steps, get_default_pet_delay, get_pet_ocr_options
from automation.pet_automation import PetAutomation

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
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color="#ffffff", anchor="w").pack(side=tk.LEFT, padx=12, pady=4)


class PetTab:
    def __init__(self, parent_frame, main_window):
        self.parent_frame = parent_frame
        self.main_window = main_window

        self.automation = PetAutomation(
            main_window.game_connector,
            main_window.ocr_engine,
            main_window.update_status,
            main_window.bot_core,
        )

        # Coordinate storage
        self.step_coords = {step: None for step in get_pet_untrain_steps()}
        self.ocr_area = None
        self.ocr_targets = []
        self.selected_ocr_options = {}

        self.create_ui()
        self.load_config()

    def _get_config_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "pet_config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    # ──────────────────────────────────────────────────────────
    def create_ui(self):
        scroll = ctk.CTkScrollableFrame(self.parent_frame, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True)

        # Intro
        intro = ctk.CTkFrame(scroll, corner_radius=8, fg_color=("#dbeafe", "#1e2a3a"))
        intro.pack(fill=tk.X, pady=(0, 8))
        inner = ctk.CTkFrame(intro, fg_color="transparent")
        inner.pack(fill=tk.X, padx=12, pady=8)
        ctk.CTkLabel(inner, text="🐾", font=ctk.CTkFont("Segoe UI", 16)).pack(side=tk.LEFT, padx=(0, 8))
        tf = ctk.CTkFrame(inner, fg_color="transparent")
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkLabel(tf, text="PET UNTRAIN — Automated Pet Skill Reroll", font=ctk.CTkFont("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        ctk.CTkLabel(tf, text="1) Set Positions  •  2) Define OCR Area  •  3) Select Skills  •  4) Start", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"], anchor="w").pack(fill=tk.X)

        # Step coordinates
        coord_card = ctk.CTkFrame(scroll, corner_radius=8)
        coord_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(coord_card, "📍  Step Positions")
        coord_body = ctk.CTkFrame(coord_card, fg_color="transparent")
        coord_body.pack(fill=tk.X, padx=12, pady=8)

        self.step_coord_vars = {}
        steps = get_pet_untrain_steps()
        for step in steps:
            self.step_coord_vars[step] = tk.StringVar(value="Not set")
            row = ctk.CTkFrame(coord_body, fg_color="transparent")
            row.pack(fill=tk.X, pady=(0, 4))
            ctk.CTkLabel(row, text=f"{step}:", font=ctk.CTkFont("Segoe UI", 11, "bold"), anchor="w").pack(side=tk.LEFT)
            ctk.CTkLabel(row, textvariable=self.step_coord_vars[step], font=ctk.CTkFont("Segoe UI", 11), text_color=_A["primary"], anchor="w").pack(side=tk.LEFT, padx=(6, 8), fill=tk.X, expand=True)
            ctk.CTkButton(row, text="Set", font=ctk.CTkFont("Segoe UI", 11, "bold"), fg_color=_A["primary"], hover_color="#1a5a8e", width=60, height=28, corner_radius=6, command=lambda s=step: self.set_step_position(s)).pack(side=tk.RIGHT)

        # OCR area
        ocr_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ocr_frame.pack(fill=tk.X, pady=(0, 8))
        self.btn_define_area = ctk.CTkButton(ocr_frame, text="📐  Define OCR Area", font=ctk.CTkFont("Segoe UI", 12, "bold"), fg_color=_A["purple"], hover_color="#6b2fc7", height=36, corner_radius=8, command=self.define_ocr_area)
        self.btn_define_area.pack(expand=True)

        # OCR Target selection (checkbox grid)
        target_card = ctk.CTkFrame(scroll, corner_radius=8)
        target_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(target_card, "🎯  OCR Target Skills (select desired)", _A["success"])
        target_body = ctk.CTkFrame(target_card, fg_color="transparent")
        target_body.pack(fill=tk.X, padx=12, pady=8)

        ocr_options = get_pet_ocr_options()
        self.ocr_check_vars = {}
        # 2-column grid
        for i, opt in enumerate(ocr_options):
            r = i // 2
            c = i % 2
            var = tk.BooleanVar(value=False)
            self.ocr_check_vars[opt] = var
            cb = ctk.CTkCheckBox(
                target_body, text=opt,
                variable=var,
                font=ctk.CTkFont("Segoe UI", 11),
                corner_radius=4,
                checkbox_width=20, checkbox_height=20,
                onvalue=True, offvalue=False,
            )
            cb.grid(row=r, column=c, sticky="w", padx=(0, 16), pady=2)

        # Delay
        delay_card = ctk.CTkFrame(scroll, corner_radius=8)
        delay_card.pack(fill=tk.X, pady=(0, 8))
        _section_header(delay_card, "⏱️  Delay Settings", _A["warning"])
        delay_body = ctk.CTkFrame(delay_card, fg_color="transparent")
        delay_body.pack(fill=tk.X, padx=12, pady=8)

        delay_row = ctk.CTkFrame(delay_body, fg_color="transparent")
        delay_row.pack(fill=tk.X)
        ctk.CTkLabel(delay_row, text="Delay (ms):", font=ctk.CTkFont("Segoe UI", 11, "bold"), width=90, anchor="w").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value=str(get_default_pet_delay()))
        self.delay_entry = ctk.CTkEntry(delay_row, textvariable=self.delay_var, width=90, height=28, font=ctk.CTkFont("Segoe UI", 11), placeholder_text="800")
        self.delay_entry.pack(side=tk.LEFT, padx=(6, 8))
        ctk.CTkLabel(delay_row, text="(delay between actions)", font=ctk.CTkFont("Segoe UI", 10), text_color=_A["muted"]).pack(side=tk.LEFT)

        # Controls
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
    # BUSINESS LOGIC — UNCHANGED
    # ══════════════════════════════════════════════════════════

    def set_step_position(self, step_name):
        if not self.main_window.game_connector.is_connected():
            if not self.main_window.game_connector.connect_to_game():
                messagebox.showerror("Error", "Could not connect to the game window. Make sure the game is running.")
                return
        messagebox.showinfo("Instruction", f"Click on '{step_name}' in the game window.\nThe coordinates will be captured automatically.")
        self.main_window.root.config(cursor="crosshair")

        def capture_click():
            try:
                mouse.wait(button='left')
                x, y = mouse.get_position()
                rel_x, rel_y, success = self.main_window.game_connector.convert_to_window_coords(x, y)
                if success:
                    self.step_coords[step_name] = (rel_x, rel_y)
                    self.automation.set_step_coords(step_name, (rel_x, rel_y))
                    self.step_coord_vars[step_name].set(f"({rel_x}, {rel_y})")
                    self.main_window.update_status(f"'{step_name}' set at ({rel_x}, {rel_y})")
                    self._check_enable_start()
                else:
                    messagebox.showerror("Error", "Failed to convert coordinates")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to capture click: {str(e)}")
            finally:
                self.main_window.root.config(cursor="")

        threading.Thread(target=capture_click, daemon=True).start()

    def define_ocr_area(self):
        def area_callback(area):
            self.ocr_area = area
            self.automation.set_ocr_area(area)
            self._check_enable_start()
            self.main_window.update_status(f"OCR area defined: {area}")

        if not hasattr(self.main_window, 'area_selector'):
            from core.area_selector import AreaSelector
            self.main_window.area_selector = AreaSelector(self.main_window.root, area_callback)
        else:
            self.main_window.area_selector.callback = area_callback
        self.main_window.area_selector.select_area()

    def _check_enable_start(self):
        all_set = all(coords is not None for coords in self.step_coords.values())
        if all_set and self.ocr_area:
            self.btn_start.configure(state="normal")

    def _get_selected_ocr_targets(self):
        targets = []
        for opt, var in self.ocr_check_vars.items():
            if var.get():
                targets.append(opt)
        return targets

    def save_config(self):
        config_data = {
            "step_coords": {k: list(v) if v else None for k, v in self.step_coords.items()},
            "ocr_area": list(self.ocr_area) if self.ocr_area else None,
            "delay_ms": self.delay_var.get(),
            "selected_ocr_options": [opt for opt, var in self.ocr_check_vars.items() if var.get()],
        }
        try:
            path = self._get_config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.main_window.update_status("Pet Untrain config saved successfully!")
            messagebox.showinfo("Config Saved", "Pet Untrain configuration has been saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save Pet Untrain config: {e}")

    def load_config(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("step_coords"):
                for step, coords in data["step_coords"].items():
                    if coords and step in self.step_coords:
                        self.step_coords[step] = tuple(coords)
                        self.automation.set_step_coords(step, tuple(coords))
                        if step in self.step_coord_vars:
                            self.step_coord_vars[step].set(f"({coords[0]}, {coords[1]})")
            if data.get("ocr_area"):
                self.ocr_area = tuple(data["ocr_area"])
                self.automation.set_ocr_area(self.ocr_area)
            if data.get("delay_ms"):
                self.delay_var.set(str(data["delay_ms"]))
            if data.get("selected_ocr_options"):
                for opt in data["selected_ocr_options"]:
                    if opt in self.ocr_check_vars:
                        self.ocr_check_vars[opt].set(True)
            self._check_enable_start()
        except Exception as e:
            print(f"Failed to load Pet Untrain config: {e}")

    def start_automation(self):
        if not self.main_window.set_running_tool("Pet Untrain"):
            return
        try:
            delay_ms = int(self.delay_var.get())
            if delay_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay in milliseconds (positive integer).")
            self.main_window.clear_running_tool()
            return

        ocr_targets = self._get_selected_ocr_targets()
        if not ocr_targets:
            messagebox.showwarning("Warning", "Please select at least one OCR target skill to search for.")
            self.main_window.clear_running_tool()
            return

        self.automation.set_delay(delay_ms)
        self.automation.set_ocr_targets(ocr_targets)

        if self.automation.start():
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.main_window.update_status("Pet Untrain automation started")
        else:
            self.main_window.clear_running_tool()

    def stop_automation(self):
        self.automation.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()
        self.main_window.update_status("Pet Untrain automation stopped")

    def emergency_stop(self):
        self.automation.emergency_stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.main_window.clear_running_tool()